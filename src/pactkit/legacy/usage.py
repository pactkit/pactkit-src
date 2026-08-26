"""Machine-local usage counter for explicit legacy-engine invocations.

Records ONLY the command name and dates — never arguments or content.
Stored under ~/.pactkit (NOT the project tree): per-machine usage is the
deletion signal, and STORY-slim-146 pins the project .pactkit tree as
write-free for read-only continuation commands. No telemetry — the
counter is read by `pactkit doctor` to inform the deletion decision
(STORY-slim-20260826cb37edfdd4da R3/R4).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pactkit.utils import atomic_write

_KNOWN_COMMANDS = ("workflow", "work-unit", "continuation")


def _counter_path() -> Path:
    return Path.home() / ".pactkit" / "legacy-engine-usage.json"


def record_legacy_usage(command: str) -> None:
    """Increment the machine-local counter for one explicit invocation.

    Test invocations MUST NOT count: the kill-switch env var is set by the
    e2e test harness so CI noise never corrupts the deletion decision.
    """
    import os

    if command not in _KNOWN_COMMANDS:
        return
    if os.environ.get("PACTKIT_DISABLE_USAGE_COUNTING"):
        return
    path = _counter_path()
    data: dict = {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            data = payload
    except (OSError, ValueError):
        pass
    entry = data.get(command)
    entry = entry if isinstance(entry, dict) else {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data[command] = {
        "count": int(entry.get("count", 0)) + 1,
        "first_seen": entry.get("first_seen") or today,
        "last_seen": today,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_legacy_usage() -> dict:
    """Return the recorded usage map (validated; {} when absent/corrupt)."""
    path = _counter_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        command: entry
        for command, entry in payload.items()
        if command in _KNOWN_COMMANDS and isinstance(entry, dict)
    }
