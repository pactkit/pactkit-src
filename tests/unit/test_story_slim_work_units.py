import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest


def _initialize_work_unit_project(root: Path) -> None:
    config = root / ".codex/pactkit.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("developer: test\n", encoding="utf-8")
    (root / "docs/product/stories").mkdir(parents=True, exist_ok=True)
    (root / "docs/architecture/graphs").mkdir(parents=True, exist_ok=True)


def _write_plan_inputs(root: Path, story_id: str = "STORY-slim-999") -> Path:
    _initialize_work_unit_project(root)
    spec = root / "docs/specs" / f"{story_id}.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    source_specs = Path(__file__).parents[2] / "docs/specs"
    source_spec = source_specs / "STORY-slim-20260823d854b0cf1875.md"
    spec.write_text(
        source_spec.read_text(encoding="utf-8").replace(
            "STORY-slim-20260823d854b0cf1875", story_id,
        ),
        encoding="utf-8",
    )
    # The canonical Spec declares these dependencies.  Copying them preserves
    # the production linter contract instead of weakening the lint gate.
    for dependency in (
        "STORY-slim-147",
        "STORY-slim-2026082381e832771d4e",
        "STORY-slim-20260823de7e85d6042a",
    ):
        source = source_specs / f"{dependency}.md"
        (spec.parent / source.name).write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
    graph = root / "docs/architecture/graphs/system_design.mmd"
    graph.parent.mkdir(parents=True, exist_ok=True)
    graph.write_text("graph TD\n A-->B\n", encoding="utf-8")
    return spec


def _advance_plan_to_step(engine, run_id, root, story_id, target_step="finalize_plan"):
    """Submit the minimum Core-validated evidence for every Plan WorkUnit."""
    from pactkit.workflow_engine import EvidenceReceipt

    claims_by_step = {
        "preflight": {"guard": "pass"},
        "clarification": {"clarification_resolved": True},
        "archaeology": {"trace": ["workflow_engine"]},
        "story_identity": {"story_id": story_id},
        "spec_scaffold": {},
        "spec_content": {},
        "spec_security": {"security_scoped": True},
        "spec_lint": {},
    }
    files_by_step = {
        "spec_scaffold": [f"docs/specs/{story_id}.md"],
        "spec_content": [
            f"docs/specs/{story_id}.md",
            "docs/architecture/graphs/system_design.mmd",
        ],
        "spec_security": [f"docs/specs/{story_id}.md"],
        "spec_lint": [f"docs/specs/{story_id}.md"],
    }
    while engine.status(run_id)["step_id"] != target_step:
        unit = engine.acquire(
            run_id, owner="codex", idempotency_key=f"acquire-{engine.status(run_id)['step_id']}",
        )
        receipt = EvidenceReceipt.for_files(
            unit, owner="codex", root=root,
            files=files_by_step.get(unit.step_id, []),
            claims=claims_by_step[unit.step_id],
        )
        result = engine.submit(
            unit.unit_id, receipt, owner="codex",
            idempotency_key=f"submit-{unit.step_id}",
        )
        assert result.attempt_status == "succeeded", result


def _advance_plan_to_finalize(engine, run_id, root, story_id):
    _advance_plan_to_step(engine, run_id, root, story_id)


def _prepare_act_run(root: Path, story_id: str = "STORY-slim-999"):
    from pactkit.governance import BoardRenderer, StoryRepository
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _write_plan_inputs(root, story_id)
    repository = StoryRepository(root)
    repository.add(story_id, "Act story", ["one", "two"])
    board = root / "docs/product/sprint_board.md"
    board.parent.mkdir(parents=True, exist_ok=True)
    board.write_text(BoardRenderer(repository).render(), encoding="utf-8")
    test_file = root / "tests/test_act_story.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_story():\n    assert True\n", encoding="utf-8")
    source_file = root / "src/act_story.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("VALUE = True\n", encoding="utf-8")

    engine = WorkflowEngine(root)
    run = engine.start("project-act", goal="implement", story_id=story_id)
    claims_by_step = {
        "act_preflight": {"spec_lint": "pass", "trace": ["src/act_story.py"]},
        "red": {"story_tests": {"exit_code": 1}},
        "implementation": {"changed_files": ["src/act_story.py"]},
        "story_tests": {"story_tests": {"exit_code": 0}},
        "regression_lint": {"regression": "pass", "lint": "pass"},
        "sync_coverage": {
            "coverage": {"R1": ["test_act_story"]},
            "acceptance_coverage": {"AC1": ["test_act_story"]},
            "board_tasks": ["one", "two"],
        },
    }
    files_by_step = {
        "red": ["tests/test_act_story.py"],
        "implementation": ["src/act_story.py"],
    }
    while engine.status(run.run_id)["step_id"] != "finalize_act":
        step = engine.status(run.run_id)["step_id"]
        unit = engine.acquire(run.run_id, owner="codex", idempotency_key=f"{step}-acquire")
        result = engine.submit(
            unit.unit_id, EvidenceReceipt.for_files(
                unit, owner="codex", root=root, files=files_by_step.get(step, []),
                claims=claims_by_step[step],
            ), owner="codex", idempotency_key=f"{step}-submit",
        )
        assert result.attempt_status == "succeeded", result
    final = engine.acquire(run.run_id, owner="codex", idempotency_key="final-acquire")
    receipt = EvidenceReceipt.for_files(
        final, owner="codex", root=root, files=[], claims={"completed": True},
    )
    return engine, run, receipt


def test_work_unit_lease_owner_expiry_and_idempotent_submit(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkUnitError

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan feature")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire-1", now=10)
    assert unit.run_id == run.run_id
    assert unit.allowed_writes == ()  # read-only preflight still carries an explicit scope
    assert unit.forbidden_operations
    assert unit.acceptance_commands
    assert unit.receipt_schema_version == 1
    assert engine.acquire(run.run_id, owner="codex", idempotency_key="acquire-1", now=11) == unit
    with pytest.raises(WorkUnitError, match="lease_owner_mismatch"):
        engine.renew(unit.unit_id, owner="other", now=12)
    engine.renew(unit.unit_id, owner="codex", now=12)
    receipt = EvidenceReceipt.for_files(
        unit, owner="codex", root=tmp_path, files=[], claims={"guard": "pass"},
    )
    first = engine.submit(unit.unit_id, receipt, owner="codex", idempotency_key="submit-1", now=13)
    second = engine.submit(unit.unit_id, receipt, owner="codex", idempotency_key="submit-1", now=14)
    assert first == second
    assert first.attempt_status == "succeeded"
    assert first.workflow_status == "running"
    with pytest.raises(WorkUnitError, match="lease_expired"):
        engine.renew(unit.unit_id, owner="codex", now=10_000)


def test_acquire_and_retry_idempotency_keys_are_owner_and_unit_bound(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path, lease_seconds=5)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)

    with pytest.raises(WorkUnitError, match="idempotency_key_conflict"):
        engine.acquire(run.run_id, owner="mallory", idempotency_key="acquire", now=2)

    engine.reject(unit.unit_id, owner="alice", reason_code="retry", now=3)
    retried = engine.retry(unit.unit_id, owner="alice", idempotency_key="retry", now=4)

    with pytest.raises(WorkUnitError, match="idempotency_key_conflict"):
        engine.retry(unit.unit_id, owner="mallory", idempotency_key="retry", now=5)
    assert retried.version == 2


def test_retry_refreshes_instruction_contract_without_expanding_write_scope(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine

    story = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story)
    _advance_plan_to_step(engine, run.run_id, tmp_path, story, "spec_content")
    unit = engine.acquire(
        run.run_id, owner="codex", idempotency_key="legacy-content-acquire",
    )
    engine.reject(unit.unit_id, owner="codex", reason_code="validator_failed")

    # Emulate a Unit persisted before Core added explicit receipt guidance.
    state = engine._read(run.run_id)
    state["units"][unit.unit_id]["required_claims"] = ()
    engine._write(state)

    retried = engine.retry(
        unit.unit_id, owner="codex", idempotency_key="legacy-content-retry",
    )

    assert retried.version == 2
    assert retried.allowed_writes == unit.allowed_writes
    assert "evidence_files must exactly equal allowed_writes" in retried.required_claims
    assert "valid Mermaid graph or flowchart" in " ".join(retried.required_claims)


@pytest.mark.parametrize(
    ("owner", "idempotency_key"),
    [
        ("", "acquire"),
        (None, "acquire"),
        (object(), "acquire"),
        ("alice", ""),
        ("alice", None),
        ("alice", object()),
    ],
)
def test_acquire_rejects_invalid_persisted_identity_inputs_before_state_changes(
    tmp_path, owner, idempotency_key,
):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")

    with pytest.raises(WorkUnitError, match="invalid_idempotency_identity"):
        engine.acquire(run.run_id, owner=owner, idempotency_key=idempotency_key, now=1)

    state = engine._read(run.run_id)
    assert state["units"] == {}
    assert state["idempotency"] == {}


@pytest.mark.parametrize("goal", ["", None, object()])
def test_start_rejects_invalid_goal_before_creating_a_run(tmp_path, goal):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)

    with pytest.raises(WorkUnitError, match="invalid_workflow_goal"):
        engine.start("project-plan", goal=goal)

    assert not engine.directory.exists()


@pytest.mark.parametrize("now", [float("nan"), float("inf"), "invalid", object()])
def test_acquire_rejects_invalid_timestamp_before_state_changes(tmp_path, now):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")

    with pytest.raises(WorkUnitError, match="invalid_timestamp"):
        engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=now)

    state = engine._read(run.run_id)
    assert state["units"] == {}
    assert state["idempotency"] == {}


@pytest.mark.parametrize("lease_seconds", [0, -1, True, 1.5, float("nan"), "5"])
def test_engine_rejects_invalid_lease_duration(lease_seconds, tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    with pytest.raises(WorkUnitError, match="invalid_lease_duration"):
        WorkflowEngine(tmp_path, lease_seconds=lease_seconds)


@pytest.mark.parametrize("run_id", ["", "run-invalid", None, [], object()])
def test_run_paths_reject_invalid_run_id_values(tmp_path, run_id):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)

    with pytest.raises(WorkUnitError, match="invalid_run_id"):
        engine.path_for(run_id)


@pytest.mark.parametrize("unit_id", ["", None, [], {}, object()])
def test_unit_operations_reject_invalid_unit_id_values(tmp_path, unit_id):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)

    with pytest.raises(WorkUnitError, match="invalid_unit_id"):
        engine.renew(unit_id, owner="alice", now=1)


@pytest.mark.parametrize("story_id", ["", "story-invalid", None, [], object()])
def test_story_operations_reject_invalid_story_id_values(tmp_path, story_id):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)

    with pytest.raises(WorkUnitError, match="invalid_story_id"):
        engine.resume(story_id)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda state: state.pop("workflow_id"),
        lambda state: state.__setitem__("current_index", True),
        lambda state: state.__setitem__("units", []),
        lambda state: state.__setitem__("idempotency", []),
        lambda state: state.__setitem__("attempts", {}),
    ],
)
def test_corrupt_run_state_fails_closed_before_transition(tmp_path, mutation):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    mutation(state)
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)

    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: record.__setitem__("state", "unknown"),
        lambda record: record.__setitem__("version", True),
        lambda record: record.__setitem__("lease_expires_at", float("nan")),
        lambda record: record.__setitem__("allowed_writes", "docs/**"),
        lambda record: record.pop("lease_owner"),
    ],
)
def test_corrupt_unit_record_fails_closed_before_transition(tmp_path, mutation):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    mutation(state["units"][unit.unit_id])
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.renew(unit.unit_id, owner="alice", now=2)

    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda state: state.__setitem__("attempts", ["broken"]),
        lambda state: state.__setitem__("attempts", [{"attempt_id": "attempt-x"}]),
        lambda state: state.__setitem__("attempts", [{
            "attempt_id": "attempt-x", "unit_id": "unit-" + "0" * 32,
            "unit_version": True, "host": None, "status": "succeeded",
        }]),
    ],
)
def test_corrupt_attempt_record_fails_closed_before_transition(tmp_path, mutation):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    mutation(state)
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)

    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda state: state["idempotency"].__setitem__("submit:unrelated", None),
        lambda state: state["idempotency"].__setitem__("submit:unrelated", {
            "unit_id": "unit-" + "0" * 32,
            "request_unit_version": None,
            "owner": "alice",
            "receipt_digest": "malformed:forged",
            "result": {
                "attempt_id": "attempt-" + "0" * 32,
                "attempt_status": "rejected",
                "workflow_status": "running",
                "decision": "ignored",
                "reason_code": "malformed_receipt",
                "next_unit_id": None,
            },
        }),
        lambda state: state["fingerprints"].__setitem__("docs/specs/unknown.md", "not-a-sha256"),
    ],
)
def test_corrupt_recovery_metadata_fails_closed_before_unrelated_transition(tmp_path, mutation):
    """Every persisted recovery record must be valid before Core writes again."""
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    mutation(state)
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.acquire(run.run_id, owner="alice", idempotency_key="unrelated", now=1)

    assert path.read_bytes() == before


def test_recovery_rejects_a_state_that_skips_a_required_work_unit(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    state["units"][unit.unit_id]["state"] = "succeeded"
    state["current_index"] = 1
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.acquire(run.run_id, owner="alice", idempotency_key="clarification", now=2)

    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda state: state.update({"status": "completed", "current_index": 8}),
        lambda state: state.update({"status": "blocked"}),
    ],
)
def test_native_run_rejects_forged_terminal_state(tmp_path, mutation):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    mutation(state)
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)

    assert path.read_bytes() == before


def test_resume_fails_closed_for_a_corrupt_active_story_run(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id="STORY-slim-999")
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    state["fingerprints"]["docs/specs/unknown.md"] = "not-a-sha256"
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.resume("STORY-slim-999")

    assert path.read_bytes() == before


