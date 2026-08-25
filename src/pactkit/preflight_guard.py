"""Claude Code mutation guard for Spec preflight receipts.

The guard is deliberately scoped to an explicit session-to-Story Act binding.
Historical workflow state never activates it, and internal failures fail open.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pactkit.config import find_pactkit_yaml, load_config
from pactkit.project_root import ProjectRootNotFound, resolve_project_root
from pactkit.spec_preflight import (
    active_story,
    bind_active_story,
    check_preflight_receipt,
    clear_active_story,
)
from pactkit.utils import atomic_write

HOOK_COMMAND = "pactkit preflight-guard --hook"
MUTATION_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
_RECOVERY_PREFIXES = (".pactkit/", "docs/specs/", "docs/product/", ".claude/")
_ACTIVATE_RE = re.compile(
    r"(?:^|[;&|]\s*)(?:python(?:3)?\s+-m\s+pactkit|pactkit)\s+spec-preflight\s+"
    r"(?P<spec>[^\s;&|]+).*?(?:^|\s)--activate(?:\s|$)"
)


def _mode(root: Path) -> str:
    config_path = find_pactkit_yaml(root)
    config = load_config(config_path) if config_path else {}
    value = (config.get("preflight") or {}).get("mode", "warn")
    return value if value in {"off", "warn", "enforce"} else "warn"


def _target_path(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    return str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")


def _is_recovery_path(root: Path, target: str) -> bool:
    if not target:
        return False
    path = Path(target)
    if not path.is_absolute():
        path = root / path
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return False
    return any(relative == prefix.rstrip("/") or relative.startswith(prefix) for prefix in _RECOVERY_PREFIXES)


def hook_entry(stdin_text: str, root: Path | None = None) -> tuple[str, int]:
    """Return ``(message, exit_code)`` under Claude Code's hook contract."""
    try:
        payload = json.loads(stdin_text or "{}")
        start = Path(payload.get("cwd") or root or Path.cwd())
        project_root = resolve_project_root(start, explicit=root) if root else resolve_project_root(start)
        session_id = str(payload.get("session_id") or "")
        if payload.get("tool_name") == "Bash":
            command = str((payload.get("tool_input") or {}).get("command") or "")
            activation = _ACTIVATE_RE.search(command)
            if activation and session_id:
                story_id = Path(activation.group("spec").strip("'\"")).stem
                bind_active_story(project_root, story_id, session_id)
            return "", 0
        if payload.get("tool_name") not in MUTATION_TOOLS:
            return "", 0
        mode = _mode(project_root)
        if mode == "off" or _is_recovery_path(project_root, _target_path(payload)):
            return "", 0
        story_id = active_story(project_root, session_id)
        if not story_id:
            return (
                "[WARN] PactKit preflight: this session is not bound to an Act Story; "
                "write allowed. Run `pactkit spec-preflight <spec> --activate` to bind it.",
                0,
            )
        check = check_preflight_receipt(project_root, story_id, session_id=session_id)
        if check.valid:
            clear_active_story(project_root, session_id)
            return "", 0
        message = (
            f"PactKit spec preflight is stale for {story_id}: {check.reason}. "
            f"Run `pactkit spec-preflight docs/specs/{story_id}.md --activate`."
        )
        if mode == "enforce":
            return message, 2
        return f"[WARN] {message} Write allowed because preflight.mode=warn.", 0
    except (ProjectRootNotFound, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return f"[WARN] PactKit preflight guard unavailable ({type(exc).__name__}: {exc}); write allowed.", 0


def install_preflight_hook(root: Path) -> str:
    """Idempotently merge PactKit's mutation guard into Claude settings."""
    root = Path(root).resolve()
    settings_path = root / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return f"preflight hook: {settings_path} is not valid JSON — left untouched"
    else:
        settings = {}
    if not isinstance(settings, dict):
        return f"preflight hook: {settings_path} has unexpected shape — left untouched"
    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])
    entry = {
        "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [{"type": "command", "command": HOOK_COMMAND}],
    }
    for index, existing in enumerate(pre_tool):
        commands = [h.get("command", "") for h in existing.get("hooks", []) if isinstance(h, dict)]
        if any("preflight-guard" in command for command in commands):
            pre_tool[index] = entry
            break
    else:
        pre_tool.append(entry)
    atomic_write(settings_path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
    return f"preflight hook: installed in {settings_path}"
