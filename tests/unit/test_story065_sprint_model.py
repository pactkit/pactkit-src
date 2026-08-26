"""Sprint is host- and model-neutral."""

from pactkit.prompts import SPRINT_PROMPT


def test_sprint_does_not_bind_provider_model_names():
    lower = SPRINT_PROMPT.lower()
    for detail in ("opus", "sonnet", "haiku", "agent_models", "model:"):
        assert detail not in lower


def test_sprint_keeps_phase_outcomes_without_subagent_roles():
    for phase in ("Plan", "Act", "Check", "Done"):
        assert phase in SPRINT_PROMPT
    for role in ("system-architect", "senior-developer", "qa-engineer", "repo-maintainer"):
        assert role not in SPRINT_PROMPT


def test_phase_contracts_are_references_not_inline_content():
    for phase in ("plan", "act", "check", "done"):
        assert f"phases/{phase}-contract.md" in SPRINT_PROMPT
    assert "## Completion Evidence" not in SPRINT_PROMPT
