"""Tests for BUG-014: Version hygiene across specs, prompts, and CHANGELOG.

AC1: Stale 1.1.5 specs updated (no phantom versions)
AC2: Stale 1.2.1 specs updated (no phantom versions)
AC3: TBD specs backfilled with correct version
AC4: CHANGELOG has BUG-010~013 entries
AC5: No remaining TBD specs
AC6: Prompt template versions are valid release versions (not internal iterations)
AC7: Deployed files reflect new versions (requires pactkit init — skip in unit tests)
"""
import re
from pathlib import Path

from pactkit import __version__

ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = ROOT / "docs" / "specs"
PROMPTS_DIR = ROOT / "src" / "pactkit" / "prompts"
SKILLS_DIR = ROOT / "src" / "pactkit" / "skills"

CURRENT_VERSION = __version__
CURRENT_V_PREFIX = f"v{CURRENT_VERSION}"

# Invalid/phantom versions that were never actually released
INVALID_VERSIONS = {"1.1.5", "1.2.1", "TBD"}

# Old internal iteration versions (not real releases)
OLD_ITERATION_VERSIONS = {
    "v16.2", "v18.6", "v19.5", "v19.8", "v22.0", "v23.0",
}


def _get_release(spec_path):
    """Extract Release value from a spec file."""
    text = spec_path.read_text()
    # Table format: | Release | 1.3.0 |
    m = re.search(r'\|\s*Release\s*\|\s*(.+?)\s*\|', text)
    if m:
        return m.group(1).strip()
    # Inline format: - **Release**: 1.3.0
    m = re.search(r'\*\*Release\*\*:\s*(.+)', text)
    if m:
        return m.group(1).strip()
    return None


def _is_valid_release_version(version):
    """Check if version is a valid release version (not phantom/TBD)."""
    if version is None:
        return False
    if version.upper() == "TBD":
        return False
    if version in INVALID_VERSIONS:
        return False
    # Must match semantic version pattern
    return bool(re.match(r'^\d+\.\d+\.\d+$', version))


