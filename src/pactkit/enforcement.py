"""Gate enforcement completeness reporting (STORY-slim-20260827024e71df170f R3).

Every gate declares how completely it is currently enforcing, instead of
degrading silently through a WARN line.  Statuses:

  - ``full``        the gate enforces its full contract
  - ``degraded``    the gate runs but with reduced enforcement
  - ``unavailable`` the gate cannot run (self-lock protection fires)

Two evidence sources merge per gate: a static capability probe (can the
gate run in this environment at all?) and the last recorded run outcome
written by the gate itself (``.pactkit/enforcement/<gate>.json``).  The
worse of the two wins — a healthy environment must not mask the last
degraded run, and a degraded record must not survive an impossible probe.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pactkit.utils import atomic_write

FULL = "full"
DEGRADED = "degraded"
UNAVAILABLE = "unavailable"
# Attempt fencing (STORY-slim-20260827eddbe9669c87 R3): a record written
# BEFORE a verification runs and overwritten by its terminal outcome.  A
# surviving "running" record means the attempt never completed — its
# verdict cannot be trusted (outcome unknown).
RUNNING = "running"
UNKNOWN_TEXT = "unknown"
STATUS_LEVELS = (FULL, DEGRADED, UNAVAILABLE)
_RANK = {FULL: 0, DEGRADED: 1, UNAVAILABLE: 2}

GATES = ("commit_gate", "coverage_gate", "finish_gate")


def _status_path(root: Path, gate: str) -> Path:
    return root / ".pactkit" / "enforcement" / f"{gate}.json"


def record_status(root: Path, gate: str, status: str, reason: str = "") -> dict[str, Any]:
    """Persist the gate's terminal outcome, closing any open attempt fence."""
    if status not in STATUS_LEVELS:
        raise ValueError(f"unknown enforcement status: {status}")
    record = {
        "gate": gate,
        "status": status,
        "reason": str(reason)[:500],
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    atomic_write(
        _status_path(root, gate),
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
    )
    return record


def record_attempt(root: Path, gate: str) -> dict[str, Any]:
    """Open an attempt fence BEFORE the verification runs (R3).

    The fence is a durability barrier in the dsh sense: a crash between
    this write and the terminal ``record_status`` leaves a surviving
    ``running`` record whose verdict cannot be trusted.  The recorded pid
    lets consumers distinguish "still running" from "crashed" without
    time-window guessing.  Best-effort — a failed fence write degrades to
    the pre-fence behavior, never blocks the gate itself.
    """
    record = {
        "gate": gate,
        "status": RUNNING,
        "reason": "",
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pid": os.getpid(),
    }
    try:
        atomic_write(
            _status_path(root, gate),
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        )
    except Exception:  # noqa: BLE001 - the fence is best-effort, never blocks
        pass
    return record


def pid_alive(pid: Any) -> bool:
    """Deterministic liveness for a fence pid (no time-window guessing).

    An absent or malformed pid reads as dead — the actionable default for
    a fence nobody can attribute is "re-run the gate".  Permission errors
    on a live check read as alive (conservative: wait, do not re-run).
    """
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def read_status(root: Path, gate: str) -> dict[str, Any] | None:
    path = _status_path(root, gate)
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(record, dict) or record.get("status") not in (*STATUS_LEVELS, RUNNING):
        return None
    return record


def _no_git_enabled(root: Path) -> bool:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from pactkit.config import load_config

        for candidate in (
            root / ".claude" / "pactkit.yaml",
            root / ".codex" / "pactkit.yaml",
        ):
            if not candidate.is_file():
                continue
            try:
                enterprise = load_config(candidate).get("enterprise", {})
            except Exception:  # noqa: BLE001 - probe must never raise
                continue
            if isinstance(enterprise, dict) and enterprise.get("no_git"):
                return True
    return False


def _pytest_interpreter(root: Path) -> str | None:
    """Resolve the interpreter the gates will actually drive (project venv
    first, via ``pytest_command``) — NOT the current interpreter, which for
    a pipx-installed CLI has no pytest at all (2.24.0 probe regression)."""
    import subprocess

    from pactkit.utils import pytest_command

    cmd = pytest_command(root)
    try:
        proc = subprocess.run(
            [cmd[0], "-m", "pytest", "--version"],
            capture_output=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return cmd[0] if proc.returncode == 0 else None


def _module_available(interpreter: str, module: str) -> bool:
    import subprocess

    try:
        proc = subprocess.run(
            [interpreter, "-c", f"import {module}"],
            capture_output=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def probe_commit_gate(root: Path) -> dict[str, Any]:
    """Static capability probe for the commit gate."""
    if _no_git_enabled(root):
        return {"status": UNAVAILABLE, "reason": "skipped (enterprise.no_git)"}
    if shutil.which("git") is None:
        return {"status": UNAVAILABLE, "reason": "git binary not found"}
    if not (root / ".git").exists():
        return {"status": UNAVAILABLE, "reason": "not a git repository"}
    if _pytest_interpreter(root) is None:
        return {"status": UNAVAILABLE, "reason": "pytest not resolvable (no project venv pytest)"}
    return {"status": FULL, "reason": ""}


def probe_coverage_gate(root: Path) -> dict[str, Any]:
    """Static capability probe for the coverage gate."""
    interpreter = _pytest_interpreter(root)
    if interpreter is None:
        return {"status": UNAVAILABLE, "reason": "pytest not resolvable (no project venv pytest)"}
    if not _module_available(interpreter, "pytest_cov"):
        return {
            "status": DEGRADED,
            "reason": "pytest-cov not installed — coverage cannot be measured",
        }
    return {"status": FULL, "reason": ""}


def probe_finish_gate(root: Path) -> dict[str, Any]:
    """Static probe: the finish gate reads checkpoints; corruption degrades it."""
    corrupt: list[str] = []
    for directory in (
        root / ".pactkit" / "continuations",
        root / ".pactkit" / "continuations" / "runs",
    ):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                corrupt.append(path.name)
    if corrupt:
        return {"status": DEGRADED, "reason": "corrupt checkpoint: " + ", ".join(corrupt)}
    return {"status": FULL, "reason": ""}


_PROBES = {
    "commit_gate": probe_commit_gate,
    "coverage_gate": probe_coverage_gate,
    "finish_gate": probe_finish_gate,
}


def _merge(probe: dict[str, Any], record: dict[str, Any] | None) -> dict[str, Any]:
    if record is None:
        return {"status": probe["status"], "reason": probe["reason"], "last_run": None}
    if record["status"] == RUNNING:
        # An open attempt fence is not an observed degradation — doctor's
        # summary stays capability-based; the fence is consumed by the
        # continuation outcome_unknown check (STORY-slim-20260827eddbe9669c87 R4).
        return {"status": probe["status"], "reason": probe["reason"], "last_run": None}
    probe_rank = _RANK[probe["status"]]
    record_rank = _RANK[record["status"]]
    if record_rank >= probe_rank:
        status, reason = record["status"], record["reason"]
    else:
        status, reason = probe["status"], probe["reason"]
    return {
        "status": status,
        "reason": reason,
        "last_run": {
            "status": record["status"],
            "reason": record["reason"],
            "ts": record.get("ts"),
        },
    }


def assess(root: Path) -> dict[str, dict[str, Any]]:
    """Enforcement completeness for every gate (probe + last recorded run)."""
    assessment: dict[str, dict[str, Any]] = {}
    for gate in GATES:
        probe = _PROBES[gate](root)
        assessment[gate] = _merge(probe, read_status(root, gate))
    return assessment


def render_summary(assessment: dict[str, dict[str, Any]]) -> str:
    """One-line-per-gate human summary for `pactkit doctor`."""
    lines = []
    for gate in GATES:
        entry = assessment.get(gate, {})
        status = entry.get("status", UNKNOWN_TEXT)
        reason = entry.get("reason") or ""
        suffix = f" ({reason})" if reason else ""
        lines.append(f"  Enforcement: {gate} = {status}{suffix}")
    return "\n".join(lines)
