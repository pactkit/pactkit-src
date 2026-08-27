"""STORY-slim-138: pre-commit test gate.

Two interception channels share one decision pipeline:
  - Claude Code PreToolUse hook: `pactkit commit-gate --hook` (stdin JSON,
    exit 2 = block, per Claude Code hook contract)
  - git pre-commit hook: `pactkit commit-gate` (exit 1 = block)

The pipeline: collect changed files -> regression classification -> minimal
test set via test-map -> run pytest -rs -> report passed/failed/skipped
separately (skip != pass transparency, R2).

Self-lock protection (R3): any failure of the gate itself (no pytest, parse
errors, timeouts) exits 0 with a loud WARN — a gate that blocks the commit
fixing the gate is worse than a gate that warns.
"""

import json
import os
import re
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

# Branches where direct commits always trigger the full unit suite (R1)
MAIN_BRANCHES = frozenset({"main", "master", "develop"})

# Any skip count above this emits an explicit WARN listing (R2). Zero by
# default: every skip is reported, never silently absorbed into "green".
SKIP_WARN_THRESHOLD = 0

PYTEST_TIMEOUT_SECONDS = 600

# Git exports these repository-specific variables while running hooks.  They
# must not leak into pytest because tests may create and operate on their own
# temporary repositories.
GIT_REPOSITORY_ENV_VARS = frozenset({
    "GIT_DIR",
    "GIT_INDEX_FILE",
    "GIT_WORK_TREE",
})

# Hook command matching: git commit with any flag ordering (git -C x commit …)
_GIT_COMMIT_RE = re.compile(r"\bgit\s+(?:-\S+\s+\S+\s+|-\S+\s+)*commit\b")

_SUMMARY_RE = re.compile(r"(\d+)\s+(failed|passed|skipped|errors?|deselected)")
_SKIPPED_RE = re.compile(r"^SKIPPED\b.*", re.MULTILINE)

HOOK_COMMAND = "pactkit commit-gate --hook"


@dataclass
class GateResult:
    lines: list[str] = field(default_factory=list)
    exit_code: int = 0

    def render(self) -> str:
        return "\n".join(self.lines)


# ---------------------------------------------------------------------------
# Environment probes (isolated for test mocking)
# ---------------------------------------------------------------------------


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=30,
        )
        return proc.returncode, proc.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


class GitCollectionError(Exception):
    """git collection failed — the gate must block, not masquerade as skip."""


def collect_changed_files(root: Path) -> list[str]:
    """Staged + worktree changes + untracked files (what a commit would include).

    A nonzero git exit code is a collection failure, not evidence of an
    empty change set (STORY-slim-20260826ce35b77ce005 R5).  The single
    exception is a repo with no commits yet: ``git diff HEAD`` has nothing
    to diff against, which is a benign known state, not a probe failure —
    staged + untracked probes still cover the full initial change set.
    """
    seen: set[str] = set()
    probes = [
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ]
    head_code, _ = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    if head_code == 0:
        probes.insert(1, ("diff", "HEAD", "--name-only"))
    for args in probes:
        code, out = _git(root, *args)
        if code != 0:
            raise GitCollectionError(
                f"git {' '.join(args)} failed (exit {code}) — cannot collect changes"
            )
        seen.update(ln.strip() for ln in out.splitlines() if ln.strip())
    return sorted(seen)


def current_branch(root: Path) -> str:
    code, out = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if code == 0 else ""


def _pytest_command(root: Path) -> list[str]:
    """Venv-aware pytest command (shared single source in utils.py)."""
    from pactkit.utils import pytest_command

    return pytest_command(root)