def test_run_path_and_durable_run_id_must_match_before_transition(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    first = engine.start("project-plan", goal="first")
    second = engine.start("project-plan", goal="second")
    first_path = engine.path_for(first.run_id)
    second_state = json.loads(engine.path_for(second.run_id).read_text(encoding="utf-8"))
    first_path.write_text(json.dumps(second_state), encoding="utf-8")
    before = first_path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.acquire(first.run_id, owner="alice", idempotency_key="acquire", now=1)

    assert first_path.read_bytes() == before


def test_idempotency_snapshot_must_reference_a_durable_unit(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    cached = state["idempotency"]["acquire:acquire"]
    forged_unit_id = "unit-" + "0" * 32
    assert forged_unit_id != unit.unit_id
    cached["unit_id"] = forged_unit_id
    cached["result"]["unit_id"] = forged_unit_id
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.acquire(run.run_id, owner="alice", idempotency_key="other", now=2)

    assert path.read_bytes() == before


def test_submit_idempotency_result_must_reference_its_durable_attempt(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkUnitError

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)
    result = engine.submit(
        unit.unit_id,
        EvidenceReceipt.for_files(unit, owner="alice", root=tmp_path, files=[], claims={"guard": "pass"}),
        owner="alice", idempotency_key="submit", now=2,
    )
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    assert state["idempotency"]["submit:submit"]["result"]["attempt_id"] == result.attempt_id
    state["idempotency"]["submit:submit"]["result"]["attempt_id"] = "attempt-" + "0" * 32
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.acquire(run.run_id, owner="alice", idempotency_key="other", now=3)

    assert path.read_bytes() == before


def test_submit_idempotency_rejects_unknown_malformed_receipt_digest(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkUnitError

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)
    engine.submit(
        unit.unit_id,
        EvidenceReceipt.for_files(unit, owner="alice", root=tmp_path, files=[], claims={"guard": "pass"}),
        owner="alice", idempotency_key="submit", now=2,
    )
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    state["idempotency"]["submit:submit"]["receipt_digest"] = "malformed:forged"
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.acquire(run.run_id, owner="alice", idempotency_key="other", now=3)

    assert path.read_bytes() == before


def test_retry_idempotency_key_cannot_replay_a_different_unit(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path, lease_seconds=5)
    _initialize_work_unit_project(tmp_path)
    run = engine.start("project-plan", goal="plan")
    first = engine.acquire(run.run_id, owner="alice", idempotency_key="first", now=1)
    engine.reject(first.unit_id, owner="alice", reason_code="retry", now=2)
    retried = engine.retry(first.unit_id, owner="alice", idempotency_key="retry", now=3)
    engine.submit(
        retried.unit_id,
        EvidenceReceipt.for_files(
            retried, owner="alice", root=tmp_path, files=[], claims={"guard": "pass"},
        ),
        owner="alice", idempotency_key="submit", now=4,
    )
    second = engine.acquire(run.run_id, owner="alice", idempotency_key="second", now=5)
    engine.reject(second.unit_id, owner="alice", reason_code="retry", now=6)

    with pytest.raises(WorkUnitError, match="idempotency_key_conflict"):
        engine.retry(second.unit_id, owner="alice", idempotency_key="retry", now=7)


def test_acquire_and_retry_idempotency_replays_return_immutable_snapshots(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine

    engine = WorkflowEngine(tmp_path, lease_seconds=5)
    run = engine.start("project-plan", goal="plan")
    acquired = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)
    engine.reject(acquired.unit_id, owner="alice", reason_code="retry", now=2)
    first_retry = engine.retry(acquired.unit_id, owner="alice", idempotency_key="retry-1", now=3)
    engine.reject(first_retry.unit_id, owner="alice", reason_code="retry", now=4)
    latest = engine.retry(first_retry.unit_id, owner="alice", idempotency_key="retry-2", now=5)

    assert latest.version == 3
    assert engine.acquire(
        run.run_id, owner="alice", idempotency_key="acquire", now=6,
    ) == acquired
    assert engine.retry(
        acquired.unit_id, owner="alice", idempotency_key="retry-1", now=6,
    ) == first_retry


def test_submit_idempotency_replays_original_result_after_retry(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path, lease_seconds=20)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)
    receipt = EvidenceReceipt.for_files(
        unit, owner="alice", root=tmp_path, files=[], claims={},
    )

    first = engine.submit(
        unit.unit_id, receipt, owner="alice", idempotency_key="submit", now=2,
    )
    retried = engine.retry(unit.unit_id, owner="alice", idempotency_key="retry", now=3)
    replay = engine.submit(
        unit.unit_id, receipt, owner="alice", idempotency_key="submit", now=4,
    )

    assert first.reason_code == "validator_failed"
    assert retried.version == 2
    assert replay == first
    record = engine._read(run.run_id)["units"][unit.unit_id]
    assert record["version"] == 2
    assert record["state"] == "leased"


def test_expire_cannot_rewrite_a_terminal_unit(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkUnitError

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path, lease_seconds=5)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)
    accepted = engine.submit(
        unit.unit_id,
        EvidenceReceipt.for_files(
            unit, owner="alice", root=tmp_path, files=[], claims={"guard": "pass"},
        ),
        owner="alice", idempotency_key="submit", now=2,
    )
    assert accepted.attempt_status == "succeeded"

    with pytest.raises(WorkUnitError, match="unit_not_expirable"):
        engine.expire(unit.unit_id, owner="alice", now=7)

    assert engine._read(run.run_id)["units"][unit.unit_id]["state"] == "succeeded"
    assert engine.status(run.run_id)["step_id"] == "clarification"


def test_reject_requires_the_current_unexpired_lease(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path, lease_seconds=5)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)

    with pytest.raises(WorkUnitError, match="lease_expired"):
        engine.reject(unit.unit_id, owner="alice", reason_code="host_error", now=7)

    assert engine._read(run.run_id)["units"][unit.unit_id]["state"] == "leased"

    engine.reject(unit.unit_id, owner="alice", reason_code="host_error", now=2)
    with pytest.raises(WorkUnitError, match="unit_not_rejectable"):
        engine.reject(unit.unit_id, owner="alice", reason_code="duplicate", now=3)


def test_failure_must_retry_the_same_unit_instead_of_acquiring_parallel_work(tmp_path):
    from pactkit.workflow_engine import HostCapabilities, WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path, lease_seconds=5)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=1)
    engine.record_turn_terminal(
        run.run_id, unit_id=unit.unit_id, unit_version=unit.version,
        owner="codex", host="codex", status="host_error",
        capabilities=HostCapabilities(host="codex"), now=2,
    )

    with pytest.raises(WorkUnitError, match="retry_required"):
        engine.acquire(run.run_id, owner="codex", idempotency_key="new-acquire", now=3)
    retried = engine.retry(unit.unit_id, owner="codex", idempotency_key="retry", now=3)
    assert retried.unit_id == unit.unit_id
    assert retried.version == 2


def test_lease_current_recovers_an_expired_active_unit_in_one_call(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine

    engine = WorkflowEngine(tmp_path, lease_seconds=5)
    run = engine.start("project-plan", goal="plan")
    old = engine.acquire(run.run_id, owner="codex", idempotency_key="old", now=1)

    recovered = engine.lease_current(
        run.run_id, owner="codex", idempotency_key="new-invocation", now=7,
    )

    assert recovered.unit_id == old.unit_id
    assert recovered.version == old.version + 1
    assert recovered.lease_expires_at == 12
    assert engine._read(run.run_id)["units"][old.unit_id]["state"] == "leased"


def test_terminal_attempt_requires_current_owner_lease_and_is_not_repeatable(tmp_path):
    from pactkit.workflow_engine import HostCapabilities, WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path, lease_seconds=5)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=1)
    kwargs = {
        "run_id": run.run_id, "unit_id": unit.unit_id, "unit_version": unit.version,
        "host": "codex", "status": "succeeded",
        "capabilities": HostCapabilities(host="codex"), "turn": "turn-1",
    }

    with pytest.raises(WorkUnitError, match="lease_owner_mismatch"):
        engine.record_turn_terminal(owner="mallory", now=2, **kwargs)
    with pytest.raises(WorkUnitError, match="lease_expired"):
        engine.record_turn_terminal(owner="codex", now=7, **kwargs)

    engine.record_turn_terminal(owner="codex", now=2, **kwargs)
    with pytest.raises(WorkUnitError, match="duplicate_attempt_terminal"):
        engine.record_turn_terminal(owner="codex", now=3, **kwargs)
    with pytest.raises(WorkUnitError, match="duplicate_attempt_terminal"):
        engine.record_turn_terminal(
            owner="codex", now=3, **{**kwargs, "status": "host_error"},
        )


@pytest.mark.parametrize(
    "metadata",
    [
        {"result_refs": (object(),)},
        {"started_at": float("nan")},
        {"host": ""},
        {"invalid_capabilities": True},
        {"capabilities": {"host": "codex"}},
    ],
)
def test_terminal_attempt_rejects_non_serializable_or_invalid_host_metadata(tmp_path, metadata):
    from pactkit.workflow_engine import HostCapabilities, WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path, lease_seconds=20)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=1)
    kwargs = {
        "unit_id": unit.unit_id,
        "unit_version": unit.version,
        "owner": "codex",
        "host": "codex",
        "status": "host_error",
        "capabilities": HostCapabilities(host="codex"),
        "now": 2,
    }
    if metadata.pop("invalid_capabilities", False):
        metadata["capabilities"] = HostCapabilities(
            host="codex", discovery_source=object(),
        )

    with pytest.raises(WorkUnitError, match="invalid_attempt_metadata"):
        engine.record_turn_terminal(run.run_id, **{**kwargs, **metadata})

    record = engine._read(run.run_id)["units"][unit.unit_id]
    assert record["state"] == "leased"
    assert engine._read(run.run_id)["attempts"] == []


@pytest.mark.parametrize("status", ["", [], {}, 1])
def test_terminal_attempt_rejects_invalid_terminal_status_before_state_changes(tmp_path, status):
    from pactkit.workflow_engine import HostCapabilities, WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path, lease_seconds=20)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=1)

    with pytest.raises(WorkUnitError, match="invalid_attempt_terminal"):
        engine.record_turn_terminal(
            run.run_id, unit_id=unit.unit_id, unit_version=unit.version,
            owner="codex", host="codex", status=status,
            capabilities=HostCapabilities(host="codex"), now=2,
        )

    state = engine._read(run.run_id)
    assert state["units"][unit.unit_id]["state"] == "leased"
    assert state["attempts"] == []


def test_preflight_rereads_project_guard_instead_of_trusting_receipt_claim(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan feature")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire")

    result = engine.submit(
        unit.unit_id,
        EvidenceReceipt.for_files(
            unit, owner="codex", root=tmp_path, files=[], claims={"guard": "pass"},
        ),
        owner="codex", idempotency_key="submit",
    )

    assert result.attempt_status == "rejected"
    assert result.reason_code == "validator_failed"


def test_late_or_non_owner_submit_cannot_reopen_a_succeeded_unit_or_skip_steps(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path, lease_seconds=20)
    run = engine.start("project-plan", goal="plan")
    preflight = engine.acquire(run.run_id, owner="alice", idempotency_key="preflight", now=1)
    receipt = EvidenceReceipt.for_files(
        preflight, owner="alice", root=tmp_path, files=[], claims={"guard": "pass"},
    )
    accepted = engine.submit(
        preflight.unit_id, receipt, owner="alice", idempotency_key="accept", now=2,
    )
    assert accepted.attempt_status == "succeeded"
    assert engine.status(run.run_id)["step_id"] == "clarification"

    late = engine.submit(
        preflight.unit_id, receipt, owner="mallory", idempotency_key="late", now=3,
    )
    state = engine._read(run.run_id)
    assert late.attempt_status == "rejected"
    assert late.reason_code == "lease_owner_mismatch"
    assert state["units"][preflight.unit_id]["state"] == "succeeded"
    assert engine.status(run.run_id)["step_id"] == "clarification"

    replay = engine.submit(
        preflight.unit_id, receipt, owner="alice", idempotency_key="replay", now=4,
    )
    state = engine._read(run.run_id)
    assert replay.attempt_status == "rejected"
    assert state["units"][preflight.unit_id]["state"] == "succeeded"
    assert engine.status(run.run_id)["step_id"] == "clarification"


@pytest.mark.parametrize(
    "tamper",
    [
        lambda receipt: dataclasses.replace(receipt, owner="mallory"),
        lambda receipt: dataclasses.replace(receipt, unit_version=receipt.unit_version + 1),
        lambda receipt: dataclasses.replace(receipt, unit_id="unit-other"),
    ],
)
def test_foreign_receipt_identity_cannot_release_the_current_lease(tmp_path, tamper):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path, lease_seconds=20)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire", now=1)
    receipt = EvidenceReceipt.for_files(
        unit, owner="alice", root=tmp_path, files=[], claims={"guard": "pass"},
    )

    result = engine.submit(
        unit.unit_id, tamper(receipt), owner="alice", idempotency_key="foreign", now=2,
    )

    assert result.attempt_status == "rejected"
    assert result.decision == "ignored"
    assert engine._read(run.run_id)["units"][unit.unit_id]["state"] == "leased"
    assert engine.status(run.run_id)["step_id"] == "preflight"


def test_receipt_is_reverified_and_agent_final_does_not_complete_run(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    story_id = "STORY-slim-999"
    target = _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_step(engine, run.run_id, tmp_path, story_id, "spec_lint")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="a", now=1)
    receipt = EvidenceReceipt(
        schema_version=1, unit_id=unit.unit_id, unit_version=unit.version,
        owner="codex", claims={"success": True},
        file_fingerprints={str(target.relative_to(tmp_path)): "0" * 64},
    )
    result = engine.submit(unit.unit_id, receipt, owner="codex", idempotency_key="s", now=2)
    assert result.attempt_status == "rejected"
    assert result.workflow_status == "running"
    assert result.reason_code == "fingerprint_mismatch"
    # Core's rejected Receipt is already the terminal audit fact for this
    # lease. A later host event must use a fresh versioned retry instead of
    # mutating the closed lease.
    assert engine._read(run.run_id)["units"][unit.unit_id]["state"] == "retry"


