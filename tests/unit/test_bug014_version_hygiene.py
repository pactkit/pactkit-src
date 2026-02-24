"""Tests for BUG-014: Version hygiene across specs, prompts, and CHANGELOG.

AC1: Stale 1.1.5 specs updated to 1.2.0
AC2: Stale 1.2.1 specs updated to 1.2.0
AC3: TBD specs backfilled with correct version
AC4: CHANGELOG has BUG-010~013 entries
AC5: No remaining TBD specs
AC6: Prompt template versions unified to v1.2.0
AC7: Deployed files reflect new versions (requires pactkit init — skip in unit tests)
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = ROOT / "docs" / "specs"
PROMPTS_DIR = ROOT / "src" / "pactkit" / "prompts"
SKILLS_DIR = ROOT / "src" / "pactkit" / "skills"


def _get_release(spec_path):
    """Extract Release value from a spec file."""
    text = spec_path.read_text()
    # Table format: | Release | 1.2.0 |
    m = re.search(r'\|\s*Release\s*\|\s*(.+?)\s*\|', text)
    if m:
        return m.group(1).strip()
    # Inline format: - **Release**: 1.2.0
    m = re.search(r'\*\*Release\*\*:\s*(.+)', text)
    if m:
        return m.group(1).strip()
    return None


# ===========================================================================
# AC1: Stale 1.1.5 specs updated to 1.2.0
# ===========================================================================
class TestAC1Stale115:
    """STORY-019~024 should have Release: 1.2.0, not 1.1.5."""

    def test_story019_release(self):
        assert _get_release(SPECS_DIR / "STORY-019.md") == "1.2.0"

    def test_story020_release(self):
        assert _get_release(SPECS_DIR / "STORY-020.md") == "1.2.0"

    def test_story021_release(self):
        assert _get_release(SPECS_DIR / "STORY-021.md") == "1.2.0"

    def test_story022_release(self):
        assert _get_release(SPECS_DIR / "STORY-022.md") == "1.2.0"

    def test_story023_release(self):
        assert _get_release(SPECS_DIR / "STORY-023.md") == "1.2.0"

    def test_story024_release(self):
        assert _get_release(SPECS_DIR / "STORY-024.md") == "1.2.0"


# ===========================================================================
# AC2: Stale 1.2.1 specs updated to 1.2.0
# ===========================================================================
class TestAC2Stale121:
    """BUG-006, BUG-007, STORY-031, STORY-032 should have Release: 1.2.0."""

    def test_bug006_release(self):
        assert _get_release(SPECS_DIR / "BUG-006.md") == "1.2.0"

    def test_bug007_release(self):
        assert _get_release(SPECS_DIR / "BUG-007.md") == "1.2.0"

    def test_story031_release(self):
        assert _get_release(SPECS_DIR / "STORY-031.md") == "1.2.0"

    def test_story032_release(self):
        assert _get_release(SPECS_DIR / "STORY-032.md") == "1.2.0"


# ===========================================================================
# AC3: TBD specs backfilled
# ===========================================================================
class TestAC3TBDBackfilled:
    """All TBD specs should have their correct release version."""

    def test_story001_release(self):
        assert _get_release(SPECS_DIR / "STORY-001.md") == "1.0.0"

    def test_story002_release(self):
        assert _get_release(SPECS_DIR / "STORY-002.md") == "1.0.0"

    def test_story003_release(self):
        assert _get_release(SPECS_DIR / "STORY-003.md") == "1.0.0"

    def test_story004_release(self):
        assert _get_release(SPECS_DIR / "STORY-004.md") == "1.0.0"

    def test_story005_release(self):
        assert _get_release(SPECS_DIR / "STORY-005.md") == "1.1.0"

    def test_story006_release(self):
        assert _get_release(SPECS_DIR / "STORY-006.md") == "1.1.0"

    def test_story007_release(self):
        assert _get_release(SPECS_DIR / "STORY-007.md") == "1.1.0"

    def test_story008_release(self):
        assert _get_release(SPECS_DIR / "STORY-008.md") == "1.1.0"

    def test_story009_release(self):
        assert _get_release(SPECS_DIR / "STORY-009.md") == "1.1.0"

    def test_story012_release(self):
        assert _get_release(SPECS_DIR / "STORY-012.md") == "1.1.1"

    def test_story025_release(self):
        assert _get_release(SPECS_DIR / "STORY-025.md") == "1.2.0"

    def test_story026_release(self):
        assert _get_release(SPECS_DIR / "STORY-026.md") == "1.2.0"

    def test_story027_release(self):
        assert _get_release(SPECS_DIR / "STORY-027.md") == "1.2.0"

    def test_story028_release(self):
        assert _get_release(SPECS_DIR / "STORY-028.md") == "1.2.0"

    def test_story029_release(self):
        assert _get_release(SPECS_DIR / "STORY-029.md") == "1.2.0"

    def test_story030_release(self):
        assert _get_release(SPECS_DIR / "STORY-030.md") == "1.2.0"


# ===========================================================================
# AC4: CHANGELOG has BUG-010~013
# ===========================================================================
class TestAC4ChangelogBugs:
    """CHANGELOG [1.2.0] section must include BUG-010 through BUG-013."""

    def _get_120_section(self):
        text = (ROOT / "CHANGELOG.md").read_text()
        start = text.index("[1.2.0]")
        # Find next version section
        next_section = text.find("\n## [", start + 1)
        return text[start:next_section] if next_section != -1 else text[start:]

    def test_bug010_in_changelog(self):
        assert "BUG-010" in self._get_120_section()

    def test_bug011_in_changelog(self):
        assert "BUG-011" in self._get_120_section()

    def test_bug012_in_changelog(self):
        assert "BUG-012" in self._get_120_section()

    def test_bug013_in_changelog(self):
        assert "BUG-013" in self._get_120_section()


# ===========================================================================
# AC5: No remaining TBD specs
# ===========================================================================
class TestAC5NoTBD:
    """No spec file should have Release: TBD."""

    def test_no_tbd_in_any_spec(self):
        tbd_specs = []
        for spec in sorted(SPECS_DIR.glob("*.md")):
            release = _get_release(spec)
            if release and release.upper() == "TBD":
                tbd_specs.append(spec.name)
        assert tbd_specs == [], f"Specs still have TBD: {tbd_specs}"


# ===========================================================================
# AC6: Prompt template versions unified to v1.2.0
# ===========================================================================
class TestAC6PromptVersions:
    """All prompt headers should use v1.2.0, not old iteration versions."""

    def _check_no_old_versions(self, filepath, pattern):
        """Verify no old version labels remain in command/skill headers."""
        text = filepath.read_text()
        # Find all version labels in headers like "# Command: X (vNN.N ...)"
        matches = re.findall(pattern, text)
        old = [m for m in matches if m != "v1.2.0"]
        return old

    def test_commands_py_versions(self):
        old = self._check_no_old_versions(
            PROMPTS_DIR / "commands.py",
            r'# Command: \w+ \((v[\d.]+)',
        )
        assert old == [], f"Old versions in commands.py: {old}"

    def test_workflows_py_command_versions(self):
        old = self._check_no_old_versions(
            PROMPTS_DIR / "workflows.py",
            r'# (?:Command|Skill): \w+ \((v[\d.]+)',
        )
        assert old == [], f"Old versions in workflows.py: {old}"

    def test_rules_py_constitution_version(self):
        text = (PROMPTS_DIR / "rules.py").read_text()
        m = re.search(r'PactKit Global Constitution \((v[\d.]+)', text)
        assert m, "Constitution version not found"
        assert m.group(1) == "v1.2.0", f"Got {m.group(1)}"

    def test_visualize_py_section_versions(self):
        text = (SKILLS_DIR / "visualize.py").read_text()
        # Check no old version labels in section comments
        old_patterns = [r'original, v\d+\.\d+', r'v\d+\.\d+ Multi-Mode']
        for pat in old_patterns:
            m = re.search(pat, text)
            if m and "v1.2.0" not in m.group(0):
                assert False, f"Old version in visualize.py: {m.group(0)}"