def run_pytest(root: Path, test_files: list[str] | None) -> tuple[int, str]:
    """Run pytest -rs (unit only); returns (returncode, combined output)."""
    cmd = [*_pytest_command(root), "-rs", "-q"]
    if test_files:
        cmd.extend(test_files)
    else:
        cmd.append("tests/unit/")
    env = os.environ.copy()
    for key in GIT_REPOSITORY_ENV_VARS:
        env.pop(key, None)
    try:
        proc = subprocess.run(
            cmd, cwd=root, capture_output=True, text=True,
            timeout=PYTEST_TIMEOUT_SECONDS, env=env,
        )
        return proc.returncode, proc.stdout + proc.stderr
    except FileNotFoundError:
        raise GateUnavailable("pytest not found")
    except subprocess.TimeoutExpired:
        raise GateUnavailable(f"pytest exceeded {PYTEST_TIMEOUT_SECONDS}s")


class GateUnavailable(Exception):
    """The gate itself cannot run — caller degrades to WARN + pass (R3)."""


# ---------------------------------------------------------------------------
# Decision pipeline
# ---------------------------------------------------------------------------


def decide_test_set(root: Path, changed: list[str]) -> tuple[str, list[str] | None, str]:
    """Returns (strategy, test_files|None, reason). None = full unit suite."""
    from pactkit.regression import classify_changes

    branch = current_branch(root)
    if branch in MAIN_BRANCHES:
        return "full", None, f"direct commit on {branch} — full unit suite"

    strategy, reason = classify_changes(changed)
    if strategy != "impact":
        return strategy, None if strategy == "full" else [], reason

    from pactkit.test_mapper import map_to_tests

    mapped = map_to_tests(changed, root).get("mapped", [])
    existing = [t for t in mapped if (root / t).exists()]
    if not existing:
        return "full", None, "impact mapping empty — full unit suite (safe default)"
    return "impact", existing, f"{len(existing)} mapped test file(s)"


def parse_pytest_summary(output: str) -> dict:
    """Extract passed/failed/skipped counts and skip reasons from -rs output."""
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    for num, kind in _SUMMARY_RE.findall(output):
        key = {"error": "errors", "errors": "errors"}.get(kind, kind)
        if key in counts:
            counts[key] += int(num)
    counts["skip_reasons"] = _SKIPPED_RE.findall(output)
    return counts


# ---------------------------------------------------------------------------
# Gate entry points
# ---------------------------------------------------------------------------


def run_gate(root: Path) -> GateResult:
    """The shared decision pipeline. exit 1 = block, 0 = allow."""
    from pactkit.enforcement import DEGRADED, FULL, UNAVAILABLE, record_attempt, record_status

    # Attempt fence (STORY-slim-20260827eddbe9669c87 R3): opened before the
    # gate runs, closed by every terminal record_status below.  A crash in
    # between leaves the verdict unknowable — resume reports it as
    # outcome unknown until the gate is re-run.
    try:
        record_attempt(root, "commit_gate")
    except Exception:  # noqa: BLE001 - the fence is best-effort, never blocks
        pass

    result = GateResult()
    try:
        if not (root / ".git").exists():
            result.lines.append("[WARN] commit-gate: not a git repository — skipped")
            record_status(root, "commit_gate", UNAVAILABLE, "not a git repository — skipped")
            return result

        changed = collect_changed_files(root)
        strategy, test_files, reason = decide_test_set(root, changed)
        result.lines.append(f"commit-gate: {strategy.upper()} — {reason}")

        if strategy == "skip":
            record_status(root, "commit_gate", FULL, f"strategy=skip ({reason})")
            return result

        returncode, output = run_pytest(root, test_files)
        summary = parse_pytest_summary(output)
        result.lines.append(
            f"tests: {summary['passed']} passed, {summary['failed']} failed, "
            f"{summary['skipped']} skipped, {summary['errors']} errors"
        )

        if summary["skipped"] > SKIP_WARN_THRESHOLD:
            result.lines.append(f"[WARN] {summary['skipped']} test(s) SKIPPED — skip != pass:")
            result.lines.extend(f"  {line}" for line in summary["skip_reasons"][:20])

        if returncode != 0:
            result.lines.append("[FAIL] tests are RED — commit blocked (R5: fix is yours, not the gate's)")
            tail = [ln for ln in output.splitlines() if ln.startswith(("FAILED", "ERROR"))][:10]
            result.lines.extend(f"  {ln}" for ln in tail)
            result.exit_code = 1
        record_status(root, "commit_gate", FULL, "")
        return result

    except GitCollectionError as exc:
        result.lines.append(f"[FAIL] commit-gate: COLLECTION-FAILED — {exc}")
        result.exit_code = 1
        # Fail-closed: collection failure blocks the commit, so the gate
        # still enforced its contract.
        record_status(root, "commit_gate", FULL, f"collection failure blocked (fail-closed): {exc}")
        return result
    except GateUnavailable as exc:
        result.lines.append(f"[WARN] commit-gate unavailable ({exc}) — allowing commit")
        record_status(root, "commit_gate", UNAVAILABLE, str(exc))
        return result
    except Exception as exc:  # R3 self-lock protection
        result.lines.append(f"[WARN] commit-gate internal error ({type(exc).__name__}: {exc}) — allowing commit")
        record_status(root, "commit_gate", DEGRADED, f"internal error ({type(exc).__name__}): {exc}")
        return result


