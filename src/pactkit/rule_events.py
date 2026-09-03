"""Rule-telemetry events (STORY-slim-20260903a4ef6915ed62 / ADR-0003).

Project-scoped append-only event stream at ``.pactkit/events/rules.jsonl``
(same pattern as gates.jsonl). Locality red line: payloads are whitelisted
to non-identifying fields and recording NEVER raises into the caller — a
broken telemetry path must not break linting or the CLI.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

RULE_EVENT_TYPES = ("rule_warning", "guide_loaded", "diagnosis_emitted")

# Locality red line (R6): these and only these keys may appear in a payload.
_PAYLOAD_WHITELIST = {"event", "guide", "rule", "spec", "ts"}


def rules_events_path(root: Path) -> Path:
    return Path(root) / ".pactkit" / "events" / "rules.jsonl"


def append_rule_event(root: Path, event: str, payload: dict | None = None) -> None:
    """Append one telemetry event; never raises (recording is best-effort)."""
    if event not in RULE_EVENT_TYPES:
        raise ValueError(f"unknown rule event: {event}")
    try:
        record = {"event": event, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        record.update({k: v for k, v in (payload or {}).items() if k in _PAYLOAD_WHITELIST})
        record = {k: v for k, v in record.items() if k in _PAYLOAD_WHITELIST}
        path = rules_events_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except (OSError, ValueError):
        # Telemetry must never break the caller (lint output, CLI exit codes).
        return


def read_rule_events(root: Path) -> list[dict]:
    """Read all events; corrupt lines are skipped, missing file is empty."""
    path = rules_events_path(root)
    if not path.is_file():
        return []
    events: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return events
