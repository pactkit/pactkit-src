"""Friction statistics from run event streams (STORY-slim-20260827024e71df170f R2).

Aggregates the append-only event logs written by the continuation stores
into per-run friction metrics: duration, blocker dwell by kind, step
rework, and gate-relevant transitions.  Runs predating the event stream
(the overwrite-checkpoint era) are reported as ``events: unavailable``
rather than failing the command.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pactkit.run_events import read_events


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _summarize(
    identifier: str,
    events: list[dict[str, Any]],
    corrupt: int,
    *,
    kind: str,
    story_id: str | None,
    run_id: str | None,
) -> dict[str, Any]:
    timestamps = [ts for e in events if (ts := _parse_ts(e.get("ts")))]
    duration = 0.0
    if len(timestamps) >= 2:
        duration = max(0.0, (timestamps[-1] - timestamps[0]).total_seconds())

    # Blocker dwell: pair blocker_raised with the next blocker_cleared;
    # an unclosed episode runs to the last observed event.
    blocker_dwell: dict[str, float] = {}
    open_ts: datetime | None = None
    open_kind = "unknown"
    for event, ts in [(e, _parse_ts(e.get("ts"))) for e in events]:
        if ts is None:
            continue
        if event["event"] == "blocker_raised":
            open_ts, open_kind = ts, "unknown"
            detail = event.get("detail")
            if isinstance(detail, dict) and detail.get("blocker_kind"):
                open_kind = str(detail["blocker_kind"])
        elif event["event"] == "blocker_cleared" and open_ts is not None:
            blocker_dwell[open_kind] = (
                blocker_dwell.get(open_kind, 0.0) + max(0.0, (ts - open_ts).total_seconds())
            )
            open_ts = None
    if open_ts is not None and timestamps:
        blocker_dwell[open_kind] = blocker_dwell.get(open_kind, 0.0) + max(
            0.0, (timestamps[-1] - open_ts).total_seconds()
        )

    # Step rework: checkpoint rewrites beyond the first per step, plus
    # every evidence invalidation.
    step_writes: dict[str, int] = {}
    invalidations = 0
    authorization_decisions = {"asked": 0, "granted": 0, "denied": 0}
    for event in events:
        if event["event"] == "checkpoint_written":
            step = str(event.get("step_id") or "?")
            step_writes[step] = step_writes.get(step, 0) + 1
        elif event["event"] == "evidence_invalidated":
            invalidations += 1
        elif event["event"] == "authorization_asked":
            authorization_decisions["asked"] += 1
        elif event["event"] == "authorization_granted":
            authorization_decisions["granted"] += 1
        elif event["event"] == "authorization_denied":
            authorization_decisions["denied"] += 1
    rework = invalidations + sum(max(0, count - 1) for count in step_writes.values())

    status = "unknown"
    for event in reversed(events):
        if event.get("status"):
            status = str(event["status"])
            break
    if any(e["event"] == "run_completed" for e in events):
        status = "completed"

    return {
        "kind": kind,
        "story_id": story_id,
        "run_id": run_id,
        "identifier": identifier,
        "events": "available",
        "event_count": len(events),
        "corrupt_lines": corrupt,
        "duration_seconds": round(duration, 3),
        "blocker_dwell_seconds": {k: round(v, 3) for k, v in blocker_dwell.items()},
        "step_rework": rework,
        "step_writes": step_writes,
        "authorization_decisions": authorization_decisions,
        "status": status,
    }


def _unavailable(
    *, kind: str, story_id: str | None, run_id: str | None, status: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "story_id": story_id,
        "run_id": run_id,
        "identifier": story_id or run_id,
        "events": "unavailable",
        "event_count": 0,
        "corrupt_lines": 0,
        "duration_seconds": None,
        "blocker_dwell_seconds": {},
        "step_rework": 0,
        "step_writes": {},
        "authorization_decisions": {"asked": 0, "granted": 0, "denied": 0},
        "status": status,
    }


def collect_runs(root: Path) -> list[dict[str, Any]]:
    """Per-run friction summaries from event streams + legacy checkpoints."""

    runs: list[dict[str, Any]] = []
    seen: set[str] = set()

    story_dir = root / ".pactkit" / "continuations" / "events"
    if story_dir.is_dir():
        for path in sorted(story_dir.glob("*.jsonl")):
            events, corrupt = read_events(path)
            runs.append(_summarize(
                path.stem, events, corrupt, kind="story",
                story_id=path.stem, run_id=None,
            ))
            seen.add(path.stem)

    runs_dir = root / ".pactkit" / "continuations" / "runs" / "events"
    if runs_dir.is_dir():
        for path in sorted(runs_dir.glob("*.jsonl")):
            events, corrupt = read_events(path)
            story = next((e.get("story_id") for e in events if e.get("story_id")), None)
            runs.append(_summarize(
                path.stem, events, corrupt, kind="run",
                story_id=story, run_id=path.stem,
            ))
            seen.add(path.stem)

    # Overwrite-era checkpoints without an event stream (pre-2.24 runs).
    for path in sorted((root / ".pactkit" / "continuations").glob("*.json")):
        if path.stem in seen or path.suffix == ".lock":
            continue
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            status = str(state.get("status", "unknown"))
            story_id = state.get("story_id") or path.stem
        except (OSError, json.JSONDecodeError):
            story_id, status = path.stem, "corrupt"
        runs.append(_unavailable(
            kind="story", story_id=story_id, run_id=None, status=status,
        ))
        seen.add(path.stem)
    for path in sorted((root / ".pactkit" / "continuations" / "runs").glob("run-*.json")):
        if path.stem in seen:
            continue
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            status = str(state.get("status", "unknown"))
            story_id = state.get("story_id")
        except (OSError, json.JSONDecodeError):
            story_id, status = None, "corrupt"
        runs.append(_unavailable(
            kind="run", story_id=story_id, run_id=path.stem, status=status,
        ))
        seen.add(path.stem)

    return runs


def json_report(runs: list[dict[str, Any]]) -> dict[str, Any]:
    available = [r for r in runs if r["events"] == "available"]
    total_dwell: dict[str, float] = {}
    for run in available:
        for kind, seconds in run["blocker_dwell_seconds"].items():
            total_dwell[kind] = round(total_dwell.get(kind, 0.0) + seconds, 3)
    return {
        "runs": runs,
        "summary": {
            "run_count": len(runs),
            "with_events": len(available),
            "without_events": len(runs) - len(available),
            "total_blocker_dwell_seconds": total_dwell,
            "total_step_rework": sum(r["step_rework"] for r in available),
        },
    }


def render_report(runs: list[dict[str, Any]]) -> str:
    """Human-readable friction table."""
    if not runs:
        return "No runs found."
    lines = ["Run friction metrics:", ""]
    for run in runs:
        name = run.get("story_id") or run.get("run_id") or run["identifier"]
        if run["events"] == "unavailable":
            lines.append(
                f"  {name}: events=unavailable (pre-2.24 checkpoint) status={run['status']}"
            )
            continue
        dwell = ", ".join(
            f"{kind}={seconds}s" for kind, seconds in sorted(run["blocker_dwell_seconds"].items())
        ) or "none"
        lines.append(
            f"  {name}: duration={run['duration_seconds']}s "
            f"rework={run['step_rework']} status={run['status']} "
            f"blocker_dwell[{dwell}]"
        )
    corrupt = sum(r["corrupt_lines"] for r in runs)
    if corrupt:
        lines.append(f"  [WARN] {corrupt} corrupt event line(s) skipped")
    return "\n".join(lines)
