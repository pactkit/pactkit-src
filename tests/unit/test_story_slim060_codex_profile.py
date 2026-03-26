"""Tests for STORY-slim-060: Codex FormatProfile in core (R2, AC2).

Verifies that the 'codex' profile is registered in FORMAT_PROFILES
and accessible via get_profile('codex').
"""

import pytest

from pactkit.profiles import FORMAT_PROFILES, FormatProfile, get_profile


class TestCodexProfileRegistration:
    """AC2: Codex profile available from core."""

    def test_codex_in_format_profiles(self):
        """'codex' key exists in FORMAT_PROFILES."""
        assert "codex" in FORMAT_PROFILES

    def test_get_profile_codex_returns_format_profile(self):
        """get_profile('codex') returns a FormatProfile instance."""
        profile = get_profile("codex")
        assert isinstance(profile, FormatProfile)

    def test_codex_profile_name(self):
        """Profile name is 'codex'."""
        profile = get_profile("codex")
        assert profile.name == "codex"

    def test_codex_profile_display_name(self):
        """Display name is 'Codex CLI'."""
        profile = get_profile("codex")
        assert profile.display_name == "Codex CLI"

    def test_codex_profile_global_config_dir(self):
        """Global config dir is ~/.codex."""
        profile = get_profile("codex")
        assert profile.global_config_dir == "~/.codex"

    def test_codex_profile_project_config_dir(self):
        """Project config dir is .codex."""
        profile = get_profile("codex")
        assert profile.project_config_dir == ".codex"

    def test_codex_profile_skills_dir(self):
        """Skills dir is ~/.codex/skills."""
        profile = get_profile("codex")
        assert profile.skills_dir == "~/.codex/skills"

    def test_codex_profile_pactkit_yaml_path(self):
        """pactkit.yaml path is .codex/pactkit.yaml."""
        profile = get_profile("codex")
        assert profile.pactkit_yaml_path == ".codex/pactkit.yaml"

    def test_codex_profile_instructions_file(self):
        """Project instructions file is AGENTS.md."""
        profile = get_profile("codex")
        assert profile.project_instructions_file == "AGENTS.md"

    def test_codex_profile_is_frozen(self):
        """Profile is immutable (frozen dataclass)."""
        profile = get_profile("codex")
        with pytest.raises(AttributeError):
            profile.name = "modified"


class TestCodexInValidFormats:
    """Verify codex is included in VALID_FORMATS."""

    def test_codex_in_valid_formats(self):
        from pactkit.profiles import VALID_FORMATS

        assert "codex" in VALID_FORMATS

    def test_codex_in_pactkit_yaml_candidates(self):
        from pactkit.profiles import PACTKIT_YAML_CANDIDATES

        assert ".codex/pactkit.yaml" in PACTKIT_YAML_CANDIDATES
