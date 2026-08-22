"""STORY-slim-147: generic workflow continuation and Plan recovery."""

from pathlib import Path

import pytest


def _plan_project(root: Path) -> None:
    (root / "docs/specs").mkdir(parents=True)
    (root / "docs/product").mkdir(parents=True)
    (root / "docs/product/sprint_board.md").write_text(
        "# Sprint Board\n\n## 📋 Backlog\n\n## 🔄 In Progress\n\n## ✅ Done\n",
        encoding="utf-8",
    )


def test_reliability_registry_covers_all_deployed_entries():
    from pactkit.config import VALID_COMMANDS
    from pactkit.prompts.commands import COMMANDS_CONTENT
    from pactkit.prompts.skills import SKILL_MANIFEST
    from pactkit.workflow_registry import EXECUTION_RELIABILITY_REGISTRY, validate_registry

    expected = set(VALID_COMMANDS) | {entry["name"] for entry in SKILL_MANIFEST}
    assert len(expected) == 25
    assert set(EXECUTION_RELIABILITY_REGISTRY) == expected
    assert {name.removesuffix(".md") for name in COMMANDS_CONTENT} == set(VALID_COMMANDS)
    assert validate_registry() == []
    assert EXECUTION_RELIABILITY_REGISTRY["project-plan"].persistence == "full"
    assert EXECUTION_RELIABILITY_REGISTRY["project-release"].recovery == "manual_confirmation"
    assert EXECUTION_RELIABILITY_REGISTRY["project-check"].persistence == "not_persisted"


def test_generic_engine_dispatches_act_and_plan_without_embedded_steps(tmp_path):
    from pactkit.continuation import ContinuationEngine
    from pactkit.workflow_registry import get_workflow

    _plan_project(tmp_path)
    engine = ContinuationEngine(tmp_path)
    assert get_workflow("project-act").steps[0] == "preflight"
    assert get_workflow("project-plan").steps[-1] == "board_synced"
    assert engine.definition("project-plan") == get_workflow("project-plan")


def test_plan_run_resumes_before_story_exists_and_binds_once(tmp_path):
    from pactkit.continuation import ContinuationEngine, ContinuationError

    _plan_project(tmp_path)
    engine = ContinuationEngine(tmp_path)
    state = engine.start("project-plan", evidence={"guard": "pass", "input_fingerprint": "abc"})
    run_id = state["run_id"]
    assert run_id.startswith("run-")
    engine.checkpoint(run_id, step_id="intent_clarified", evidence={"input_fingerprint": "abc", "answers": []})
    engine.checkpoint(run_id, step_id="archaeology", evidence={"trace": ["src/pactkit/cli.py:main"]})
    assert engine.resume(run_id)["next_step"] == "story_identified"
    engine.bind_story(run_id, "STORY-slim-999")
    assert engine.read(run_id)["story_id"] == "STORY-slim-999"
    assert engine.resume("STORY-slim-999")["run_id"] == run_id
    with pytest.raises(ContinuationError, match="already bound"):
        engine.bind_story(run_id, "STORY-slim-998")


def test_plan_scaffold_requires_real_spec_and_identity(tmp_path):
    from pactkit.continuation import ContinuationEngine, ContinuationError

    _plan_project(tmp_path)
    engine = ContinuationEngine(tmp_path)
    state = engine.start("project-plan", evidence={"guard": "pass", "input_fingerprint": "abc"})
    run_id = state["run_id"]
    engine.checkpoint(run_id, step_id="intent_clarified", evidence={"input_fingerprint": "abc", "answers": []})
    engine.checkpoint(run_id, step_id="archaeology", evidence={"trace": ["cli.main"]})
    engine.bind_story(run_id, "STORY-slim-999")
    engine.checkpoint(run_id, step_id="story_identified", evidence={"story_id": "STORY-slim-999"})
    with pytest.raises(ContinuationError, match="Spec scaffold"):
        engine.checkpoint(
            run_id, step_id="spec_scaffolded",
            evidence={"spec_path": "docs/specs/STORY-slim-999.md"},
        )


def test_plan_resume_detects_sharded_story_fact_drift(tmp_path):
    from pactkit.continuation import ContinuationEngine
    from pactkit.governance import StoryRepository

    _plan_project(tmp_path)
    engine = ContinuationEngine(tmp_path)
    state = engine.start("project-plan", evidence={"guard": "pass", "input_fingerprint": "abc"})
    run_id = state["run_id"]
    engine.checkpoint(
        run_id, step_id="intent_clarified",
        evidence={"input_fingerprint": "abc", "answers": []},
    )
    engine.checkpoint(run_id, step_id="archaeology", evidence={"trace": ["cli.main"]})
    engine.bind_story(run_id, "STORY-slim-999")
    repository = StoryRepository(tmp_path)
    repository.add("STORY-slim-999", "Recoverable Plan", ["write spec"])
    engine.checkpoint(
        run_id, step_id="story_identified",
        evidence={"story_id": "STORY-slim-999"},
    )

    repository.move("STORY-slim-999", "in_progress")

    resumed = engine.resume(run_id)
    assert resumed["decision"] == "blocked"
    assert "story fact" in resumed["reasons"][0]


def test_legacy_act_store_remains_compatible(tmp_path):
    from pactkit.continuation import ContinuationStore

    story_id = "STORY-slim-146"
    (tmp_path / "docs/specs").mkdir(parents=True)
    (tmp_path / "docs/product").mkdir(parents=True)
    (tmp_path / f"docs/specs/{story_id}.md").write_text(
        f"# {story_id}\n\n| Field | Value |\n|---|---|\n| ID | {story_id} |\n"
        "| Status | Draft |\n| Priority | P1 |\n| Release | 2.20.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\n\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n\n"
        "- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n| SEC-1 | N/A | test |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/product/sprint_board.md").write_text(
        f"# Sprint Board\n\n## 📋 Backlog\n\n## 🔄 In Progress\n\n### [{story_id}] Test\n- [ ] Task 1\n\n## ✅ Done\n",
        encoding="utf-8",
    )
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "docs"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    store = ContinuationStore(tmp_path)
    state = store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
    assert state["command"] == "$project-act"
    assert store.resume("STORY-slim-146")["next_step"] == "red"