def hook_entry(stdin_text: str, root: Path) -> tuple[str, int]:
    """PreToolUse hook mode. Returns (stderr_message, exit_code).

    Claude Code hook contract: exit 2 = block (stderr shown to the agent),
    exit 0 = allow. Non-commit commands exit 0 without running anything.
    Gate-internal failures always exit 0 (R3 self-lock protection).

    Codex CLI uses the same wire contract (tool_name "Bash", exit 2 +
    stderr block); its legacy shell tool may pass the command as an
    array, and both hosts serialize the session cwd into the payload
    (STORY-slim-20260827024e71df170f R4).
    """
    try:
        payload = json.loads(stdin_text or "{}")
    except json.JSONDecodeError:
        return "", 0
    if not isinstance(payload, dict):
        return "", 0
    raw_command = (payload.get("tool_input") or {}).get("command") or ""
    if isinstance(raw_command, list):  # legacy codex shell tool form
        command = " ".join(str(part) for part in raw_command)
    else:
        command = str(raw_command)
    if not _GIT_COMMIT_RE.search(command):
        return "", 0
    if "--no-verify" in command:
        return "", 0  # explicit human bypass — done-verify catches it at archive time

    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        candidate = Path(cwd)
        if candidate.is_dir():
            root = candidate

    result = run_gate(root)
    if result.exit_code != 0:
        return result.render(), 2
    # Surface WARN lines (e.g. skips) even when allowing
    warns = [ln for ln in result.lines if ln.startswith("[WARN]") or ln.startswith("  SKIPPED")]
    return "\n".join(warns), 0


# ---------------------------------------------------------------------------
# Hook deployment (R4)
# ---------------------------------------------------------------------------


def _no_git_enabled(root: Path) -> bool:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from pactkit.config import load_config

        cfg = load_config(root / ".claude" / "pactkit.yaml")
    enterprise = cfg.get("enterprise", {})
    return isinstance(enterprise, dict) and bool(enterprise.get("no_git"))


def install_hook(root: Path) -> str:
    """Merge the PreToolUse hook into .claude/settings.json (idempotent).

    Preserves all existing user configuration; updates pactkit's own entry
    in place on repeat installs. Skipped entirely under enterprise.no_git.
    """
    if _no_git_enabled(root):
        return "commit-gate hook: skipped (enterprise.no_git)"

    settings_path = root / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return f"commit-gate hook: {settings_path} is not valid JSON — left untouched"
    else:
        settings = {}
    if not isinstance(settings, dict):
        return f"commit-gate hook: {settings_path} has unexpected shape — left untouched"

    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])
    entry = {"matcher": "Bash", "hooks": [{"type": "command", "command": HOOK_COMMAND}]}

    for i, existing in enumerate(pre_tool):
        cmds = [h.get("command", "") for h in existing.get("hooks", []) if isinstance(h, dict)]
        if any("commit-gate" in c for c in cmds):
            pre_tool[i] = entry  # idempotent refresh of our own entry
            break
    else:
        pre_tool.append(entry)

    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f"commit-gate hook: installed in {settings_path}"


