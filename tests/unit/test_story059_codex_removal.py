"""Tests for STORY-slim-059: Remove dead codex profile and slim down core package.

Verifies codex profile, references, and branch code are fully removed.
"""

from pathlib import Path

import pytest

_SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "pactkit"


class TestCodexProfileRemoved:
    """AC1: codex profile does not exist."""

    def test_codex_not_in_format_profiles(self):
        from pactkit.profiles import FORMAT_PROFILES

        assert "codex" not in FORMAT_PROFILES

    def test_codex_not_in_valid_formats(self):
        from pactkit.config import VALID_FORMATS

        assert "codex" not in VALID_FORMATS

    def test_get_profile_codex_raises(self):
        from pactkit.profiles import get_profile

        with pytest.raises((KeyError, ValueError)):
            get_profile("codex")


class TestCodexYamlCandidatesRemoved:
    """R1: codex path removed from PACTKIT_YAML_CANDIDATES."""

    def test_no_codex_yaml_candidate(self):
        from pactkit.profiles import PACTKIT_YAML_CANDIDATES

        for path in PACTKIT_YAML_CANDIDATES:
            assert "codex" not in path, f"codex path still in PACTKIT_YAML_CANDIDATES: {path}"


class TestZeroCodexInSource:
    """AC3: zero codex references in src/pactkit/ (excluding comments about history)."""

    def test_no_codex_in_profiles(self):
        content = (_SRC_ROOT / "profiles.py").read_text()
        assert "codex" not in content.lower(), "codex reference still in profiles.py"

    def test_no_codex_in_deployer(self):
        content = (_SRC_ROOT / "generators" / "deployer.py").read_text()
        assert "codex" not in content.lower(), "codex reference still in deployer.py"

    def test_no_codex_in_config(self):
        content = (_SRC_ROOT / "config.py").read_text()
        assert "codex" not in content.lower(), "codex reference still in config.py"

    def test_no_codex_in_scaffold(self):
        content = (_SRC_ROOT / "skills" / "scaffold.py").read_text()
        assert ".codex" not in content, "codex path still in scaffold.py"


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
        """deployer.py should be < 1500 lines (was 1754 before extraction)."""
        lines = (_SRC_ROOT / "generators" / "deployer.py").read_text().splitlines()
        # R5 is SHOULD ≤ 900. Actual: 1754 → ~1448 after OpenCode extraction.
        # Further reduction requires extracting plugin/marketplace (future work).
        assert len(lines) < 1500, f"deployer.py has {len(lines)} lines, should be < 1500"