def test_capability_negotiation_is_truthful_and_protocol_fails_closed():
    from pactkit.workflow_engine import HostCapabilities, ProtocolError, select_execution_mode

    assert select_execution_mode(HostCapabilities(host="claude", native_commands=True)).value == "portable"
    assert select_execution_mode(HostCapabilities(host="copilot", tool_execution=True)).value == "guided"
    assert select_execution_mode(HostCapabilities(host="codex", tool_execution=True, thread_resume=True)).value == "guided"
    assert select_execution_mode(HostCapabilities(
        host="codex", tool_execution=True, thread_resume=True, e2e_validated=True,
    )).value == "resumable"
    assert select_execution_mode(HostCapabilities(
        host="codex", structured_results=True, tool_execution=True, lifecycle_events=True,
        thread_resume=True, turn_steer=True, background_execution=True, cancellation=True,
        e2e_validated=True,
    )).value == "managed"
    with pytest.raises(ProtocolError, match="protocol_version_mismatch"):
        select_execution_mode(HostCapabilities(host="codex", protocol_version=99))
    with pytest.raises(ProtocolError, match="protocol_version_mismatch"):
        select_execution_mode(HostCapabilities(host="codex", protocol_version=True))


def test_project_plan_units_are_bounded_and_finalize_is_recoverable(tmp_path, monkeypatch):
    from pactkit.workflow_engine import PLAN_WORK_UNITS, PlanFinalizer, WorkflowEngine

    assert tuple(item.step_id for item in PLAN_WORK_UNITS) == (
        "preflight", "clarification", "archaeology", "story_identity", "spec_scaffold",
        "spec_content", "spec_security", "spec_lint", "finalize_plan",
    )
    assert all(len(item.allowed_writes) <= 3 for item in PLAN_WORK_UNITS[:-1])
    content = next(item for item in PLAN_WORK_UNITS if item.step_id == "spec_content")
    assert any(
        "evidence_files must exactly equal allowed_writes" in rule
        for rule in content.required_claims
    )
    assert any(
        "valid Mermaid graph or flowchart" in rule
        for rule in content.required_claims
    )
    lint = next(item for item in PLAN_WORK_UNITS if item.step_id == "spec_lint")
    assert any(
        "remove every scaffold placeholder" in rule
        for rule in lint.required_claims
    )
    story_id = "STORY-slim-999"
    spec = _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    original = finalizer._write_context
    calls = {"count": 0}

    def fail_once():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("crash")
        original()

    monkeypatch.setattr(finalizer, "_write_context", fail_once)
    with pytest.raises(RuntimeError, match="crash"):
        finalizer.finalize(run.run_id, story_id=story_id, title="Title", tasks=["one"],
                           idempotency_key="finalize-1")
    result = finalizer.finalize(run.run_id, story_id=story_id, title="Title", tasks=["one"],
                                idempotency_key="finalize-1")
    assert result["status"] == "completed"
    assert (tmp_path / "docs/product/stories" / f"{story_id}.yaml").is_file()
    board = (tmp_path / "docs/product/sprint_board.md").read_text(encoding="utf-8")
    assert board.count(f"### [{story_id}]") == 1
    assert (tmp_path / ".pactkit/context.md").is_file()
    state = json.loads(engine.path_for(run.run_id).read_text())
    assert state["status"] == "completed"
    assert state["fingerprints"]["spec"] == hashlib.sha256(spec.read_bytes()).hexdigest()


def test_completed_plan_finalize_replays_its_original_result(tmp_path):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)

    first = finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    replay = finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )

    assert replay == first
    with pytest.raises(WorkUnitError, match="finalize_idempotency_conflict"):
        finalizer.finalize(
            run.run_id, story_id=story_id, title="Changed title", tasks=["one"],
            idempotency_key="finalize",
        )


def test_finalizer_acquires_story_lock_before_run_lock(tmp_path, monkeypatch):
    from contextlib import contextmanager

    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    acquired: list[str] = []

    @contextmanager
    def run_lock(_run_id):
        acquired.append("run")
        yield

    @contextmanager
    def story_lock(_story_id):
        acquired.append("story")
        yield

    monkeypatch.setattr(engine, "_lock", run_lock)
    monkeypatch.setattr(finalizer, "_story_lock", story_lock)
    finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )

    assert acquired[:2] == ["story", "run"]


def test_completed_run_without_finalize_journal_fails_closed(tmp_path):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    journal_path = finalizer._journal_path(run.run_id)
    journal_path.unlink()
    before = engine.path_for(run.run_id).read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)
    with pytest.raises(WorkUnitError, match="corrupt_finalize_journal"):
        finalizer.finalize(
            run.run_id, story_id=story_id, title="Title", tasks=["one"],
            idempotency_key="finalize",
        )

    assert engine.path_for(run.run_id).read_bytes() == before


def test_completed_run_with_unfinished_journal_only_recovers_via_finalizer(tmp_path, monkeypatch):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    original = finalizer._save_journal

    def crash_before_completion(path, journal):
        if journal.get("stage") == "completed":
            raise RuntimeError("crash after run completion")
        original(path, journal)

    monkeypatch.setattr(finalizer, "_save_journal", crash_before_completion)
    with pytest.raises(RuntimeError, match="crash after run completion"):
        finalizer.finalize(
            run.run_id, story_id=story_id, title="Title", tasks=["one"],
            idempotency_key="finalize",
        )

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)

    monkeypatch.setattr(finalizer, "_save_journal", original)
    result = finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )

    assert result["status"] == "completed"
    assert engine.status(run.run_id)["status"] == "completed"


@pytest.mark.parametrize("journal", [[], "corrupt", 42])
def test_completed_run_rejects_non_object_finalize_journal(tmp_path, journal):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    journal_path = finalizer._journal_path(run.run_id)
    journal_path.write_text(json.dumps(journal), encoding="utf-8")
    before = engine.path_for(run.run_id).read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)

    assert engine.path_for(run.run_id).read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda journal: journal.pop("request_digest"),
        lambda journal: journal.__setitem__("request_digest", "not-a-sha256"),
        lambda journal: journal.__setitem__("idempotency_key", ""),
        lambda journal: journal.__setitem__("fingerprints", {"spec": "0" * 64}),
    ],
)
def test_completed_run_rejects_incomplete_finalize_journal(tmp_path, mutation):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    journal_path = finalizer._journal_path(run.run_id)
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    mutation(journal)
    journal_path.write_text(json.dumps(journal), encoding="utf-8")
    before = engine.path_for(run.run_id).read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)

    assert engine.path_for(run.run_id).read_bytes() == before


@pytest.mark.parametrize(
    "relative",
    [
        "docs/specs/STORY-slim-999.md",
        "docs/architecture/graphs/system_design.mmd",
        "docs/product/stories/STORY-slim-999.yaml",
        "docs/product/sprint_board.md",
        ".pactkit/context.md",
    ],
)
def test_completed_run_rejects_tampered_finalize_projection(tmp_path, relative):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    PlanFinalizer(tmp_path, engine).finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    target = tmp_path / relative
    target.write_text(target.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
    before = engine.path_for(run.run_id).read_bytes()

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)

    assert engine.path_for(run.run_id).read_bytes() == before


def test_completed_finalize_replay_rejects_tampered_projection(tmp_path):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    spec = tmp_path / "docs/specs" / f"{story_id}.md"
    spec.write_text("invalid spec\n", encoding="utf-8")

    with pytest.raises(WorkUnitError, match="corrupt_finalize_journal"):
        finalizer.finalize(
            run.run_id, story_id=story_id, title="Title", tasks=["one"],
            idempotency_key="finalize",
        )


def test_later_finalize_keeps_prior_completed_run_readable(tmp_path):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine

    engine = WorkflowEngine(tmp_path)
    first_story = "STORY-slim-999"
    second_story = "STORY-slim-998"
    _write_plan_inputs(tmp_path, first_story)
    first = engine.start("project-plan", goal="first", story_id=first_story)
    _advance_plan_to_finalize(engine, first.run_id, tmp_path, first_story)
    PlanFinalizer(tmp_path, engine).finalize(
        first.run_id, story_id=first_story, title="First", tasks=["one"],
        idempotency_key="first-finalize",
    )

    _write_plan_inputs(tmp_path, second_story)
    second = engine.start("project-plan", goal="second", story_id=second_story)
    _advance_plan_to_finalize(engine, second.run_id, tmp_path, second_story)
    PlanFinalizer(tmp_path, engine).finalize(
        second.run_id, story_id=second_story, title="Second", tasks=["two"],
        idempotency_key="second-finalize",
    )

    assert engine.status(first.run_id)["status"] == "completed"
    assert engine.status(second.run_id)["status"] == "completed"


def test_completed_run_survives_later_story_and_hld_evolution(tmp_path):
    from pactkit.context_gen import context_output_path, generate_context
    from pactkit.governance import BoardRenderer, StoryRepository
    from pactkit.utils import atomic_write
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine

    story_id = "STORY-slim-996"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    PlanFinalizer(tmp_path, engine).finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )

    repository = StoryRepository(tmp_path)
    repository.complete_task(story_id, "one")
    atomic_write(tmp_path / "docs/product/sprint_board.md", BoardRenderer(repository).render())
    atomic_write(context_output_path(tmp_path), generate_context(tmp_path, command="pactkit context"))
    next_story = "STORY-slim-997"
    _write_plan_inputs(tmp_path, next_story)
    hld = tmp_path / "docs/architecture/graphs/system_design.mmd"
    hld.write_text("graph TD\n A-->B\n B-->C\n", encoding="utf-8")
    next_run = engine.start("project-plan", goal="next", story_id=next_story)
    _advance_plan_to_finalize(engine, next_run.run_id, tmp_path, next_story)
    PlanFinalizer(tmp_path, engine).finalize(
        next_run.run_id, story_id=next_story, title="Next", tasks=["two"],
        idempotency_key="next-finalize",
    )

    assert engine.status(run.run_id)["status"] == "completed"


def test_completed_run_accepts_core_verified_in_progress_hld_change(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, PlanFinalizer, WorkflowEngine

    first_story = "STORY-slim-996"
    _write_plan_inputs(tmp_path, first_story)
    engine = WorkflowEngine(tmp_path)
    first = engine.start("project-plan", goal="first", story_id=first_story)
    _advance_plan_to_finalize(engine, first.run_id, tmp_path, first_story)
    PlanFinalizer(tmp_path, engine).finalize(
        first.run_id, story_id=first_story, title="First", tasks=["one"],
        idempotency_key="first-finalize",
    )

    second_story = "STORY-slim-997"
    _write_plan_inputs(tmp_path, second_story)
    second = engine.start("project-plan", goal="second", story_id=second_story)
    _advance_plan_to_step(engine, second.run_id, tmp_path, second_story, "spec_content")
    hld = tmp_path / "docs/architecture/graphs/system_design.mmd"
    hld.write_text("graph TD\n A-->B\n B-->C\n", encoding="utf-8")
    unit = engine.acquire(second.run_id, owner="codex", idempotency_key="content")
    assert unit.step_id == "spec_content"
    accepted = engine.submit(
        unit.unit_id, EvidenceReceipt.for_files(
            unit, owner="codex", root=tmp_path,
            files=[f"docs/specs/{second_story}.md", "docs/architecture/graphs/system_design.mmd"],
        ),
        owner="codex", idempotency_key="content-submit",
    )
    assert accepted.attempt_status == "succeeded"

    assert engine.status(first.run_id)["status"] == "completed"


def test_completed_run_ignores_corrupt_unrelated_run_during_hld_authorization_scan(tmp_path):
    """A damaged run cannot authorize HLD, but cannot poison another run either."""
    from pactkit.workflow_engine import EvidenceReceipt, PlanFinalizer, WorkflowEngine

    first_story = "STORY-slim-996"
    _write_plan_inputs(tmp_path, first_story)
    engine = WorkflowEngine(tmp_path)
    first = engine.start("project-plan", goal="first", story_id=first_story)
    _advance_plan_to_finalize(engine, first.run_id, tmp_path, first_story)
    PlanFinalizer(tmp_path, engine).finalize(
        first.run_id, story_id=first_story, title="First", tasks=["one"],
        idempotency_key="first-finalize",
    )

    second_story = "STORY-slim-997"
    _write_plan_inputs(tmp_path, second_story)
    second = engine.start("project-plan", goal="second", story_id=second_story)
    _advance_plan_to_step(engine, second.run_id, tmp_path, second_story, "spec_content")
    hld = tmp_path / "docs/architecture/graphs/system_design.mmd"
    hld.write_text("graph TD\n A-->B\n B-->C\n", encoding="utf-8")
    unit = engine.acquire(second.run_id, owner="codex", idempotency_key="content")
    assert engine.submit(
        unit.unit_id, EvidenceReceipt.for_files(
            unit, owner="codex", root=tmp_path,
            files=[f"docs/specs/{second_story}.md", "docs/architecture/graphs/system_design.mmd"],
        ),
        owner="codex", idempotency_key="content-submit",
    ).attempt_status == "succeeded"

    unrelated = engine.start("project-plan", goal="unrelated")
    path = engine.path_for(unrelated.run_id)
    damaged = json.loads(path.read_text(encoding="utf-8"))
    damaged["units"] = []
    path.write_text(json.dumps(damaged), encoding="utf-8")

    assert engine.status(first.run_id)["status"] == "completed"


def test_recovery_rejects_malformed_attempt_file_fingerprints(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-996"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_step(engine, run.run_id, tmp_path, story_id, "spec_content")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="content")
    engine.submit(
        unit.unit_id, EvidenceReceipt.for_files(
            unit, owner="codex", root=tmp_path,
            files=[f"docs/specs/{story_id}.md", "docs/architecture/graphs/system_design.mmd"],
        ),
        owner="codex", idempotency_key="content-submit",
    )
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    attempt = next(item for item in state["attempts"] if item["unit_id"] == unit.unit_id)
    attempt["file_fingerprints"] = {"../escape": "0" * 64}
    path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda story: story.__setitem__("title", "Rewritten"),
        lambda story: story["tasks"].__setitem__(0, {
            **story["tasks"][0], "title": "Rewritten task",
        }),
        lambda story: story.__setitem__("spec_path", "docs/specs/other.md"),
    ],
)
def test_completed_run_rejects_story_contract_rewrite(tmp_path, mutation):
    from pactkit.context_gen import context_output_path, generate_context
    from pactkit.governance import BoardRenderer
    from pactkit.governance import StoryRepository
    from pactkit.utils import atomic_write
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-996"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    PlanFinalizer(tmp_path, engine).finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    repository = StoryRepository(tmp_path)
    story = repository.load(story_id)
    mutation(story)
    repository._write(story)
    atomic_write(tmp_path / "docs/product/sprint_board.md", BoardRenderer(repository).render())
    atomic_write(context_output_path(tmp_path), generate_context(tmp_path, command="pactkit context"))

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)


