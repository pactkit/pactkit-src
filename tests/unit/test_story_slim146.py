"""STORY-slim-146: resumable Act execution and runtime-skill contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _project(root: Path, story_id: str = "STORY-slim-146") -> None:
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "product").mkdir(parents=True)
    (root / "docs" / "specs" / f"{story_id}.md").write_text(
        f"# {story_id}\n\n"
        "| Field | Value |\n|---|---|\n"
        f"| ID | {story_id} |\n"
        "| Status | Draft |\n| Priority | P1 |\n| Release | 2.20.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\n\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n\n- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n| SEC-1 | N/A | test |\n",
        encoding="utf-8",
    )
    (root / "docs" / "product" / "sprint_board.md").write_text(
        "# Sprint Board\n\n## 📋 Backlog\n\n## 🔄 In Progress\n\n"
        f"### [{story_id}] Test\n- [ ] Task 1\n\n## ✅ Done\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "docs"], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "fixture"],
        cwd=root, check=True,
    )


def _advance_to_green(store, story_id: str = "STORY-slim-146") -> None:
    store.checkpoint(story_id, step_id="preflight", evidence={"spec_lint": "pass"})
    store.checkpoint(story_id, step_id="red", evidence={"story_tests": {"exit_code": 1}})
    store.checkpoint(story_id, step_id="green", evidence={"story_tests": {"exit_code": 0}})


def _advance_to_regression(store, story_id: str = "STORY-slim-146") -> None:
    _advance_to_green(store, story_id)
    store.checkpoint(
        story_id, step_id="regression_lint",
        evidence={"regression": "pass", "lint": "pass"},
    )


class TestSkillRecoveryContracts:
    def test_contracts_cover_manifest_exactly_once(self):
        from pactkit.prompts.skills import SKILL_MANIFEST, SKILL_RECOVERY_CONTRACTS, validate_skill_recovery_contracts

        assert validate_skill_recovery_contracts() == []
        assert set(SKILL_RECOVERY_CONTRACTS) == {entry["name"] for entry in SKILL_MANIFEST}

    def test_high_side_effect_skills_require_manual_confirmation(self):
        from pactkit.prompts.skills import SKILL_RECOVERY_CONTRACTS

        for name in ("pactkit-release", "pactkit-draw"):
            assert SKILL_RECOVERY_CONTRACTS[name]["recovery"] == "manual_confirmation"
        assert SKILL_RECOVERY_CONTRACTS["pactkit-board"]["recovery"] == "idempotent_local_write"

    def test_contracts_encode_operation_level_replay_exceptions(self):
        from pactkit.prompts.skills import SKILL_RECOVERY_CONTRACTS

        board = SKILL_RECOVERY_CONTRACTS["pactkit-board"]
        assert set(board["safe_operations"].split(",")) == {"move_story", "update_task"}
        assert set(board["manual_operations"].split(",")) == {"add_story", "archive", "snapshot"}
        assert SKILL_RECOVERY_CONTRACTS["pactkit-audit"]["manual_operations"] == "--append"
        assert SKILL_RECOVERY_CONTRACTS["pactkit-release"]["manual_operations"] == "release,tag,publish"

    def test_canonical_act_keeps_recovery_semantics_in_every_profile(self):
        from pactkit.generators.deploy_base import DeployerBase
        from pactkit.generators.deployer import _render_prompt
        from pactkit.profiles import get_profile
        from pactkit.prompts.commands import COMMANDS_CONTENT

        template = COMMANDS_CONTENT["project-act.md"]
        for name in ("classic", "opencode", "codex", "copilot"):
            profile = get_profile(name)
            content = _render_prompt(template, profile)
            assert "checkpoint" in content.lower(), name
            assert "resume" in content.lower() or "verification" in content.lower(), name
            assert DeployerBase.validate_deployed_content(content, profile) == [], name


class TestContinuationStore:
    def test_checkpoint_holds_process_lock_across_read_validate_write(self, tmp_path, monkeypatch):
        import pactkit.continuation as continuation
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        lock_path = tmp_path / ".pactkit/continuations/STORY-slim-146.lock"
        real_read = store.read
        real_atomic_write = continuation.atomic_write

        def checked_read(story_id):
            assert lock_path.exists()
            return real_read(story_id)

        def checked_write(path, content):
            assert lock_path.exists()
            return real_atomic_write(path, content)

        monkeypatch.setattr(store, "read", checked_read)
        monkeypatch.setattr(continuation, "atomic_write", checked_write)
        store.checkpoint(
            "STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"},
        )

    def test_explicit_checkpoint_is_atomic_and_sanitized(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        result = store.checkpoint(
            "STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass", "command_output": "token=abc"},
            phase="Phase 0", blocker="token=abc\n## injected",
        )
        path = tmp_path / ".pactkit" / "continuations" / "STORY-slim-146.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert result["status"] == "in_progress"
        assert data["step_id"] == "preflight"
        assert "\n" not in data["blocker"]
        assert "token=" not in data["blocker"].lower()
        assert data["evidence"]["command_output"] == "[redacted]"
        assert not path.with_suffix(".tmp").exists()

    def test_sensitive_evidence_keys_and_bearer_values_are_redacted(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        result = ContinuationStore(tmp_path).checkpoint(
            "STORY-slim-146", step_id="preflight",
            evidence={
                "spec_lint": "pass",
                "password": "plain-secret",
                "authorization": "Bearer abc.def.ghi",
                "nested": {"api_key": "sk-live-value"},
            },
        )
        assert result["evidence"]["password"] == "[redacted]"
        assert result["evidence"]["authorization"] == "[redacted]"
        assert result["evidence"]["nested"]["api_key"] == "[redacted]"
        persisted = ContinuationStore(tmp_path).path_for("STORY-slim-146").read_text(encoding="utf-8")
        assert "plain-secret" not in persisted
        assert "abc.def.ghi" not in persisted
        assert "sk-live-value" not in persisted

    @pytest.mark.parametrize(
        ("step_id", "evidence"),
        [
            ("preflight", {"spec_lint": "fail"}),
            ("red", {"story_tests": {"exit_code": 0}}),
            ("green", {"story_tests": {"exit_code": 1}}),
            ("regression_lint", {"regression": "pass", "lint": "fail"}),
        ],
    )
    def test_each_safe_boundary_rejects_false_evidence(self, tmp_path, step_id, evidence):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        with pytest.raises(ContinuationError, match="invalid .* evidence"):
            ContinuationStore(tmp_path).checkpoint(
                "STORY-slim-146", step_id=step_id, evidence=evidence,
            )

    def test_preflight_runs_real_spec_lint_instead_of_trusting_claim(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        (tmp_path / "docs/specs/STORY-slim-146.md").write_text(
            "# broken spec\n", encoding="utf-8",
        )
        with pytest.raises(ContinuationError, match="Spec lint failed"):
            ContinuationStore(tmp_path).checkpoint(
                "STORY-slim-146", step_id="preflight",
                evidence={"spec_lint": "pass"},
            )

    def test_checkpoint_cannot_skip_safe_boundaries(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
        with pytest.raises(ContinuationError, match="cannot skip checkpoint step"):
            store.checkpoint(
                "STORY-slim-146", step_id="green",
                evidence={"story_tests": {"exit_code": 0}},
            )

    def test_resume_is_read_only_and_returns_next_safe_step(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        _advance_to_green(store)
        before = store.path_for("STORY-slim-146").read_bytes()
        decision = store.resume("STORY-slim-146")
        assert decision["decision"] == "resume_at"
        assert decision["next_step"] == "regression_lint"
        assert store.path_for("STORY-slim-146").read_bytes() == before

    @pytest.mark.parametrize("change", ["spec", "board"])
    def test_changed_artifacts_block_resume_without_writing(self, tmp_path, change):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint("STORY-slim-146", step_id="red", evidence={"story_tests": {"exit_code": 1}})
        target = tmp_path / "docs" / ("specs/STORY-slim-146.md" if change == "spec" else "product/sprint_board.md")
        target.write_text(target.read_text(encoding="utf-8") + "\nchanged", encoding="utf-8")
        before = store.path_for("STORY-slim-146").read_bytes()
        decision = store.resume("STORY-slim-146")
        assert decision["decision"] == "blocked"
        assert change in " ".join(decision["reasons"]).lower()
        assert store.path_for("STORY-slim-146").read_bytes() == before

    def test_stale_checkpoint_cannot_advance_and_refresh_fingerprints(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
        before = store.path_for("STORY-slim-146").read_bytes()
        spec = tmp_path / "docs/specs/STORY-slim-146.md"
        spec.write_text(spec.read_text(encoding="utf-8") + "\nmanual change\n", encoding="utf-8")
        with pytest.raises(ContinuationError, match="stale checkpoint: spec fingerprint changed"):
            store.checkpoint(
                "STORY-slim-146", step_id="red",
                evidence={"story_tests": {"exit_code": 1}},
            )
        assert store.path_for("STORY-slim-146").read_bytes() == before

    def test_completion_requires_all_evidence_and_board_tasks(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        with pytest.raises(ContinuationError, match="missing completion evidence"):
            store.checkpoint("STORY-slim-146", step_id="sync_coverage", status="completed", evidence={})

    def test_completion_runs_real_spec_lint_instead_of_trusting_claim(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        spec = tmp_path / "docs/specs/STORY-slim-146.md"
        spec.write_text("# broken spec\n", encoding="utf-8")
        board = tmp_path / "docs/product/sprint_board.md"
        board.write_text(board.read_text(encoding="utf-8").replace("- [ ] Task 1", "- [x] Task 1"), encoding="utf-8")
        evidence = {
            "spec_lint": "pass", "story_tests": {"exit_code": 0},
            "regression": "pass", "lint": "pass",
            "coverage": {"R1": ["test"]},
            "acceptance_coverage": {"AC1": ["test"]},
            "board_tasks": ["Task 1"],
        }
        # A blocked checkpoint records the detected mutation, but a completion
        # claim must independently reject the structurally invalid Spec.
        store.checkpoint(
            "STORY-slim-146", step_id="regression_lint", status="blocked",
            evidence={}, blocker="Spec changed; rerun preflight",
        )
        # Isolate the completion validator: stale-input behavior has its own
        # tests and intentionally runs before completion evidence validation.
        store._stale_reasons = lambda *_: []
        with pytest.raises(ContinuationError, match="Spec lint failed"):
            store.checkpoint(
                "STORY-slim-146", step_id="sync_coverage",
                status="completed", evidence=evidence,
            )

    def test_completion_requires_coverage_for_every_must_requirement(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        spec = tmp_path / "docs/specs/STORY-slim-146.md"
        spec.write_text(
            spec.read_text(encoding="utf-8") + "\n### R2: Another requirement (MUST)\n",
            encoding="utf-8",
        )
        board = tmp_path / "docs/product/sprint_board.md"
        board.write_text(board.read_text(encoding="utf-8").replace("- [ ] Task 1", "- [x] Task 1"), encoding="utf-8")
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        with pytest.raises(ContinuationError, match="missing completion coverage: R2"):
            store.checkpoint(
                "STORY-slim-146", step_id="sync_coverage", status="completed",
                evidence={"spec_lint": "pass", "story_tests": {"exit_code": 0}, "regression": "pass", "lint": "pass", "coverage": {"R1": ["test"]}, "acceptance_coverage": {"AC1": ["test"]}, "board_tasks": ["Task 1"]},
            )

    def test_completion_requires_coverage_for_every_acceptance_criterion(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        board = tmp_path / "docs/product/sprint_board.md"
        board.write_text(board.read_text(encoding="utf-8").replace("- [ ] Task 1", "- [x] Task 1"), encoding="utf-8")
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        with pytest.raises(ContinuationError, match="missing completion acceptance coverage: AC1"):
            store.checkpoint(
                "STORY-slim-146", step_id="sync_coverage", status="completed",
                evidence={"spec_lint": "pass", "story_tests": {"exit_code": 0}, "regression": "pass", "lint": "pass", "coverage": {"R1": ["test"]}, "acceptance_coverage": {}, "board_tasks": ["Task 1"]},
            )

    def test_completion_rejects_empty_traceability_evidence(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        board = tmp_path / "docs/product/sprint_board.md"
        board.write_text(board.read_text(encoding="utf-8").replace("- [ ] Task 1", "- [x] Task 1"), encoding="utf-8")
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        with pytest.raises(ContinuationError, match="empty completion traceability evidence"):
            store.checkpoint(
                "STORY-slim-146", step_id="sync_coverage", status="completed",
                evidence={
                    "spec_lint": "pass", "story_tests": {"exit_code": 0},
                    "regression": "pass", "lint": "pass",
                    "coverage": {"R1": []}, "acceptance_coverage": {"AC1": []},
                    "board_tasks": ["Task 1"],
                },
            )

    def test_completion_requires_board_task_evidence_to_match_board(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        board = tmp_path / "docs/product/sprint_board.md"
        board.write_text(board.read_text(encoding="utf-8").replace("- [ ] Task 1", "- [x] Task 1"), encoding="utf-8")
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        with pytest.raises(ContinuationError, match="board task evidence mismatch"):
            store.checkpoint(
                "STORY-slim-146", step_id="sync_coverage", status="completed",
                evidence={
                    "spec_lint": "pass", "story_tests": {"exit_code": 0},
                    "regression": "pass", "lint": "pass",
                    "coverage": {"R1": ["test"]},
                    "acceptance_coverage": {"AC1": ["test"]},
                    "board_tasks": ["Different task"],
                },
            )

    def test_completion_ignores_unrelated_backlog_tasks(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        board = tmp_path / "docs" / "product" / "sprint_board.md"
        board.write_text(
            "# Sprint Board\n\n## 📋 Backlog\n\n### [STORY-slim-999] Other\n- [ ] Other task\n"
            "\n## 🔄 In Progress\n\n### [STORY-slim-146] Test\n- [x] Task 1\n\n## ✅ Done\n",
            encoding="utf-8",
        )
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        result = store.checkpoint(
            "STORY-slim-146",
            step_id="sync_coverage",
            status="completed",
            evidence={
                "spec_lint": "pass",
                "story_tests": {"exit_code": 0},
                "regression": "pass",
                "lint": "pass",
                "coverage": {"R1": ["tests/unit/test_story_slim146.py"]},
                "acceptance_coverage": {"AC1": ["tests/unit/test_story_slim146.py"]},
                "board_tasks": ["Task 1"],
            },
        )
        assert result["status"] == "completed"

    def test_blocked_state_never_auto_resumes(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint("STORY-slim-146", step_id="red", status="blocked", evidence={"story_tests": {"exit_code": 1}}, blocker="RFC")
        assert store.resume("STORY-slim-146")["decision"] == "blocked"

    def test_blocked_checkpoint_requires_manual_handoff(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        with pytest.raises(ContinuationError, match="requires a blocker"):
            ContinuationStore(tmp_path).checkpoint(
                "STORY-slim-146", step_id="red", status="blocked", evidence={},
            )

    def test_blocked_checkpoint_cannot_skip_unverified_boundaries(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
        with pytest.raises(ContinuationError, match="cannot skip checkpoint step"):
            store.checkpoint(
                "STORY-slim-146", step_id="sync_coverage", status="blocked",
                evidence={}, blocker="manual action required",
            )

    def test_blocked_input_change_requires_explicit_fresh_preflight(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        _advance_to_green(store)
        spec = tmp_path / "docs/specs/STORY-slim-146.md"
        spec.write_text(spec.read_text(encoding="utf-8") + "\nmanual repair\n", encoding="utf-8")
        store.checkpoint(
            "STORY-slim-146", step_id="regression_lint", status="blocked",
            evidence={}, blocker="Spec changed; restart verification",
        )
        with pytest.raises(ContinuationError, match="stale checkpoint: spec fingerprint changed"):
            store.checkpoint(
                "STORY-slim-146", step_id="regression_lint",
                evidence={"regression": "pass", "lint": "pass"},
            )
        fresh = store.checkpoint(
            "STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"}, fresh=True,
        )
        assert fresh["status"] == "in_progress"
        assert fresh["step_id"] == "preflight"
        history = list((tmp_path / ".pactkit/continuations/history").glob("STORY-slim-146-*.json"))
        assert len(history) == 1
        assert json.loads(history[0].read_text(encoding="utf-8"))["status"] == "blocked"

    def test_changed_worktree_blocks_resume_without_writing(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint("STORY-slim-146", step_id="red", evidence={"story_tests": {"exit_code": 1}})
        (tmp_path / "new-untracked-file.txt").write_text("changed", encoding="utf-8")
        before = store.path_for("STORY-slim-146").read_bytes()
        decision = store.resume("STORY-slim-146")
        assert decision["decision"] == "blocked"
        assert "worktree fingerprint changed" in decision["reasons"]
        assert store.path_for("STORY-slim-146").read_bytes() == before

    def test_second_edit_to_already_dirty_file_changes_worktree_fingerprint(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        tracked = tmp_path / "tracked.txt"
        tracked.write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "tracked fixture"],
            cwd=tmp_path, check=True,
        )
        tracked.write_text("first edit\n", encoding="utf-8")
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint("STORY-slim-146", step_id="red", evidence={"story_tests": {"exit_code": 1}})
        tracked.write_text("second edit\n", encoding="utf-8")
        decision = store.resume("STORY-slim-146")
        assert decision["decision"] == "blocked"
        assert "worktree fingerprint changed" in decision["reasons"]

    def test_competing_active_checkpoint_blocks_resume(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint("STORY-slim-146", step_id="red", evidence={"story_tests": {"exit_code": 1}})
        source_spec = tmp_path / "docs/specs/STORY-slim-146.md"
        (tmp_path / "docs/specs/STORY-slim-999.md").write_text(
            source_spec.read_text(encoding="utf-8").replace(
                "STORY-slim-146", "STORY-slim-999"
            ),
            encoding="utf-8",
        )
        store.checkpoint("STORY-slim-999", step_id="preflight", evidence={"spec_lint": "pass"})
        decision = store.resume("STORY-slim-146")
        assert decision["decision"] == "blocked"
        assert "competing active checkpoints: STORY-slim-999" in decision["reasons"]

    def test_auxiliary_json_is_not_a_competing_checkpoint(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint("STORY-slim-146", step_id="red", evidence={"story_tests": {"exit_code": 1}})
        auxiliary = tmp_path / ".pactkit/continuations/STORY-slim-146-evidence.json"
        auxiliary.write_text("{}", encoding="utf-8")
        assert store.resume("STORY-slim-146")["decision"] == "resume_at"
        assert store.diagnostics() == []

    def test_checkpoint_cannot_move_backward(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        _advance_to_green(store)
        with pytest.raises(ContinuationError, match="cannot move backward"):
            store.checkpoint("STORY-slim-146", step_id="red", evidence={"story_tests": {"exit_code": 1}})

    def test_fresh_cycle_archives_completed_evidence_without_overwriting_it(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        board = tmp_path / "docs/product/sprint_board.md"
        board.write_text(board.read_text(encoding="utf-8").replace("- [ ] Task 1", "- [x] Task 1"), encoding="utf-8")
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        completed = store.checkpoint(
            "STORY-slim-146", step_id="sync_coverage", status="completed",
            evidence={"spec_lint": "pass", "story_tests": {"exit_code": 0}, "regression": "pass", "lint": "pass", "coverage": {"R1": ["test"]}, "acceptance_coverage": {"AC1": ["test"]}, "board_tasks": ["Task 1"]},
        )
        fresh = store.checkpoint(
            "STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"}, fresh=True,
        )
        history = list((tmp_path / ".pactkit/continuations/history").glob("STORY-slim-146-*.json"))
        assert fresh["step_id"] == "preflight"
        assert len(history) == 1
        assert json.loads(history[0].read_text(encoding="utf-8")) == completed

    def test_fresh_cycle_is_retryable_if_active_write_fails_after_archive(self, tmp_path, monkeypatch):
        import pactkit.continuation as continuation
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        board = tmp_path / "docs/product/sprint_board.md"
        board.write_text(board.read_text(encoding="utf-8").replace("- [ ] Task 1", "- [x] Task 1"), encoding="utf-8")
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        completed = store.checkpoint(
            "STORY-slim-146", step_id="sync_coverage", status="completed",
            evidence={"spec_lint": "pass", "story_tests": {"exit_code": 0}, "regression": "pass", "lint": "pass", "coverage": {"R1": ["test"]}, "acceptance_coverage": {"AC1": ["test"]}, "board_tasks": ["Task 1"]},
        )
        real_atomic_write = continuation.atomic_write
        active = store.path_for("STORY-slim-146")
        failed = False

        def fail_active_once(path, content):
            nonlocal failed
            if Path(path) == active and not failed:
                failed = True
                raise OSError("simulated active write failure")
            return real_atomic_write(path, content)

        monkeypatch.setattr(continuation, "atomic_write", fail_active_once)
        with pytest.raises(OSError, match="simulated active write failure"):
            store.checkpoint(
                "STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"}, fresh=True,
            )
        assert store.read("STORY-slim-146") == completed
        fresh = store.checkpoint(
            "STORY-slim-146", step_id="preflight", evidence={"spec_lint": "pass"}, fresh=True,
        )
        assert fresh["step_id"] == "preflight"

    def test_completed_checkpoint_cannot_bypass_required_boundaries(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        board = tmp_path / "docs/product/sprint_board.md"
        board.write_text(board.read_text(encoding="utf-8").replace("- [ ] Task 1", "- [x] Task 1"), encoding="utf-8")
        with pytest.raises(ContinuationError, match="must start at preflight"):
            ContinuationStore(tmp_path).checkpoint(
                "STORY-slim-146", step_id="sync_coverage", status="completed",
                evidence={
                    "spec_lint": "pass", "story_tests": {"exit_code": 0},
                    "regression": "pass", "lint": "pass",
                    "coverage": {"R1": ["test"]},
                    "acceptance_coverage": {"AC1": ["test"]},
                    "board_tasks": ["Task 1"],
                },
            )

    def test_diagnostics_reports_corrupt_checkpoint(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        path = tmp_path / ".pactkit" / "continuations" / "STORY-slim-146.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json", encoding="utf-8")
        assert ContinuationStore(tmp_path).diagnostics() == ["Continuation corrupt: STORY-slim-146.json"]

    def test_corrupt_checkpoint_error_does_not_expose_absolute_home_path(self, tmp_path, monkeypatch):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        path = tmp_path / ".pactkit/continuations/STORY-slim-146.json"
        path.parent.mkdir(parents=True)
        path.write_text("broken", encoding="utf-8")
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path.parent))
        with pytest.raises(ContinuationError) as caught:
            ContinuationStore(tmp_path).read("STORY-slim-146")
        assert str(tmp_path.parent) not in str(caught.value)

    def test_checkpoint_story_mismatch_is_corrupt_and_does_not_resume(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        path = tmp_path / ".pactkit" / "continuations" / "STORY-slim-146.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps({"schema_version": 1, "story_id": "STORY-slim-999"}),
            encoding="utf-8",
        )
        store = ContinuationStore(tmp_path)
        with pytest.raises(ContinuationError, match="invalid checkpoint state"):
            store.resume("STORY-slim-146")
        assert store.diagnostics() == ["Continuation corrupt: STORY-slim-146.json"]

    def test_legacy_handoff_requires_a_new_preflight_checkpoint(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        context = tmp_path / "docs/product/context.md"
        context.write_text(
            "## Agent Continuation\nLast Command: /project-act STORY-slim-146\nPhase Reached: Phase 3\n",
            encoding="utf-8",
        )
        store = ContinuationStore(tmp_path)
        decision = store.resume("STORY-slim-146")
        assert decision == {
            "decision": "start_fresh", "story_id": "STORY-slim-146",
            "next_step": "preflight",
            "reasons": ["unverifiable legacy handoff; create a preflight checkpoint"],
        }
        assert store.diagnostics() == ["Unverifiable legacy handoff: STORY-slim-146"]

    def test_garden_surfaces_invalid_continuation(self, tmp_path):
        from pactkit.garden import check_stale_docs

        _project(tmp_path)
        path = tmp_path / ".pactkit" / "continuations" / "STORY-slim-146.json"
        path.parent.mkdir(parents=True)
        path.write_text("broken", encoding="utf-8")
        findings = check_stale_docs(tmp_path, None)["findings"]
        assert any(f["type"] == "STALE-CONTINUATION" for f in findings)

    def test_doctor_diagnostics_ignores_completed_but_garden_keeps_it(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        board = tmp_path / "docs" / "product" / "sprint_board.md"
        board.write_text(
            "# Sprint Board\n\n## 📋 Backlog\n\n## 🔄 In Progress\n\n"
            "## ✅ Done\n\n### [STORY-slim-146] Test\n- [x] Task 1\n",
            encoding="utf-8",
        )
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        store.checkpoint(
            "STORY-slim-146", step_id="sync_coverage", status="completed",
            evidence={"spec_lint": "pass", "story_tests": {"exit_code": 0}, "regression": "pass", "lint": "pass", "coverage": {"R1": ["test"]}, "acceptance_coverage": {"AC1": ["test"]}, "board_tasks": ["Task 1"]},
        )
        assert store.diagnostics() == []
        assert store.diagnostics(include_completed=True) == ["Completed continuation retained: STORY-slim-146"]

    def test_completed_checkpoint_is_terminal_after_derived_context_changes(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        board = tmp_path / "docs/product/sprint_board.md"
        board.write_text(
            board.read_text(encoding="utf-8").replace("- [ ] Task 1", "- [x] Task 1"),
            encoding="utf-8",
        )
        store = ContinuationStore(tmp_path)
        _advance_to_regression(store)
        store.checkpoint(
            "STORY-slim-146", step_id="sync_coverage", status="completed",
            evidence={"spec_lint": "pass", "story_tests": {"exit_code": 0}, "regression": "pass", "lint": "pass", "coverage": {"R1": ["test"]}, "acceptance_coverage": {"AC1": ["test"]}, "board_tasks": ["Task 1"]},
        )
        context = tmp_path / "docs/product/context.md"
        context.write_text("derived completion summary\n", encoding="utf-8")
        assert store.resume("STORY-slim-146") == {
            "decision": "blocked",
            "story_id": "STORY-slim-146",
            "reasons": ["checkpoint is completed"],
        }

    def test_real_adapter_deployments_keep_act_recovery_contract(self, tmp_path, monkeypatch):
        """R5: inspect actual adapter output, not a hand-shortened template."""
        from pactkit.generators.deploy_base import DeployerBase
        from pactkit.generators.deployer import ClassicDeployer
        from pactkit.profiles import get_profile

        pytest.importorskip("pactkit_opencode")
        pytest.importorskip("pactkit_codex")
        pytest.importorskip("pactkit_copilot")
        from pactkit_codex.deployer import CodexDeployer
        from pactkit_copilot.deployer import CopilotDeployer
        from pactkit_opencode.deployer import OpenCodeDeployer

        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        fake_home = sandbox / "home"
        fake_home.mkdir()
        cwd = sandbox / "cwd"
        cwd.mkdir()
        project_config = cwd / ".claude/pactkit.yaml"
        project_config.parent.mkdir()
        project_config.write_text(
            "stack: python\nci:\n  provider: none\n", encoding="utf-8",
        )
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

        deployments = (
            ("classic", ClassicDeployer(), Path("skills/project-act/SKILL.md")),
            ("opencode", OpenCodeDeployer(), Path("commands/project-act.md")),
            ("codex", CodexDeployer(), Path("skills/project-act/SKILL.md")),
            ("copilot", CopilotDeployer(), Path(".github/prompts/project-act.prompt.md")),
        )
        for name, deployer, relative_command in deployments:
            target = sandbox / "targets" / name
            before = {
                path.relative_to(sandbox): path.read_bytes()
                for path in sandbox.rglob("*")
                if path.is_file() and not path.is_relative_to(target)
            }
            deployer.deploy(target=target)
            command = target / relative_command
            content = command.read_text(encoding="utf-8")
            assert command.is_relative_to(target)
            assert "checkpoint" in content.lower()
            assert "resume" in content.lower() or "verification" in content.lower()
            assert "Run run" not in content
            assert DeployerBase.validate_deployed_content(content, get_profile(name)) == []
            after = {
                path.relative_to(sandbox): path.read_bytes()
                for path in sandbox.rglob("*")
                if path.is_file() and not path.is_relative_to(target)
            }
            assert after == before, f"{name} wrote outside its explicit target"
