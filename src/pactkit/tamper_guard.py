"""STORY-slim-202608289e83eeb30df4: tamper guard (R5).

PreToolUse gate that blocks agent modifications to enforcement-owned
artifacts.  The incident behind this story: an agent asked to push to
master modified PactKit's own rules/config to accomplish the push.  The
rule and the actor it constrains shared the same permission domain — this
module moves the boundary into code.

Protected surface:
  - fully protected (any agent write is tamper): ``.git/hooks/**``,
    ``.pactkit/enforcement/**``, ``.codex/hooks.json``
  - conditionally protected: ``.claude/settings.json`` — only edits that
    remove or rewrite a gate registration (the ``commit-gate`` command
    moves from old content to absent/changed); unrelated settings edits
    pass untouched.

Bypass channels (never in-conversation):
  - ``PACTKIT_ALLOW_CONFIG_EDIT=1`` — human runs the edit themselves
    (the ``!`` prefix channel)
  - ``enforcement.tamper_guard: false`` in pactkit.yaml — repo owner
    opt-out (PactKit's own repository uses this: maintainers edit hooks)

Every blocked attempt is recorded via ``enforcement.record_status`` under
gate name ``tamper_guard`` — the audit trail survives the block.
"""

import os
import re
from pathlib import Path

TAMPER_GATE = "tamper_guard"
CONFIG_EDIT_BYPASS_ENV = "PACTKIT_ALLOW_CONFIG_EDIT"
# STORY-slim-20260828897396a935ab R3: spec tampering ("Spec is Law")
SPEC_EDIT_BYPASS_ENV = "PACTKIT_ALLOW_SPEC_EDIT"
_SPEC_DIR = "docs/specs"
_SPEC_FILE_RE = re.compile(r"docs/specs/([\w\-]+)\.md")

# Gate registrations are identified by their command string; anything that
# carries the commit-gate entry is enforcement-owned configuration.
GATE_COMMAND_MARKERS = ("commit-gate",)

# Any agent write to these locations is a tamper attempt.
_PROTECTED_DIRS = (".git/hooks", ".pactkit/enforcement")
_PROTECTED_FILES = (".codex/hooks.json",)
# Gate-entry removal inside these files is a tamper attempt; other edits pass.
_CONDITIONAL_FILES = (".claude/settings.json",)

# Bash write semantics aimed at a protected path.  `>` is guarded against
# `->`, `>=`, and word characters (e.g. identifiers) preceding it.
_BASH_WRITE_RE = re.compile(
    r"(>>|(?<![-\w])>|(?<![\w-])rm\s|(?<![\w-])mv\s|(?<![\w-])cp\s|"
    r"(?<![\w-])chmod\s|(?<![\w-])tee\s|sed\s+-i|(?<![\w-])truncate\s|(?<![\w-])dd\s)"
)

_BLOCK_MESSAGE = (
    "[FAIL] tamper-guard: modifying enforcement artifacts is blocked "
    "(L1: enforcement-artifact tampering is Spec tampering).\n"
    "  Human bypass: run the edit yourself with {env}=1 "
    "(e.g. `! {env}=1 <command>`).\n"
    "  Config change (repo owner): enforcement.tamper_guard in pactkit.yaml."
)


def _bypassed() -> bool:
    return os.environ.get(CONFIG_EDIT_BYPASS_ENV, "") == "1"


def _record(root: Path, reason: str) -> None:
    _record_gate(root, TAMPER_GATE, reason)


def _record_gate(root: Path, gate: str, reason: str) -> None:
    from pactkit.enforcement import FULL, record_status

    try:
        record_status(root, gate, FULL, reason)
    except Exception:  # noqa: BLE001 - audit is best-effort, never blocks
        pass


def _relpath(root: Path, file_path: Path) -> str | None:
    """Posix-style path relative to root; None when outside the project."""
    try:
        rel = file_path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    return rel.as_posix()


def _is_fully_protected(rel: str) -> bool:
    if rel in _PROTECTED_FILES:
        return True
    return any(rel == d or rel.startswith(d + "/") for d in _PROTECTED_DIRS)


def _removes_gate_entry(tool_name: str, tool_input: dict, path: Path) -> bool:
    """Does this edit remove or rewrite a gate registration?"""
    if tool_name == "Edit":
        old = str(tool_input.get("old_string") or "")
        new = str(tool_input.get("new_string") or "")
        had = any(m in old for m in GATE_COMMAND_MARKERS)
        has = any(m in new for m in GATE_COMMAND_MARKERS)
        return had and not has
    # Write: compare against the on-disk content being replaced.
    try:
        existing = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    content = str(tool_input.get("content") or "")
    had = any(m in existing for m in GATE_COMMAND_MARKERS)
    has = any(m in content for m in GATE_COMMAND_MARKERS)
    return had and not has