def test_concurrent_finalizers_serialize_global_projections(tmp_path, monkeypatch):
    from pactkit.governance import BoardRenderer, StoryRepository
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine

    engine = WorkflowEngine(tmp_path)
    runs = {}
    for story_id in ("STORY-slim-994", "STORY-slim-995"):
        _write_plan_inputs(tmp_path, story_id)
        runs[story_id] = engine.start("project-plan", goal=story_id, story_id=story_id)
        _advance_plan_to_finalize(engine, runs[story_id].run_id, tmp_path, story_id)
    first = PlanFinalizer(tmp_path, engine)
    second = PlanFinalizer(tmp_path, engine)
    entered = threading.Event()
    release = threading.Event()
    original = first._write_board

    def pause_after_render():
        entered.set()
        assert release.wait(5)
        original()

    monkeypatch.setattr(first, "_write_board", pause_after_render)
    errors = []

    def finalize_first():
        try:
            first.finalize(
                runs["STORY-slim-994"].run_id, story_id="STORY-slim-994",
                title="One", tasks=["one"], idempotency_key="one",
            )
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    thread = threading.Thread(target=finalize_first)
    thread.start()
    assert entered.wait(5)
    second_result = []

    def finalize_second():
        try:
            second_result.append(second.finalize(
                runs["STORY-slim-995"].run_id, story_id="STORY-slim-995",
                title="Two", tasks=["two"], idempotency_key="two",
            ))
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    other = threading.Thread(target=finalize_second)
    other.start()
    release.set()
    thread.join(5)
    other.join(5)

    assert not thread.is_alive() and not other.is_alive()
    assert not errors and second_result
    assert BoardRenderer(StoryRepository(tmp_path)).check(tmp_path / "docs/product/sprint_board.md")
    assert engine.status(runs["STORY-slim-994"].run_id)["status"] == "completed"
    assert engine.status(runs["STORY-slim-995"].run_id)["status"] == "completed"


def test_context_stage_recovery_rejects_changed_snapshot(tmp_path):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-993"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    journal_path = finalizer._journal_path(run.run_id)
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    journal.pop("fingerprints")
    journal["stage"] = "context"
    journal_path.write_text(json.dumps(journal), encoding="utf-8")
    spec = tmp_path / "docs/specs" / f"{story_id}.md"
    spec.write_text(spec.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")

    with pytest.raises(WorkUnitError, match="corrupt_finalize_journal"):
        finalizer.finalize(
            run.run_id, story_id=story_id, title="Title", tasks=["one"],
            idempotency_key="finalize",
        )
    assert json.loads(journal_path.read_text(encoding="utf-8"))["stage"] == "context"


def test_completed_run_rejects_journal_without_story_contract(tmp_path):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-991"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    journal_path = finalizer._journal_path(run.run_id)
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    journal.pop("story_contract")
    journal_path.write_text(json.dumps(journal), encoding="utf-8")

    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)


def test_doctor_rejects_completed_run_with_tampered_projection(tmp_path):
    from pactkit.doctor import check_workflow_continuation
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine

    story_id = "STORY-slim-992"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    PlanFinalizer(tmp_path, engine).finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    (tmp_path / "docs/product/sprint_board.md").write_text("tampered\n", encoding="utf-8")

    health = check_workflow_continuation(tmp_path)
    assert f"corrupt WorkUnit state: {run.run_id}.json" in health["warnings"]
    assert health["work_unit_runs"] == []


def test_completed_work_unit_run_supersedes_legacy_act_checkpoint_diagnostics(tmp_path):
    """A preserved v1 checkpoint cannot resurrect a verified Core run."""
    from pactkit.continuation import ContinuationEngine, ContinuationStore

    story_id = "STORY-slim-994"
    _write_plan_inputs(tmp_path, story_id)
    generic = ContinuationEngine(tmp_path)
    run = generic.start("project-act", evidence={"spec_lint": "pass"})
    generic.bind_story(run["run_id"], story_id)
    generic.checkpoint(
        run["run_id"], step_id="red", evidence={"story_tests": {"exit_code": 1}},
    )
    generic.checkpoint(
        run["run_id"], step_id="green", evidence={"story_tests": {"exit_code": 0}},
    )
    generic.checkpoint(
        run["run_id"], step_id="regression_lint",
        evidence={"regression": "pass", "lint": "pass"},
    )
    completion = {
        "spec_lint": "pass", "story_tests": {"exit_code": 0},
        "regression": "pass", "lint": "pass",
        "coverage": {"R1": ["test"]},
        "acceptance_coverage": {"AC1": ["test"]},
        "board_tasks": ["one"],
    }
    generic.checkpoint(
        run["run_id"], step_id="sync_coverage", evidence=completion,
        status="completed",
    )

    legacy = {
        "schema_version": 1, "story_id": story_id, "command": "$project-act",
        "phase": "Phase 1: preflight", "step_id": "preflight",
        "status": "in_progress", "evidence": {"spec_lint": "pass"},
        "fingerprints": {}, "blocker": "", "blocker_kind": None,
        "updated_at": "2026-08-23T00:00:00+00:00",
    }
    legacy_path = tmp_path / ".pactkit/continuations" / f"{story_id}.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
    before = legacy_path.read_bytes()

    store = ContinuationStore(tmp_path)
    result = store.resume(story_id)

    assert result["decision"] == "completed"
    assert result["run_id"] == run["run_id"]
    assert legacy_path.read_bytes() == before
    status = store.status(story_id)
    assert status["decision"] == "completed"
    assert status["run_id"] == run["run_id"]
    guard = generic.finish_guard(story_id)
    assert guard["decision"] == "done"
    assert guard["run_id"] == run["run_id"]

    # The directory is recovery authority. An unreadable competing v2 record
    # must block supersession instead of being silently ignored.
    corrupt_path = generic.directory / "run-unknown.json"
    corrupt_path.write_text("{not-json", encoding="utf-8")

    ambiguous_resume = store.resume(story_id)
    assert ambiguous_resume["decision"] == "fail_closed"
    assert ambiguous_resume["status"] == "completed"
    assert ambiguous_resume["run_id"] == run["run_id"]
    assert ambiguous_resume["reason_code"] == "ambiguous_v2_state"
    ambiguous_status = store.status(story_id)
    assert ambiguous_status["decision"] == "fail_closed"
    assert ambiguous_status["status"] == "completed"
    assert ambiguous_status["run_id"] == run["run_id"]
    assert generic.finish_guard(story_id)["decision"] == "fail_closed"


def test_active_or_malformed_generic_act_run_cannot_supersede_legacy_checkpoint(tmp_path):
    """Only verified terminal v2 Act state may retire an active v1 handoff."""
    from pactkit.continuation import ContinuationEngine, ContinuationStore

    story_id = "STORY-slim-997"
    _write_plan_inputs(tmp_path, story_id)
    legacy = {
        "schema_version": 1, "story_id": story_id, "command": "$project-act",
        "phase": "Phase 1: preflight", "step_id": "preflight",
        "status": "in_progress", "evidence": {"spec_lint": "pass"},
        "fingerprints": {}, "blocker": "", "blocker_kind": None,
        "updated_at": "2026-08-23T00:00:00+00:00",
    }
    legacy_path = tmp_path / ".pactkit/continuations" / f"{story_id}.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(json.dumps(legacy), encoding="utf-8")

    engine = ContinuationEngine(tmp_path)
    active = engine.start("project-act", evidence={"spec_lint": "pass"})
    engine.bind_story(active["run_id"], story_id)
    assert ContinuationStore(tmp_path).resume(story_id)["decision"] == "blocked"

    active_path = engine.path_for(active["run_id"])
    active_path.write_text(
        json.dumps({"run_id": active["run_id"], "story_id": story_id,
                    "workflow_id": "project-act", "status": "completed"}),
        encoding="utf-8",
    )
    malformed = ContinuationStore(tmp_path).resume(story_id)
    assert malformed["decision"] == "fail_closed"
    assert malformed["reason_code"] == "ambiguous_v2_state"


def test_finalizer_rejects_completed_run_with_pre_context_journal(tmp_path):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    finalizer.finalize(
        run.run_id, story_id=story_id, title="Title", tasks=["one"],
        idempotency_key="finalize",
    )
    journal_path = finalizer._journal_path(run.run_id)
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    journal.pop("fingerprints")
    journal["stage"] = "story"
    journal_path.write_text(json.dumps(journal), encoding="utf-8")

    with pytest.raises(WorkUnitError, match="corrupt_finalize_journal"):
        finalizer.finalize(
            run.run_id, story_id=story_id, title="Title", tasks=["one"],
            idempotency_key="finalize",
        )


def test_finalize_rejects_a_forged_completed_journal(tmp_path):
    from pactkit.workflow_engine import (
        PlanFinalizer, WorkflowEngine, WorkUnitError, _finalize_request_digest,
    )

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)
    finalizer = PlanFinalizer(tmp_path, engine)
    journal_path = finalizer._journal_path(run.run_id)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(json.dumps({
        "run_id": run.run_id,
        "story_id": story_id,
        "idempotency_key": "finalize",
        "request_digest": _finalize_request_digest(
            run_id=run.run_id, story_id=story_id, title="Title", tasks=["one"],
        ),
        "stage": "completed",
    }), encoding="utf-8")

    with pytest.raises(WorkUnitError, match="corrupt_finalize_journal"):
        finalizer.finalize(
            run.run_id, story_id=story_id, title="Title", tasks=["one"],
            idempotency_key="finalize",
        )

    assert engine.status(run.run_id)["status"] == "running"


def test_plan_run_cannot_be_completed_outside_journaled_finalizer(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, story_id)

    with pytest.raises(WorkUnitError, match="finalize_must_use_plan_finalizer"):
        engine.complete(run.run_id, fingerprints={})

    assert engine.status(run.run_id)["status"] == "running"
    assert not (tmp_path / "docs/product/stories" / f"{story_id}.yaml").exists()


