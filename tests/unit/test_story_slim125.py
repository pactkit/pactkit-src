"""Tests for STORY-slim-125 (updated by STORY-slim-134): No model frontmatter in PDCA commands.

Originally verified model: field presence. Superseded by STORY-slim-134 which removes
the model: field to fix Bedrock alias resolution issues in VS Code plugin environments.
"""

import re


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
# AC1: No command has model field
# ---------------------------------------------------------------------------


class TestAC1AllCommandsHaveModel:
    def test_commands_py_prompts_have_model(self):
        """No prompt in COMMANDS_CONTENT must have a model: field (STORY-slim-134)."""
        prompts = _get_all_command_prompts()
        for name, content in prompts.items():
            model = _extract_model(content)
            assert model is None, (
                f"{name} still has model: {model!r} in frontmatter — "
                "remove to avoid Bedrock alias resolution issues (STORY-slim-134)"
            )

    def test_workflow_prompts_have_model(self):
        """Sprint, Hotfix, Design prompts must NOT have model: field (STORY-slim-134)."""
        prompts = _get_workflow_prompts()
        for name, content in prompts.items():
            model = _extract_model(content)
            assert model is None, (
                f"{name} still has model: {model!r} in frontmatter — "
                "remove to avoid Bedrock alias resolution issues (STORY-slim-134)"
            )


# ---------------------------------------------------------------------------
# AC2: Deploy produces no model in SKILL.md
# ---------------------------------------------------------------------------


class TestAC2CorrectModelAssignment:
    def test_command_models_match_spec(self):
        """No command prompt must have a model: field (STORY-slim-134)."""
        prompts = _get_all_command_prompts()
        for name, content in prompts.items():
            actual = _extract_model(content)
            assert actual is None, (
                f"{name}: must not have model field, got model={actual}"
            )

    def test_workflow_models_match_spec(self):
        """Workflow prompts must not have model: field (STORY-slim-134)."""
        prompts = _get_workflow_prompts()
        for name, content in prompts.items():
            actual = _extract_model(content)
            assert actual is None, (
                f"{name}: must not have model field, got model={actual}"
            )


# ---------------------------------------------------------------------------
# AC3: project-design has no model field
# ---------------------------------------------------------------------------


class TestAC3DesignUsesOpus:
    def test_design_prompt_has_opus(self):
        """project-design must NOT have model: field (STORY-slim-134)."""
        from pactkit.prompts.workflows import DESIGN_PROMPT
        model = _extract_model(DESIGN_PROMPT)
        assert model is None, (
            f"project-design still has model: {model!r} — remove it (STORY-slim-134)"
        )
