"""STORY-014: Release v1.1.3 — version consistency and CHANGELOG completeness."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
TARGET_VERSION = "1.1.3"


class TestVersionConsistency:
    """All version sources must agree on the target version."""

    def test_pyproject_version(self):
        text = (ROOT / "pyproject.toml").read_text()
        m = re.search(r'^version\s*=\s*"(.+?)"', text, re.MULTILINE)
        assert m, "version not found in pyproject.toml"
        assert m.group(1) == TARGET_VERSION

    def test_init_version(self):
        text = (ROOT / "src" / "pactkit" / "__init__.py").read_text()
        m = re.search(r'__version__\s*=\s*"(.+?)"', text)
        assert m, "__version__ not found in __init__.py"
        assert m.group(1) == TARGET_VERSION

    def test_pactkit_yaml_version(self):
        text = (ROOT / ".claude" / "pactkit.yaml").read_text()
        data = yaml.safe_load(text)
        assert str(data.get("version")) == TARGET_VERSION


class TestChangelogCompleteness:
    """CHANGELOG must have entries for v1.1.2 and v1.1.3."""

    def _read_changelog(self):
        return (ROOT / "CHANGELOG.md").read_text()

    def test_has_112_section(self):
        text = self._read_changelog()
        assert "[1.1.2]" in text, "CHANGELOG missing [1.1.2] section"

    def test_has_113_section(self):
        text = self._read_changelog()
        assert "[1.1.3]" in text, "CHANGELOG missing [1.1.3] section"

    def test_112_mentions_bug001(self):
        text = self._read_changelog()
        assert "BUG-001" in text, "CHANGELOG [1.1.2] should mention BUG-001"

    def test_112_mentions_bug002(self):
        text = self._read_changelog()
        assert "BUG-002" in text, "CHANGELOG [1.1.2] should mention BUG-002"

    def test_113_mentions_bug003(self):
        text = self._read_changelog()
        # BUG-003 should be in the 1.1.3 section
        section_113 = text[text.index("[1.1.3]"):]
        assert "BUG-003" in section_113

    def test_113_mentions_bug004(self):
        text = self._read_changelog()
        section_113 = text[text.index("[1.1.3]"):]
        assert "BUG-004" in section_113

    def test_113_mentions_bug005(self):
        text = self._read_changelog()
        section_113 = text[text.index("[1.1.3]"):]
        assert "BUG-005" in section_113
