"""STORY-slim-2026082381e832771d4e: workflow termination safety."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _start(root: Path, workflow: str = "project-act") -> tuple[object, str]:
    from pactkit.continuation import ContinuationEngine

    engine = ContinuationEngine(root)
    evidence = {"spec_lint": "pass"} if workflow == "project-act" else {
        "guard": "pass", "input_fingerprint": "abc",
    }
    state = engine.start(workflow, evidence=evidence)
    return engine, state["run_id"]


def test_finish_guard_is_read_only_and_in_progress_must_continue(tmp_path):
    engine, run_id = _start(tmp_path)
    path = engine.path_for(run_id)
    before = path.read_bytes()

    decision = engine.finish_guard(run_id)

    assert decision["decision"] == "continue_current_turn"
    assert decision["next_step"] == "red"
    assert decision["exit_code"] != 0
    assert decision["auto_resume_available"] is False
    assert decision["manual_resume_command"] == f"pactkit workflow resume {run_id}"
    assert path.read_bytes() == before


def test_finish_guard_allows_only_completed_or_external_blocker(tmp_path):
    engine, run_id = _start(tmp_path)
    state_path = engine.path_for(run_id)
    state = engine.read(run_id)

    state.update(
        status="blocked", blocker="Need user authorization to publish",
        blocker_kind="authorization",
    )
    state_path.write_text(json.dumps(state), encoding="utf-8")
    assert engine.finish_guard(run_id)["decision"] == "await_user"
    assert engine.finish_guard(run_id)["exit_code"] == 0

    state.update(
        status="blocked", blocker="more work remains after tool returned",
        blocker_kind="external_state",
    )
    state_path.write_text(json.dumps(state), encoding="utf-8")
    assert engine.finish_guard(run_id)["decision"] == "fail_closed"

    state.update(status="blocked", blocker="arbitrary internal problem", blocker_kind=None)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    assert engine.finish_guard(run_id)["decision"] == "fail_closed"

    state.update(status="completed", blocker="")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    forged = engine.finish_guard(run_id)
    assert forged["decision"] == "fail_closed"
    assert forged["reason_code"] == "invalid_completion"


def test_checkpoint_requires_structured_external_blocker(tmp_path):
    from pactkit.continuation import ContinuationError

    engine, run_id = _start(tmp_path)
    with pytest.raises(ContinuationError, match="blocker kind"):
        engine.checkpoint(
            run_id, step_id="preflight", evidence={}, status="blocked",
            blocker="Need user decision",
        )
    blocked = engine.checkpoint(
        run_id, step_id="preflight", evidence={}, status="blocked",
        blocker="Need user decision", blocker_kind="user_input",
    )
    assert blocked["blocker_kind"] == "user_input"
    assert engine.finish_guard(run_id)["decision"] == "await_user"


def test_legacy_act_checkpoint_carries_structured_blocker(tmp_path):
    from pactkit.continuation import ContinuationEngine, ContinuationStore

    story_id = "STORY-slim-991"
    (tmp_path / "docs/specs").mkdir(parents=True)
    (tmp_path / "docs/product").mkdir(parents=True)
    (tmp_path / "docs/specs" / f"{story_id}.md").write_text(
        f"# {story_id}: Test\n\n| Field | Value |\n|---|---|\n"
        f"| ID | {story_id} |\n| Status | Draft |\n| Priority | P1 |\n| Release | 1.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n"
        "- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n"
        "| SEC-1 | N/A | test |\n", encoding="utf-8",
    )
    (tmp_path / "docs/product/sprint_board.md").write_text(
        f"# Sprint Board\n\n## 📋 Backlog\n\n## 🔄 In Progress\n\n"
        f"### [{story_id}] Test\n- [ ] task\n\n## ✅ Done\n", encoding="utf-8",
    )
    store = ContinuationStore(tmp_path)
    store.checkpoint(
        story_id, step_id="preflight", evidence={"spec_lint": "pass"},
        status="blocked", blocker="Need user decision", blocker_kind="user_input",
    )

    decision = ContinuationEngine(tmp_path).finish_guard(story_id)

    assert decision["decision"] == "await_user"
    assert decision["exit_code"] == 0


def test_finish_guard_accepts_validated_completed_state(tmp_path):
    engine, run_id = _start(tmp_path)
    state_path = engine.path_for(run_id)
    state = engine.read(run_id)
    state.update(
        status="completed", step_id="sync_coverage", blocker="",
        evidence={"story_tests": {"exit_code": 0}}, completion_validated=True,
    )
    state_path.write_text(json.dumps(state), encoding="utf-8")

    decision = engine.finish_guard(run_id)

    assert decision["decision"] == "done"
    assert decision["exit_code"] == 0


def test_finish_guard_revalidates_completed_evidence(tmp_path):
    engine, run_id = _start(tmp_path, "project-plan")
    path = engine.path_for(run_id)
    state = engine.read(run_id)
    state.update(
        status="completed", step_id="board_synced", story_id="STORY-slim-999",
        completion_validated=True, evidence={"title": "Missing", "tasks": ["task"]},
    )
    path.write_text(json.dumps(state), encoding="utf-8")

    decision = engine.finish_guard(run_id)

    assert decision["decision"] == "fail_closed"
    assert decision["reason_code"] == "invalid_completion"


def test_managed_operation_rejects_wrong_step_before_mutation(tmp_path):
    from pactkit.continuation import ContinuationError

    engine, run_id = _start(tmp_path, "project-plan")
    target = tmp_path / "docs/specs/STORY-slim-999.md"
    with pytest.raises(ContinuationError, match="not allowed"):
        engine.validate_managed_operation(
            run_id, workflow_id="project-plan", operation="create_spec",
            story_id="STORY-slim-999",
        )
    assert not target.exists()


def test_host_runner_detects_no_progress_and_respects_manual_boundary(tmp_path):
    from pactkit.host_continuation import HostCapabilities, HostContinuationRunner

    engine, run_id = _start(tmp_path)
    runner = HostContinuationRunner(
        engine, HostCapabilities(completion_hook=True, session_reentry=True), max_attempts=2,
    )
    first = runner.after_model_turn(run_id, session_locator="session-1")
    assert first["decision"] == "resume_session"
    assert first["attempt"] == 1
    second = runner.after_model_turn(run_id, session_locator="session-1")
    assert second["decision"] == "await_user"
    assert second["reason_code"] == "no_progress"
    blocked = engine.read(run_id)
    assert blocked["status"] == "blocked"
    assert "no_progress" in blocked["blocker"]
    assert blocked["blocker_kind"] == "external_state"
    assert blocked["host_continuation"]["lease_expires_at"] is None
    assert blocked["host_continuation"]["session_locator"].startswith("sha256:")
    assert "session-1" not in json.dumps(blocked["host_continuation"])

    manual = runner.before_operation(run_id, "publish")
    assert manual["decision"] == "await_user"
    assert manual["reason_code"] == "manual_operation"


def test_agent_loop_rejects_premature_final(tmp_path):
    from pactkit.host_continuation import evaluate_agent_final

    engine, run_id = _start(tmp_path)
    result = evaluate_agent_final(
        engine, run_id, "Second Spec passed lint; HLD and Board remain."
    )
    assert result["accepted"] is False
    assert result["decision"] == "continue_current_turn"
    assert "red" == result["next_step"]


def test_plan_and_act_share_pre_final_protocol():
    from pactkit.prompts.commands import COMMANDS_CONTENT, get_deployable_commands

    for name in ("project-plan.md", "project-act.md"):
        prompt = COMMANDS_CONTENT[name]
        assert "Pre-Final Protocol" in prompt
        assert "pactkit workflow finish-guard" in prompt
        assert "progress is not final" in prompt.lower()
    plan = get_deployable_commands()["project-plan.md"]
    assert "pactkit work-unit acquire" in plan
    assert "pactkit work-unit submit" in plan
    assert "finalize-plan" in plan
    assert "Stop hook" in plan and "Never" in plan


def test_cli_finish_guard_has_machine_exit_semantics(tmp_path):
    engine, run_id = _start(tmp_path)
    del engine
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")
    result = subprocess.run(
        [sys.executable, "-m", "pactkit.cli", "workflow", "finish-guard",
         run_id, "--json"],
        cwd=tmp_path, env=env, text=True, capture_output=True,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["decision"] == "continue_current_turn"


def test_managed_scaffold_and_explicit_standalone_are_observable(tmp_path):
    from pactkit.skills.scaffold import create_spec

    standalone = create_spec(
        "STORY-slim-998", "Standalone", standalone=True, project_root=tmp_path,
    )
    assert "managed=false" in standalone

    engine, run_id = _start(tmp_path, "project-plan")
    engine.checkpoint(
        run_id, step_id="intent_clarified",
        evidence={"input_fingerprint": "abc", "answers": []},
    )
    engine.checkpoint(run_id, step_id="archaeology", evidence={"trace": ["cli.main"]})
    engine.bind_story(run_id, "STORY-slim-999")
    engine.checkpoint(
        run_id, step_id="story_identified", evidence={"story_id": "STORY-slim-999"},
    )
    managed = create_spec(
        "STORY-slim-999", "Managed", run_id=run_id, standalone=False,
        project_root=tmp_path,
    )
    assert "managed=true" in managed
    retry = create_spec(
        "STORY-slim-999", "Managed", run_id=run_id, standalone=False,
        project_root=tmp_path,
    )
    assert "already exists" in retry
    spec = tmp_path / "docs/specs/STORY-slim-999.md"
    spec.write_text("different", encoding="utf-8")
    mismatch = create_spec(
        "STORY-slim-999", "Managed", run_id=run_id, standalone=False,
        project_root=tmp_path,
    )
    assert "mismatch" in mismatch.lower()


def test_managed_story_create_is_idempotent_only_when_content_matches(tmp_path):
    from pactkit.governance import GovernanceError, StoryRepository

    engine, run_id = _start(tmp_path, "project-plan")
    engine.checkpoint(
        run_id, step_id="intent_clarified",
        evidence={"input_fingerprint": "abc", "answers": []},
    )
    engine.checkpoint(run_id, step_id="archaeology", evidence={"trace": ["cli.main"]})
    engine.bind_story(run_id, "STORY-slim-995")
    engine.checkpoint(
        run_id, step_id="story_identified", evidence={"story_id": "STORY-slim-995"},
    )
    repository = StoryRepository(
        tmp_path, run_id=run_id, workflow_id="project-plan", standalone=False,
    )
    first = repository.add("STORY-slim-995", "Managed", ["task"])
    second = repository.add("STORY-slim-995", "Managed", ["task"])
    assert first["id"] == second["id"]
    assert second["managed"] is True
    with pytest.raises(GovernanceError, match="mismatch"):
        repository.add("STORY-slim-995", "Changed", ["task"])


def test_doctor_exposes_process_guarantee_and_stale_lease(tmp_path):
    from pactkit.doctor import check_workflow_continuation

    engine, run_id = _start(tmp_path)
    host_dir = tmp_path / ".pactkit/continuations/hosts"
    host_dir.mkdir(parents=True)
    (host_dir / f"{run_id}.json").write_text(json.dumps({
        "run_id": run_id, "lease_expires_at": "2020-01-01T00:00:00+00:00",
        "termination_reason": "no_progress",
    }), encoding="utf-8")
    result = check_workflow_continuation(tmp_path, home=tmp_path / "empty-home")
    assert result["guarantee_level"] == "guided"
    assert result["auto_resume_available"] is False
    assert result["active"][0]["run_id"] == run_id
    assert any("stale host lease" in warning for warning in result["warnings"])


def test_doctor_reads_host_metadata_from_authoritative_run(tmp_path):
    from pactkit.doctor import check_workflow_continuation

    engine, run_id = _start(tmp_path)
    path = engine.path_for(run_id)
    state = engine.read(run_id)
    state["host_continuation"] = {
        "run_id": run_id, "lease_expires_at": "2020-01-01T00:00:00+00:00",
        "termination_reason": "attempt_limit", "attempt": 3,
    }
    path.write_text(json.dumps(state), encoding="utf-8")

    result = check_workflow_continuation(tmp_path)

    assert any("stale host lease" in warning for warning in result["warnings"])
    assert any("attempt_limit" in warning for warning in result["warnings"])


def test_doctor_ignores_legacy_host_metadata_after_core_completion(tmp_path):
    from pactkit.doctor import check_workflow_continuation

    engine, run_id = _start(tmp_path)
    path = engine.path_for(run_id)
    state = engine.read(run_id)
    state.update({
        "status": "completed",
        "host_continuation": {
            "run_id": run_id,
            "termination_reason": "no_progress",
        },
    })
    path.write_text(json.dumps(state), encoding="utf-8")

    result = check_workflow_continuation(tmp_path)

    assert not any("no_progress" in warning for warning in result["warnings"])


def test_story_repository_managed_mode_fails_before_write(tmp_path):
    from pactkit.governance import GovernanceError, StoryRepository

    engine, run_id = _start(tmp_path, "project-plan")
    repository = StoryRepository(
        tmp_path, run_id=run_id, workflow_id="project-plan", standalone=False,
    )
    with pytest.raises(GovernanceError, match="not allowed"):
        repository.add("STORY-slim-997", "Unsafe", ["task"])
    assert not repository.path_for("STORY-slim-997").exists()


def test_all_format_rendering_preserves_pre_final_semantics():
    from pactkit.generators.deployer import _render_prompt
    from pactkit.profiles import get_profile
    from pactkit.prompts.commands import COMMANDS_CONTENT

    for format_name in ("classic", "opencode", "codex", "copilot"):
        for command in ("project-plan.md", "project-act.md"):
            rendered = _render_prompt(COMMANDS_CONTENT[command], get_profile(format_name))
            assert "Pre-Final Protocol" in rendered
            assert "continue_current_turn" in rendered
            assert "await_user" in rendered
            assert "Progress is not final" in rendered


def test_manifest_reports_capability_derived_guarantee_without_false_auto_resume(tmp_path):
    from pactkit.deploy_manifest import write_deploy_manifest

    expected_modes = {
        "classic": "portable", "opencode": "portable",
        "codex": "guided", "copilot": "guided",
    }
    for format_name, mode in expected_modes.items():
        root = tmp_path / format_name
        payload = json.loads(write_deploy_manifest(root, format_name).read_text())
        capability = payload["workflow_continuation"]
        assert capability["finish_guard_supported"] is True
        assert capability["auto_resume_available"] is False
        assert capability["guarantee_level"] == mode
        assert capability["execution_mode"] == mode
        assert capability["stop_hook_required"] is False


def test_runner_lease_allows_only_one_owner(tmp_path):
    from pactkit.host_continuation import HostCapabilities, HostContinuationRunner

    engine, run_id = _start(tmp_path)
    capabilities = HostCapabilities(completion_hook=True, session_reentry=True)
    owner_a = HostContinuationRunner(engine, capabilities, owner="owner-a")
    owner_b = HostContinuationRunner(engine, capabilities, owner="owner-b")
    assert owner_a.after_model_turn(
        run_id, session_locator="session-a"
    )["decision"] == "resume_session"
    contended = owner_b.after_model_turn(run_id, session_locator="session-b")
    assert contended["decision"] == "await_user"
    assert contended["reason_code"] == "lease_contended"


def test_runner_attempt_limit_is_reachable_when_progress_changes(tmp_path):
    from pactkit.host_continuation import HostCapabilities, HostContinuationRunner

    engine, run_id = _start(tmp_path)
    runner = HostContinuationRunner(
        engine, HostCapabilities(completion_hook=True, session_reentry=True),
        max_attempts=1,
    )
    assert runner.after_model_turn(
        run_id, session_locator="session-1"
    )["decision"] == "resume_session"
    state_path = engine.path_for(run_id)
    state = engine.read(run_id)
    state["evidence"] = {"progress": "changed"}
    state_path.write_text(json.dumps(state), encoding="utf-8")

    limited = runner.after_model_turn(run_id, session_locator="session-1")

    assert limited["decision"] == "await_user"
    assert limited["reason_code"] == "attempt_limit"
    assert engine.read(run_id)["status"] == "blocked"


@pytest.mark.parametrize("reason_code", ["permission_denied", "artifact_drift"])
def test_runner_persists_resume_failures_as_blocked(tmp_path, reason_code):
    from pactkit.host_continuation import HostCapabilities, HostContinuationRunner

    engine, run_id = _start(tmp_path)
    runner = HostContinuationRunner(
        engine, HostCapabilities(completion_hook=True, session_reentry=True),
    )

    decision = runner.record_resume_failure(
        run_id, reason_code=reason_code, session_locator="session-1",
    )

    assert decision["decision"] == "await_user"
    assert decision["reason_code"] == reason_code
    state = engine.read(run_id)
    assert state["status"] == "blocked"
    assert state["blocker_kind"] == "external_state"


def test_runner_converts_finish_guard_drift_into_recoverable_block(tmp_path):
    from pactkit.host_continuation import HostCapabilities, HostContinuationRunner

    engine, run_id = _start(tmp_path, "project-plan")
    path = engine.path_for(run_id)
    state = engine.read(run_id)
    state["story_id"] = "STORY-slim-993"
    state["fingerprints"] = {"spec": "trusted-but-now-stale"}
    path.write_text(json.dumps(state), encoding="utf-8")
    runner = HostContinuationRunner(
        engine, HostCapabilities(completion_hook=True, session_reentry=True),
    )

    decision = runner.after_model_turn(run_id, session_locator="session-1")

    assert decision["decision"] == "await_user"
    assert decision["reason_code"] == "artifact_drift"
    assert engine.read(run_id)["status"] == "blocked"


def test_finish_guard_prefers_active_legacy_act_over_completed_plan(tmp_path):
    from pactkit.continuation import ContinuationEngine, ContinuationStore

    story_id = "STORY-slim-996"
    (tmp_path / "docs/specs").mkdir(parents=True)
    (tmp_path / "docs/product").mkdir(parents=True)
    (tmp_path / "docs/specs" / f"{story_id}.md").write_text(
        f"# {story_id}: Test\n\n| Field | Value |\n|---|---|\n"
        f"| ID | {story_id} |\n| Status | Draft |\n| Priority | P1 |\n| Release | 1.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n"
        "- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n"
        "| SEC-1 | N/A | test |\n", encoding="utf-8",
    )
    (tmp_path / "docs/product/sprint_board.md").write_text(
        f"# Sprint Board\n\n## 📋 Backlog\n\n## 🔄 In Progress\n\n"
        f"### [{story_id}] Test\n- [ ] task\n\n## ✅ Done\n", encoding="utf-8",
    )
    store = ContinuationStore(tmp_path)
    store.checkpoint(story_id, step_id="preflight", evidence={"spec_lint": "pass"})
    engine = ContinuationEngine(tmp_path)
    plan = engine.start(
        "project-plan", evidence={"guard": "pass", "input_fingerprint": "abc"},
    )
    plan_path = engine.path_for(plan["run_id"])
    plan_state = engine.read(plan["run_id"])
    plan_state.update(
        story_id=story_id, status="completed", step_id="board_synced",
        completion_validated=True,
    )
    plan_path.write_text(json.dumps(plan_state), encoding="utf-8")

    decision = engine.finish_guard(story_id)

    assert decision["workflow_id"] == "project-act"
    assert decision["decision"] == "continue_current_turn"
    assert decision["next_step"] == "red"


def test_finish_guard_prefers_completed_legacy_act_over_completed_plan(tmp_path):
    from pactkit.continuation import ContinuationEngine, ContinuationStore

    story_id = "STORY-slim-995"
    (tmp_path / "docs/specs").mkdir(parents=True)
    (tmp_path / "docs/product").mkdir(parents=True)
    (tmp_path / "docs/specs" / f"{story_id}.md").write_text(
        f"# {story_id}: Test\n\n| Field | Value |\n|---|---|\n"
        f"| ID | {story_id} |\n| Status | Draft |\n| Priority | P1 |\n| Release | 1.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n"
        "- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n"
        "| SEC-1 | N/A | test |\n", encoding="utf-8",
    )
    (tmp_path / "docs/product/sprint_board.md").write_text(
        f"# Sprint Board\n\n## 📋 Backlog\n\n## 🔄 In Progress\n\n"
        f"### [{story_id}] Test\n- [x] task\n\n## ✅ Done\n", encoding="utf-8",
    )
    store = ContinuationStore(tmp_path)
    store.checkpoint(story_id, step_id="preflight", evidence={"spec_lint": "pass"})
    store.checkpoint(story_id, step_id="red", evidence={"story_tests": {"exit_code": 1}})
    store.checkpoint(story_id, step_id="green", evidence={"story_tests": {"exit_code": 0}})
    store.checkpoint(
        story_id, step_id="regression_lint",
        evidence={"regression": "pass", "lint": "pass"},
    )
    store.checkpoint(
        story_id, step_id="sync_coverage", status="completed",
        evidence={
            "spec_lint": "pass", "story_tests": {"exit_code": 0},
            "regression": "pass", "lint": "pass",
            "coverage": {"R1": ["test"]},
            "acceptance_coverage": {"AC1": ["test"]},
            "board_tasks": ["task"],
        },
    )
    engine = ContinuationEngine(tmp_path)
    plan = engine.start(
        "project-plan", evidence={"guard": "pass", "input_fingerprint": "abc"},
    )
    plan_path = engine.path_for(plan["run_id"])
    plan_state = engine.read(plan["run_id"])
    plan_state.update(
        story_id=story_id, status="completed", step_id="board_synced",
        completion_validated=True,
    )
    plan_path.write_text(json.dumps(plan_state), encoding="utf-8")

    decision = engine.finish_guard(story_id)

    assert decision["workflow_id"] == "project-act"
    assert decision["decision"] == "done"
    assert decision["legacy_checkpoint"] is True


def test_story_lookup_prefers_active_generic_run_over_history(tmp_path):
    engine, old_run = _start(tmp_path, "project-plan")
    old_path = engine.path_for(old_run)
    old_state = engine.read(old_run)
    old_state.update(
        story_id="STORY-slim-992", status="completed", step_id="board_synced",
        completion_validated=True, updated_at="2026-01-01T00:00:00+00:00",
    )
    old_path.write_text(json.dumps(old_state), encoding="utf-8")
    new_state = engine.start(
        "project-plan", evidence={"guard": "pass", "input_fingerprint": "new"},
    )
    new_path = engine.path_for(new_state["run_id"])
    active = engine.read(new_state["run_id"])
    active.update(story_id="STORY-slim-992", updated_at="2026-02-01T00:00:00+00:00")
    new_path.write_text(json.dumps(active), encoding="utf-8")

    decision = engine.finish_guard("STORY-slim-992")

    assert decision["run_id"] == new_state["run_id"]
    assert decision["decision"] == "continue_current_turn"


def test_plan_spec_linted_premature_final_requires_board_sync(tmp_path):
    from pactkit.host_continuation import evaluate_agent_final

    engine, run_id = _start(tmp_path, "project-plan")
    path = engine.path_for(run_id)
    state = engine.read(run_id)
    state.update(story_id="STORY-slim-994", step_id="spec_linted")
    state["fingerprints"] = engine.definition("project-plan").validator_factory(
        tmp_path
    ).fingerprints(state)
    path.write_text(json.dumps(state), encoding="utf-8")

    result = evaluate_agent_final(engine, run_id, "Spec lint passed; Board remains.")

    assert result["accepted"] is False
    assert result["decision"] == "continue_current_turn"
    assert result["next_step"] == "board_synced"


def test_all_project_commands_are_persistent_registered_workflows():
    from pactkit.config import VALID_COMMANDS
    from pactkit.workflow_registry import (
        EXECUTION_RELIABILITY_REGISTRY,
        WORKFLOW_REGISTRY,
    )

    assert set(WORKFLOW_REGISTRY) == set(VALID_COMMANDS)
    for command in VALID_COMMANDS:
        contract = EXECUTION_RELIABILITY_REGISTRY[command]
        workflow = WORKFLOW_REGISTRY[command]
        assert contract.persistence == "full"
        assert contract.completion == "validated"
        assert len(workflow.steps) >= 2
        assert workflow.steps[0] == "started" or command in {"project-plan", "project-act"}


def test_all_project_templates_have_managed_lifecycle_protocol():
    from pactkit.config import VALID_COMMANDS
    from pactkit.prompts.commands import COMMANDS_CONTENT

    for command in VALID_COMMANDS:
        prompt = COMMANDS_CONTENT[f"{command}.md"]
        assert f"pactkit workflow contract {command} --json" in prompt
        assert "finish-guard" in prompt
        assert "Progress is not final" in prompt


def test_done_premature_final_is_rejected_until_completed(tmp_path):
    from pactkit.continuation import ContinuationEngine
    from pactkit.host_continuation import evaluate_agent_final

    engine = ContinuationEngine(tmp_path)
    state = engine.start("project-done", evidence={"started": True})

    premature = evaluate_agent_final(
        engine, state["run_id"], "Done audit complete. Archive and commit remain.",
    )
    assert premature["accepted"] is False
    assert premature["decision"] == "continue_current_turn"
    assert premature["next_step"] == "audited"

    for step in ("audited", "governance_synced"):
        engine.checkpoint(state["run_id"], step_id=step, evidence={"phase": "verified"})
    engine.checkpoint(
        state["run_id"], step_id="completed", status="completed",
        evidence={
            "audit": "pass", "governance": "pass",
            "deployment": "pass", "git": {"mode": "no_git"},
        },
    )
    completed = evaluate_agent_final(engine, state["run_id"], "Done complete.")
    assert completed["accepted"] is True
    assert completed["decision"] == "done"


@pytest.mark.parametrize(
    "workflow_id",
    [
        "project-check", "project-done", "project-init", "project-sprint",
        "project-hotfix", "project-design", "project-clarify",
        "project-release", "project-pr", "project-debug",
    ],
)
def test_generic_project_workflow_rejects_early_final_and_validates_completion(
    tmp_path, workflow_id,
):
    from pactkit.continuation import ContinuationEngine

    engine = ContinuationEngine(tmp_path)
    state = engine.start(workflow_id, evidence={"started": True})
    run_id = state["run_id"]
    assert engine.finish_guard(run_id)["decision"] == "continue_current_turn"

    steps = engine.definition(workflow_id).steps
    for step in steps[1:-1]:
        engine.checkpoint(run_id, step_id=step, evidence={"phase": "verified"})
        decision = engine.finish_guard(run_id)
        assert decision["decision"] == "continue_current_turn"
        assert decision["next_step"] == steps[steps.index(step) + 1]

    with pytest.raises(Exception, match="completion evidence"):
        engine.checkpoint(
            run_id, step_id=steps[-1], status="completed", evidence={},
        )
    evidence = {
        "project-check": {
            "security_scan": "pass", "quality_scan": "pass",
            "spec_alignment": "pass", "tests": {"exit_code": 0},
        },
        "project-done": {
            "audit": "pass", "governance": "pass",
            "deployment": "pass", "git": {"mode": "no_git"},
        },
        "project-init": {
            "guard": "pass", "configuration_created": True,
            "governance_created": True,
        },
        "project-sprint": {
            "planned": True, "executed": True, "cleanup": "pass",
            "stories": ["STORY-slim-001"],
        },
        "project-hotfix": {
            "traceability": True, "tests": {"exit_code": 0},
            "lint": "pass",
        },
        "project-design": {
            "prd_created": True, "stories_created": 1,
            "board_synced": True,
        },
        "project-clarify": {
            "requirements_confirmed": True, "decision_count": 1,
        },
        "project-release": {
            "version": "1.2.3", "tag": "v1.2.3",
            "release": {"mode": "local_only"},
        },
        "project-pr": {
            "branch": "feature/test",
            "pull_request": {"mode": "not_required", "reason": "local test"},
        },
        "project-debug": {
            "root_cause": "deterministic test cause",
            "evidence": ["reproduction"], "next_action": "fix",
        },
    }[workflow_id]
    engine.checkpoint(
        run_id, step_id=steps[-1], status="completed", evidence=evidence,
    )
    assert engine.finish_guard(run_id)["decision"] == "done"


@pytest.mark.parametrize(
    "workflow_id",
    [
        "project-check", "project-done", "project-init", "project-sprint",
        "project-hotfix", "project-design", "project-clarify",
        "project-release", "project-pr", "project-debug",
    ],
)
def test_generic_completion_rejects_self_declared_verified(tmp_path, workflow_id):
    from pactkit.continuation import ContinuationEngine, ContinuationError

    engine = ContinuationEngine(tmp_path)
    state = engine.start(workflow_id, evidence={"started": True})
    for step in engine.definition(workflow_id).steps[1:-1]:
        engine.checkpoint(state["run_id"], step_id=step, evidence={"phase": "verified"})

    with pytest.raises(ContinuationError, match="completion evidence"):
        engine.checkpoint(
            state["run_id"], step_id="completed", status="completed",
            evidence={"completion": "verified"},
        )


def test_workflow_contract_exposes_command_specific_completion_requirements():
    from pactkit.workflow_registry import WORKFLOW_REGISTRY

    assert "tests.exit_code=0" in WORKFLOW_REGISTRY["project-check"].completion_evidence_requirements
    assert "deployment=pass" in WORKFLOW_REGISTRY["project-done"].completion_evidence_requirements
    assert "pull_request=<url|not_required>" in (
        WORKFLOW_REGISTRY["project-pr"].completion_evidence_requirements
    )


@pytest.mark.parametrize(
    ("workflow_id", "operation"),
    [
        ("project-done", "commit"),
        ("project-done", "archive"),
        ("project-release", "tag"),
        ("project-release", "publish"),
        ("project-release", "release"),
        ("project-pr", "push"),
        ("project-pr", "pull_request"),
    ],
)
def test_all_high_side_effect_operations_require_user_boundary(
    tmp_path, workflow_id, operation,
):
    from pactkit.continuation import ContinuationEngine
    from pactkit.host_continuation import HostCapabilities, HostContinuationRunner

    engine = ContinuationEngine(tmp_path)
    state = engine.start(workflow_id, evidence={"started": True})
    runner = HostContinuationRunner(
        engine, HostCapabilities(completion_hook=True, session_reentry=True),
    )

    decision = runner.before_operation(state["run_id"], operation)

    assert decision["decision"] == "await_user"
    assert decision["reason_code"] == "manual_operation"
