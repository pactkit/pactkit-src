"""Tests for STORY-slim-082: Sync prompt templates for --mode module and --focus scoping."""


class TestSkillVisualizeMD:
    """AC1-AC3: SKILL_VISUALIZE_MD updates."""

    def test_command_syntax_includes_module(self):
        """AC1: Command syntax contains file|class|call|module."""
        from pactkit.prompts.skills import SKILL_VISUALIZE_MD
        assert 'file|class|call|module' in SKILL_VISUALIZE_MD

    def test_focus_description_no_requires_call(self):
        """AC2: --focus no longer says 'requires --mode call'."""
        from pactkit.prompts.skills import SKILL_VISUALIZE_MD
        lines = SKILL_VISUALIZE_MD.split('\n')
        focus_lines = [l for l in lines if '`--focus' in l]
        for line in focus_lines:
            assert "requires `--mode call`" not in line, f"--focus still says requires call: {line}"

    def test_focus_description_mentions_scoping(self):
        """AC2: --focus mentions file, class, call scoping."""
        from pactkit.prompts.skills import SKILL_VISUALIZE_MD
        lines = SKILL_VISUALIZE_MD.split('\n')
        focus_line = [l for l in lines if '`--focus' in l and 'module' in l.lower()]
        assert len(focus_line) >= 1, "--focus row not found in parameter table"

    def test_module_graph_in_output_table(self):
        """AC3: Output table has module_graph.mmd row."""
        from pactkit.prompts.skills import SKILL_VISUALIZE_MD
        assert 'module_graph.mmd' in SKILL_VISUALIZE_MD

    def test_description_says_four_modes(self):
        """R1: Description updated to four analysis modes."""
        from pactkit.prompts.skills import SKILL_VISUALIZE_MD
        assert 'four' in SKILL_VISUALIZE_MD.lower()

    def test_module_mode_in_parameter_table(self):
        """R1: --mode module row exists in parameter table."""
        from pactkit.prompts.skills import SKILL_VISUALIZE_MD
        assert '`--mode module`' in SKILL_VISUALIZE_MD


class TestVisualFirstRule:
    """AC4: Visual First includes module mode."""

    def test_visual_first_has_module(self):
        """AC4: rules.py Visual First section includes --mode module."""
        from pactkit.prompts.rules import RULES_MODULES
        core = RULES_MODULES['core']
        assert '--mode module' in core


class TestReleaseSnapshot:
    """AC5: Release snapshot mentions module mode."""

    def test_release_mentions_module(self):
        """AC5: Release skill template includes module in mode list."""
        from pactkit.prompts.skills import SKILL_RELEASE_MD
        lines = SKILL_RELEASE_MD.split('\n')
        viz_lines = [l for l in lines if 'visualize' in l.lower() and 'mode' in l.lower()]
        found = any('module' in l.lower() for l in viz_lines)
        assert found, "No visualize line mentions module mode"


class TestInitPhase3:
    """AC6: Init generates module graph."""

    def test_init_has_module_visualize(self):
        """AC6: Init command Phase 3 includes --mode module."""
        from pactkit.prompts.commands import COMMANDS_CONTENT
        init_md = COMMANDS_CONTENT['project-init.md']
        assert '--mode module' in init_md