def test_legacy_state_import_is_non_destructive_and_stop_hook_is_optional(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine

    legacy = tmp_path / ".pactkit/continuations/STORY-slim-999.json"
    legacy.parent.mkdir(parents=True)
    payload = {"schema_version": 1, "story_id": "STORY-slim-999", "status": "in_progress", "step_id": "red"}
    legacy.write_text(json.dumps(payload), encoding="utf-8")
    engine = WorkflowEngine(tmp_path)
    imported = engine.import_legacy(legacy)
    assert imported.source_schema_version == 1
    assert json.loads(legacy.read_text()) == payload
    status = engine.status(imported.run_id)
    assert status["guarantee_level"] == "guided"
    assert status["stop_hook_required"] is False


def test_legacy_blocked_state_is_preserved_and_cannot_be_acquired(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    legacy = tmp_path / ".pactkit/continuations/STORY-slim-997.json"
    legacy.parent.mkdir(parents=True)
    payload = {
        "schema_version": 2,
        "story_id": "STORY-slim-997",
        "status": "blocked",
        "blocker": "awaiting product decision",
    }
    legacy.write_text(json.dumps(payload), encoding="utf-8")

    engine = WorkflowEngine(tmp_path)
    imported = engine.import_legacy(legacy)

    assert imported.status == "blocked"
    assert engine.status(imported.run_id)["status"] == "blocked"
    assert engine._read(imported.run_id)["legacy_blocker"] == payload["blocker"]
    with pytest.raises(WorkUnitError, match="workflow_blocked"):
        engine.acquire(imported.run_id, owner="codex", idempotency_key="acquire")
    assert json.loads(legacy.read_text(encoding="utf-8")) == payload


def test_attempt_terminal_records_sanitized_capabilities_results_and_failure(tmp_path):
    from pactkit.workflow_engine import HostCapabilities, WorkflowEngine

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire")
    engine.record_turn_terminal(
        run.run_id,
        unit_id=unit.unit_id,
        unit_version=unit.version,
        owner="codex",
        host="codex",
        status="host_error",
        session="session-secret",
        thread="thread-secret",
        turn="turn-secret",
        capabilities=HostCapabilities(host="codex", tool_execution=True),
        result_refs=("artifact://receipt-1",),
        failure_reason="adapter_disconnect",
        started_at=10.0,
        adapter_version="codex-adapter-test",
    )

    attempt = engine._read(run.run_id)["attempts"][-1]
    assert attempt["host"] == "codex"
    assert attempt["unit_id"] == unit.unit_id
    assert attempt["unit_version"] == unit.version
    assert attempt["session_ref"].startswith("sha256:")
    assert "session-secret" not in attempt["session_ref"]
    assert attempt["capabilities"]["tool_execution"] is True
    assert attempt["execution_mode"] == "guided"
    assert attempt["decision"] == "retry"
    assert attempt["adapter_version"] == "codex-adapter-test"
    assert attempt["started_at"] == 10.0
    assert attempt["latency_ms"] >= 0
    assert attempt["result_refs"] == ["artifact://receipt-1"]
    assert attempt["reason_code"] == "adapter_disconnect"


def test_submit_attempt_persists_decision_latency_and_adapter_version(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=10)
    receipt = EvidenceReceipt.for_files(
        unit, owner="codex", root=tmp_path, files=[], claims={"guard": "pass"},
    )
    receipt = dataclasses.replace(receipt, adapter_version="codex-adapter-test", started_at=10)

    result = engine.submit(
        unit.unit_id, receipt, owner="codex", idempotency_key="submit", now=12,
    )

    attempt = engine._read(run.run_id)["attempts"][-1]
    assert attempt["decision"] == result.decision
    assert attempt["adapter_version"] == "codex-adapter-test"
    assert attempt["started_at"] == 10
    assert attempt["finished_at"] == 12
    assert attempt["latency_ms"] == 2000


def test_explicit_reject_persists_complete_audit_shape(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=10)

    engine.reject(unit.unit_id, owner="codex", reason_code="host_error", now=12)

    attempt = engine._read(run.run_id)["attempts"][-1]
    assert attempt["decision"] == "retry"
    assert attempt["adapter_version"] is None
    assert attempt["started_at"] == 12
    assert attempt["finished_at"] == 12
    assert attempt["latency_ms"] == 0


def test_failed_terminal_releases_unit_for_versioned_retry(tmp_path):
    from pactkit.workflow_engine import HostCapabilities, WorkflowEngine

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=10)

    engine.record_turn_terminal(
        run.run_id, unit_id=unit.unit_id, unit_version=unit.version,
        owner="codex", host="codex", status="host_error",
        capabilities=HostCapabilities(host="codex", tool_execution=True),
        now=11,
    )

    assert engine._read(run.run_id)["units"][unit.unit_id]["state"] == "retry"
    retry = engine.retry(unit.unit_id, owner="codex", idempotency_key="retry", now=11)
    assert retry.version == unit.version + 1


def test_attempt_terminal_fails_closed_for_incompatible_capability_protocol(tmp_path):
    from pactkit.workflow_engine import HostCapabilities, ProtocolError, WorkflowEngine

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire")

    with pytest.raises(ProtocolError, match="protocol_version_mismatch"):
        engine.record_turn_terminal(
                run.run_id,
                unit_id=unit.unit_id,
                unit_version=unit.version,
                owner="codex",
                host="codex",
            status="succeeded",
            capabilities=HostCapabilities(
                host="codex", protocol_version=999, tool_execution=True,
            ),
        )

    assert engine._read(run.run_id)["attempts"] == []


def test_turn_terminal_requires_a_unit_owned_by_the_run(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    first = engine.start("project-plan", goal="first")
    second = engine.start("project-plan", goal="second")
    unit = engine.acquire(first.run_id, owner="codex", idempotency_key="acquire")

    with pytest.raises(WorkUnitError, match="attempt_unit_mismatch"):
        engine.record_turn_terminal(
            second.run_id, unit_id=unit.unit_id, unit_version=unit.version,
            owner="codex", host="codex", status="interrupted",
        )


def test_story_resume_discovers_one_active_run_without_mutating_it(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id="STORY-slim-999")
    state_path = engine.path_for(run.run_id)
    before = state_path.read_bytes()

    resumed = engine.resume("STORY-slim-999")

    assert resumed == {
        "decision": "resume_at",
        "run_id": run.run_id,
        "workflow_id": "project-plan",
        "workflow_status": "running",
        "step_id": "preflight",
        "manual_resume_command": f"pactkit work-unit acquire {run.run_id} --owner <owner> --idempotency-key <key>",
    }
    assert state_path.read_bytes() == before


def test_story_resume_fails_closed_when_no_or_multiple_active_runs(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    with pytest.raises(WorkUnitError, match="no_active_workflow_run"):
        engine.resume("STORY-slim-999")

    first = engine.start("project-plan", goal="one", story_id="STORY-slim-999")
    duplicate = json.loads(engine.path_for(first.run_id).read_text(encoding="utf-8"))
    duplicate["run_id"] = "run-" + "0" * 32
    engine.path_for(duplicate["run_id"]).write_text(
        json.dumps(duplicate), encoding="utf-8"
    )
    with pytest.raises(WorkUnitError, match="multiple_active_workflow_runs"):
        engine.resume("STORY-slim-999")


def test_start_rejects_a_second_active_run_for_the_same_story(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path)
    first = engine.start("project-plan", goal="one", story_id="STORY-slim-999")

    with pytest.raises(WorkUnitError, match="story_already_has_active_workflow_run"):
        engine.start("project-plan", goal="two", story_id="STORY-slim-999")

    assert engine.resume("STORY-slim-999")["run_id"] == first.run_id


def test_story_identity_unit_can_atomically_bind_an_unbound_plan_run(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkUnitError

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    preflight = engine.acquire(run.run_id, owner="codex", idempotency_key="preflight")
    engine.submit(
        preflight.unit_id,
        EvidenceReceipt.for_files(
            preflight, owner="codex", root=tmp_path, files=[], claims={"guard": "pass"},
        ),
        owner="codex", idempotency_key="preflight-submit",
    )
    clarification = engine.acquire(run.run_id, owner="codex", idempotency_key="clarification")
    engine.submit(
        clarification.unit_id,
        EvidenceReceipt.for_files(
            clarification, owner="codex", root=tmp_path, files=[],
            claims={"clarification_resolved": True},
        ),
        owner="codex", idempotency_key="clarification-submit",
    )
    archaeology = engine.acquire(run.run_id, owner="codex", idempotency_key="archaeology")
    engine.submit(
        archaeology.unit_id,
        EvidenceReceipt.for_files(
            archaeology, owner="codex", root=tmp_path, files=[], claims={"trace": ["x"]},
        ),
        owner="codex", idempotency_key="archaeology-submit",
    )
    identity = engine.acquire(run.run_id, owner="codex", idempotency_key="identity")

    bound = engine.bind_story(
        run.run_id, story_id="STORY-slim-999", owner="codex",
        idempotency_key="bind-story",
    )
    assert bound.story_id == "STORY-slim-999"
    accepted = engine.submit(
        identity.unit_id,
        EvidenceReceipt.for_files(
            identity, owner="codex", root=tmp_path, files=[],
            claims={"story_id": "STORY-slim-999"},
        ),
        owner="codex", idempotency_key="identity-submit",
    )
    assert accepted.attempt_status == "succeeded"

    with pytest.raises(WorkUnitError, match="story_identity_mismatch"):
        engine.bind_story(
            run.run_id, story_id="STORY-slim-998", owner="codex",
            idempotency_key="late-bind",
        )
    with pytest.raises(WorkUnitError, match="story_bind_not_allowed"):
        engine.bind_story(
            run.run_id, story_id="STORY-slim-999", owner="codex",
            idempotency_key="late-bind-same-story",
        )


def test_story_identity_cannot_succeed_before_core_binds_a_story(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    for step_id, claims in (
        ("preflight", {"guard": "pass"}),
        ("clarification", {"clarification_resolved": True}),
        ("archaeology", {"trace": ["workflow_engine"]}),
    ):
        unit = engine.acquire(run.run_id, owner="alice", idempotency_key=f"acquire-{step_id}")
        result = engine.submit(
            unit.unit_id, EvidenceReceipt.for_files(unit, owner="alice", root=tmp_path, files=[], claims=claims),
            owner="alice", idempotency_key=f"submit-{step_id}",
        )
        assert result.attempt_status == "succeeded"

    identity = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire-identity")
    result = engine.submit(
        identity.unit_id,
        EvidenceReceipt.for_files(identity, owner="alice", root=tmp_path, files=[], claims={}),
        owner="alice", idempotency_key="submit-identity",
    )

    assert result.attempt_status == "rejected"
    assert result.reason_code == "validator_failed"
    assert engine._read(run.run_id)["story_id"] is None


def test_bind_story_idempotency_replays_original_run_snapshot(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    for step_id, claims in (
        ("preflight", {"guard": "pass"}),
        ("clarification", {"clarification_resolved": True}),
        ("archaeology", {"trace": ["workflow_engine"]}),
    ):
        unit = engine.acquire(run.run_id, owner="alice", idempotency_key=f"acquire-{step_id}")
        assert unit.step_id == step_id
        result = engine.submit(
            unit.unit_id,
            EvidenceReceipt.for_files(unit, owner="alice", root=tmp_path, files=[], claims=claims),
            owner="alice", idempotency_key=f"submit-{step_id}",
        )
        assert result.attempt_status == "succeeded"

    identity = engine.acquire(run.run_id, owner="alice", idempotency_key="acquire-identity")
    first = engine.bind_story(
        run.run_id, story_id="STORY-slim-999", owner="alice",
        idempotency_key="bind-story",
    )
    accepted = engine.submit(
        identity.unit_id,
        EvidenceReceipt.for_files(
            identity, owner="alice", root=tmp_path, files=[],
            claims={"story_id": "STORY-slim-999"},
        ),
        owner="alice", idempotency_key="submit-identity",
    )
    replay = engine.bind_story(
        run.run_id, story_id="STORY-slim-999", owner="alice",
        idempotency_key="bind-story",
    )

    assert accepted.attempt_status == "succeeded"
    assert first.current_index == 3
    assert replay == first
    assert engine.status(run.run_id)["step_id"] == "spec_scaffold"


def test_completed_legacy_state_is_imported_without_regression(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine

    legacy = tmp_path / ".pactkit/continuations/STORY-slim-998.json"
    legacy.parent.mkdir(parents=True)
    payload = {"schema_version": 2, "story_id": "STORY-slim-998", "status": "completed"}
    legacy.write_text(json.dumps(payload), encoding="utf-8")

    engine = WorkflowEngine(tmp_path)
    imported = engine.import_legacy(legacy)

    assert imported.status == "completed"
    assert engine.status(imported.run_id)["status"] == "completed"
    assert json.loads(legacy.read_text(encoding="utf-8")) == payload


def test_portable_methods_are_single_source_and_stateless():
    from pactkit.portable_methods import get_portable_methods
    from pactkit.prompts.skills import get_skill_manifest

    methods = get_portable_methods()
    names = {item["name"] for item in methods}
    deployed = {item["name"]: item for item in get_skill_manifest()}
    assert names == {
        "pactkit-method-clarify", "pactkit-method-architecture-trace",
        "pactkit-method-spec-writing", "pactkit-method-tdd",
        "pactkit-method-verification", "pactkit-method-release-preparation",
    }
    assert all(deployed[name]["skill_md"] == item["skill_md"] for name, item in
               ((item["name"], item) for item in methods))
    assert all("completion checkpoint" not in item["skill_md"].lower() for item in methods)
    assert all("WorkflowRun" not in item["skill_md"] for item in methods)


def test_work_unit_cli_start_acquire_status(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")
    started = subprocess.run(
        [sys.executable, "-m", "pactkit", "work-unit", "start", "project-plan",
         "--goal", "plan safely", "--story-id", "STORY-slim-999"],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert started.returncode == 0, started.stderr + started.stdout
    run_id = json.loads(started.stdout[started.stdout.index("{"):])["run_id"]
    acquired = subprocess.run(
        [sys.executable, "-m", "pactkit", "work-unit", "acquire", run_id,
         "--owner", "codex", "--idempotency-key", "a1"],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert acquired.returncode == 0, acquired.stderr + acquired.stdout
    unit = json.loads(acquired.stdout[acquired.stdout.index("{"):])
    assert unit["step_id"] == "preflight"
    status = subprocess.run(
        [sys.executable, "-m", "pactkit", "work-unit", "status", run_id],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert json.loads(status.stdout)["stop_hook_required"] is False


def test_work_unit_cli_binds_story_and_resumes_the_same_run(tmp_path):
    _initialize_work_unit_project(tmp_path)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")

    def invoke(*args):
        result = subprocess.run(
            [sys.executable, "-m", "pactkit", "work-unit", *args],
            cwd=tmp_path, env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr + result.stdout
        return json.loads(result.stdout[result.stdout.index("{"):])

    started = invoke("start", "project-plan", "--goal", "plan safely")
    run_id = started["run_id"]
    unit = invoke("acquire", run_id, "--owner", "codex", "--idempotency-key", "preflight")
    invoke(
        "submit", unit["unit_id"], "--owner", "codex", "--idempotency-key", "preflight-submit",
        "--receipt", json.dumps({
            "schema_version": 1, "unit_id": unit["unit_id"], "unit_version": unit["version"],
            "owner": "codex", "claims": {"guard": "pass"},
        }),
    )
    unit = invoke("acquire", run_id, "--owner", "codex", "--idempotency-key", "clarification")
    invoke(
        "submit", unit["unit_id"], "--owner", "codex", "--idempotency-key", "clarification-submit",
        "--receipt", json.dumps({
            "schema_version": 1, "unit_id": unit["unit_id"], "unit_version": unit["version"],
            "owner": "codex", "claims": {"clarification_resolved": True},
        }),
    )
    unit = invoke("acquire", run_id, "--owner", "codex", "--idempotency-key", "archaeology")
    invoke(
        "submit", unit["unit_id"], "--owner", "codex", "--idempotency-key", "archaeology-submit",
        "--receipt", json.dumps({
            "schema_version": 1, "unit_id": unit["unit_id"], "unit_version": unit["version"],
            "owner": "codex", "claims": {"trace": ["workflow_engine"]},
        }),
    )
    unit = invoke("acquire", run_id, "--owner", "codex", "--idempotency-key", "identity")
    bound = invoke(
        "bind-story", run_id, "STORY-slim-999", "--owner", "codex",
        "--idempotency-key", "bind",
    )
    assert bound["story_id"] == "STORY-slim-999"
    resumed = invoke("resume", "STORY-slim-999")
    assert resumed["run_id"] == run_id
    assert resumed["step_id"] == "story_identity"
    assert unit["step_id"] == "story_identity"


def test_plan_prompt_is_a_work_unit_facade():
    from pactkit.prompts.commands import COMMANDS_CONTENT, get_deployable_commands

    prompt = get_deployable_commands()["project-plan.md"]
    assert "pactkit work-unit" in prompt
    assert "one WorkUnit" in prompt
    assert "pactkit-codex-work-unit run" in prompt
    assert "pactkit-codex-work-unit execute" not in prompt
    assert "finalize-plan" in prompt
    assert "Phase 0.7" not in prompt
    assert "Do NOT try to plan the entire Spec" not in prompt
    assert "Phase 0.7" in COMMANDS_CONTENT["project-plan.md"]


def test_manifest_uses_versioned_truthful_host_contract(tmp_path):
    from pactkit.deploy_manifest import write_deploy_manifest

    for host in ("classic", "opencode", "codex", "copilot"):
        payload = json.loads(write_deploy_manifest(tmp_path / host, host).read_text())
        contract = payload["host_capabilities"]
        assert contract["protocol_version"] == 1
        assert contract["verification_source"]
        assert contract["execution_mode"] in {"portable", "guided", "resumable", "managed"}
        assert payload["workflow_continuation"]["stop_hook_required"] is False


def test_manifest_workflow_guarantee_matches_the_declared_host_capability(tmp_path):
    """A manifest must not advertise more than its own capability profile."""
    from pactkit.deploy_manifest import write_deploy_manifest

    expected = {
        "classic": "portable",
        "opencode": "portable",
        "codex": "guided",
        "copilot": "guided",
    }
    for host, mode in expected.items():
        payload = json.loads(write_deploy_manifest(tmp_path / host, host).read_text())
        capability = payload["host_capabilities"]
        workflow = payload["workflow_continuation"]
        assert capability["execution_mode"] == mode
        assert workflow["execution_mode"] == mode
        assert workflow["guarantee_level"] == mode
        assert workflow["e2e_validated"] is capability["e2e_validated"]


def test_explicit_reject_expire_retry_and_write_scope(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkUnitError

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path, lease_seconds=5)
    run = engine.start("project-plan", goal="plan", story_id="STORY-slim-999")
    first = engine.acquire(run.run_id, owner="codex", idempotency_key="preflight", now=1)
    engine.submit(
        first.unit_id,
        EvidenceReceipt.for_files(first, owner="codex", root=tmp_path, files=[], claims={"guard": "pass"}),
        owner="codex", idempotency_key="preflight-submit", now=2,
    )
    clarification = engine.acquire(run.run_id, owner="codex", idempotency_key="clarification", now=3)
    engine.submit(
        clarification.unit_id,
        EvidenceReceipt.for_files(clarification, owner="codex", root=tmp_path, files=[], claims={"clarification_resolved": True}),
        owner="codex", idempotency_key="clarification-submit", now=4,
    )
    archaeology = engine.acquire(run.run_id, owner="codex", idempotency_key="archaeology", now=5)
    engine.submit(
        archaeology.unit_id,
        EvidenceReceipt.for_files(archaeology, owner="codex", root=tmp_path, files=[], claims={"trace": ["x"]}),
        owner="codex", idempotency_key="archaeology-submit", now=6,
    )
    identity = engine.acquire(run.run_id, owner="codex", idempotency_key="identity", now=7)
    engine.submit(
        identity.unit_id,
        EvidenceReceipt.for_files(identity, owner="codex", root=tmp_path, files=[], claims={"story_id": "STORY-slim-999"}),
        owner="codex", idempotency_key="identity-submit", now=8,
    )
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="a", now=10)
    rejected_scope = engine.submit(
        unit.unit_id,
        EvidenceReceipt(1, unit.unit_id, unit.version, "codex", {}, {"src/evil.py": "missing"}),
        owner="codex", idempotency_key="bad", now=11,
    )
    assert rejected_scope.attempt_status == "rejected"
    assert rejected_scope.reason_code == "write_scope_violation"
    assert engine._read(run.run_id)["units"][unit.unit_id]["state"] == "retry"
    with pytest.raises(WorkUnitError, match="unit_not_rejectable"):
        engine.reject(unit.unit_id, owner="codex", reason_code="host_error", now=12)
    retry = engine.retry(unit.unit_id, owner="codex", idempotency_key="retry-1", now=13)
    assert retry.version == 2
    assert retry.unit_id == unit.unit_id
    expired = engine.expire(unit.unit_id, owner="codex", now=20)
    assert expired["state"] == "expired"


def test_malformed_candidate_receipt_is_audited_and_recoverable(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=10)
    malformed = EvidenceReceipt(
        schema_version=1,
        unit_id=unit.unit_id,
        unit_version=unit.version,
        owner="codex",
        claims={"guard": "pass"},
        # A non-string path would otherwise reach fnmatch/path construction
        # and escape the receipt protocol without an Attempt.
        file_fingerprints={42: "not-a-fingerprint"},
        capabilities={"unexpected": object()},
    )

    result = engine.submit(
        unit.unit_id, malformed, owner="codex", idempotency_key="submit", now=11,
    )

    assert result.attempt_status == "rejected"
    assert result.reason_code == "malformed_receipt"
    attempt = engine._read(run.run_id)["attempts"][-1]
    assert attempt["reason_code"] == "malformed_receipt"
    assert attempt["capabilities"] == {}
    assert engine._read(run.run_id)["units"][unit.unit_id]["state"] == "retry"


@pytest.mark.parametrize(
    "candidate",
    [
        {"claims": {"score": float("nan")}},
        {"claims": {"score": float("inf")}},
        {"capabilities": {"latency": float("-inf")}},
        {"claims": {"nested": [1, {"score": float("nan")}]}},
    ],
)
def test_receipt_rejects_non_finite_nested_json_evidence(tmp_path, candidate):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path, lease_seconds=20)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=1)
    receipt = EvidenceReceipt(
        schema_version=1, unit_id=unit.unit_id, unit_version=unit.version,
        owner="codex", claims=candidate.get("claims", {"guard": "pass"}),
        capabilities=candidate.get("capabilities", {}),
    )

    result = engine.submit(
        unit.unit_id, receipt, owner="codex", idempotency_key="submit", now=2,
    )

    assert result.attempt_status == "rejected"
    assert result.reason_code == "malformed_receipt"
    state = engine._read(run.run_id)
    assert state["units"][unit.unit_id]["state"] == "retry"
    assert state["attempts"][-1]["capabilities"] == {}


@pytest.mark.parametrize(
    "receipt_fields",
    [
        {"schema_version": True},
        {"unit_version": True},
    ],
)
def test_receipt_rejects_boolean_protocol_versions(tmp_path, receipt_fields):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path, lease_seconds=20)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=1)
    receipt = EvidenceReceipt(
        schema_version=receipt_fields.get("schema_version", 1),
        unit_id=unit.unit_id,
        unit_version=receipt_fields.get("unit_version", unit.version),
        owner="codex", claims={"guard": "pass"},
    )

    result = engine.submit(
        unit.unit_id, receipt, owner="codex", idempotency_key="submit", now=2,
    )

    assert result.attempt_status == "rejected"
    assert result.reason_code == "malformed_receipt"
    assert engine._read(run.run_id)["units"][unit.unit_id]["state"] == "retry"


def test_receipt_rejects_boolean_started_at(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path, lease_seconds=20)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=1)
    receipt = EvidenceReceipt(
        schema_version=1, unit_id=unit.unit_id, unit_version=unit.version,
        owner="codex", claims={"guard": "pass"}, started_at=True,
    )

    result = engine.submit(
        unit.unit_id, receipt, owner="codex", idempotency_key="submit", now=2,
    )

    assert result.attempt_status == "rejected"
    assert result.reason_code == "malformed_receipt"
    assert engine._read(run.run_id)["attempts"][-1]["started_at"] == 2


def test_terminal_attempt_rejects_boolean_unit_version_before_state_changes(tmp_path):
    from pactkit.workflow_engine import HostCapabilities, WorkflowEngine, WorkUnitError

    engine = WorkflowEngine(tmp_path, lease_seconds=20)
    run = engine.start("project-plan", goal="plan")
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="acquire", now=1)

    with pytest.raises(WorkUnitError, match="invalid_attempt_unit_version"):
        engine.record_turn_terminal(
            run.run_id, unit_id=unit.unit_id, unit_version=True,
            owner="codex", host="codex", status="host_error",
            capabilities=HostCapabilities(host="codex"), now=2,
        )

    state = engine._read(run.run_id)
    assert state["units"][unit.unit_id]["state"] == "leased"
    assert state["attempts"] == []


def test_spec_lint_validator_rereads_repository(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    story = "STORY-slim-999"
    spec = tmp_path / "docs/specs" / f"{story}.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("# invalid placeholder TBD\n")
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story)
    for step, claims in (
        ("preflight", {"guard": "pass"}),
        ("clarification", {"clarification_resolved": True}),
        ("archaeology", {"trace": ["x"]}),
        ("story_identity", {"story_id": story}),
        ("spec_scaffold", {}),
        ("spec_content", {}),
        ("spec_security", {"security_scoped": True}),
    ):
        unit = engine.acquire(run.run_id, owner="codex", idempotency_key=f"{step}-a", now=1)
        files = [f"docs/specs/{story}.md"] if step in {"spec_scaffold", "spec_security"} else []
        if step == "spec_content":
            graph = tmp_path / "docs/architecture/graphs/system_design.mmd"
            graph.parent.mkdir(parents=True, exist_ok=True)
            graph.write_text("graph TD\n", encoding="utf-8")
            files = [f"docs/specs/{story}.md", "docs/architecture/graphs/system_design.mmd"]
        engine.submit(
            unit.unit_id, EvidenceReceipt.for_files(unit, owner="codex", root=tmp_path, files=files, claims=claims),
            owner="codex", idempotency_key=f"{step}-s", now=2,
        )
    unit = engine.acquire(run.run_id, owner="codex", idempotency_key="a", now=1)
    receipt = EvidenceReceipt.for_files(
        unit, owner="codex", root=tmp_path,
        files=[f"docs/specs/{story}.md"], claims={"success": True},
    )
    result = engine.submit(unit.unit_id, receipt, owner="codex", idempotency_key="s", now=2)
    assert result.attempt_status == "rejected"
    assert result.reason_code == "validator_failed"


def test_spec_content_validator_rejects_non_mermaid_hld(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    story = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story)
    _advance_plan_to_step(engine, run.run_id, tmp_path, story, "spec_content")
    hld = tmp_path / "docs/architecture/graphs/system_design.mmd"
    hld.write_text("not a Mermaid graph\n", encoding="utf-8")
    unit = engine.acquire(
        run.run_id, owner="codex", idempotency_key="invalid-hld-acquire",
    )
    receipt = EvidenceReceipt.for_files(
        unit, owner="codex", root=tmp_path,
        files=[f"docs/specs/{story}.md", "docs/architecture/graphs/system_design.mmd"],
    )

    result = engine.submit(
        unit.unit_id, receipt, owner="codex", idempotency_key="invalid-hld-submit",
    )

    assert result.attempt_status == "rejected"
    assert result.reason_code == "validator_failed"


def test_plan_cannot_start_at_or_finalize_without_verified_prior_units(tmp_path):
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    with pytest.raises(TypeError):
        engine.start("project-plan", goal="skip", story_id=story_id, start_step="finalize_plan")

    run = engine.start("project-plan", goal="skip", story_id=story_id)
    with pytest.raises(WorkUnitError, match="finalize_not_ready"):
        PlanFinalizer(tmp_path, engine).finalize(
            run.run_id, story_id=story_id, title="Title", tasks=["one"], idempotency_key="x",
        )


def test_empty_receipts_and_cross_unit_submit_idempotency_are_rejected(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkUnitError

    _initialize_work_unit_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="validate", story_id="STORY-slim-999")
    preflight = engine.acquire(run.run_id, owner="codex", idempotency_key="preflight", now=1)
    empty = EvidenceReceipt.for_files(preflight, owner="codex", root=tmp_path, files=[])
    rejected = engine.submit(preflight.unit_id, empty, owner="codex", idempotency_key="shared", now=2)
    assert rejected.reason_code == "validator_failed"

    retry = engine.retry(preflight.unit_id, owner="codex", idempotency_key="retry", now=3)
    accepted = engine.submit(
        retry.unit_id,
        EvidenceReceipt.for_files(retry, owner="codex", root=tmp_path, files=[], claims={"guard": "pass"}),
        owner="codex", idempotency_key="retry-submit", now=4,
    )
    assert accepted.attempt_status == "succeeded"
    clarification = engine.acquire(run.run_id, owner="codex", idempotency_key="clarification", now=5)
    with pytest.raises(WorkUnitError, match="idempotency_key_conflict"):
        engine.submit(
            clarification.unit_id,
            EvidenceReceipt.for_files(clarification, owner="codex", root=tmp_path, files=[], claims={"clarification_resolved": True}),
            owner="codex", idempotency_key="retry-submit", now=6,
        )


def test_write_units_reject_missing_files_even_when_receipt_fingerprint_matches(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    story_id = "STORY-slim-999"
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=story_id)
    for step, claims in (
        ("preflight", {"guard": "pass"}),
        ("clarification", {"clarification_resolved": True}),
        ("archaeology", {"trace": ["x"]}),
        ("story_identity", {"story_id": story_id}),
    ):
        unit = engine.acquire(run.run_id, owner="codex", idempotency_key=f"{step}-acquire")
        result = engine.submit(
            unit.unit_id,
            EvidenceReceipt.for_files(unit, owner="codex", root=tmp_path, files=[], claims=claims),
            owner="codex", idempotency_key=f"{step}-submit",
        )
        assert result.attempt_status == "succeeded"

    scaffold = engine.acquire(run.run_id, owner="codex", idempotency_key="scaffold-acquire")
    result = engine.submit(
        scaffold.unit_id,
        EvidenceReceipt.for_files(
            scaffold, owner="codex", root=tmp_path,
            files=[f"docs/specs/{story_id}.md"],
        ),
        owner="codex", idempotency_key="scaffold-submit",
    )

    assert result.attempt_status == "rejected"
    assert result.reason_code == "fingerprint_mismatch"


def test_doctor_reports_work_unit_guarantee(tmp_path):
    from pactkit.doctor import check_workflow_continuation
    from pactkit.workflow_engine import WorkflowEngine

    WorkflowEngine(tmp_path).start("project-plan", goal="plan")
    result = check_workflow_continuation(tmp_path, home=tmp_path / "empty-home")
    assert result["guarantee_level"] == "guided"
    assert result["stop_hook_required"] is False
    assert result["work_unit_runs"]


def test_doctor_derives_guarantee_from_project_deployment_capability(tmp_path):
    from pactkit.deploy_manifest import write_deploy_manifest
    from pactkit.doctor import check_workflow_continuation

    write_deploy_manifest(tmp_path / ".claude", "classic")

    result = check_workflow_continuation(tmp_path, home=tmp_path / "empty-home")

    assert result["guarantee_level"] == "portable"
    assert result["host_guarantees"] == {"classic": "portable"}


def _write_codex_capability_manifest(root: Path, mode: str = "resumable") -> None:
    manifest = root / ".codex/.pactkit-deployed.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "format": "codex",
        "host_capabilities": {"execution_mode": mode},
        "workflow_continuation": {"guarantee_level": mode},
    }), encoding="utf-8")


def test_doctor_uses_global_codex_capability_when_project_manifest_is_absent(tmp_path):
    from pactkit.doctor import check_workflow_continuation

    project = tmp_path / "project"
    fake_home = tmp_path / "home"
    project.mkdir()
    _write_codex_capability_manifest(fake_home)
    result = check_workflow_continuation(project, home=fake_home)
    assert result["guarantee_level"] == "resumable"
    assert result["host_guarantees"] == {"codex": "resumable"}


def test_doctor_prefers_project_codex_capability_over_global(tmp_path):
    from pactkit.doctor import check_workflow_continuation

    project = tmp_path / "project"
    fake_home = tmp_path / "home"
    project.mkdir()
    _write_codex_capability_manifest(project, "portable")
    _write_codex_capability_manifest(fake_home, "resumable")
    result = check_workflow_continuation(project, home=fake_home)
    assert result["guarantee_level"] == "portable"
    assert result["host_guarantees"] == {"codex": "portable"}


def test_doctor_does_not_mask_resumable_codex_with_guided_copilot(tmp_path):
    from pactkit.doctor import check_workflow_continuation

    project = tmp_path / "project"
    fake_home = tmp_path / "home"
    project.mkdir()
    _write_codex_capability_manifest(fake_home, "resumable")
    copilot = project / ".github/.pactkit-deployed.json"
    copilot.parent.mkdir(parents=True)
    copilot.write_text(json.dumps({
        "format": "copilot",
        "host_capabilities": {"execution_mode": "guided"},
        "workflow_continuation": {"guarantee_level": "guided"},
    }), encoding="utf-8")

    result = check_workflow_continuation(project, home=fake_home)

    assert result["guarantee_level"] == "resumable"
    assert result["host_guarantees"] == {
        "codex": "resumable", "copilot": "guided",
    }


def test_doctor_fails_closed_for_corrupt_global_codex_capability(tmp_path):
    from pactkit.doctor import check_workflow_continuation

    project = tmp_path / "project"
    fake_home = tmp_path / "home"
    project.mkdir()
    manifest = fake_home / ".codex/.pactkit-deployed.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{broken", encoding="utf-8")
    result = check_workflow_continuation(project, home=fake_home)
    assert result["guarantee_level"] == "portable"
    assert result["host_guarantees"] == {"codex": "portable"}
    assert result["warnings"] == [
        f"corrupt host capability manifest: {manifest}",
    ]


@pytest.mark.parametrize("payload", ["{not-json", "[]", "null", '"manifest"', "1"])
def test_doctor_fails_closed_for_corrupt_project_deployment_capability(tmp_path, payload):
    from pactkit.doctor import check_workflow_continuation

    manifest = tmp_path / ".claude" / ".pactkit-deployed.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(payload, encoding="utf-8")

    result = check_workflow_continuation(tmp_path, home=tmp_path / "empty-home")

    assert result["guarantee_level"] == "portable"
    assert result["host_guarantees"] == {"classic": "portable"}
    assert result["warnings"] == [
        "corrupt host capability manifest: .claude/.pactkit-deployed.json",
    ]


def test_doctor_reports_semantically_corrupt_work_unit_state(tmp_path):
    from pactkit.doctor import check_workflow_continuation
    from pactkit.workflow_engine import WorkflowEngine

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan")
    path = engine.path_for(run.run_id)
    state = json.loads(path.read_text(encoding="utf-8"))
    state["fingerprints"]["docs/specs/unknown.md"] = "not-a-sha256"
    path.write_text(json.dumps(state), encoding="utf-8")

    result = check_workflow_continuation(tmp_path)

    assert not result["work_unit_runs"]
    assert f"corrupt WorkUnit state: {path.name}" in result["warnings"]


@pytest.mark.parametrize("payload", ["[]", "null", "1"])
def test_doctor_reports_non_object_legacy_workflow_state(tmp_path, payload):
    from pactkit.doctor import check_workflow_continuation

    runs = tmp_path / ".pactkit/continuations/runs"
    runs.mkdir(parents=True)
    path = runs / f"run-{'0' * 32}.json"
    path.write_text(payload, encoding="utf-8")

    result = check_workflow_continuation(tmp_path)

    assert result["active"] == []
    assert f"corrupt workflow state: {path.name}" in result["warnings"]


@pytest.mark.parametrize("payload", ["[]", "null", "1"])
def test_doctor_reports_non_object_host_lease(tmp_path, payload):
    from pactkit.doctor import check_workflow_continuation

    hosts = tmp_path / ".pactkit/continuations/hosts"
    hosts.mkdir(parents=True)
    path = hosts / f"run-{'0' * 32}.json"
    path.write_text(payload, encoding="utf-8")

    result = check_workflow_continuation(tmp_path)

    assert f"corrupt host lease: {path.name}" in result["warnings"]


def test_finish_guard_fails_closed_for_non_object_workflow_checkpoint(tmp_path):
    from pactkit.continuation import ContinuationEngine

    engine = ContinuationEngine(tmp_path)
    run_id = f"run-{'0' * 32}"
    path = engine.path_for(run_id)
    path.parent.mkdir(parents=True)
    path.write_text("[]", encoding="utf-8")

    result = engine.finish_guard(run_id)

    assert result["decision"] == "fail_closed"
    assert result["reason_code"] == "invalid_state"
    assert result["exit_code"] == 2


def test_native_work_unit_registry_covers_every_project_command():
    from pactkit.config import VALID_COMMANDS
    from pactkit.workflow_engine import WORKFLOW_UNITS

    assert set(WORKFLOW_UNITS) == set(VALID_COMMANDS)
    assert [unit.step_id for unit in WORKFLOW_UNITS["project-act"]] == [
        "act_preflight", "red", "implementation", "story_tests",
        "regression_lint", "sync_coverage", "finalize_act",
    ]


def test_act_red_must_be_core_accepted_before_implementation(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    story_id = "STORY-slim-999"
    _write_plan_inputs(tmp_path, story_id)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-act", goal="implement", story_id=story_id)
    preflight = engine.acquire(run.run_id, owner="codex", idempotency_key="preflight")
    accepted = engine.submit(
        preflight.unit_id, EvidenceReceipt.for_files(
            preflight, owner="codex", root=tmp_path, files=[],
            claims={"spec_lint": "pass", "trace": ["target"]},
        ), owner="codex", idempotency_key="preflight-submit",
    )
    assert accepted.attempt_status == "succeeded"
    red = engine.acquire(run.run_id, owner="codex", idempotency_key="red")
    rejected = engine.submit(
        red.unit_id, EvidenceReceipt.for_files(
            red, owner="codex", root=tmp_path, files=[],
            claims={"story_tests": {"exit_code": 0}},
        ), owner="codex", idempotency_key="red-submit",
    )
    assert rejected.reason_code == "validator_failed"
    assert engine.status(run.run_id)["step_id"] == "red"


def test_generic_finalizer_is_journaled_and_replay_safe(tmp_path):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine, WorkflowFinalizer

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-debug", goal="diagnose")
    for step, claims in (
        ("preflight", {"ready": True}),
        ("hypotheses", {"evidence": ["reproduction"]}),
        ("diagnosis", {"root_cause": "cause", "next_action": "fix"}),
    ):
        unit = engine.acquire(run.run_id, owner="codex", idempotency_key=step)
        result = engine.submit(
            unit.unit_id, EvidenceReceipt.for_files(
                unit, owner="codex", root=tmp_path, files=[], claims=claims,
            ), owner="codex", idempotency_key=f"{step}-submit",
        )
        assert result.attempt_status == "succeeded"
    final = engine.acquire(run.run_id, owner="codex", idempotency_key="final")
    receipt = EvidenceReceipt.for_files(
        final, owner="codex", root=tmp_path, files=[],
        claims={"completed": True},
    )
    finalizer = WorkflowFinalizer(tmp_path, engine)
    first = finalizer.finalize(
        run.run_id, receipt, owner="codex", idempotency_key="final-v1",
    )
    second = finalizer.finalize(
        run.run_id, receipt, owner="codex", idempotency_key="final-v1",
    )
    assert first["status"] == second["status"] == "completed"
    assert engine.status(run.run_id)["status"] == "completed"


def test_act_finalizer_completes_story_tasks_and_board(tmp_path):
    from pactkit.governance import BoardRenderer, StoryRepository
    from pactkit.workflow_engine import WorkflowFinalizer

    engine, run, receipt = _prepare_act_run(tmp_path)
    result = WorkflowFinalizer(tmp_path, engine).finalize(
        run.run_id, receipt, owner="codex", idempotency_key="act-final",
    )
    repository = StoryRepository(tmp_path)
    record = repository.load("STORY-slim-999")
    assert result["status"] == "completed"
    assert record["status"] == "done"
    assert all(task["completed"] for task in record["tasks"])
    assert BoardRenderer(repository).check(tmp_path / "docs/product/sprint_board.md")
    assert "- [x] one" in (
        tmp_path / "docs/product/sprint_board.md"
    ).read_text(encoding="utf-8")
    story_bytes = repository.path_for("STORY-slim-999").read_bytes()
    board_bytes = (tmp_path / "docs/product/sprint_board.md").read_bytes()
    replay = WorkflowFinalizer(tmp_path, engine).finalize(
        run.run_id, receipt, owner="codex", idempotency_key="act-final",
    )
    assert replay["status"] == "completed"
    assert repository.path_for("STORY-slim-999").read_bytes() == story_bytes
    assert (tmp_path / "docs/product/sprint_board.md").read_bytes() == board_bytes


def test_completed_act_run_rejects_tampered_board_projection(tmp_path):
    from pactkit.workflow_engine import WorkflowFinalizer, WorkUnitError

    engine, run, receipt = _prepare_act_run(tmp_path)
    WorkflowFinalizer(tmp_path, engine).finalize(
        run.run_id, receipt, owner="codex", idempotency_key="act-final",
    )
    (tmp_path / "docs/product/sprint_board.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine.status(run.run_id)


def test_act_finalizer_rejects_noncanonical_board_tasks_without_mutation(tmp_path):
    from pactkit.governance import StoryRepository
    from pactkit.workflow_engine import WorkflowFinalizer, WorkUnitError

    engine, run, receipt = _prepare_act_run(tmp_path)
    state = engine._read(run.run_id, allow_finalize_recovery=True)
    sync = next(
        record for record in state["units"].values()
        if record["step_id"] == "sync_coverage"
    )
    sync["accepted_claims"]["board_tasks"] = ["wrong"]
    engine._write(state)
    before = StoryRepository(tmp_path).load("STORY-slim-999")
    with pytest.raises(WorkUnitError, match="workflow_completion_validation_failed"):
        WorkflowFinalizer(tmp_path, engine).finalize(
            run.run_id, receipt, owner="codex", idempotency_key="act-final",
        )
    assert StoryRepository(tmp_path).load("STORY-slim-999") == before


def test_act_finalizer_recovers_after_governance_projection_crash(tmp_path, monkeypatch):
    from pactkit.governance import StoryRepository
    from pactkit.workflow_engine import WorkflowFinalizer

    engine, run, receipt = _prepare_act_run(tmp_path)
    original_write = engine._write
    crashed = False

    def crash_before_run_completion(state):
        nonlocal crashed
        if state.get("status") == "completed" and not crashed:
            crashed = True
            raise OSError("simulated crash after governance projection")
        return original_write(state)

    monkeypatch.setattr(engine, "_write", crash_before_run_completion)
    finalizer = WorkflowFinalizer(tmp_path, engine)
    with pytest.raises(OSError, match="simulated crash"):
        finalizer.finalize(
            run.run_id, receipt, owner="codex", idempotency_key="act-final",
        )
    journal = json.loads(finalizer._journal_path(run.run_id).read_text(encoding="utf-8"))
    assert journal["stage"] == "governance"
    assert StoryRepository(tmp_path).load("STORY-slim-999")["status"] == "done"

    monkeypatch.setattr(engine, "_write", original_write)
    recovered = finalizer.finalize(
        run.run_id, receipt, owner="codex", idempotency_key="act-final",
    )
    assert recovered["status"] == "completed"
    assert json.loads(finalizer._journal_path(run.run_id).read_text(encoding="utf-8"))[
        "stage"
    ] == "completed"


def test_act_completion_requires_board_tasks():
    from pactkit.workflow_engine import WorkflowFinalizer

    evidence = {
        "story_tests": {"exit_code": 0}, "regression": "pass", "lint": "pass",
        "coverage": {"R1": ["test"]},
        "acceptance_coverage": {"AC1": ["test"]},
    }
    assert not WorkflowFinalizer._validate_pdca_completion("project-act", evidence)


def test_check_and_done_require_completed_story_predecessors(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkUnitError

    story_id = "STORY-slim-999"
    engine = WorkflowEngine(tmp_path)
    with pytest.raises(WorkUnitError, match="project-act_completion_required"):
        engine.start("project-check", goal="check", story_id=story_id)
    with pytest.raises(WorkUnitError, match="project-check_completion_required"):
        engine.start("project-done", goal="done", story_id=story_id)


def test_sprint_phase_requires_completed_child_runs_for_every_story(
    tmp_path, monkeypatch,
):
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowEngine

    stories = ["STORY-slim-901", "STORY-slim-902"]
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-sprint", goal="deliver sprint")
    preflight = engine.acquire(run.run_id, owner="codex", idempotency_key="preflight")
    assert engine.submit(
        preflight.unit_id,
        EvidenceReceipt.for_files(
            preflight, owner="codex", root=tmp_path, files=[],
            claims={"stories": stories},
        ),
        owner="codex", idempotency_key="preflight-submit",
    ).attempt_status == "succeeded"

    phase = engine.acquire(run.run_id, owner="codex", idempotency_key="plan")
    missing = engine.submit(
        phase.unit_id,
        EvidenceReceipt.for_files(
            phase, owner="codex", root=tmp_path, files=[],
            claims={"planned": True},
        ),
        owner="codex", idempotency_key="plan-missing-submit",
    )
    assert missing.reason_code == "validator_failed"
    assert engine.status(run.run_id)["step_id"] == "plan_phase"

    retried = engine.retry(
        phase.unit_id, owner="codex", idempotency_key="plan-retry",
    )
    monkeypatch.setattr(
        engine, "_completed_run_for_story",
        lambda story_id, workflow_id: (
            {"story_id": story_id, "workflow_id": workflow_id, "status": "completed"}
            if story_id in stories and workflow_id == "project-plan" else None
        ),
    )
    accepted = engine.submit(
        retried.unit_id,
        EvidenceReceipt.for_files(
            retried, owner="codex", root=tmp_path, files=[],
            claims={"planned": True},
        ),
        owner="codex", idempotency_key="plan-complete-submit",
    )
    assert accepted.attempt_status == "succeeded"
    assert engine.status(run.run_id)["step_id"] == "act_phase"


def test_every_sprint_lifecycle_phase_requires_explicit_orchestration_authorization():
    from pactkit.workflow_engine import WORKFLOW_UNITS

    phases = {
        unit.step_id: unit for unit in WORKFLOW_UNITS["project-sprint"]
        if unit.step_id.endswith("_phase")
    }
    assert set(phases) == {"plan_phase", "act_phase", "check_phase", "done_phase"}
    assert all(unit.manual_authorization == ("orchestrate",) for unit in phases.values())


def test_failed_completion_validation_keeps_terminal_unit_retryable(tmp_path):
    from pactkit.workflow_engine import (
        EvidenceReceipt, WorkflowEngine, WorkflowFinalizer, WorkUnitError,
    )

    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-debug", goal="diagnose")
    evidence_by_step = (
        ("preflight", {"ready": True}),
        ("hypotheses", {"evidence": ["reproduction"]}),
        ("diagnosis", {"root_cause": "cause", "next_action": "fix"}),
    )
    for step, claims in evidence_by_step:
        unit = engine.acquire(run.run_id, owner="codex", idempotency_key=step)
        assert engine.submit(
            unit.unit_id, EvidenceReceipt.for_files(
                unit, owner="codex", root=tmp_path, files=[], claims=claims,
            ), owner="codex", idempotency_key=f"{step}-submit",
        ).attempt_status == "succeeded"
    final = engine.acquire(run.run_id, owner="codex", idempotency_key="final")
    invalid = EvidenceReceipt.for_files(
        final, owner="codex", root=tmp_path, files=[], claims={"completed": False},
    )
    with pytest.raises(WorkUnitError, match="workflow_completion_validation_failed"):
        WorkflowFinalizer(tmp_path, engine).finalize(
            run.run_id, invalid, owner="codex", idempotency_key="bad-final",
        )
    state = engine._read(run.run_id)
    assert state["status"] == "running"
    assert state["units"][final.unit_id]["state"] == "retry"


def test_done_completion_rejects_a_well_formed_commit_that_is_not_head(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine, WorkflowFinalizer, WorkUnitError

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "pactkit@example.invalid"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "PactKit Test"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    marker = tmp_path / "marker.txt"
    marker.write_text("committed\n", encoding="utf-8")
    subprocess.run(["git", "add", "marker.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test"], cwd=tmp_path,
        check=True, capture_output=True,
    )

    evidence = {
        "audit": "pass",
        "governance": "pass",
        "deployment": "pass",
        "git": {"commit": "deadbee"},
    }
    finalizer = WorkflowFinalizer(tmp_path, WorkflowEngine(tmp_path))

    with pytest.raises(WorkUnitError, match="workflow_completion_validation_failed"):
        finalizer._validate_completion({"workflow_id": "project-done"}, evidence)


@pytest.mark.parametrize("payload", ["[]", "{not-json"])
def test_bind_story_fails_closed_for_corrupt_competing_checkpoint(tmp_path, payload):
    from pactkit.continuation import ContinuationEngine, ContinuationError

    engine = ContinuationEngine(tmp_path)
    run = engine.start(
        "project-plan",
        evidence={"guard": "pass", "input_fingerprint": "test-input"},
    )
    competing = engine.directory / f"run-{'f' * 32}.json"
    competing.write_text(payload, encoding="utf-8")

    with pytest.raises(ContinuationError, match="corrupt workflow checkpoint"):
        engine.bind_story(run["run_id"], "STORY-slim-999")

    assert engine.read(run["run_id"])["story_id"] is None


def test_acquire_zero_regression_without_write_scope_or_touches(tmp_path):
    """R7 (STORY-slim-20260824dd23a0ed3b4c): with no write_scope config and no
    Story Touches, WorkflowEngine.acquire produces a scope identical to the
    frozen template floor — resolve_scope adds nothing (zero regression).
    """
    from pactkit.workflow_engine import ACT_WORK_UNITS, WorkflowEngine

    _initialize_work_unit_project(tmp_path)
    sid = "STORY-slim-998"
    spec = tmp_path / "docs/specs" / f"{sid}.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(
        f"# {sid}: regression\n\n"
        "| Field | Value |\n|-------|-------|\n"
        f"| ID | {sid} |\n| Status | Draft |\n| Priority | P1 |\n| Release | 2.22.0 |\n\n"
        "## Dependency Surface\n\n"
        "| Field | Value |\n|-------|-------|\n"
        "| Depends on | None |\n| Provides | None |\n| Touches | None |\n| Conflict risk | LOW |\n",
        encoding="utf-8",
    )
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-act", goal="regression", story_id=sid)
    unit = engine.acquire(run.run_id, owner="claude", idempotency_key="reg-zero-1")

    preflight = next(u for u in ACT_WORK_UNITS if u.step_id == "act_preflight")
    expected_reads = tuple(r.replace("{story_id}", sid) for r in preflight.allowed_reads)
    assert unit.allowed_reads == expected_reads
    assert unit.allowed_writes == preflight.allowed_writes


# ---------------------------------------------------------------------------
# STORY-slim-2026082466c8670d9655 — completed runs survive cross-workflow
# projection evolution (predecessor-lookup leniency + context regen).
# ---------------------------------------------------------------------------

_ACT_SURVIVAL_CLAIMS = {
    "act_preflight": {"spec_lint": "pass", "trace": ["src/act_story.py"]},
    "red": {"story_tests": {"exit_code": 1}},
    "implementation": {"changed_files": ["src/act_story.py"]},
    "story_tests": {"story_tests": {"exit_code": 0}},
    "regression_lint": {"regression": "pass", "lint": "pass"},
    "sync_coverage": {
        "coverage": {"R1": ["test_act_story"]},
        "acceptance_coverage": {"AC1": ["test_act_story"]},
        "board_tasks": ["one", "two"],
    },
}
_ACT_SURVIVAL_FILES = {"red": ["tests/test_act_story.py"], "implementation": ["src/act_story.py"]}


def _finalize_act_for_story(root: Path, engine, story_id: str) -> str:
    """Advance + finalize an Act run for *story_id* (plan already finalized)."""
    from pactkit.workflow_engine import EvidenceReceipt, WorkflowFinalizer

    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests/test_act_story.py").write_text("def test_story():\n    assert True\n", encoding="utf-8")
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src/act_story.py").write_text("VALUE = True\n", encoding="utf-8")
    run = engine.start("project-act", goal="act", story_id=story_id)
    while engine.status(run.run_id)["step_id"] != "finalize_act":
        step = engine.status(run.run_id)["step_id"]
        unit = engine.acquire(run.run_id, owner="codex", idempotency_key=f"{step}-acquire")
        result = engine.submit(
            unit.unit_id, EvidenceReceipt.for_files(
                unit, owner="codex", root=root,
                files=_ACT_SURVIVAL_FILES.get(step, []),
                claims=_ACT_SURVIVAL_CLAIMS[step],
            ), owner="codex", idempotency_key=f"{step}-submit",
        )
        assert result.attempt_status == "succeeded", result
    final = engine.acquire(run.run_id, owner="codex", idempotency_key="final-acquire")
    receipt = EvidenceReceipt.for_files(
        final, owner="codex", root=root, files=[], claims={"completed": True},
    )
    WorkflowFinalizer(root, engine).finalize(
        run.run_id, receipt, owner="codex", idempotency_key=f"act-{story_id}",
    )
    return run.run_id


def test_check_start_survives_stale_plan_journal_after_act(tmp_path):
    """R2/R4: after Plan + Act finalize, project-check start must NOT crash
    with invalid_workflow_state (predecessor project-act found leniently)."""
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine

    sid = "STORY-slim-996"
    _write_plan_inputs(tmp_path, sid)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=sid)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, sid)
    PlanFinalizer(tmp_path, engine).finalize(
        run.run_id, story_id=sid, title="Survival", tasks=["one", "two"],
        idempotency_key=f"plan-{sid}",
    )
    _finalize_act_for_story(tmp_path, engine, sid)  # overwrites story/board/context

    check = engine.start("project-check", goal="check", story_id=sid)
    assert check.status == "running"


def test_done_start_reports_honest_predecessor_error_not_crash(tmp_path):
    """R4: project-done start (no completed check) must raise the honest
    project-check_completion_required, NOT invalid_workflow_state."""
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    sid = "STORY-slim-996"
    _write_plan_inputs(tmp_path, sid)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=sid)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, sid)
    PlanFinalizer(tmp_path, engine).finalize(
        run.run_id, story_id=sid, title="Survival", tasks=["one", "two"],
        idempotency_key=f"plan-{sid}",
    )
    _finalize_act_for_story(tmp_path, engine, sid)

    with pytest.raises(WorkUnitError, match="project-check_completion_required"):
        engine.start("project-done", goal="done", story_id=sid)


