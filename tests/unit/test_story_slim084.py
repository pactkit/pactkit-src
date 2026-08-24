"""Tests for STORY-slim-084: Adapter deploy-output validation guard.

AC1-AC4, AC7, AC9: validate_deployed_content() + has_pactkit_cli field.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from pactkit.generators.deploy_base import DeployerBase
from pactkit.profiles import FORMAT_PROFILES, CLIPolicy, get_profile


def _make_profile(*, name, global_config_dir, has_pactkit_cli=True):
    """Create a minimal mock profile for testing."""
    p = MagicMock()
    p.name = name
    p.global_config_dir = global_config_dir
    p.has_pactkit_cli = has_pactkit_cli
    return p


def _unavailable_profile():
    profile = _make_profile(
        name="synthetic", global_config_dir=".synthetic", has_pactkit_cli=False,
    )
    return profile


class TestValidateDeployedContent:
    """AC1-AC4: validate_deployed_content() detects foreign references."""

    def test_detects_foreign_path(self):
        """AC1: codex profile + ~/.claude/ path → violation."""
        content = "Deploy skills to ~/.claude/skills/pactkit-visualize"
        profile = get_profile("codex")
        violations = DeployerBase.validate_deployed_content(content, profile)
        assert any("~/.claude/skills/" in v for v in violations)

    def test_allows_own_path(self):
        """AC2: classic profile + ~/.claude/ path → no violation."""
        content = "Deploy skills to ~/.claude/skills/pactkit-visualize"
        profile = get_profile("classic")
        violations = DeployerBase.validate_deployed_content(content, profile)
        assert violations == []

    def test_detects_cli_ref_for_explicitly_cli_less_profile(self):
        """AC3a: a CLI-less adapter + pactkit visualize → violation."""
        content = "Run `pactkit visualize --mode class` to update graph"
        profile = _unavailable_profile()
        violations = DeployerBase.validate_deployed_content(content, profile)
        assert any("`pactkit visualize" in v for v in violations)

    def test_allows_cli_ref_for_classic(self):
        """AC3b: classic (has CLI) + pactkit visualize → no violation."""
        content = "Run `pactkit visualize --mode class` to update graph"
        profile = get_profile("classic")
        violations = DeployerBase.validate_deployed_content(content, profile)
        assert violations == []

    def test_skips_install_instructions(self):
        """AC4: pactkit init --format is installation guidance, not a CLI ref."""
        content = "run `pactkit init --format copilot` from the terminal"
        profile = _unavailable_profile()
        violations = DeployerBase.validate_deployed_content(content, profile)
        assert violations == []

    def test_detects_multiple_violations(self):
        """Multiple foreign patterns detected in single content."""
        content = (
            "Deploy to ~/.claude/skills/foo\n"
            "Also check ~/.config/opencode/commands/bar\n"
            "Run `pactkit clean` to tidy up\n"
        )
        profile = _unavailable_profile()
        violations = DeployerBase.validate_deployed_content(content, profile)
        assert len(violations) >= 3

    def test_empty_content_no_violations(self):
        """Empty content → no violations."""
        profile = get_profile("codex")
        violations = DeployerBase.validate_deployed_content("", profile)
        assert violations == []

    def test_opencode_own_path_allowed(self):
        """OpenCode profile + ~/.config/opencode/ path → no violation."""
        content = "Skills at ~/.config/opencode/skills/pactkit-board"
        profile = get_profile("opencode")
        violations = DeployerBase.validate_deployed_content(content, profile)
        assert violations == []

    def test_copilot_own_path_allowed(self):
        """Copilot profile + .github/ paths → no violation."""
        content = "Deploy to .github/skills/pactkit-visualize/SKILL.md"
        profile = get_profile("copilot")
        violations = DeployerBase.validate_deployed_content(content, profile)
        assert violations == []


class TestHasPactkitCli:
    """AC7: FormatProfile.has_pactkit_cli values."""

    def test_classic_has_cli(self):
        assert get_profile("classic").has_pactkit_cli is True

    def test_opencode_has_cli(self):
        assert get_profile("opencode").has_pactkit_cli is True

    def test_codex_has_cli(self):
        # STORY-slim-145 R1: codex is now CLIPolicy.PREFERRED -> has_pactkit_cli True.
        # The CLI is preserved (preferred), with explicit fallback when unavailable.
        assert get_profile("codex").has_pactkit_cli is True
        assert get_profile("codex").cli_policy is CLIPolicy.PREFERRED

    def test_copilot_preserves_terminal_cli_for_manual_resume(self):
        assert get_profile("copilot").has_pactkit_cli is True

    def test_all_profiles_have_field(self):
        """Every profile in FORMAT_PROFILES must define has_pactkit_cli."""
        for name, profile in FORMAT_PROFILES.items():
            assert hasattr(profile, "has_pactkit_cli"), f"{name} missing has_pactkit_cli"
            assert isinstance(profile.has_pactkit_cli, bool), f"{name}.has_pactkit_cli is not bool"
