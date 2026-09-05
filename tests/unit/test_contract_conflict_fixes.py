"""STORY-slim-20260905efced66ebc9c: playbook-kernel contract conflict fixes (R1-R6).

R1 coverage gate reports an acceptance gap instead of blocking
R2 Act tool restriction becomes query-first with a recorded fallback
R3 lesson-append unavailability reports a gap instead of stopping
R4 unchecked tasks auto-fix on verified evidence instead of asking
R5 regression baseline uses a verification fingerprint instead of HEAD~1
R6 init/clarify/design/debug load their own phase capsules
"""

import json
import subprocess

import pytest

from pactkit.prompts import COMMANDS_CONTENT
from pactkit.prompts.rules import (
    COMMAND_RULES_MAP,
    PHASE_CONTRACTS,
    RULE_DEFINITIONS,
)
from pactkit.regression import (
    check_verification,
    record_verification,
    verification_path,
)

STORY = "STORY-slim-20260905efced66ebc9c"


def _git(repo, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@example.com",
         "-c", "user.name=T", *args],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture()
def repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    _git(tmp_path, "init")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


# ==============================================================================
# R1: coverage gate reports a gap, never blocks for confirmation
# ==============================================================================
class TestR1CoverageGate:
    def test_no_block_for_confirmation(self):
        done = COMMANDS_CONTENT["project-done.md"]
        assert "BLOCK for confirmation" not in done

    def test_below_50_is_acceptance_gap(self):
        done = COMMANDS_CONTENT["project-done.md"]
        assert "acceptance gap" in done

    def test_pass_and_warn_semantics_kept(self):
        done = COMMANDS_CONTENT["project-done.md"]
        assert "≥80% PASS" in done
        assert "50–79% WARN" in done


# ==============================================================================
# R2: Act allows fallback to standard tools with a recorded reason
# ==============================================================================
class TestR2RecordedFallback:
    def test_no_absolute_prohibition(self):
        act = COMMANDS_CONTENT["project-act.md"]
        assert "Do not invoke" not in act

    def test_fallback_reason_recorded_twice(self):
        act = COMMANDS_CONTENT["project-act.md"]
        # Phase 1 scan + Phase 3 regression selection
        assert act.count("degradation reason") >= 2

    def test_allow_fallback_flag_kept(self):
        act = COMMANDS_CONTENT["project-act.md"]
        assert "--allow-fallback" in act


# ==============================================================================
# R3: lesson-append unavailability reports a gap and continues
# ==============================================================================
class TestR3LessonAppendGap:
    def test_no_stop_and_request(self):
        done = COMMANDS_CONTENT["project-done.md"]
        assert "stop and request a Core upgrade" not in done

    def test_manual_projection_prohibition_kept(self):
        done = COMMANDS_CONTENT["project-done.md"]
        assert "ever write a shared Lesson projection manually" in done


# ==============================================================================
# R4: unchecked tasks auto-fix on verified evidence
# ==============================================================================
class TestR4TaskAutoFix:
    def test_no_forced_ask(self):
        done = COMMANDS_CONTENT["project-done.md"]
        assert "Tests passed but tasks are unchecked" not in done

    def test_verify_then_update(self):
        done = COMMANDS_CONTENT["project-done.md"]
        assert "verify each task's evidence" in done
        assert "board complete-task" in done


# ==============================================================================
# R5: verification fingerprint replaces HEAD~1
# ==============================================================================
class TestR5PlaybookBaseline:
    def test_act_records_fingerprint(self):
        act = COMMANDS_CONTENT["project-act.md"]
        assert "regression --record" in act

    def test_done_checks_record(self):
        done = COMMANDS_CONTENT["project-done.md"]
        assert "regression --check-record" in done

    def test_head1_gone_from_act_and_done(self):
        assert "HEAD~1" not in COMMANDS_CONTENT["project-act.md"]
        assert "HEAD~1" not in COMMANDS_CONTENT["project-done.md"]


class TestR5RecordAndCheck:
    def test_record_writes_commit_and_fingerprint(self, repo):
        message = record_verification(repo, STORY)
        assert message.startswith("Record:")
        record = json.loads(verification_path(repo, STORY).read_text())
        assert record["schema_version"] == 1
        assert record["story_id"] == STORY
        assert record["commit"]
        assert record["fingerprint"].startswith("sha256:")

    def test_unchanged_state_is_verified_current(self, repo):
        record_verification(repo, STORY)
        assert check_verification(repo, STORY).startswith("VERIFIED-CURRENT")

    def test_dirty_source_change_is_stale_with_file(self, repo):
        record_verification(repo, STORY)
        (repo / "src" / "app.py").write_text("x = 2\n")
        verdict = check_verification(repo, STORY)
        assert verdict.startswith("STALE")
        assert "src/app.py" in verdict

    def test_committed_change_is_stale_with_file(self, repo):
        record_verification(repo, STORY)
        (repo / "src" / "app.py").write_text("x = 2\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "change")
        verdict = check_verification(repo, STORY)
        assert verdict.startswith("STALE")
        assert "src/app.py" in verdict

    def test_doc_only_dirty_change_stays_current(self, repo):
        record_verification(repo, STORY)
        (repo / "README.md").write_text("# more\n")
        assert check_verification(repo, STORY).startswith("VERIFIED-CURRENT")

    def test_missing_record_reports_no_record(self, repo):
        assert check_verification(repo, STORY).startswith("NO-RECORD")

    def test_record_degrades_without_git(self, tmp_path):
        (tmp_path / "src").mkdir()
        message = record_verification(tmp_path, STORY)
        assert "unavailable" in message
        assert not verification_path(tmp_path, STORY).exists()

    def test_story_id_rejects_traversal(self, repo):
        with pytest.raises(ValueError):
            record_verification(repo, "../../etc/passwd")

    def test_check_rejects_invalid_story_id(self, repo):
        with pytest.raises(ValueError):
            check_verification(repo, "../escape")


# ==============================================================================
# R6: accurate phase capsules for init/clarify/design/debug
# ==============================================================================
class TestR6PhaseCapsules:
    def test_commands_load_own_capsules(self):
        assert COMMAND_RULES_MAP["project-init"] == [
            "runtime", "pdca-lifecycle", "phase-init", "shared-execution",
        ]
        assert COMMAND_RULES_MAP["project-clarify"] == [
            "runtime", "pdca-lifecycle", "phase-clarify",
        ]
        assert COMMAND_RULES_MAP["project-design"] == [
            "runtime", "pdca-lifecycle", "phase-design",
        ]
        assert COMMAND_RULES_MAP["project-debug"] == [
            "runtime", "pdca-lifecycle", "phase-debug", "shared-execution",
        ]

    def test_phase_plan_scope_narrowed(self):
        assert RULE_DEFINITIONS["phase-plan"].scope == ("project-plan",)

    def test_new_capsules_render_own_contracts(self):
        for rule_id in ("phase-init", "phase-clarify", "phase-design", "phase-debug"):
            command = f"project-{rule_id.removeprefix('phase-')}"
            assert RULE_DEFINITIONS[rule_id].content == PHASE_CONTRACTS[command].render()

    def test_classic_init_skill_imports_init_contract(self, tmp_path):
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        _deploy_commands(
            tmp_path / "skills", ["project-init"], profile=get_profile("classic"),
        )
        content = (tmp_path / "skills" / "project-init" / "SKILL.md").read_text()
        assert "@~/.claude/skills/_rules/phases/init-contract.md" in content
        assert "phases/plan-contract.md" not in content
