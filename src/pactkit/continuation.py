"""Versioned, verifiable continuation checkpoints (STORY-slim-146)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pactkit.id_generator import ITEM_ID_PATTERN, ITEM_ID_RE
from pactkit.run_events import append_event, run_events_path, story_events_path
from pactkit.utils import atomic_write
from pactkit.workflow_registry import get_workflow
from pactkit.workflow_validators import WorkflowEvidenceError

SCHEMA_VERSION = 1
STEPS = ("preflight", "red", "green", "regression_lint", "sync_coverage")
STATUSES = ("in_progress", "blocked", "completed")
BLOCKER_KINDS = ("user_input", "authorization", "external_state")
LOCK_TIMEOUT_SECONDS = 5.0
LOCK_POLL_SECONDS = 0.05
_NEXT_STEP = dict(zip(STEPS, STEPS[1:] + ("completed",)))
_STORY_ID = ITEM_ID_RE
_SECRET = re.compile(r"(?i)(?:token|password|secret|api[_-]?key)\s*=\s*[^\s,;]+")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SENSITIVE_KEY = re.compile(
    r"(?i)(?:authorization|credential|password|passwd|secret|token|api[_-]?key|private[_-]?key)"
)
_STORY_BLOCK = re.compile(
    rf"^###\s+\[(?P<id>{ITEM_ID_PATTERN})\].*?(?=^###\s+\[|^##\s+|\Z)",
    re.MULTILINE | re.DOTALL,
)
_MUST_REQUIREMENT = re.compile(r"^###\s+(R\d+):.*?\(MUST\)", re.MULTILINE)
_ACCEPTANCE_CRITERION = re.compile(r"^###\s+(AC\d+):", re.MULTILINE)
_LEGACY_HANDOFF = re.compile(
    rf"^Last Command:\s*/project-act\s+(?P<story>{ITEM_ID_PATTERN})\s*$",
    re.MULTILINE,
)
_INVALID_BLOCKER = re.compile(
    r"(?i)(?:ran out of context|tool returned|more work remains|progress summary|"
    r"remaining work|continue later|context limit)"
)


class ContinuationError(ValueError):
    """Raised when a checkpoint or its completion evidence is invalid."""


def verification_outcome_unknown(root: Path) -> str | None:
    """Reason string when a commit-gate attempt fence never closed (R4).

    An open ``running`` fence means the last verification attempt produced
    no terminal verdict.  Its conclusions cannot be trusted, so resume
    blocks until the gate is re-run (which closes the fence).  The fence's
    pid disambiguates deterministically: a live pid means the attempt is
    still running (wait), a dead pid means it crashed (re-run) — no
    time-window guessing.  Read-only and fail-safe: a missing or corrupt
    fence reads as absent.
    """
    try:
        from pactkit.enforcement import RUNNING, pid_alive, read_status

        record = read_status(root, "commit_gate")
    except Exception:  # noqa: BLE001 - the check must never break resume
        return None
    if not isinstance(record, dict) or record.get("status") != RUNNING:
        return None
    when = record.get("ts", "unknown time")
    pid = record.get("pid")
    if pid_alive(pid):
        return (
            f"verification outcome unknown: commit-gate attempt at {when} "
            f"(pid {pid}) appears still active — wait for it to finish "
            "before resuming"
        )
    return (
        f"verification outcome unknown: commit-gate attempt at {when} "
        "never completed — re-run the gate"
    )


class ContinuationEngine:
    """Generic workflow-run store; the legacy Act store remains its compatibility facade."""

    def __init__(self, project_root: Path):
        self.root = project_root.resolve()
        self.directory = self.root / ".pactkit" / "continuations" / "runs"

    @contextmanager
    def _run_lock(self, run_id: str):
        """Exclusive per-run lock, platform-split like _story_lock (R3).

        fcntl is POSIX-only; the unconditional import crashed every engine
        mutation path on Windows.
        """
        lock_path = self.path_for(run_id).with_suffix(".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
        acquired = False
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        try:
            if os.name == "nt":  # pragma: no cover - exercised on Windows CI
                import msvcrt

                while time.monotonic() < deadline:
                    try:
                        if handle.tell() == 0:
                            handle.write(b"0")
                            handle.flush()
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        acquired = True
                        break
                    except (BlockingIOError, PermissionError, OSError):
                        time.sleep(LOCK_POLL_SECONDS)
            else:
                import fcntl

                while time.monotonic() < deadline:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired = True
                        break
                    except BlockingIOError:
                        time.sleep(LOCK_POLL_SECONDS)
            if not acquired:
                raise ContinuationError(f"workflow lock timeout: {run_id}")
            yield
        finally:
            if acquired:
                if os.name == "nt":  # pragma: no cover - exercised on Windows CI
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    @contextmanager
    def _bind_lock(self):
        """Store-wide lock serializing cross-run Story bindings (R4).

        Per-run locks cannot serialize a check-then-write that spans all run
        files: two concurrent bind_story calls for different runs would both
        pass the uniqueness scan. Lock ordering is bind lock outer, run lock
        inner.
        """
        lock_path = self.directory / ".bind.lock"
        self.directory.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
        acquired = False
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        try:
            if os.name == "nt":  # pragma: no cover - exercised on Windows CI
                import msvcrt

                while time.monotonic() < deadline:
                    try:
                        if handle.tell() == 0:
                            handle.write(b"0")
                            handle.flush()
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        acquired = True
                        break
                    except (BlockingIOError, PermissionError, OSError):
                        time.sleep(LOCK_POLL_SECONDS)
            else:
                import fcntl

                while time.monotonic() < deadline:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired = True
                        break
                    except BlockingIOError:
                        time.sleep(LOCK_POLL_SECONDS)
            if not acquired:
                raise ContinuationError("story bind lock timeout")
            yield
        finally:
            if acquired:
                if os.name == "nt":  # pragma: no cover - exercised on Windows CI
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def definition(self, workflow_id: str):
        return get_workflow(workflow_id)

    def _validate_run_id(self, run_id: str) -> None:
        if not re.fullmatch(r"run-[0-9a-f]{32}", run_id):
            raise ContinuationError(f"invalid run ID: {run_id}")

    def path_for(self, run_id: str) -> Path:
        self._validate_run_id(run_id)
        return self.directory / f"{run_id}.json"

    def _find(self, identifier: str) -> tuple[Path, dict[str, Any]]:
        exact = identifier.startswith("run-")
        candidates = [self.path_for(identifier)] if exact else sorted(
            self.directory.glob("run-*.json")
        )
        matches: list[tuple[Path, dict[str, Any]]] = []
        for path in candidates:
            if not path.exists():
                continue
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ContinuationError(f"corrupt workflow checkpoint: {path.name}") from exc
            if not isinstance(state, dict):
                raise ContinuationError(f"corrupt workflow checkpoint: {path.name}")
            if state.get("run_id") == identifier or state.get("story_id") == identifier:
                if exact:
                    return path, state
                matches.append((path, state))
        if matches:
            status_rank = {"in_progress": 2, "blocked": 1, "completed": 0}
            return max(
                matches,
                key=lambda item: (
                    status_rank.get(item[1].get("status"), -1),
                    str(item[1].get("updated_at", "")),
                    item[0].name,
                ),
            )
        raise ContinuationError(f"workflow run not found: {identifier}")

    def read(self, identifier: str) -> dict[str, Any]:
        return self._find(identifier)[1]

    @staticmethod
    def _host_reference(value: str, field: str) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > 4096:
            raise ContinuationError(f"invalid {field}")
        return "sha256:" + hashlib.sha256(value.encode()).hexdigest()

    def _host_binding_path(self, session_ref: str) -> Path:
        digest = session_ref.removeprefix("sha256:")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ContinuationError("invalid host session reference")
        return self.root / ".pactkit" / "continuations" / "bindings" / f"{digest}.json"

    def bind_host_session(
        self, identifier: str, *, session_id: str, turn_id: str | None = None,
    ) -> dict[str, Any]:
        """Bind an opaque host session to the currently executing workflow run."""
        _path, initial = self._find(identifier)
        session_ref = self._host_reference(session_id, "session ID")
        turn_ref = self._host_reference(turn_id, "turn ID") if turn_id else None
        with self._run_lock(initial["run_id"]):
            path, state = self._find(initial["run_id"])
            if state.get("status") == "completed":
                raise ContinuationError("completed workflow is immutable")
            binding = {
                "session_ref": session_ref,
                "turn_ref": turn_ref,
                "run_id": state["run_id"],
                "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            state["host_binding"] = binding
            state["updated_at"] = binding["updated_at"]
            atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
            atomic_write(
                self._host_binding_path(session_ref),
                json.dumps(binding, indent=2, ensure_ascii=False) + "\n",
            )
        return binding

    def resolve_host_run(
        self, *, session_id: str, turn_id: str | None = None,
    ) -> dict[str, Any]:
        """Resolve the workflow owned by a host session without trusting prose."""
        session_ref = self._host_reference(session_id, "session ID")
        turn_ref = self._host_reference(turn_id, "turn ID") if turn_id else None
        binding_path = self._host_binding_path(session_ref)
        if binding_path.exists():
            try:
                binding = json.loads(binding_path.read_text(encoding="utf-8"))
                if not isinstance(binding, dict):
                    raise TypeError
                state = self.read(str(binding["run_id"]))
            except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ContinuationError("corrupt host session binding") from exc
            if binding.get("session_ref") != session_ref:
                raise ContinuationError("host session binding mismatch")
            if turn_ref and binding.get("turn_ref") not in (None, turn_ref):
                # A session binding remains authoritative across continuation turns.
                pass
            return self._host_resolution(state)

        active: list[dict[str, Any]] = []
        if self.directory.is_dir():
            for path in sorted(self.directory.glob("run-*.json")):
                try:
                    state = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise ContinuationError(f"corrupt workflow checkpoint: {path.name}") from exc
                if not isinstance(state, dict):
                    raise ContinuationError(f"corrupt workflow checkpoint: {path.name}")
                if state.get("status") == "in_progress":
                    active.append(state)
        if not active:
            raise ContinuationError("no active workflow run")
        if len(active) != 1:
            raise ContinuationError("multiple active workflow runs")
        return self._host_resolution(active[0])

    @staticmethod
    def _host_resolution(state: dict[str, Any]) -> dict[str, Any]:
        story_id = state.get("story_id")
        return {
            "identifier": state.get("run_id"),
            "run_id": state.get("run_id"),
            "story_id": story_id,
            "workflow_id": state.get("workflow_id"),
            "step_id": state.get("step_id"),
            "status": state.get("status"),
        }

    def start(self, workflow_id: str, *, evidence: dict[str, Any]) -> dict[str, Any]:
        definition = self.definition(workflow_id)
        run_id = "run-" + uuid.uuid4().hex
        state = {
            "schema_version": 2, "workflow_id": workflow_id, "command": f"${workflow_id}",
            "run_id": run_id, "story_id": None, "step_id": definition.steps[0],
            "status": "in_progress", "evidence": _sanitize_evidence(evidence),
            "fingerprints": {}, "blocker": "",
            "blocker_kind": None,
            "completion_validated": False,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        validator = definition.validator_factory(self.root)
        try:
            validator.validate(state, definition.steps[0], evidence, "in_progress")
        except WorkflowEvidenceError as exc:
            raise ContinuationError(str(exc)) from exc
        with self._run_lock(run_id):
            atomic_write(self.path_for(run_id), json.dumps(state, indent=2, ensure_ascii=False) + "\n")
            append_event(
                run_events_path(self.root, run_id), event="step_entered",
                story_id=None, run_id=run_id, step_id=definition.steps[0],
                status="in_progress",
                detail=_sanitize_evidence({"workflow_id": workflow_id, "first": True}),
            )
        return state

    def bind_story(self, identifier: str, story_id: str) -> dict[str, Any]:
        if not _STORY_ID.fullmatch(story_id):
            raise ContinuationError(f"invalid Story ID: {story_id}")
        path, initial = self._find(identifier)
        with self._bind_lock():
            with self._run_lock(initial["run_id"]):
                path, state = self._find(initial["run_id"])
                if state.get("status") == "completed":
                    raise ContinuationError("completed workflow is immutable")
                if state.get("story_id") and state["story_id"] != story_id:
                    raise ContinuationError(f"workflow run already bound to {state['story_id']}")
                for candidate in self.directory.glob("run-*.json"):
                    if candidate == path:
                        continue
                    try:
                        other = json.loads(candidate.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        raise ContinuationError(
                            f"corrupt workflow checkpoint: {candidate.name}"
                        ) from exc
                    if not isinstance(other, dict):
                        raise ContinuationError(
                            f"corrupt workflow checkpoint: {candidate.name}"
                        )
                    if other.get("story_id") == story_id and other.get("status") != "completed":
                        raise ContinuationError(f"Story already bound to active run: {story_id}")
                state["story_id"] = story_id
                state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        return state

    # DEFERRED(SHOULD): R6 typed disk-state guards (STORY-slim-202608267c3989223b4d)
    # — direct state key access below operates on engine-validated states;
    # guarding the legacy store's raw access sites requires a records schema
    # redesign that exceeds this story's blast-radius budget.
    def checkpoint(
        self, identifier: str, *, step_id: str, evidence: dict[str, Any],
        status: str = "in_progress", blocker: str = "",
        blocker_kind: str | None = None,
    ) -> dict[str, Any]:
        _path, initial = self._find(identifier)
        with self._run_lock(initial["run_id"]):
            path, state = self._find(initial["run_id"])
            definition = self.definition(state["workflow_id"])
            if state["status"] == "completed":
                raise ContinuationError("completed workflow is immutable")
            if step_id not in definition.steps:
                raise ContinuationError(f"invalid step_id: {step_id}")
            current = definition.steps.index(state["step_id"])
            target = definition.steps.index(step_id)
            if target < current or target > current + 1:
                raise ContinuationError("workflow checkpoint must advance exactly one step")
            if status not in STATUSES:
                raise ContinuationError(f"invalid workflow status: {status}")
            if status == "blocked" and not blocker.strip():
                raise ContinuationError("blocked checkpoint requires a blocker")
            if status == "blocked" and blocker_kind not in BLOCKER_KINDS:
                raise ContinuationError("blocked checkpoint requires a valid blocker kind")
            validator = definition.validator_factory(self.root)
            try:
                validator.validate(state, step_id, evidence, status)
            except WorkflowEvidenceError as exc:
                raise ContinuationError(str(exc)) from exc
            previous_step, previous_status = state["step_id"], state["status"]
            previous_blocker_kind = state.get("blocker_kind")
            state.update({
                "step_id": step_id, "status": status,
                "evidence": _sanitize_evidence(evidence), "blocker": _sanitize(blocker),
                "blocker_kind": blocker_kind if status == "blocked" else None,
                "completion_validated": status == "completed",
                "fingerprints": validator.fingerprints(state),
                "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
            self._emit_run_events(
                state["run_id"], story_id=state.get("story_id"),
                previous_step=previous_step, previous_status=previous_status,
                step_id=step_id, status=status,
                detail={"blocker_kind": blocker_kind if status == "blocked" else None},
                previous_blocker_kind=previous_blocker_kind,
                blocker_text=blocker if status == "blocked" else "",
            )
        return state

    def _emit_run_events(
        self, run_id: str, *, story_id: str | None,
        previous_step: str | None, previous_status: str | None,
        step_id: str, status: str,
        detail: dict[str, Any] | None = None,
        previous_blocker_kind: str | None = None,
        blocker_text: str = "",
    ) -> None:
        """Append the transition events for one engine checkpoint write.

        Called inside the run lock right after the checkpoint projection is
        durable (STORY-slim-20260827024e71df170f R1).
        """
        path = run_events_path(self.root, run_id)
        common = {
            "story_id": story_id, "run_id": run_id,
            "step_id": step_id, "status": status,
        }
        blocker_kind = (detail or {}).get("blocker_kind")
        if step_id != previous_step:
            append_event(path, event="step_entered", detail=detail, **common)
        if status == "blocked":
            append_event(path, event="blocker_raised", detail=detail, **common)
        elif previous_status == "blocked":
            append_event(path, event="blocker_cleared", detail=detail, **common)
        # Authorization audit layer (STORY-slim-20260827eddbe9669c87 R1) —
        # asked carries the sanitized question, matching the store path.
        if status == "blocked" and blocker_kind == "authorization":
            append_event(
                path, event="authorization_asked",
                detail=_sanitize_evidence({
                    "blocker_kind": blocker_kind,
                    "blocker": _sanitize(blocker_text),
                }),
                **common,
            )
        elif previous_status == "blocked" and previous_blocker_kind == "authorization":
            append_event(path, event="authorization_granted", detail=detail, **common)
        if status == "completed":
            append_event(path, event="run_completed", detail=detail, **common)
        append_event(path, event="checkpoint_written", detail=detail, **common)

    def resume(self, identifier: str) -> dict[str, Any]:
        _path, state = self._find(identifier)
        if state["status"] == "completed":
            return {"decision": "completed", "run_id": state["run_id"], "reasons": []}
        if state["status"] == "blocked":
            return {
                "decision": "blocked",
                "run_id": state["run_id"],
                "reasons": [state.get("blocker") or "checkpoint is blocked"],
            }
        validator = self.definition(state["workflow_id"]).validator_factory(self.root)
        actual = validator.fingerprints(state)
        expected = state.get("fingerprints", {})
        drift = [name for name, digest in expected.items() if actual.get(name) != digest]
        if drift:
            return {
                "decision": "blocked",
                "run_id": state["run_id"],
                "story_id": state.get("story_id"),
                "reasons": [
                    "artifact drift: "
                    + ", ".join(name.replace("_", " ") for name in drift)
                ],
            }
        steps = self.definition(state["workflow_id"]).steps
        index = steps.index(state["step_id"])
        next_step = steps[index + 1] if index + 1 < len(steps) else "completed"
        return {
            "decision": "resume_at",
            "run_id": state["run_id"],
            "story_id": state.get("story_id"),
            "next_step": next_step,
            "reasons": [],
        }

    def revalidate_artifacts(self, identifier: str) -> dict[str, Any]:
        """Audit and accept changed artifacts after deterministic validation.

        This is the only transition allowed to refresh a stale run's artifact
        fingerprints. Normal checkpoints retain their compare-before-write
        behavior and therefore cannot erase drift accidentally.
        """
        _path, initial = self._find(identifier)
        with self._run_lock(initial["run_id"]):
            path, state = self._find(initial["run_id"])
            if state.get("status") != "in_progress":
                raise ContinuationError("artifact revalidation requires an active run")
            validator = self.definition(state["workflow_id"]).validator_factory(self.root)
            actual = validator.fingerprints(state)
            expected = state.get("fingerprints", {})
            if not isinstance(expected, dict):
                raise ContinuationError("invalid workflow checkpoint state")
            drift = tuple(sorted(
                name for name, digest in expected.items()
                if actual.get(name) != digest
            ))
            if not drift:
                raise ContinuationError("artifact revalidation requires drift")
            try:
                validator.revalidate_artifacts(state, drift)
            except WorkflowEvidenceError as exc:
                raise ContinuationError(str(exc)) from exc
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            audit = {
                "step_id": state["step_id"],
                "artifacts": list(drift),
                "previous_fingerprints": {name: expected[name] for name in drift},
                "validated_fingerprints": {name: actual[name] for name in drift},
                "validated_at": now,
            }
            history = state.get("revalidations", [])
            if not isinstance(history, list):
                raise ContinuationError("invalid workflow checkpoint state")
            state["revalidations"] = [*history, audit]
            state["fingerprints"] = actual
            state["updated_at"] = now
            atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
            append_event(
                run_events_path(self.root, state["run_id"]),
                event="evidence_invalidated", story_id=state.get("story_id"),
                run_id=state["run_id"], step_id=state["step_id"],
                status=state["status"],
                detail=_sanitize_evidence({"artifacts": list(drift)}),
            )
        return self.resume(initial["run_id"])

    def finish_guard(
        self, identifier: str, *, auto_resume_available: bool = False,
    ) -> dict[str, Any]:
        """Return the only authoritative, read-only turn termination decision."""
        # STORY-slim-146 Act checkpoints predate generic run files.  A Story
        # may therefore have a completed Plan run and an active legacy Act
        # checkpoint at the same time.  Never let historical completion mask
        # the active workflow.
        if not identifier.startswith("run-") and _STORY_ID.fullmatch(identifier):
            resolution = ContinuationStore(self.root)._generic_act_resolution(identifier)
            if resolution["kind"] == "completed":
                return resolution["decision"]
            if resolution["kind"] == "ambiguous":
                return ContinuationStore(self.root)._ambiguous_generic_act_result(
                    identifier, resolution,
                    auto_resume_available=auto_resume_available,
                    finish_guard=True,
                )
            legacy = ContinuationStore(self.root).read(identifier)
            generic = None
            try:
                generic = self._find(identifier)[1]
            except ContinuationError:
                pass
            rank = {"in_progress": 0, "blocked": 1, "completed": 2}
            if legacy is not None and (
                generic is None
                or rank.get(legacy.get("status"), -1)
                < rank.get(generic.get("status"), -1)
                or (
                    legacy.get("status") == "completed"
                    and generic.get("status") == "completed"
                    and generic.get("workflow_id") != "project-act"
                )
            ):
                return self._legacy_finish_guard(
                    identifier, legacy, auto_resume_available=auto_resume_available,
                )
        try:
            _path, state = self._find(identifier)
            definition = self.definition(str(state.get("workflow_id", "")))
            required = {"run_id", "workflow_id", "step_id", "status", "evidence"}
            if required - state.keys() or state.get("step_id") not in definition.steps:
                raise ContinuationError("invalid workflow checkpoint state")
            status = state.get("status")
            step = str(state["step_id"])
            base = {
                "workflow_id": state["workflow_id"],
                "run_id": state["run_id"],
                "story_id": state.get("story_id"),
                "step_id": step,
                "status": status,
                "auto_resume_available": bool(auto_resume_available),
                "resume_token": state["run_id"],
                "manual_resume_command": f"pactkit workflow resume {state['run_id']}",
            }
            if status == "completed":
                if step != definition.steps[-1] or state.get("completion_validated") is False:
                    return {
                        **base, "decision": "fail_closed", "next_step": None,
                        "reasons": ["completed state is not at the final workflow step"],
                        "reason_code": "invalid_completion", "exit_code": 2,
                    }
                try:
                    definition.validator_factory(self.root).validate(
                        state, step, state.get("evidence", {}), "completed",
                    )
                except WorkflowEvidenceError as exc:
                    return {
                        **base, "decision": "fail_closed", "next_step": None,
                        "reasons": [_sanitize(str(exc))],
                        "reason_code": "invalid_completion", "exit_code": 2,
                    }
                return {**base, "decision": "done", "next_step": None,
                        "reasons": [], "reason_code": "completed", "exit_code": 0}
            if status == "blocked":
                blocker = str(state.get("blocker", "")).strip()
                blocker_kind = state.get("blocker_kind")
                if (
                    blocker
                    and blocker_kind in BLOCKER_KINDS
                    and not _INVALID_BLOCKER.search(blocker)
                ):
                    return {**base, "decision": "await_user", "next_step": None,
                            "reasons": [blocker], "reason_code": "external_blocker",
                            "exit_code": 0}
                return {**base, "decision": "fail_closed", "next_step": None,
                        "reasons": ["blocked state lacks a verified external dependency"],
                        "reason_code": "invalid_blocker", "exit_code": 2}
            if status != "in_progress":
                raise ContinuationError("invalid workflow status")
            validator = definition.validator_factory(self.root)
            actual = validator.fingerprints(state)
            expected = state.get("fingerprints", {})
            drift = [key for key, digest in expected.items() if actual.get(key) != digest]
            index = definition.steps.index(step)
            next_step = definition.steps[index + 1] if index + 1 < len(definition.steps) else "completed"
            if drift:
                return {**base, "decision": "fail_closed", "next_step": next_step,
                        "reasons": ["artifact drift: " + ", ".join(drift)],
                        "reason_code": "artifact_drift", "exit_code": 2}
            # STORY-slim-20260827eddbe9669c87 R4: surface an open verification
            # fence on the in-progress decision — the decision stays
            # continue_current_turn, the reason demands a gate re-run.
            unknown = verification_outcome_unknown(self.root)
            return {**base, "decision": "continue_current_turn", "next_step": next_step,
                    "reasons": [unknown] if unknown else [],
                    "reason_code": "in_progress", "exit_code": 2}
        except (ContinuationError, ValueError, KeyError, TypeError) as exc:
            return {
                "decision": "fail_closed", "workflow_id": None, "run_id": None,
                "story_id": None, "step_id": None, "next_step": None,
                "status": "invalid", "reasons": [_sanitize(str(exc))],
                "reason_code": "invalid_state", "auto_resume_available": False,
                "resume_token": None, "exit_code": 2,
                "manual_resume_command": None,
            }

    def _legacy_finish_guard(
        self, story_id: str, state: dict[str, Any], *, auto_resume_available: bool,
    ) -> dict[str, Any]:
        """Project the legacy Act store into the generic finish contract."""
        run_id = "run-" + hashlib.sha256(story_id.encode()).hexdigest()[:32]
        base = {
            "workflow_id": "project-act", "run_id": run_id,
            "story_id": story_id, "step_id": state["step_id"],
            "status": state["status"],
            "auto_resume_available": bool(auto_resume_available),
            "resume_token": run_id, "legacy_checkpoint": True,
            "manual_resume_command": f"pactkit continuation resume {story_id}",
        }
        if state["status"] == "completed":
            return {**base, "decision": "done", "next_step": None,
                    "reasons": [], "reason_code": "completed", "exit_code": 0}
        if state["status"] == "blocked":
            blocker = str(state.get("blocker", "")).strip()
            blocker_kind = state.get("blocker_kind")
            if (
                blocker
                and blocker_kind in BLOCKER_KINDS
                and not _INVALID_BLOCKER.search(blocker)
            ):
                return {**base, "decision": "await_user", "next_step": None,
                        "reasons": [blocker], "reason_code": "external_blocker",
                        "exit_code": 0}
            return {**base, "decision": "fail_closed", "next_step": None,
                    "reasons": ["blocked state lacks a verified external dependency"],
                    "reason_code": "invalid_blocker", "exit_code": 2}
        resumed = ContinuationStore(self.root).resume(story_id)
        if resumed.get("decision") == "blocked":
            return {**base, "decision": "fail_closed", "next_step": None,
                    "reasons": resumed.get("reasons", []),
                    "reason_code": "artifact_drift", "exit_code": 2}
        return {**base, "decision": "continue_current_turn",
                "next_step": resumed.get("next_step"), "reasons": [],
                "reason_code": "in_progress", "exit_code": 2}

    def validate_managed_operation(
        self, identifier: str, *, workflow_id: str, operation: str, story_id: str | None = None,
    ) -> dict[str, Any]:
        """Authorize a workflow-owned write before the target is mutated."""
        _path, state = self._find(identifier)
        if state.get("status") != "in_progress":
            raise ContinuationError("managed operation requires an active run")
        if state.get("workflow_id") != workflow_id:
            raise ContinuationError("managed operation workflow mismatch")
        allowed = self.definition(workflow_id).managed_operations.get(state["step_id"], ())
        if operation not in allowed:
            raise ContinuationError(
                f"managed operation {operation} is not allowed at step {state['step_id']}"
            )
        bound = state.get("story_id")
        if story_id is not None and bound != story_id:
            raise ContinuationError("managed operation Story binding mismatch")
        return {"managed": True, "run_id": state["run_id"], "operation": operation}


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _worktree_fingerprint(root: Path) -> str:
    """Fingerprint actual tracked/untracked content, not only dirty path names."""
    status = subprocess.run(
        [
            "git", "status", "--porcelain=v1", "--untracked-files=all",
            "--", ".", ":(exclude).pactkit",
        ],
        cwd=root, capture_output=True,
    )
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--", ".", ":(exclude).pactkit"],
        cwd=root, capture_output=True,
    )
    untracked = subprocess.run(
        [
            "git", "ls-files", "--others", "--exclude-standard", "-z",
            "--", ".", ":(exclude).pactkit",
        ],
        cwd=root, capture_output=True,
    )
    if status.returncode != 0 or diff.returncode != 0 or untracked.returncode != 0:
        return "unavailable"
    digest = hashlib.sha256(status.stdout + b"\0" + diff.stdout)
    for raw_path in sorted(filter(None, untracked.stdout.split(b"\0"))):
        path = root / raw_path.decode(errors="surrogateescape")
        digest.update(b"\0" + raw_path + b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"[unreadable]")
    return digest.hexdigest()


def _sanitize(value: str | None) -> str:
    if not value:
        return ""
    clean = value.splitlines()[0].strip()
    clean = _SECRET.sub("[redacted]", clean)
    clean = _BEARER.sub("[redacted]", clean)
    clean = clean.replace(str(Path.home()), "~")
    return clean[:500]


def _sanitize_evidence(value: Any) -> Any:
    """Recursively remove secret-looking free text before persistence."""
    if isinstance(value, str):
        return _sanitize(value)
    if isinstance(value, list):
        return [_sanitize_evidence(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): "[redacted]" if _SENSITIVE_KEY.search(str(key)) else _sanitize_evidence(item)
            for key, item in value.items()
        }
    return value


class ContinuationStore:
    """Core-owned continuation store; resume intentionally never writes."""

    def __init__(self, project_root: Path):
        self.root = project_root.resolve()

    def path_for(self, story_id: str) -> Path:
        self._validate_story_id(story_id)
        return self.root / ".pactkit" / "continuations" / f"{story_id}.json"

    def _validate_story_id(self, story_id: str) -> None:
        if not _STORY_ID.fullmatch(story_id):
            raise ContinuationError(f"invalid Story ID: {story_id}")

    def _paths(self, story_id: str) -> tuple[Path, Path]:
        return (
            self.root / "docs" / "specs" / f"{story_id}.md",
            self.root / "docs" / "product" / "sprint_board.md",
        )

    def _story_fact_path(self, story_id: str) -> Path | None:
        directory = self.root / "docs" / "product" / "stories"
        return directory / f"{story_id}.yaml" if directory.is_dir() else None

    def _generic_act_resolution(self, story_id: str) -> dict[str, Any]:
        """Resolve v2 Act authority without collapsing ambiguity into absence.

        The legacy checkpoint remains immutable audit evidence. It must not,
        however, make a Story resumable after the v2 Act engine has completed
        that same Story. This accepts only completed ``project-act`` runs
        whose own finish guard validates all completion evidence; active,
        malformed, or conflicting v2 files leave the legacy checkpoint
        authoritative and therefore fail closed.
        """
        engine = ContinuationEngine(self.root)
        candidates: list[tuple[str, dict[str, Any]]] = []
        ambiguous_paths: list[str] = []
        active_paths: list[str] = []
        for path in sorted(engine.directory.glob("run-*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                ambiguous_paths.append(path.name)
                continue
            if not isinstance(raw, dict):
                ambiguous_paths.append(path.name)
                continue
            if raw.get("story_id") != story_id or raw.get("workflow_id") != "project-act":
                continue
            try:
                state = engine.read(path.stem)
            except ContinuationError:
                # This file explicitly claims the same Story, so malformed
                # state is an ambiguous competing authority and must block
                # legacy retirement.
                ambiguous_paths.append(path.name)
                continue
            if state.get("status") in {"in_progress", "blocked"}:
                active_paths.append(path.name)
                continue
            if state.get("status") != "completed":
                ambiguous_paths.append(path.name)
                continue
            decision = engine.finish_guard(str(state["run_id"]))
            if decision.get("decision") != "done" or decision.get("exit_code") != 0:
                ambiguous_paths.append(path.name)
                continue
            candidates.append((str(state.get("updated_at", "")), decision))
        latest = (
            max(candidates, key=lambda item: (item[0], item[1]["run_id"]))[1]
            if candidates else None
        )
        if ambiguous_paths:
            return {
                "kind": "ambiguous", "decision": latest,
                "paths": sorted(ambiguous_paths),
            }
        if active_paths:
            return {
                "kind": "active", "decision": latest,
                "paths": sorted(active_paths),
            }
        if not candidates:
            return {"kind": "absent", "decision": None, "paths": []}
        # Multiple completed runs are historical facts, not a competing active
        # authority. Prefer the latest deterministic completion projection.
        return {"kind": "completed", "decision": latest, "paths": []}

    def _ambiguous_generic_act_result(
        self, story_id: str, resolution: dict[str, Any], *,
        auto_resume_available: bool = False, finish_guard: bool = False,
    ) -> dict[str, Any]:
        """Return a stable terminal projection for ambiguous v2 recovery state."""
        verified = resolution.get("decision")
        paths = resolution.get("paths", [])
        reasons = ["ambiguous v2 workflow state: " + ", ".join(paths)]
        result = {
            "decision": "fail_closed", "story_id": story_id,
            "status": "completed" if verified is not None else "invalid",
            "run_id": verified.get("run_id") if verified is not None else None,
            "reasons": reasons, "reason_code": "ambiguous_v2_state",
        }
        if not finish_guard:
            return result
        return {
            **result,
            "workflow_id": "project-act", "step_id": (
                verified.get("step_id") if verified is not None else None
            ),
            "next_step": None, "auto_resume_available": bool(auto_resume_available),
            "resume_token": verified.get("run_id") if verified is not None else None,
            "manual_resume_command": None, "exit_code": 2,
        }

    def _fingerprints(self, story_id: str) -> dict[str, str]:
        spec, board = self._paths(story_id)
        fingerprints = {
            "spec": _fingerprint(spec),
            "git_head": _git_head(self.root),
            "worktree": _worktree_fingerprint(self.root),
        }
        story_fact = self._story_fact_path(story_id)
        if story_fact is not None:
            fingerprints["story_fact"] = _fingerprint(story_fact)
        else:
            fingerprints["board"] = _fingerprint(board)
        return fingerprints

    def read(self, story_id: str) -> dict[str, Any] | None:
        self._validate_story_id(story_id)
        path = self.path_for(story_id)
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContinuationError(f"corrupt checkpoint: {path.name}: {exc}") from exc
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
            raise ContinuationError(f"unsupported checkpoint schema: {path.name}")
        required = {
            "story_id", "command", "phase", "step_id", "status", "evidence",
            "fingerprints", "blocker", "updated_at",
        }
        if required - set(value):
            raise ContinuationError(f"invalid checkpoint state: {path.name}")
        if value["story_id"] != story_id or value["command"] != "$project-act":
            raise ContinuationError(f"checkpoint Story or command mismatch: {path.name}")
        if value["step_id"] not in STEPS or value["status"] not in STATUSES:
            raise ContinuationError(f"invalid checkpoint state: {path.name}")
        if not isinstance(value["evidence"], dict) or not isinstance(value["fingerprints"], dict):
            raise ContinuationError(f"invalid checkpoint state: {path.name}")
        return value

    def legacy_handoff(self, story_id: str) -> bool:
        """Whether context.md holds only an unverifiable pre-checkpoint handoff."""
        self._validate_story_id(story_id)
        context = self.root / "docs" / "product" / "context.md"
        if not context.exists():
            return False
        try:
            return any(match.group("story") == story_id for match in _LEGACY_HANDOFF.finditer(
                context.read_text(encoding="utf-8")
            ))
        except OSError:
            return False

    def deny(self, story_id: str, reason: str) -> dict[str, Any]:
        """Record an explicit authorization denial (STORY-slim-20260827eddbe9669c87 R2).

        The only machine-expressible "no" in the state machine: appends an
        ``authorization_denied`` audit event and rewrites the blocked
        checkpoint so the blocker text itself carries the decision.  The
        fingerprints keep the last trusted baseline (a denied handoff is
        not a new verified baseline — same semantics as any blocked write).
        """
        self._validate_story_id(story_id)
        reason = _sanitize(reason.strip())
        if not reason:
            raise ContinuationError("deny requires a non-empty reason")
        with self._story_lock(story_id):
            state = self.read(story_id)
            if state is None:
                raise ContinuationError(f"no checkpoint for {story_id}")
            if state["status"] != "blocked":
                raise ContinuationError("only a blocked checkpoint can be denied")
            if state.get("blocker_kind") != "authorization":
                raise ContinuationError("deny requires an authorization blocker")
            if str(state.get("blocker", "")).startswith("denied:"):
                raise ContinuationError("authorization already denied")
            value = {
                **state,
                "blocker": _sanitize(f"denied: {reason}"),
                "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            atomic_write(
                self.path_for(story_id),
                json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            )
            append_event(
                story_events_path(self.root, story_id),
                event="authorization_denied", story_id=story_id, run_id=None,
                step_id=state["step_id"], status="blocked",
                detail=_sanitize_evidence({"reason": reason}),
            )
        return value

    def status(self, story_id: str) -> dict[str, Any]:
        """Read-only state summary, including explicit legacy-handoff detection."""
        self._validate_story_id(story_id)
        resolution = self._generic_act_resolution(story_id)
        if resolution["kind"] == "ambiguous":
            return self._ambiguous_generic_act_result(story_id, resolution)
        if resolution["kind"] == "active":
            # An active v2 workflow run leaves the legacy checkpoint
            # authoritative and fails closed — previously this block relied
            # on a git-probe drift quirk rather than explicit semantics
            # (STORY-slim-202608267c3989223b4d R5 follow-up).
            return {
                "decision": "blocked", "story_id": story_id,
                "reasons": [
                    "active v2 workflow run exists: " + ", ".join(resolution["paths"])
                ],
            }
        completed = resolution["decision"]
        if resolution["kind"] == "completed":
            return {
                "decision": "completed", "story_id": story_id,
                "run_id": completed["run_id"], "status": "completed",
                "reasons": [], "superseded_legacy_checkpoint": True,
            }
        state = self.read(story_id)
        if state is not None:
            return state
        reasons = []
        if self.legacy_handoff(story_id):
            reasons.append("unverifiable legacy handoff; create a preflight checkpoint")
        return {
            "decision": "start_fresh", "story_id": story_id,
            "next_step": "preflight", "reasons": reasons,
        }

    @contextmanager
    def _story_lock(self, story_id: str):
        """Serialize a Story's read/validate/write transaction across processes."""
        lock_path = self.path_for(story_id).with_suffix(".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
        acquired = False
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        try:
            while not acquired:
                try:
                    if os.name == "nt":  # pragma: no cover - exercised on Windows CI
                        import msvcrt

                        handle.seek(0, os.SEEK_END)
                        if handle.tell() == 0:
                            handle.write(b"0")
                            handle.flush()
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except (BlockingIOError, PermissionError, OSError) as exc:
                    if time.monotonic() >= deadline:
                        raise ContinuationError(
                            f"checkpoint lock timeout: {lock_path.name}"
                        ) from exc
                    time.sleep(LOCK_POLL_SECONDS)
            yield
        finally:
            if acquired:
                if os.name == "nt":  # pragma: no cover - exercised on Windows CI
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def checkpoint(
        self,
        story_id: str,
        *,
        step_id: str,
        evidence: dict[str, Any],
        status: str = "in_progress",
        phase: str = "",
        blocker: str = "",
        blocker_kind: str | None = None,
        fresh: bool = False,
    ) -> dict[str, Any]:
        with self._story_lock(story_id):
            return self._checkpoint_locked(
                story_id, step_id=step_id, evidence=evidence, status=status,
                phase=phase, blocker=blocker, blocker_kind=blocker_kind, fresh=fresh,
            )

    def _checkpoint_locked(
        self,
        story_id: str,
        *,
        step_id: str,
        evidence: dict[str, Any],
        status: str = "in_progress",
        phase: str = "",
        blocker: str = "",
        blocker_kind: str | None = None,
        fresh: bool = False,
    ) -> dict[str, Any]:
        self._validate_story_id(story_id)
        if step_id not in STEPS:
            raise ContinuationError(f"invalid step_id: {step_id}")
        if status not in STATUSES:
            raise ContinuationError(f"invalid status: {status}")
        if not isinstance(evidence, dict):
            raise ContinuationError("evidence must be a JSON object")
        if status == "blocked" and not blocker.strip():
            raise ContinuationError("blocked checkpoint requires a blocker with a manual next action")
        if blocker_kind is not None and blocker_kind not in BLOCKER_KINDS:
            raise ContinuationError("invalid blocker kind")
        self._validate_step_evidence(story_id, step_id, evidence, status)
        if fresh and (step_id != "preflight" or status != "in_progress"):
            raise ContinuationError("--fresh requires an in_progress preflight checkpoint")

        previous = self.read(story_id)
        if previous is None and step_id != "preflight":
            raise ContinuationError("checkpoint cycle must start at preflight")
        if previous and previous["status"] == "completed":
            if not fresh:
                raise ContinuationError("completed checkpoint is immutable; use --fresh to start new work")
        elif previous and previous["status"] == "blocked":
            if not fresh and status != "blocked":
                stale = self._stale_reasons(previous, story_id)
                if stale:
                    raise ContinuationError("stale checkpoint: " + "; ".join(stale))
        elif fresh:
            raise ContinuationError("--fresh is only valid after a completed or blocked checkpoint")
        if previous and not fresh and status != "blocked":
            stale = self._stale_reasons(previous, story_id)
            if stale:
                raise ContinuationError("stale checkpoint: " + "; ".join(stale))
        if previous and not fresh and STEPS.index(step_id) < STEPS.index(previous["step_id"]):
            raise ContinuationError("checkpoint step cannot move backward")
        if (
            previous and not fresh
            and STEPS.index(step_id) > STEPS.index(previous["step_id"]) + 1
        ):
            raise ContinuationError("cannot skip checkpoint step")
        if fresh and previous:
            self._archive_completed(story_id, previous)
        if status == "completed":
            self._validate_completion(step_id, evidence, story_id)
        value = {
            "schema_version": SCHEMA_VERSION,
            "story_id": story_id,
            "command": "$project-act",
            "phase": _sanitize(phase),
            "step_id": step_id,
            "status": status,
            "evidence": _sanitize_evidence(evidence),
            # A blocked write is a handoff, not a new verified baseline. Keep
            # the last trusted fingerprints so later progress cannot silently
            # accept inputs that changed while the workflow was blocked.
            "fingerprints": (
                previous["fingerprints"]
                if status == "blocked" and previous and not fresh
                else self._fingerprints(story_id)
            ),
            "blocker": _sanitize(blocker),
            "blocker_kind": blocker_kind if status == "blocked" else None,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        atomic_write(self.path_for(story_id), json.dumps(value, indent=2, ensure_ascii=False) + "\n")
        self._emit_checkpoint_events(story_id, previous, value, fresh=fresh)
        return value

    def _emit_checkpoint_events(
        self, story_id: str, previous: dict[str, Any] | None,
        value: dict[str, Any], *, fresh: bool,
    ) -> None:
        """Append transition events for one story checkpoint write.

        Called inside the story lock right after the projection is durable
        (STORY-slim-20260827024e71df170f R1).  The overwrite-style JSON
        keeps its readers; the event log holds the history it discards.
        """
        path = story_events_path(self.root, story_id)
        previous_step = previous.get("step_id") if previous else None
        previous_status = previous.get("status") if previous else None
        previous_kind = previous.get("blocker_kind") if previous else None
        common = {
            "story_id": story_id, "run_id": None,
            "step_id": value["step_id"], "status": value["status"],
        }
        if value["step_id"] != previous_step:
            append_event(
                path, event="step_entered",
                detail=_sanitize_evidence({"first": previous is None}), **common,
            )
        if value["status"] == "blocked":
            append_event(
                path, event="blocker_raised",
                detail=_sanitize_evidence({"blocker_kind": value.get("blocker_kind")}),
                **common,
            )
        elif previous_status == "blocked":
            append_event(path, event="blocker_cleared", **common)
        # Authorization audit layer (STORY-slim-20260827eddbe9669c87 R1):
        # the decision record, not the waiting record — asked carries the
        # sanitized question, granted fires when an authorization blocker
        # resolves, denied only comes from the explicit deny action.
        if value["status"] == "blocked" and value.get("blocker_kind") == "authorization":
            append_event(
                path, event="authorization_asked",
                detail=_sanitize_evidence({"blocker": value.get("blocker", "")}),
                **common,
            )
        elif previous_status == "blocked" and previous_kind == "authorization":
            append_event(path, event="authorization_granted", **common)
        if value["status"] == "completed":
            append_event(path, event="run_completed", **common)
        append_event(
            path, event="checkpoint_written",
            detail=_sanitize_evidence({"phase": value.get("phase", ""), "fresh": fresh}),
            **common,
        )

    def _validate_step_evidence(
        self, story_id: str, step_id: str, evidence: dict[str, Any], status: str,
    ) -> None:
        """Validate deterministic proof for each safe boundary."""
        if status == "blocked":
            return
        valid = False
        if step_id == "preflight":
            valid = evidence.get("spec_lint") == "pass"
        elif step_id in {"red", "green"}:
            tests = evidence.get("story_tests")
            expected = 1 if step_id == "red" else 0
            valid = isinstance(tests, dict) and tests.get("exit_code") == expected
        elif step_id == "regression_lint":
            valid = evidence.get("regression") == "pass" and evidence.get("lint") == "pass"
        elif step_id == "sync_coverage":
            valid = status == "completed"
        if not valid:
            raise ContinuationError(f"invalid {step_id} evidence")
        if step_id == "preflight":
            self._require_valid_spec(story_id)
            try:
                get_workflow("project-act").validator_factory(self.root).validate(
                    {"story_id": story_id}, step_id, evidence, status,
                )
            except WorkflowEvidenceError as exc:
                raise ContinuationError(str(exc)) from exc

    def _require_valid_spec(self, story_id: str) -> None:
        """Run the canonical structural linter; never trust evidence prose alone."""
        from pactkit.skills.spec_linter import validate_spec

        spec_path = self._paths(story_id)[0]
        if not validate_spec(str(spec_path)).passed:
            raise ContinuationError("Spec lint failed")

    def _archive_completed(self, story_id: str, state: dict[str, Any]) -> None:
        """Preserve immutable completion evidence before beginning a new cycle."""
        timestamp = state.get("updated_at", "unknown").replace(":", "-")
        archive = self.root / ".pactkit" / "continuations" / "history" / f"{story_id}-{timestamp}.json"
        content = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
        if archive.exists():
            try:
                if archive.read_text(encoding="utf-8") == content:
                    return
            except OSError as exc:
                raise ContinuationError(f"cannot verify checkpoint archive: {archive.name}") from exc
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
            archive = archive.with_name(f"{archive.stem}-{digest}.json")
            if archive.exists():
                try:
                    if archive.read_text(encoding="utf-8") == content:
                        return
                except OSError as exc:
                    raise ContinuationError(f"cannot verify checkpoint archive: {archive.name}") from exc
                raise ContinuationError(f"checkpoint archive collision: {archive.name}")
        atomic_write(archive, content)
        append_event(
            story_events_path(self.root, story_id), event="run_archived",
            story_id=story_id, run_id=None, step_id=state.get("step_id"),
            status=state.get("status"),
            detail=_sanitize_evidence({"archive": archive.name}),
        )

    def _validate_completion(self, step_id: str, evidence: dict[str, Any], story_id: str) -> None:
        required = {
            "spec_lint", "story_tests", "regression", "lint", "coverage",
            "acceptance_coverage", "board_tasks",
        }
        if step_id != "sync_coverage" or required - set(evidence):
            raise ContinuationError("missing completion evidence")
        if evidence["spec_lint"] != "pass" or evidence["regression"] != "pass" or evidence["lint"] != "pass":
            raise ContinuationError("missing completion evidence")
        self._require_valid_spec(story_id)
        if not isinstance(evidence["coverage"], dict) or not evidence["coverage"]:
            raise ContinuationError("missing completion evidence")
        if not isinstance(evidence["story_tests"], dict) or evidence["story_tests"].get("exit_code") != 0:
            raise ContinuationError("missing completion evidence")
        story_fact = self._story_fact_path(story_id)
        if story_fact is not None:
            from pactkit.governance import GovernanceError, StoryRepository

            try:
                record = StoryRepository(self.root).load(story_id)
            except GovernanceError as exc:
                raise ContinuationError("missing completion evidence") from exc
            if any(not task["completed"] for task in record["tasks"]):
                raise ContinuationError("missing completion evidence")
            board_tasks = [task["title"] for task in record["tasks"]]
        else:
            board = self._paths(story_id)[1]
            board_text = board.read_text(encoding="utf-8") if board.exists() else ""
            story_block = next(
                (match.group(0) for match in _STORY_BLOCK.finditer(board_text) if match.group("id") == story_id),
                "",
            )
            if not story_block or "- [ ]" in story_block:
                raise ContinuationError("missing completion evidence")
            board_tasks = [
                match.group(1).strip()
                for match in re.finditer(r"^- \[x\] (.+)$", story_block, re.MULTILINE)
            ]
        evidence_tasks = evidence["board_tasks"]
        if (
            not isinstance(evidence_tasks, list)
            or not all(isinstance(task, str) and task.strip() for task in evidence_tasks)
            or set(evidence_tasks) != set(board_tasks)
        ):
            raise ContinuationError("board task evidence mismatch")
        spec = self._paths(story_id)[0]
        spec_text = spec.read_text(encoding="utf-8") if spec.exists() else ""
        required = set(_MUST_REQUIREMENT.findall(spec_text))
        missing_coverage = required - set(evidence["coverage"])
        if missing_coverage:
            raise ContinuationError(
                "missing completion coverage: " + ", ".join(sorted(missing_coverage))
            )
        acceptance_coverage = evidence["acceptance_coverage"]
        if not isinstance(acceptance_coverage, dict):
            raise ContinuationError("missing completion evidence")
        acceptance_criteria = set(_ACCEPTANCE_CRITERION.findall(spec_text))
        missing_acceptance = acceptance_criteria - set(acceptance_coverage)
        if missing_acceptance:
            raise ContinuationError(
                "missing completion acceptance coverage: "
                + ", ".join(sorted(missing_acceptance))
            )
        for mapping in (evidence["coverage"], acceptance_coverage):
            if any(
                not isinstance(items, list)
                or not items
                or not all(isinstance(item, str) and item.strip() for item in items)
                for items in mapping.values()
            ):
                raise ContinuationError("empty completion traceability evidence")

    def resume(self, story_id: str) -> dict[str, Any]:
        self._validate_story_id(story_id)
        resolution = self._generic_act_resolution(story_id)
        if resolution["kind"] == "ambiguous":
            return self._ambiguous_generic_act_result(story_id, resolution)
        if resolution["kind"] == "active":
            # An active v2 workflow run leaves the legacy checkpoint
            # authoritative and fails closed — previously this block relied
            # on a git-probe drift quirk rather than explicit semantics
            # (STORY-slim-202608267c3989223b4d R5 follow-up).
            return {
                "decision": "blocked", "story_id": story_id,
                "reasons": [
                    "active v2 workflow run exists: " + ", ".join(resolution["paths"])
                ],
            }
        completed = resolution["decision"]
        if resolution["kind"] == "completed":
            return {
                "decision": "completed", "story_id": story_id,
                "run_id": completed["run_id"], "reasons": [],
                "superseded_legacy_checkpoint": True,
            }
        state = self.read(story_id)
        if state is None:
            return self.status(story_id)
        reasons: list[str] = []
        # Core contract validation is a deterministic, read-only recovery preflight.
        # It protects newly deployed runtime skills from silently missing a policy.
        from pactkit.prompts.skills import validate_skill_recovery_contracts

        reasons.extend(validate_skill_recovery_contracts())
        if state["status"] == "blocked":
            reasons.append("checkpoint is blocked: " + (state.get("blocker") or "manual action required"))
        if state["status"] == "completed":
            # Completed is terminal. Phase 4 intentionally generates derived
            # context/graph files after the checkpoint; reporting those as
            # stale would misleadingly imply that execution can resume.
            return {
                "decision": "blocked", "story_id": story_id,
                "reasons": reasons + ["checkpoint is completed"],
            }
        peers = self._active_peer_story_ids(story_id)
        if peers:
            reasons.append("competing active checkpoints: " + ", ".join(peers))
        reasons.extend(self._stale_reasons(state, story_id))
        # STORY-slim-20260827eddbe9669c87 R4: an open verification fence means
        # the last gate attempt never produced a verdict — block until re-run.
        unknown = verification_outcome_unknown(self.root)
        if unknown:
            reasons.append(unknown)
        if reasons:
            return {"decision": "blocked", "story_id": story_id, "reasons": reasons}
        return {
            "decision": "resume_at",
            "story_id": story_id,
            "next_step": _NEXT_STEP[state["step_id"]],
            "reasons": [],
        }

    def _stale_reasons(self, state: dict[str, Any], story_id: str) -> list[str]:
        current = self._fingerprints(story_id)
        reasons: list[str] = []
        expected = state.get("fingerprints", {})
        for key in ("spec", "story_fact", "board"):
            if key in expected and expected[key] != current.get(key):
                reasons.append(f"{key.replace('_', ' ')} fingerprint changed")
        # A transiently failing git probe ("unavailable" CURRENT) is
        # inconclusive, not drift; an ABSENT expected key (v1 checkpoint
        # without git fingerprints) is nothing to compare
        # (STORY-slim-202608267c3989223b4d R5).
        if (
            "git_head" in expected
            and expected["git_head"] not in ("unavailable", current["git_head"])
            and current["git_head"] != "unavailable"
        ):
            reasons.append("git HEAD changed")
        if (
            "worktree" in expected
            and expected["worktree"] not in ("unavailable", current["worktree"])
            and current["worktree"] != "unavailable"
        ):
            reasons.append("worktree fingerprint changed")
        return reasons

    def _active_peer_story_ids(self, story_id: str) -> list[str]:
        """List other non-terminal checkpoint Stories without trusting their contents."""
        directory = self.root / ".pactkit" / "continuations"
        if not directory.exists():
            return []
        peers: list[str] = []
        for path in sorted(directory.glob("*.json")):
            if not _STORY_ID.fullmatch(path.stem):
                continue
            if path.stem == story_id:
                continue
            try:
                state = self.read(path.stem)
            except ContinuationError:
                peers.append(path.stem)
                continue
            if state and state.get("status") in {"in_progress", "blocked"}:
                peers.append(path.stem)
        return peers

    def diagnostics(self, *, include_completed: bool = False) -> list[str]:
        """Return corrupt/stale state warnings without mutating checkpoints.

        Doctor only needs actionable corruption or inconsistency. Garden also
        requests completed checkpoints so it can flag cleanup candidates.
        """
        directory = self.root / ".pactkit" / "continuations"
        warnings: list[str] = []
        context = self.root / "docs" / "product" / "context.md"
        if context.exists():
            try:
                for match in _LEGACY_HANDOFF.finditer(context.read_text(encoding="utf-8")):
                    story_id = match.group("story")
                    if not self.path_for(story_id).exists():
                        warnings.append(f"Unverifiable legacy handoff: {story_id}")
            except OSError:
                pass
        if not directory.exists():
            return warnings
        for path in sorted(directory.glob("*.json")):
            if not _STORY_ID.fullmatch(path.stem):
                continue
            try:
                state = self.read(path.stem)
                if state and state["status"] == "completed" and include_completed:
                    warnings.append(f"Completed continuation retained: {path.stem}")
                elif state and state["status"] == "completed":
                    continue
                elif state and self.resume(path.stem)["decision"] == "blocked":
                    warnings.append(f"Continuation needs attention: {path.stem}")
            except ContinuationError:
                warnings.append(f"Continuation corrupt: {path.name}")
        return warnings
