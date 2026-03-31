"""BUG-slim-001: project-init environment detection — SUPERSEDED by STORY-slim-074.

Original BUG-slim-001 added DETECTED_ENV runtime detection to project-init.
STORY-slim-074 eliminated DETECTED_ENV entirely — the playbook is now deployed
per-format with template variables, so no runtime detection is needed.

These tests verify the new template-based approach replaces the old pattern.
"""

import unittest


class TestBugSlim001Superseded(unittest.TestCase):
    """Verify DETECTED_ENV is gone and replaced by template variables."""

    def _get_init_playbook(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        return COMMANDS_CONTENT["project-init.md"]

    def test_no_detected_env_in_playbook(self):
        """STORY-slim-074: DETECTED_ENV eliminated — template variables used instead."""
        playbook = self._get_init_playbook()
        self.assertNotIn("DETECTED_ENV", playbook)

    def test_format_name_template_var_present(self):
        """pactkit init/update uses {FORMAT_NAME} template variable."""
        playbook = self._get_init_playbook()
        self.assertIn("--format {FORMAT_NAME}", playbook)

    def test_no_hardcoded_skills_path_variable(self):
        """No $SKILLS_PATH shell variable — use {VISUALIZE_CMD} / {SCAFFOLD_CMD} instead."""
        playbook = self._get_init_playbook()
        self.assertNotIn("$SKILLS_PATH", playbook)
        self.assertNotIn("SKILLS_PATH=", playbook)

    def test_template_vars_for_project_config(self):
        """Project config uses {PROJECT_CONFIG_DIR} and {INSTRUCTIONS_FILE}."""
        playbook = self._get_init_playbook()
        self.assertIn("{PROJECT_CONFIG_DIR}", playbook)
        self.assertIn("{INSTRUCTIONS_FILE}", playbook)

    def test_pactkit_yaml_uses_template_var(self):
        """Config path uses {PACTKIT_YAML} template variable."""
        playbook = self._get_init_playbook()
        self.assertIn("{PACTKIT_YAML}", playbook)


if __name__ == "__main__":
    unittest.main()
