"""Tests for STORY-017: project-init auto-generates project-level CLAUDE.md."""

from pactkit.prompts.commands import COMMANDS_CONTENT

INIT_PROMPT = COMMANDS_CONTENT["project-init.md"]


class TestInitPromptClaudeMdGeneration:
    """Verify the project-init prompt instructs CLAUDE.md generation."""

    def test_prompt_contains_instructions_file_generation_step(self):
        """Scenario 1: prompt includes a step to generate project instructions file.

        STORY-slim-074: changed from hardcoded .claude/CLAUDE.md to template variables.
        """
        assert "{INSTRUCTIONS_FILE}" in INIT_PROMPT
        assert "{PROJECT_CONFIG_DIR}/{INSTRUCTIONS_FILE}" in INIT_PROMPT

    def test_prompt_skip_if_exists(self):
        """Scenario 2: prompt instructs to skip if CLAUDE.md already exists."""
        lower = INIT_PROMPT.lower()
        # Must mention conditional — skip/not overwrite if already exists
        assert any(
            phrase in lower
            for phrase in ["if missing", "if not exist", "already exist", "skip"]
        ), "Prompt must instruct to skip generation if CLAUDE.md already exists"

    def test_prompt_includes_context_md_reference(self):
        """Scenario 3: prompt uses local Context bootstrap, not a fragile import."""
        assert "pactkit context" in INIT_PROMPT
        assert "@./docs/product/context.md" not in INIT_PROMPT

    def test_prompt_references_lang_profiles_dev_commands(self):
        """Scenario 4: prompt references LANG_PROFILES for dev commands."""
        lower = INIT_PROMPT.lower()
        assert "lang_profiles" in lower or "test_runner" in lower or "lint_command" in lower, (
            "Prompt must reference LANG_PROFILES dev commands (test_runner, lint_command)"
        )

    def test_prompt_instructs_project_name_inclusion(self):
        """Content must include project name."""
        lower = INIT_PROMPT.lower()
        assert "project name" in lower or "project title" in lower or "directory name" in lower

    def test_prompt_instructs_language_inclusion(self):
        """Content must include detected language/stack."""
        lower = INIT_PROMPT.lower()
        assert "language" in lower and ("stack" in lower or "detected" in lower)