@contextmanager
def _hooks_json_lock(root: Path, timeout: float = 5.0):
    """Best-effort inter-process lock for hooks.json merges (session QA P3).

    Concurrent deploys in one project could otherwise lose a user hook
    added between read and write.  On timeout the merge proceeds unlocked
    — it is idempotent, and deployment must never hang on a stale lock.
    """
    import time as _time

    lock_path = root / ".codex" / ".hooks.json.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    acquired = False
    deadline = _time.monotonic() + timeout
    try:
        while not acquired:
            try:
                if os.name == "nt":  # pragma: no cover - exercised on Windows CI
                    import msvcrt

                    if handle.tell() == 0:
                        handle.write(b"0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
            except (BlockingIOError, PermissionError, OSError):
                if _time.monotonic() >= deadline:
                    break  # proceed unlocked — see docstring
                _time.sleep(0.05)
        yield
    finally:
        if acquired:
            try:
                if os.name == "nt":  # pragma: no cover - exercised on Windows CI
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def install_codex_hook(root: Path) -> str:
    """Merge the PreToolUse hook into the project's .codex/hooks.json (idempotent).

    Thin registration into Codex's native hooks engine
    (STORY-slim-20260827024e71df170f R4): the wire contract matches Claude
    Code (tool_name "Bash", exit 2 + stderr block), so the handler reuses
    `pactkit commit-gate --hook` unchanged. The hook needs a one-time
    content-hash trust confirmation inside Codex before it takes effect —
    deployment never activates it silently, and an existing config.toml is
    never touched (hooks.json is a separate, Codex-discovered file).

    User entries are preserved verbatim; pactkit refreshes only its own
    entry, identified by the commit-gate command string.  A file whose
    existing structure cannot be merged (invalid JSON, non-object root,
    ``hooks`` non-dict, ``PreToolUse`` non-list) is left byte-identical.
    """
    if _no_git_enabled(root):
        return "codex hook: skipped (enterprise.no_git)"

    hooks_path = root / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    trust_notice = (
        " — needs one-time trust confirmation inside Codex "
        "(content-hash prompt) before it takes effect"
    )
    if hooks_path.exists():
        try:
            payload = json.loads(hooks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return f"codex hook: {hooks_path} is not valid JSON — left untouched"
        if not isinstance(payload, dict):
            return f"codex hook: {hooks_path} has unexpected shape — left untouched"
    else:
        payload = {}

    hooks = payload.get("hooks")
    if "hooks" in payload and not isinstance(hooks, dict):
        return f"codex hook: {hooks_path} hooks has unexpected shape — left untouched"
    if not isinstance(hooks, dict):
        hooks = {}
        payload["hooks"] = hooks
    pre_tool = hooks.get("PreToolUse")
    if "PreToolUse" in hooks and not isinstance(pre_tool, list):
        return f"codex hook: {hooks_path} PreToolUse has unexpected shape — left untouched"
    if not isinstance(pre_tool, list):
        pre_tool = []
        hooks["PreToolUse"] = pre_tool
    entry = {"matcher": "Bash", "hooks": [{"type": "command", "command": HOOK_COMMAND}]}

    with _hooks_json_lock(root):
        for i, existing in enumerate(pre_tool):
            if not isinstance(existing, dict):
                continue
            cmds = [
                h.get("command", "")
                for h in existing.get("hooks", [])
                if isinstance(h, dict)
            ]
            if any("commit-gate" in c for c in cmds):
                pre_tool[i] = entry  # idempotent refresh of our own entry
                hooks_path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return f"codex hook: already installed in {hooks_path}{trust_notice}"
        pre_tool.append(entry)
        hooks_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
        )
    return f"codex hook: installed in {hooks_path}{trust_notice}"


def install_git_hook(root: Path) -> str:
    """Write .git/hooks/pre-commit as a thin wrapper around the CLI."""
    if _no_git_enabled(root):
        return "git pre-commit hook: skipped (enterprise.no_git)"
    hooks_dir = root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        return "git pre-commit hook: not a git repository — skipped"
    hook = hooks_dir / "pre-commit"
    script = "#!/bin/sh\n# pactkit commit-gate (STORY-slim-138)\nexec pactkit commit-gate\n"
    if hook.exists():
        existing = hook.read_text(encoding="utf-8", errors="replace")
        if "commit-gate" in existing:
            return f"git pre-commit hook: already installed at {hook}"  # idempotent no-op
        backup = hook.with_suffix(".pre-pactkit")
        backup.write_bytes(hook.read_bytes())
        chain = existing.rstrip("\n") + "\n\npactkit commit-gate || exit 1\n"
        hook.write_text(chain, encoding="utf-8")
        hook.chmod(0o755)
        return f"git pre-commit hook: chained onto existing hook (backup: {backup.name})"
    hook.write_text(script, encoding="utf-8")
    hook.chmod(0o755)
    return f"git pre-commit hook: installed at {hook}"


# ---------------------------------------------------------------------------
# Format-aware channel dispatch (STORY-slim-140)
# ---------------------------------------------------------------------------

# Formats whose runtime reads .claude/settings.json PreToolUse hooks
_PRETOOLUSE_FORMATS = frozenset({"all", "classic"})


def _codex_hook_present(root: Path) -> bool:
    hooks_path = root / ".codex" / "hooks.json"
    if not hooks_path.exists():
        return False
    try:
        payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    entries = payload.get("hooks", {})
    if not isinstance(entries, dict):
        return False
    pre_tool = entries.get("PreToolUse", [])
    return any(
        "commit-gate" in h.get("command", "")
        for e in pre_tool if isinstance(e, dict)
        for h in e.get("hooks", []) if isinstance(h, dict)
    )


def gate_channel(root: Path) -> str:
    """Report the currently active commit-gate channel for status output (R2)."""
    if _no_git_enabled(root):
        return "none (enterprise.no_git)"
    channels: list[str] = []
    settings = root / ".claude" / "settings.json"
    if settings.exists():
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
            entries = data.get("hooks", {}).get("PreToolUse", [])
            if any("commit-gate" in h.get("command", "")
                   for e in entries for h in e.get("hooks", []) if isinstance(h, dict)):
                channels.append("PreToolUse hook")
        except json.JSONDecodeError:
            pass
    if _codex_hook_present(root):
        channels.append("codex PreToolUse hook")
    hook = root / ".git" / "hooks" / "pre-commit"
    if hook.exists() and "commit-gate" in hook.read_text(encoding="utf-8", errors="replace"):
        channels.append("git pre-commit")
    if channels:
        return " + ".join(channels)
    return "none"


def ensure_gate_channel(root: Path, format_name: str) -> str:
    """Install the appropriate commit-gate channel for the deployed format.

    STORY-slim-140 R1: classic/all → PreToolUse hook (Claude Code only).
    STORY-slim-20260827024e71df170f R4: codex → thin registration into
    Codex's native hooks engine (.codex/hooks.json); "all" deploys codex
    too, so it installs both native channels. The git pre-commit fallback
    stays for codex until the user completes Codex's trust confirmation.
    Anything else (opencode/copilot…) → git pre-commit fallback, because
    git-level interception is tool-agnostic. Returns the active channel
    string for the deploy summary (R2).
    """
    root = Path(root)
    if format_name in _PRETOOLUSE_FORMATS:
        install_hook(root)
        if format_name == "all":
            install_codex_hook(root)
    elif format_name == "codex":
        install_codex_hook(root)
        if (root / ".git").is_dir():
            install_git_hook(root)
    elif (root / ".git").is_dir():
        install_git_hook(root)
    channel = gate_channel(root)
    if channel == "none" and not (root / ".git").is_dir() and format_name not in _PRETOOLUSE_FORMATS:
        return "none (not a git repository)"
    return channel
