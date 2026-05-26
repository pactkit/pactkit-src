"""Tests for STORY-slim-125: All PDCA command/skill prompts must have model frontmatter."""

import re


EXPECTED_MODELS = {
    "project-plan.md": "opus",
    "project-act.md": "sonnet",
    "project-check.md": "sonnet",
    "project-done.md": "sonnet",
    "project-clarify.md": "sonnet",
    "project-init.md": "sonnet",
    "project-release.md": "sonnet",
    "project-pr.md": "sonnet",
    "project-sprint.md": "sonnet",
    "project-hotfix.md": "sonnet",
    "project-design.md": "opus",
}


def _get_all_command_prompts():
    """Get all command prompt contents from COMMANDS_CONTENT."""
    from pactkit.prompts.commands import COMMANDS_CONTENT
    return COMMANDS_CONTENT


def _get_workflow_prompts():
    """Get workflow prompts that are PDCA commands."""
    from pactkit.prompts.workflows import (
        SPRINT_PROMPT,
        HOTFIX_PROMPT,
        DESIGN_PROMPT,
    )
    return {
        "project-sprint.md": SPRINT_PROMPT,
        "project-hotfix.md": HOTFIX_PROMPT,
        "project-design.md": DESIGN_PROMPT,
    }


def _extract_model(content):
    """Extract model value from frontmatter."""
    m = re.search(r"^model:\s*(\w+)", content, re.MULTILINE)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# AC1: All commands have model field
# ---------------------------------------------------------------------------


class TestAC1AllCommandsHaveModel:
    def test_commands_py_prompts_have_model(self):
        """Every prompt in COMMANDS_CONTENT must have a model: field."""
        prompts = _get_all_command_prompts()
        for name, content in prompts.items():
            model = _extract_model(content)
            assert model is not None, f"{name} missing model: in frontmatter"

    def test_workflow_prompts_have_model(self):
        """Sprint, Hotfix, Design prompts must have model: field."""
        prompts = _get_workflow_prompts()
        for name, content in prompts.items():
            model = _extract_model(content)
            assert model is not None, f"{name} missing model: in frontmatter"


# ---------------------------------------------------------------------------
# AC2: Correct model assignments
# ---------------------------------------------------------------------------


class TestAC2CorrectModelAssignment:
    def test_command_models_match_spec(self):
        """Each command prompt must have the model specified in the Spec."""
        prompts = _get_all_command_prompts()
        for name, expected_model in EXPECTED_MODELS.items():
            if name in prompts:
                actual = _extract_model(prompts[name])
                assert actual == expected_model, (
                    f"{name}: expected model={expected_model}, got model={actual}"
                )

    def test_workflow_models_match_spec(self):
        """Workflow prompts must have correct model."""
        prompts = _get_workflow_prompts()
        for name, expected_model in EXPECTED_MODELS.items():
            if name in prompts:
                actual = _extract_model(prompts[name])
                assert actual == expected_model, (
                    f"{name}: expected model={expected_model}, got model={actual}"
                )


# ---------------------------------------------------------------------------
# AC3: project-design uses opus
# ---------------------------------------------------------------------------


class TestAC3DesignUsesOpus:
    def test_design_prompt_has_opus(self):
        """project-design must use model: opus."""
        from pactkit.prompts.workflows import DESIGN_PROMPT
        model = _extract_model(DESIGN_PROMPT)
        assert model == "opus"
