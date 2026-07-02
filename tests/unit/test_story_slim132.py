"""STORY-slim-132: Decouple codegraph commands from hardcoded prompt."""

from pathlib import Path


# ---------------------------------------------------------------------------
# AC1 + AC3: skills.py codegraph section (R1, R4, R5)
# ---------------------------------------------------------------------------

class TestSkillsPromptCodegraphSection:
    """AC1: no specific commands; AC3: pactkit query commands preserved."""

    def _get_codegraph_section(self):
        from pactkit.prompts import skills
        # Graph Query Protocol (codegraph section) lives in SKILL_VISUALIZE_MD
        return skills.SKILL_VISUALIZE_MD

    SPECIFIC_COMMANDS = [
        "codegraph callers",
        "codegraph callees",
        "codegraph impact",
        "codegraph query",
        "codegraph explore",
        "codegraph affected",
        "codegraph status",
    ]

    def test_no_specific_codegraph_commands_in_prompt(self):
        """AC1/R1: specific CLI commands must not appear in skills prompt."""
        content = self._get_codegraph_section()
        for cmd in self.SPECIFIC_COMMANDS:
            assert cmd not in content, (
                f"Hardcoded codegraph command found: '{cmd}'. "
                "Replace with `codegraph --help` fallback."
            )

    def test_help_fallback_present(self):
        """AC1/R1: `codegraph --help` fallback must be present."""
        content = self._get_codegraph_section()
        assert "codegraph --help" in content

    def test_no_mcp_tool_name_list(self):
        """AC1/R4: hardcoded MCP tool names must not appear."""
        content = self._get_codegraph_section()
        assert "codegraph_callers" not in content
        assert "codegraph_explore" not in content
        assert "codegraph_node" not in content

    def test_pactkit_query_commands_preserved(self):
        """AC3/R5: pactkit query commands must still be present."""
        content = self._get_codegraph_section()
        assert "pactkit query --callers" in content or "pactkit query" in content


# ---------------------------------------------------------------------------
# AC2: deployer generates slim codegraph section (R2)
# ---------------------------------------------------------------------------

class TestDeployerCodegraphSection:
    """AC2: deployer-generated CLAUDE.md uses help fallback, not command list."""

    SPECIFIC_COMMANDS = [
        "codegraph callers",
        "codegraph callees",
        "codegraph impact",
        "codegraph query",
        "codegraph explore",
        "codegraph affected",
    ]

    def _generate_content(self, tmp_path):
        """Run deployer content generation with a fake .codegraph dir."""
        from pactkit.generators.deployer import _build_claude_md_managed_content

        (tmp_path / ".codegraph").mkdir()
        (tmp_path / ".claude").mkdir(parents=True)
        config = {"name": "testproject", "stack": "python"}
        result = _build_claude_md_managed_content(config, tmp_path)
        # function returns (content, venv_info) tuple
        return result[0] if isinstance(result, tuple) else result

    def test_no_specific_codegraph_commands_in_generated_content(self, tmp_path):
        """AC2/R2: generated CLAUDE.md must not list specific commands."""
        content = self._generate_content(tmp_path)
        for cmd in self.SPECIFIC_COMMANDS:
            assert cmd not in content, (
                f"Hardcoded codegraph command found in generated content: '{cmd}'"
            )

    def test_help_fallback_in_generated_content(self, tmp_path):
        """AC2/R2: generated CLAUDE.md must contain help fallback."""
        content = self._generate_content(tmp_path)
        assert "codegraph --help" in content

    def test_codegraph_section_absent_without_dir(self, tmp_path):
        """AC2: codegraph section not generated when .codegraph/ absent."""
        from pactkit.generators.deployer import _build_claude_md_managed_content

        (tmp_path / ".claude").mkdir(parents=True)
        config = {"name": "testproject", "stack": "python"}
        result = _build_claude_md_managed_content(config, tmp_path)
        content = result[0] if isinstance(result, tuple) else result
        assert "codegraph --help" not in content


# ---------------------------------------------------------------------------
# AC4: global CLAUDE.md (R3) — file-level check
# ---------------------------------------------------------------------------

class TestGlobalClaudeMd:
    """AC4: ~/.claude/CLAUDE.md Codegraph Priority section uses help fallback."""

    GLOBAL_CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"

    SPECIFIC_COMMANDS = [
        "codegraph callers",
        "codegraph callees",
        "codegraph impact",
        "codegraph query",
        "codegraph explore",
        "codegraph affected",
    ]

    def test_no_specific_commands_in_global_claude_md(self):
        """AC4/R3: global CLAUDE.md must not enumerate specific codegraph commands."""
        if not self.GLOBAL_CLAUDE_MD.exists():
            return  # not installed in this env, skip
        content = self.GLOBAL_CLAUDE_MD.read_text()
        for cmd in self.SPECIFIC_COMMANDS:
            assert cmd not in content, (
                f"Hardcoded codegraph command in global CLAUDE.md: '{cmd}'"
            )

    def test_help_fallback_in_global_claude_md(self):
        """AC4/R3: global CLAUDE.md must contain codegraph --help fallback."""
        if not self.GLOBAL_CLAUDE_MD.exists():
            return
        content = self.GLOBAL_CLAUDE_MD.read_text()
        assert "codegraph --help" in content
