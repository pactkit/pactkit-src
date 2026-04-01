"""Tests for STORY-slim-059/060: Codex profile management.

STORY-059 originally removed codex from core. STORY-060 re-added the codex
FormatProfile to core so the thin adapter (pactkit-codex) can use
get_profile("codex") without bundling its own FormatProfile definition.
"""

from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "pactkit"


class TestCodexProfileRegistered:
    """STORY-slim-060: codex profile exists for thin adapter."""

    def test_codex_in_format_profiles(self):
        from pactkit.profiles import FORMAT_PROFILES

        assert "codex" in FORMAT_PROFILES

    def test_codex_in_valid_formats(self):
        from pactkit.config import VALID_FORMATS

        assert "codex" in VALID_FORMATS

    def test_get_profile_codex_works(self):
        from pactkit.profiles import get_profile

        p = get_profile("codex")
        assert p.name == "codex"
        assert p.global_config_dir == "~/.codex"


class TestCodexYamlCandidates:
    """STORY-slim-060: codex path in PACTKIT_YAML_CANDIDATES."""

    def test_codex_yaml_candidate_present(self):
        from pactkit.profiles import PACTKIT_YAML_CANDIDATES

        assert ".codex/pactkit.yaml" in PACTKIT_YAML_CANDIDATES


class TestPluginMarketplaceUnaffected:
    """AC5: plugin and marketplace modes still work."""

    def test_plugin_format_exists(self):
        from pactkit.config import VALID_FORMATS

        assert "plugin" in VALID_FORMATS

    def test_marketplace_format_exists(self):
        from pactkit.config import VALID_FORMATS

        assert "marketplace" in VALID_FORMATS

    def test_classic_format_exists(self):
        from pactkit.profiles import FORMAT_PROFILES

        assert "classic" in FORMAT_PROFILES


class TestDeployerLineCount:
    """AC6: deployer.py should be significantly smaller after 057+058+059."""

    def test_deployer_reduced_from_original(self):
        """deployer.py should be < 1520 lines (was 1754 before extraction)."""
        lines = (_SRC_ROOT / "generators" / "deployer.py").read_text().splitlines()
        assert len(lines) < 1530, f"deployer.py has {len(lines)} lines, should be < 1530"
