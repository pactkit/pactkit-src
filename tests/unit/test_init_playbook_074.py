"""STORY-slim-074: Fix init playbook — eliminate DETECTED_ENV, use template variables.

Covers:
- AC1: No DETECTED_ENV in source template
- AC2: No hardcoded IDE paths in source template
- AC3: FORMAT_NAME resolves correctly for all 3 formats
- AC4-AC6: Deployed playbooks have only their own format's paths
- AC7: Single unified flow for project instructions
- AC8: pactkit init/update uses {FORMAT_NAME}
"""

import unittest

from pactkit.profiles import get_profile


def _get_init_source():
    from pactkit.prompts.commands import COMMANDS_CONTENT

    return COMMANDS_CONTENT["project-init.md"]


def _render(template, profile):
    from pactkit.generators.deployer import _render_prompt

    return _render_prompt(template, profile)


# ── AC1: No DETECTED_ENV in source ──────────────────────────────────────


class TestAC1NoDetectedEnv(unittest.TestCase):
    """DETECTED_ENV must not appear anywhere in the init playbook source."""

    def test_no_detected_env_in_source(self):
        source = _get_init_source()
        self.assertNotIn("DETECTED_ENV", source)


# ── AC2: No hardcoded IDE paths in source ───────────────────────────────


class TestAC2NoHardcodedPaths(unittest.TestCase):
    """Source template must use template variables, not literal IDE paths."""

    FORBIDDEN_LITERALS = [
        ".claude/",
        ".opencode/",
        ".codex/",
        "~/.config/opencode",
        "CLAUDE.md",
        "AGENTS.md",
    ]

    def test_no_hardcoded_paths_in_source(self):
        source = _get_init_source()
        for literal in self.FORBIDDEN_LITERALS:
            matches = [
                line.strip()
                for line in source.splitlines()
                if literal in line and not line.strip().startswith("#")
            ]
            self.assertEqual(
                len(matches), 0, f"Found hardcoded '{literal}' in init playbook:\n" + "\n".join(matches[:5])
            )


# ── AC3: FORMAT_NAME resolves correctly ─────────────────────────────────


class TestAC3FormatNameResolves(unittest.TestCase):
    """_render_prompt must resolve {FORMAT_NAME} to the profile name."""

    def test_format_name_classic(self):
        result = _render("{FORMAT_NAME}", get_profile("classic"))
        self.assertEqual(result, "classic")

    def test_format_name_opencode(self):
        result = _render("{FORMAT_NAME}", get_profile("opencode"))
        self.assertEqual(result, "opencode")

    def test_format_name_codex(self):
        result = _render("{FORMAT_NAME}", get_profile("codex"))
        self.assertEqual(result, "codex")


# ── AC4-AC6: Deployed output format-correct ─────────────────────────────


class TestDeployedFormatCorrectness(unittest.TestCase):
    """After rendering, each format's playbook must only contain its own paths."""

    # Cross-format identifiers that should NOT appear
    _CLASSIC_MARKERS = [".claude/", "CLAUDE.md"]
    _OPENCODE_MARKERS = [".opencode/", "~/.config/opencode"]
    _CODEX_MARKERS = [".codex/"]

    def _render_init(self, format_name):
        source = _get_init_source()
        profile = get_profile(format_name)
        return _render(source, profile)

    def _assert_no_markers(self, rendered, forbidden_markers, format_name):
        for marker in forbidden_markers:
            matches = [
                line.strip()
                for line in rendered.splitlines()
                if marker in line and not line.strip().startswith("#")
            ]
            self.assertEqual(
                len(matches),
                0,
                f"Rendered {format_name} init contains cross-format marker '{marker}':\n" + "\n".join(matches[:5]),
            )

    def test_ac4_classic_no_opencode_no_codex(self):
        rendered = self._render_init("classic")
        self._assert_no_markers(rendered, self._OPENCODE_MARKERS, "classic")
        self._assert_no_markers(rendered, self._CODEX_MARKERS, "classic")
        # Must contain its own paths
        self.assertIn(".claude/", rendered)

    def test_ac5_codex_no_classic_no_opencode(self):
        rendered = self._render_init("codex")
        self._assert_no_markers(rendered, self._CLASSIC_MARKERS, "codex")
        self._assert_no_markers(rendered, self._OPENCODE_MARKERS, "codex")
        # Must contain its own paths
        self.assertIn(".codex/", rendered)

    def test_ac6_opencode_no_classic_no_codex(self):
        rendered = self._render_init("opencode")
        self._assert_no_markers(rendered, self._CLASSIC_MARKERS, "opencode")
        self._assert_no_markers(rendered, self._CODEX_MARKERS, "opencode")
        # Must contain its own paths
        self.assertIn(".opencode/", rendered)


# ── AC7: Single unified flow ────────────────────────────────────────────


class TestAC7UnifiedFlow(unittest.TestCase):
    """Init playbook must have one instructions flow, not per-format branches."""

    def test_no_separate_opencode_phase(self):
        source = _get_init_source()
        # Old pattern: Phase 6 was OpenCode-specific
        self.assertNotIn("OpenCode Project Setup", source)

    def test_uses_template_var_for_instructions(self):
        source = _get_init_source()
        # Must use {INSTRUCTIONS_FILE} not literal file names
        self.assertIn("{INSTRUCTIONS_FILE}", source)
        self.assertIn("{PROJECT_CONFIG_DIR}", source)


# ── AC8: pactkit init/update uses FORMAT_NAME ───────────────────────────


class TestAC8FormatNameInCommands(unittest.TestCase):
    """Rendered playbook must use --format <format_name> for pactkit CLI calls."""

    def test_classic_uses_format_classic(self):
        rendered = _render(_get_init_source(), get_profile("classic"))
        self.assertIn("--format classic", rendered)

    def test_opencode_uses_format_opencode(self):
        rendered = _render(_get_init_source(), get_profile("opencode"))
        self.assertIn("--format opencode", rendered)

    def test_codex_uses_format_codex(self):
        rendered = _render(_get_init_source(), get_profile("codex"))
        self.assertIn("--format codex", rendered)


# ── Bonus: other prompts also fixed in STORY-slim-074 ───────────────────


class TestOtherPromptsNoHardcodedPaths(unittest.TestCase):
    """Verify doctor, core-protocol, and project-done also use template variables."""

    def test_doctor_uses_pactkit_yaml_var(self):
        from pactkit.prompts.skills import SKILL_DOCTOR_MD

        self.assertNotIn(".claude/pactkit.yaml", SKILL_DOCTOR_MD)
        self.assertNotIn(".opencode/pactkit.yaml", SKILL_DOCTOR_MD)
        self.assertIn("{PACTKIT_YAML}", SKILL_DOCTOR_MD)

    def test_core_protocol_uses_project_config_dir(self):
        from pactkit.prompts.rules import RULES_MODULES

        core = RULES_MODULES["core"]
        self.assertNotIn('check `.claude/`, `.opencode/`, `.codex/`', core)
        self.assertIn("{PROJECT_CONFIG_DIR}", core)

    def test_done_smoke_check_uses_temporary_target_before_any_host_update(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        done = COMMANDS_CONTENT["project-done.md"]
        self.assertNotIn("~/.claude/commands", done)
        self.assertIn("temporary target directory", done)
        self.assertIn("explicit authorization", done)


if __name__ == "__main__":
    unittest.main()
