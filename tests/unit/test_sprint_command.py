"""Current-session Sprint orchestration contract."""

from pactkit.prompts import COMMANDS_CONTENT, SPRINT_PROMPT


def test_sprint_is_registered_and_current_session():
    assert COMMANDS_CONTENT["project-sprint.md"] == SPRINT_PROMPT
    assert SPRINT_PROMPT.startswith("---")
    assert "$ARGUMENTS" in SPRINT_PROMPT
    assert "current session" in SPRINT_PROMPT.lower()
    assert "sequential" in SPRINT_PROMPT.lower()


def test_sprint_uses_single_phase_capsules():
    assert "exactly one active phase" in SPRINT_PROMPT
    for phase in ("plan", "act", "check", "done"):
        assert f"phases/{phase}-contract.md" in SPRINT_PROMPT
    assert "## Completion Evidence" not in SPRINT_PROMPT


def test_sprint_keeps_file_driven_pdca_and_repair_loop():
    assert "pactkit generate-id" in SPRINT_PROMPT
    assert "docs/specs/{STORY_ID}.md" in SPRINT_PROMPT
    assert "Check returns to Act" in SPRINT_PROMPT
    assert "does not lock" in SPRINT_PROMPT


def test_sprint_has_no_retired_execution_mechanisms():
    retired = (
        "TeamCreate", "TaskCreate", "SendMessage", "TeamDelete",
        "WorkUnit", "codex runner", "isolation=", "model: opus",
        "model: sonnet",
    )
    for term in retired:
        assert term not in SPRINT_PROMPT


def test_sprint_wave_mode_is_deterministic_and_serial_by_default():
    lower = SPRINT_PROMPT.lower()
    assert "wave mode" in lower
    assert "spec-graph" in lower and "--json" in lower
    assert "dependency order" in lower
    assert "explicitly requests parallel" in lower
    assert "serialized" in lower


def test_sprint_prompt_remains_compact():
    assert len(SPRINT_PROMPT) < 3000
