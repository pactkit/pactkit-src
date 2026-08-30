"""Append-only run event streams (STORY-slim-20260827024e71df170f R1).

Every workflow-state mutation appends one typed event line next to its
checkpoint.  The checkpoint JSON remains the projection (materialized
view); the event log is the history the overwrite-style checkpoint cannot
hold.  Appends happen inside the caller's checkpoint lock, one line per
write — a crash may lose the last event but never damages earlier lines.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENT_TYPES = (
    "step_entered",
    "checkpoint_written",
    "evidence_invalidated",
    "blocker_raised",
    "blocker_cleared",
    "run_completed",
    "run_archived",
    # Authorization audit layer (STORY-slim-20260827eddbe9669c87 R1):
    # asked/granted are derived from blocker transitions; denied is written
    # only by the explicit `pactkit continuation deny` action.
    "authorization_asked",
    "authorization_granted",
    "authorization_denied",
    # Gate telemetry (STORY-slim-20260830c65491123af1): every gate block
    # (friction/noise measurement) and every Skill invocation (real usage
    # of the direct PDCA command path, which the workflow engine never sees).
    "gate_blocked",
    "command_invoked",
)


def story_events_path(root: Path, story_id: str) -> Path:
    """Event stream for a legacy Act story checkpoint."""
    return root / ".pactkit" / "continuations" / "events" / f"{story_id}.jsonl"


def run_events_path(root: Path, run_id: str) -> Path:
    """Event stream for a generic workflow run."""
    return root / ".pactkit" / "continuations" / "runs" / "events" / f"{run_id}.jsonl"


def append_event(
    path: Path,
    *,
    event: str,
    story_id: str | None,
    run_id: str | None,
    step_id: str | None = None,
    status: str | None = None,
    detail: Any = None,
) -> dict[str, Any]:
    """Append one event line.  Single write; caller holds the state lock."""
    if event not in EVENT_TYPES:
        raise ValueError(f"unknown event type: {event}")
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "story_id": story_id,
        "run_id": run_id,
        "event": event,
        "step_id": step_id,
        "status": status,
        "detail": detail,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return record


def read_events(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Parse an event stream, skipping damaged lines.

    Returns (events, corrupt_line_count).  A half-written trailing line
    (crash residue) counts as corrupt and is skipped without failing the
    reader (AC3).
    """
    if not path.exists():
        return [], 0
    events: list[dict[str, Any]] = []
    corrupt = 0
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return [], 1
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            corrupt += 1
            continue
        if isinstance(record, dict) and record.get("event") in EVENT_TYPES:
            events.append(record)
        else:
            corrupt += 1
    return events, corrupt


# ---------------------------------------------------------------------------
# Gate telemetry (STORY-slim-20260830c65491123af1)
# ---------------------------------------------------------------------------


def gate_events_path(root: Path) -> Path:
    """Project-level gate telemetry stream (blocks, authorizations, commands).

    Deliberately separate from the per-story continuation streams: gate
    events are project-scoped with best-effort story attribution carried
    in the ``story_id`` field, and the workflow engine never owns this
    file.
    """
    return root / ".pactkit" / "events" / "gates.jsonl"


def active_story_id(root: Path) -> str | None:
    """Best-effort attribution: the most recently prefledged story.

    The newest ``current.json`` under ``.pactkit/preflight/`` is the
    closest machine-observable proxy for "the story this session is
    working on" — zero prompt dependency.
    """
    preflight = root / ".pactkit" / "preflight"
    if not preflight.is_dir():
        return None
    best: tuple[float, str] | None = None
    try:
        for story_dir in preflight.iterdir():
            marker = story_dir / "current.json"
            if marker.is_file():
                mtime = marker.stat().st_mtime
                if best is None or mtime > best[0]:
                    best = (mtime, story_dir.name)
    except OSError:
        return None
    return best[1] if best else None


def record_gate_event(root: Path, event: str, detail: Any,
                      story_id: str | None = None) -> None:
    """Best-effort gate telemetry append — NEVER blocks a gate verdict.

    Telemetry failure is silent by design: the gate's enforcement verdict
    and its enforcement status record are the contract; the event stream
    is the measurement.
    """
    try:
        append_event(
            gate_events_path(root),
            event=event,
            story_id=story_id if story_id is not None else active_story_id(root),
            run_id=None,
            detail=detail,
        )
    except Exception:  # noqa: BLE001 - measurement must never break enforcement
        pass