_SPEC_BLOCK_MESSAGE = (
    "[FAIL] spec-guard: modifying `{spec}` is blocked — Spec is Law (L1).\n"
    "  During Act the Spec MUST NOT be amended unilaterally; route changes "
    "through /project-plan (the RFC gate).\n"
    "  After user authorization: `pactkit gate authorize spec_edit`, or "
    "{env}=1 for the human channel."
)


def _spec_edit_allowed(root: Path, settings: dict) -> bool:
    """spec_guard gate: is editing a receipt-bound spec permitted now?"""
    import os

    from pactkit.auth_gate import _token_valid

    if not settings.get("spec_guard", True):
        return True
    if os.environ.get(SPEC_EDIT_BYPASS_ENV, "") == "1":
        return True
    if _token_valid(root, "spec_edit"):
        return True
    return False


def _receipt_exists(root: Path, story_id: str) -> bool:
    return (root / ".pactkit" / "preflight" / story_id / "current.json").is_file()


def _check_spec_path(root: Path, rel: str, settings: dict) -> tuple[str, int]:
    """Block edits to a spec that has an active preflight receipt.

    Plan-phase spec writing is unaffected: no receipt exists until
    spec-preflight runs (Act Phase 0.7).
    """
    if not rel.startswith(_SPEC_DIR + "/") or not rel.endswith(".md"):
        return "", 0
    story_id = rel[len(_SPEC_DIR) + 1 : -len(".md")]
    if not _receipt_exists(root, story_id):
        return "", 0
    if _spec_edit_allowed(root, settings):
        return "", 0
    _record_gate(root, "spec_guard", f"blocked spec edit on {rel} (active preflight receipt)")
    return (
        _SPEC_BLOCK_MESSAGE.format(spec=rel, env=SPEC_EDIT_BYPASS_ENV),
        2,
    )


def check_edit_tool(tool_name: str, tool_input: dict, root: Path,
                    settings: dict | None = None) -> tuple[str, int]:
    """PreToolUse hook mode for Edit/Write tool calls. exit 2 = block.

    spec_guard (its own flag) runs first — tamper_guard being off does
    not stand down the Spec-is-Law check.
    """
    if settings is None:
        from pactkit.commit_gate import _enforcement_settings

        settings = _enforcement_settings(root)

    raw_path = str(tool_input.get("file_path") or "")
    if not raw_path:
        return "", 0
    rel = _relpath(root, Path(raw_path))
    if rel is None:
        return "", 0

    spec_msg, spec_code = _check_spec_path(root, rel, settings)
    if spec_code:
        return spec_msg, spec_code

    if not settings.get("tamper_guard", True) or _bypassed():
        return "", 0

    if _is_fully_protected(rel):
        _record(root, f"blocked {tool_name} on {rel}")
        return _BLOCK_MESSAGE.format(env=CONFIG_EDIT_BYPASS_ENV), 2

    if rel in _CONDITIONAL_FILES and _removes_gate_entry(
        tool_name, tool_input, root / rel
    ):
        _record(root, f"blocked gate-entry removal in {rel}")
        return _BLOCK_MESSAGE.format(env=CONFIG_EDIT_BYPASS_ENV), 2

    return "", 0


def check_bash_command(command: str, root: Path,
                       settings: dict | None = None) -> tuple[str, int]:
    """PreToolUse hook mode for Bash commands targeting protected paths.

    spec_guard (its own flag) runs first; tamper_guard second.
    """
    if settings is None:
        from pactkit.commit_gate import _enforcement_settings

        settings = _enforcement_settings(root)

    writes = bool(_BASH_WRITE_RE.search(command))
    if writes:
        match = _SPEC_FILE_RE.search(command)
        if match and _receipt_exists(root, match.group(1)):
            if not _spec_edit_allowed(root, settings):
                _record_gate(root, "spec_guard", f"blocked bash spec edit on {match.group(0)}")
                return (
                    _SPEC_BLOCK_MESSAGE.format(spec=match.group(0), env=SPEC_EDIT_BYPASS_ENV),
                    2,
                )

    if not settings.get("tamper_guard", True) or _bypassed():
        return "", 0
    if not writes:
        return "", 0

    targets = [d for d in _PROTECTED_DIRS if d in command]
    targets += [f for f in _PROTECTED_FILES if f in command]
    if not targets:
        # Gate-entry surgery on settings.json via shell (sed/redirect).
        if any(f in command for f in _CONDITIONAL_FILES) and any(
            m in command for m in GATE_COMMAND_MARKERS
        ):
            _record(root, "blocked bash gate-entry rewrite in .claude/settings.json")
            return _BLOCK_MESSAGE.format(env=CONFIG_EDIT_BYPASS_ENV), 2
        return "", 0

    _record(root, f"blocked bash write to {', '.join(targets)}")
    return _BLOCK_MESSAGE.format(env=CONFIG_EDIT_BYPASS_ENV), 2
