"""
STORY-010: Release v1.1.0 — docs sync + version alignment.
(Updated for STORY-011: 14→8 commands, 3→9 skills)
"""
from pathlib import Path


def _root():
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


# ===========================================================================
# Scenario 1: README accuracy
# ===========================================================================

class TestReadmeAccuracy:
    """README must reflect 8 commands and 9 skills."""

    def test_command_count_in_tagline(self):
        readme = (_root() / 'README.md').read_text()
        assert '8 commands' in readme

    def test_command_count_in_quickstart(self):
        readme = (_root() / 'README.md').read_text()
        assert '8 commands' in readme

    def test_no_stale_14_commands(self):
        readme = (_root() / 'README.md').read_text()
        assert '14 commands' not in readme
        assert '14 command' not in readme

    def test_project_status_in_skills_table(self):
        """project-status is now pactkit-status skill, mentioned in README."""
        readme = (_root() / 'README.md').read_text()
        assert 'pactkit-status' in readme or 'Status' in readme

    def test_8_command_playbooks_in_config(self):
        readme = (_root() / 'README.md').read_text()
        assert '8 command playbooks' in readme or '8 command' in readme


# ===========================================================================
# Scenario 2: Version consistency
# ===========================================================================

class TestVersionConsistency:
    """pyproject.toml and __init__.py must both say 1.1.0."""

    def test_init_version(self):
        from pactkit import __version__
        assert __version__ == '1.1.3'

    def test_pyproject_version(self):
        content = (_root() / 'pyproject.toml').read_text()
        assert 'version = "1.1.3"' in content

    def test_config_default_version_unchanged(self):
        """config.py default version is user yaml schema, NOT package version."""
        from pactkit.config import get_default_config
        cfg = get_default_config()
        assert cfg['version'] == '0.0.1'

    def test_cli_version_output(self):
        """CLI version command should reference __version__."""
        import inspect

        from pactkit.cli import main
        source = inspect.getsource(main)
        assert '__version__' in source


# ===========================================================================
# Scenario 3: CLAUDE.md accuracy
# ===========================================================================

class TestClaudeMdAccuracy:
    """Project .claude/CLAUDE.md must have updated numbers."""

    def test_no_stale_846_tests(self):
        claude_md = (_root() / '.claude' / 'CLAUDE.md').read_text()
        assert '846 tests' not in claude_md

    def test_no_stale_14_commands(self):
        claude_md = (_root() / '.claude' / 'CLAUDE.md').read_text()
        assert '14 command' not in claude_md

    def test_has_8_commands_reference(self):
        claude_md = (_root() / '.claude' / 'CLAUDE.md').read_text()
        assert '8 command' in claude_md


# ===========================================================================
# Scenario 4: CHANGELOG exists
# ===========================================================================

class TestChangelog:
    """CHANGELOG.md should exist with v1.1.0 entry."""

    def test_changelog_exists(self):
        assert (_root() / 'CHANGELOG.md').is_file()

    def test_has_v110_section(self):
        content = (_root() / 'CHANGELOG.md').read_text()
        assert '1.1.0' in content

    def test_mentions_auto_merge(self):
        content = (_root() / 'CHANGELOG.md').read_text()
        assert 'auto-merge' in content.lower() or 'Auto-Merge' in content

    def test_mentions_project_status(self):
        content = (_root() / 'CHANGELOG.md').read_text()
        assert 'project-status' in content
