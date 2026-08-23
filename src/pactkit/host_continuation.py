"""Host-neutral bounded continuation protocol."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from pactkit.continuation import ContinuationEngine, ContinuationError, _sanitize
from pactkit.utils import atomic_write
from pactkit.workflow_registry import EXECUTION_RELIABILITY_REGISTRY

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_LEASE_SECONDS = 300
RESUME_FAILURE_REASONS = frozenset({"permission_denied", "artifact_drift"})


@dataclass(frozen=True)
class HostCapabilities:
    completion_hook: bool = False
    session_reentry: bool = False

    @property
    def auto_resume_available(self) -> bool:
        return self.completion_hook and self.session_reentry


class HostContinuationRunner:
    def __init__(
        self, engine: ContinuationEngine, capabilities: HostCapabilities, *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS, lease_seconds: int = DEFAULT_LEASE_SECONDS,
        owner: str = "host-runner",
    ):
        if max_attempts < 1 or lease_seconds < 1:
            raise ValueError("runner limits must be positive")
        self.engine = engine
        self.capabilities = capabilities
        self.max_attempts = max_attempts
        self.lease_seconds = lease_seconds
        self.owner = owner

    @staticmethod
    def _digest(state: dict[str, Any]) -> str:
        payload = {"step_id": state.get("step_id"), "evidence": state.get("evidence", {})}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _session_reference(session_locator: str) -> str:
        sanitized = _sanitize(session_locator)
        return "sha256:" + hashlib.sha256(sanitized.encode()).hexdigest()

    def after_model_turn(self, identifier: str, *, session_locator: str) -> dict[str, Any]:
        decision = self.engine.finish_guard(
            identifier, auto_resume_available=self.capabilities.auto_resume_available,
        )
        if (
            decision["decision"] == "fail_closed"
            and decision.get("reason_code") == "artifact_drift"
            and self.capabilities.auto_resume_available
        ):
            return self.record_resume_failure(
                identifier, reason_code="artifact_drift", session_locator=session_locator,
            )
        if decision["decision"] != "continue_current_turn":
            return decision
        if not self.capabilities.auto_resume_available:
            return {**decision, "reason_code": "host_reentry_unavailable"}
        if decision.get("legacy_checkpoint"):
            return self._after_legacy_turn(
                identifier, decision=decision, session_locator=session_locator,
            )
        run_id = decision["run_id"]
        now = datetime.now(timezone.utc)
        with self.engine._run_lock(run_id):
            path, state = self.engine._find(run_id)
            if state.get("status") == "completed":
                return self.engine.finish_guard(run_id)
            previous = state.get("host_continuation", {})
            if not isinstance(previous, dict):
                raise ContinuationError("corrupt host continuation state")
            expiry = previous.get("lease_expires_at")
            try:
                lease_active = bool(expiry and datetime.fromisoformat(expiry) > now)
            except (TypeError, ValueError) as exc:
                raise ContinuationError("corrupt host continuation lease") from exc
            if previous.get("owner") not in (None, self.owner) and lease_active:
                return {**decision, "decision": "await_user",
                        "reason_code": "lease_contended", "exit_code": 0}
            digest = self._digest(state)
            attempt = int(previous.get("attempt", 0)) + 1
            if previous.get("progress_digest") == digest:
                reason = "no_progress"
            elif attempt > self.max_attempts:
                reason = "attempt_limit"
            else:
                reason = "resume_scheduled"
            record = {
                "run_id": run_id, "owner": self.owner, "attempt": attempt,
                "step_id": state["step_id"], "progress_digest": digest,
                "session_locator": self._session_reference(session_locator),
                "lease_expires_at": (
                    (now + timedelta(seconds=self.lease_seconds)).isoformat()
                    if reason == "resume_scheduled" else None
                ),
                "termination_reason": reason, "updated_at": now.isoformat(),
            }
            state["host_continuation"] = record
            if reason != "resume_scheduled":
                state["status"] = "blocked"
                state["blocker"] = (
                    f"External host intervention required after {reason}"
                )
                state["blocker_kind"] = "external_state"
            atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        if reason != "resume_scheduled":
            return {**decision, "decision": "await_user", "attempt": attempt,
                    "reason_code": reason, "exit_code": 0}
        return {**decision, "decision": "resume_session", "attempt": attempt,
                "session_locator": self._session_reference(session_locator),
                "reason_code": reason}

    def _after_legacy_turn(
        self, identifier: str, *, decision: dict[str, Any], session_locator: str,
    ) -> dict[str, Any]:
        from pactkit.continuation import ContinuationStore

        story_id = decision.get("story_id") or identifier
        state = ContinuationStore(self.engine.root).read(story_id)
        if state is None:
            raise ContinuationError("legacy checkpoint not found")
        run_id = decision["run_id"]
        host_dir = self.engine.root / ".pactkit" / "continuations" / "hosts"
        host_path = host_dir / f"{run_id}.json"
        previous: dict[str, Any] = {}
        if host_path.exists():
            try:
                previous = json.loads(host_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ContinuationError("corrupt legacy host continuation state") from exc
        digest = self._digest(state)
        attempt = int(previous.get("attempt", 0)) + 1
        if previous.get("progress_digest") == digest:
            reason = "no_progress"
        elif attempt > self.max_attempts:
            reason = "attempt_limit"
        else:
            reason = "resume_scheduled"
        record = {
            "run_id": run_id, "owner": self.owner, "attempt": attempt,
            "step_id": state["step_id"], "progress_digest": digest,
            "session_locator": self._session_reference(session_locator),
            "lease_expires_at": None, "termination_reason": reason,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_write(host_path, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        if reason != "resume_scheduled":
            ContinuationStore(self.engine.root).checkpoint(
                story_id,
                step_id=state["step_id"],
                evidence=state.get("evidence", {}),
                status="blocked",
                phase=state.get("phase", ""),
                blocker=f"External host intervention required after {reason}",
                blocker_kind="external_state",
            )
            return {**decision, "decision": "await_user", "attempt": attempt,
                    "reason_code": reason, "exit_code": 0}
        return {**decision, "decision": "resume_session", "attempt": attempt,
                "session_locator": self._session_reference(session_locator),
                "reason_code": reason}

    def before_operation(self, identifier: str, operation: str) -> dict[str, Any]:
        decision = self.engine.finish_guard(identifier)
        manual = {op for item in EXECUTION_RELIABILITY_REGISTRY.values() for op in item.manual_operations}
        if operation in manual:
            return {**decision, "decision": "await_user",
                    "reason_code": "manual_operation", "exit_code": 0}
        return decision

    def record_resume_failure(
        self, identifier: str, *, reason_code: str, session_locator: str,
    ) -> dict[str, Any]:
        """Persist a host resume failure as an externally recoverable block."""
        if reason_code not in RESUME_FAILURE_REASONS:
            raise ValueError(f"unsupported resume failure: {reason_code}")
        initial = self.engine.read(identifier)
        run_id = initial["run_id"]
        now = datetime.now(timezone.utc)
        with self.engine._run_lock(run_id):
            path, state = self.engine._find(run_id)
            previous = state.get("host_continuation", {})
            attempt = int(previous.get("attempt", 0)) + 1 if isinstance(previous, dict) else 1
            state["host_continuation"] = {
                "run_id": run_id, "owner": self.owner, "attempt": attempt,
                "step_id": state["step_id"], "progress_digest": self._digest(state),
                "session_locator": self._session_reference(session_locator),
                "lease_expires_at": None,
                "termination_reason": reason_code, "updated_at": now.isoformat(),
            }
            state["status"] = "blocked"
            state["blocker_kind"] = "external_state"
            state["blocker"] = f"External host intervention required after {reason_code}"
            state["updated_at"] = now.isoformat()
            atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        return {
            "decision": "await_user", "workflow_id": state["workflow_id"],
            "run_id": run_id, "story_id": state.get("story_id"),
            "step_id": state["step_id"], "next_step": None, "status": "blocked",
            "reasons": [state["blocker"]], "reason_code": reason_code,
            "auto_resume_available": self.capabilities.auto_resume_available,
            "resume_token": run_id,
            "manual_resume_command": f"pactkit workflow resume {run_id}",
            "attempt": attempt, "exit_code": 0,
        }


def evaluate_agent_final(
    engine: ContinuationEngine, identifier: str, output: str,
) -> dict[str, Any]:
    """Conformance hook: agent prose never overrides persisted workflow state."""
    del output
    decision = engine.finish_guard(identifier)
    return {**decision, "accepted": decision["decision"] in {"done", "await_user"}}