def test_finalize_workflow_regen_context_to_post_completion_canonical(tmp_path):
    """R1: after Act finalize marks the story done, context.md must equal
    generate_context(root) recomputed post-completion."""
    import re
    from pactkit.context_gen import context_output_path, generate_context
    from pactkit.governance import StoryRepository
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine

    sid = "STORY-slim-996"
    _write_plan_inputs(tmp_path, sid)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=sid)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, sid)
    PlanFinalizer(tmp_path, engine).finalize(
        run.run_id, story_id=sid, title="Survival", tasks=["one", "two"],
        idempotency_key=f"plan-{sid}",
    )
    _finalize_act_for_story(tmp_path, engine, sid)

    assert StoryRepository(tmp_path).load(sid)["status"] == "done"

    def _norm(text: str) -> str:
        return re.sub(r"^> Last updated: .+$", "> Last updated: <dyn>", text, count=1, flags=re.MULTILINE)

    expected = generate_context(tmp_path, command="pactkit finalize-workflow")
    actual = context_output_path(tmp_path).read_text(encoding="utf-8")
    assert _norm(actual) == _norm(expected)


def test_execution_read_still_detects_tampered_board(tmp_path):
    """R3: _read (execution read) MUST still raise on a tampered projection
    no completed journal explains (tamper-detection intact for execution reads)."""
    from pactkit.workflow_engine import PlanFinalizer, WorkflowEngine, WorkUnitError

    sid = "STORY-slim-996"
    _write_plan_inputs(tmp_path, sid)
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-plan", goal="plan", story_id=sid)
    _advance_plan_to_finalize(engine, run.run_id, tmp_path, sid)
    PlanFinalizer(tmp_path, engine).finalize(
        run.run_id, story_id=sid, title="Survival", tasks=["one", "two"],
        idempotency_key=f"plan-{sid}",
    )
    _finalize_act_for_story(tmp_path, engine, sid)
    (tmp_path / "docs/product/sprint_board.md").write_text("TAMPERED\n", encoding="utf-8")
    with pytest.raises(WorkUnitError, match="invalid_workflow_state"):
        engine._read(run.run_id)
