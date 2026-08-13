"""STORY-slim-137: external dependency check and guided install.

pip-resolvable dependencies are covered by extras (pactkit[all]); this module
handles what pip cannot reach — npm/system-level tools (node, codegraph, gh).

Split of responsibilities (design consensus 2026-08-13):
  - HOW to install = code (this module; testable, deterministic)
  - WHEN to ask    = /project-init playbook (interactive, human present)
  - `pactkit init` CLI only ever REPORTS (may run in CI / air-gapped envs)

SEC-1: every install command comes from DEP_REGISTRY constants and is passed
to subprocess as an argument list — shell=True is never used.
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# R1: dependency registry (single source — No Magic Values)
# ---------------------------------------------------------------------------

# Each entry:
#   detect      — binary name for shutil.which
#   min_version — informational minimum (reported, not enforced by upgrade)
#   purpose     — what breaks without it
#   install     — platform -> argv list (list form only, never shell strings)
#   needs       — prerequisites that must be installed first
DEP_REGISTRY: dict[str, dict] = {
    "node": {
        "detect": "node",
        "min_version": "18",
        "purpose": "runtime required by codegraph",
        "install": {
            "darwin": ["brew", "install", "node"],
            "linux-apt": ["sudo", "apt-get", "install", "-y", "nodejs"],
        },
        "needs": [],
    },
    "codegraph": {
        "detect": "codegraph",
        "min_version": "",
        "purpose": "call-graph provider for visualize impact analysis and pactkit query",
        "install": {
            "any": ["npm", "install", "-g", "@colbymchenry/codegraph"],
        },
        "needs": ["node"],
    },
    "gh": {
        "detect": "gh",
        "min_version": "",
        "purpose": "GitHub operations: issue-sync, /project-pr, release, CI checks",
        "install": {
            "darwin": ["brew", "install", "gh"],
            "linux-apt": ["sudo", "apt-get", "install", "-y", "gh"],
        },
        "needs": [],
    },
}

# Manual install guidance when no platform mapping exists (e.g. Windows)
MANUAL_HINTS: dict[str, str] = {
    "node": "https://nodejs.org/ (LTS installer)",
    "codegraph": "npm install -g @colbymchenry/codegraph (requires node)",
    "gh": "https://cli.github.com/ (installer per platform)",
}


@dataclass
class DepStatus:
    name: str
    installed: bool
    version: str  # "" when unknown
    purpose: str
    install_hint: str


def _detect_platform() -> str:
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("linux"):
        if shutil.which("apt-get"):
            return "linux-apt"
        return "linux-other"
    return sys.platform  # win32 etc.


def _tool_version(binary: str) -> str:
    """Best-effort version probe; any failure yields 'unknown' (SEC-2)."""
    try:
        proc = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip().splitlines()[0][:60]
    return "unknown"


def _install_argv(entry: dict, platform: str) -> list[str] | None:
    mapping = entry.get("install", {})
    return mapping.get(platform) or mapping.get("any")


def check_deps(platform: str | None = None) -> list[DepStatus]:
    """R1: detect every registered dependency. Read-only, never installs."""
    platform = platform or _detect_platform()
    statuses = []
    for name, entry in DEP_REGISTRY.items():
        binary = entry["detect"]
        path = shutil.which(binary)
        argv = _install_argv(entry, platform)
        hint = " ".join(argv) if argv else MANUAL_HINTS.get(name, "see project docs")
        statuses.append(
            DepStatus(
                name=name,
                installed=path is not None,
                version=_tool_version(binary) if path else "",
                purpose=entry["purpose"],
                install_hint=hint,
            )
        )
    return statuses


def render_check_report(statuses: list[DepStatus]) -> str:
    lines = ["External dependencies:"]
    for s in statuses:
        if s.installed:
            lines.append(f"  ✅ {s.name} ({s.version or 'version unknown'})")
        else:
            lines.append(f"  ❌ {s.name} — needed for: {s.purpose}")
            lines.append(f"     install: {s.install_hint}")
    missing = [s for s in statuses if not s.installed]
    if missing:
        lines.append(f"Run `pactkit deps install` to install {len(missing)} missing item(s).")
    else:
        lines.append("All external dependencies present.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# R2: guided install
# ---------------------------------------------------------------------------


def _no_external_enabled(root: Path) -> bool:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from pactkit.config import load_config

        cfg = load_config(root / ".claude" / "pactkit.yaml")
    enterprise = cfg.get("enterprise", {})
    return isinstance(enterprise, dict) and bool(enterprise.get("no_external"))


def _run_install(argv: list[str]) -> tuple[bool, str]:
    """SEC-1: argv list only, never shell=True. SEC-7: failures are reported."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        return False, f"installer not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return False, "install timed out after 600s"
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        return False, detail[-1] if detail else f"exit {proc.returncode}"
    return True, ""


def install_deps(
    root: Path,
    *,
    assume_yes: bool = False,
    platform: str | None = None,
    confirm=None,
    runner=None,
) -> tuple[list[str], int]:
    """R2: install missing dependencies in dependency order.

    confirm: callable(prompt) -> bool (default: interactive input()).
    runner:  callable(argv) -> (ok, detail) (default: _run_install; tests inject).

    Returns (summary_lines, exit_code). exit 0 = everything installed or
    declined-by-user; 1 = an attempted install failed.
    """
    if _no_external_enabled(root):
        return (["deps install: refused — enterprise.no_external is set. "
                 "Install manually: " + "; ".join(
                     f"{n}: {h}" for n, h in MANUAL_HINTS.items())], 1)

    platform = platform or _detect_platform()
    if confirm is None:
        confirm = (lambda _prompt: True) if assume_yes else _interactive_confirm
    runner = runner or _run_install

    missing = [s for s in check_deps(platform) if not s.installed]
    if not missing:
        return ["deps install: nothing to do — all dependencies present"], 0

    # Dependency order: prerequisites first (codegraph.needs == [node])
    ordered = sorted(missing, key=lambda s: len(DEP_REGISTRY[s.name].get("needs", [])))

    lines: list[str] = []
    failures = 0
    for status in ordered:
        entry = DEP_REGISTRY[status.name]
        argv = _install_argv(entry, platform)
        if argv is None:
            lines.append(f"⏭️  {status.name}: no installer for platform {platform!r} — "
                         f"manual: {MANUAL_HINTS.get(status.name, 'see docs')}")
            continue
        if not confirm(f"Install {status.name}? Runs: {' '.join(argv)} [y/N] "):
            lines.append(f"⏭️  {status.name}: skipped by user — manual: {' '.join(argv)}")
            continue
        ok, detail = runner(argv)
        if ok:
            lines.append(f"✅ {status.name}: installed")
        else:
            failures += 1
            lines.append(f"❌ {status.name}: install failed — {detail}")
    return lines, (1 if failures else 0)


def _interactive_confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False
