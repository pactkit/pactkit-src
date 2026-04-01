"""Tests for STORY-slim-083: _build_command_rules_header OCP refactor (AC7).

The function should dispatch on profile.rules_import_style, not profile.name.
"""

from unittest.mock import MagicMock


class TestBuildCommandRulesHeaderOCP:
    """AC7: _build_command_rules_header dispatches on rules_import_style."""

    def _call(self, profile, cmd_name="project-act", config=None):
        from pactkit.generators.deployer import _build_command_rules_header

        return _build_command_rules_header(cmd_name, profile, config=config)

    def _make_profile(self, *, name, rules_import_style, rules_dir="rules"):
        """Create a minimal mock FormatProfile."""
        p = MagicMock()
        p.name = name
        p.rules_import_style = rules_import_style
        p.rules_dir = rules_dir
        return p

    def test_inline_style_returns_content_regardless_of_name(self):
        """Any profile with rules_import_style='inline' should get inlined rules."""
        profile = self._make_profile(name="copilot", rules_import_style="inline")
        result = self._call(profile)
        # Should have inlined content (non-empty), no @import lines
        assert result, "inline style should produce non-empty header"
        assert "@~/" not in result, "inline style must not have @import references"
        assert "<!-- rules-end -->" in result

    def test_import_style_returns_at_references(self):
        """Classic profile with rules_import_style='@import' should get @import lines."""
        profile = self._make_profile(name="classic", rules_import_style="@import")
        result = self._call(profile)
        assert "@~/.claude/rules/" in result
        assert "<!-- rules-end -->" not in result

    def test_fake_name_with_inline_style_still_inlines(self):
        """A hypothetical format with inline style should work without name check."""
        profile = self._make_profile(name="future-format", rules_import_style="inline")
        result = self._call(profile)
        assert result, "inline style should produce content for any profile name"
        assert "@~/" not in result
        assert "<!-- rules-end -->" in result

    def test_no_name_based_branching(self):
        """Verify the function does NOT check profile.name for dispatch."""
        import inspect
        from pactkit.generators.deployer import _build_command_rules_header

        source = inspect.getsource(_build_command_rules_header)
        # After refactor, should NOT have profile.name == "opencode" or similar
        assert 'profile.name == "opencode"' not in source, \
            "function should dispatch on rules_import_style, not profile.name"
        assert 'profile.name == "classic"' not in source, \
            "function should dispatch on rules_import_style, not profile.name"