# ===========================================================================
# AC1: Stale 1.1.5 specs have valid release versions (not phantom 1.1.5)
# ===========================================================================
class TestAC1Stale115:
    """STORY-019~024 should have valid Release versions, not phantom 1.1.5."""

    def test_story019_release(self):
        release = _get_release(SPECS_DIR / "STORY-019.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"

    def test_story020_release(self):
        release = _get_release(SPECS_DIR / "STORY-020.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"

    def test_story021_release(self):
        release = _get_release(SPECS_DIR / "STORY-021.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"

    def test_story022_release(self):
        release = _get_release(SPECS_DIR / "STORY-022.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"

    def test_story023_release(self):
        release = _get_release(SPECS_DIR / "STORY-023.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"

    def test_story024_release(self):
        release = _get_release(SPECS_DIR / "STORY-024.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"


# ===========================================================================
# AC2: Stale 1.2.1 specs have valid release versions (not phantom 1.2.1)
# ===========================================================================
class TestAC2Stale121:
    """BUG-006, BUG-007, STORY-031, STORY-032 should have valid Release versions."""

    def test_bug006_release(self):
        release = _get_release(SPECS_DIR / "BUG-006.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"

    def test_bug007_release(self):
        release = _get_release(SPECS_DIR / "BUG-007.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"

    def test_story031_release(self):
        release = _get_release(SPECS_DIR / "STORY-031.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"

    def test_story032_release(self):
        release = _get_release(SPECS_DIR / "STORY-032.md")
        assert release not in INVALID_VERSIONS, f"Invalid version: {release}"
        assert _is_valid_release_version(release), f"Invalid format: {release}"


# ===========================================================================
# AC3: TBD specs backfilled with valid versions
# ===========================================================================
class TestAC3TBDBackfilled:
    """All formerly-TBD specs should have valid release versions."""

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
        release = _get_release(SPECS_DIR / "STORY-025.md")
        assert _is_valid_release_version(release), f"Invalid: {release}"

    def test_story026_release(self):
        release = _get_release(SPECS_DIR / "STORY-026.md")
        assert _is_valid_release_version(release), f"Invalid: {release}"

    def test_story027_release(self):
        release = _get_release(SPECS_DIR / "STORY-027.md")
        assert _is_valid_release_version(release), f"Invalid: {release}"

    def test_story028_release(self):
        release = _get_release(SPECS_DIR / "STORY-028.md")
        assert _is_valid_release_version(release), f"Invalid: {release}"

    def test_story029_release(self):
        release = _get_release(SPECS_DIR / "STORY-029.md")
        assert _is_valid_release_version(release), f"Invalid: {release}"

    def test_story030_release(self):
        release = _get_release(SPECS_DIR / "STORY-030.md")
        assert _is_valid_release_version(release), f"Invalid: {release}"


# ===========================================================================
# AC4: CHANGELOG has BUG-010~013
# ===========================================================================
class TestAC4ChangelogBugs:
    """CHANGELOG [1.3.0] section must include BUG-010 through BUG-013."""

    def _get_130_section(self):
        text = (ROOT / "CHANGELOG.md").read_text()
        start = text.index("[1.3.0]")
        # Find next version section
        next_section = text.find("\n## [", start + 1)
        return text[start:next_section] if next_section != -1 else text[start:]

    def test_bug010_in_changelog(self):
        assert "BUG-010" in self._get_130_section()

    def test_bug011_in_changelog(self):
        assert "BUG-011" in self._get_130_section()

    def test_bug012_in_changelog(self):
        assert "BUG-012" in self._get_130_section()

    def test_bug013_in_changelog(self):
        assert "BUG-013" in self._get_130_section()


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
# AC6: Prompt template versions are valid (not old internal iterations)
# ===========================================================================
class TestAC6PromptVersions:
    """Prompt headers should use valid release versions, not old iteration versions."""

    def _check_no_old_iterations(self, filepath, pattern):
        """Verify no old internal iteration versions remain in headers."""
        text = filepath.read_text()
        matches = re.findall(pattern, text)
        old = [m for m in matches if m in OLD_ITERATION_VERSIONS]
        return old

    def _check_valid_version_format(self, filepath, pattern):
        """Verify all version labels match valid release format (vX.Y.Z)."""
        text = filepath.read_text()
        matches = re.findall(pattern, text)
        invalid = [m for m in matches if not re.match(r'^v\d+\.\d+\.\d+$', m)]
        return invalid

    def test_commands_py_no_old_iterations(self):
        old = self._check_no_old_iterations(
            PROMPTS_DIR / "commands.py",
            r'# Command: \w+ \((v[\d.]+)',
        )
        assert old == [], f"Old iteration versions in commands.py: {old}"

    def test_commands_py_valid_format(self):
        invalid = self._check_valid_version_format(
            PROMPTS_DIR / "commands.py",
            r'# Command: \w+ \((v[\d.]+)',
        )
        assert invalid == [], f"Invalid version format in commands.py: {invalid}"

    def test_workflows_py_no_old_iterations(self):
        old = self._check_no_old_iterations(
            PROMPTS_DIR / "workflows.py",
            r'# (?:Command|Skill): \w+ \((v[\d.]+)',
        )
        assert old == [], f"Old iteration versions in workflows.py: {old}"

    def test_workflows_py_valid_format(self):
        invalid = self._check_valid_version_format(
            PROMPTS_DIR / "workflows.py",
            r'# (?:Command|Skill): \w+ \((v[\d.]+)',
        )
        assert invalid == [], f"Invalid version format in workflows.py: {invalid}"

    def test_rules_py_constitution_version(self):
        # Check runtime value (f-string uses __version__)
        from pactkit.prompts.rules import CLAUDE_MD_TEMPLATE
        m = re.search(r'PactKit Global Constitution \((v[\d.]+)', CLAUDE_MD_TEMPLATE)
        assert m, "Constitution version not found in CLAUDE_MD_TEMPLATE"
        assert m.group(1) == CURRENT_V_PREFIX, f"Got {m.group(1)}, expected {CURRENT_V_PREFIX}"

    def test_visualize_py_no_old_iterations(self):
        text = (SKILLS_DIR / "visualize.py").read_text()
        for old_v in OLD_ITERATION_VERSIONS:
            assert old_v not in text, f"Old iteration version {old_v} in visualize.py"
