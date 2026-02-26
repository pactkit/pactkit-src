"""Tests for BUG-020: CLAUDE.md backup and regenerate strategy.

NOTE: BUG-021 superseded the backup-and-regenerate behavior.
Per BUG-021 R1, if CLAUDE.md exists, the function MUST skip (not overwrite).
These tests are updated to reflect the new Playbook-aligned behavior.

AC1: Existing file NOT modified (per BUG-021)
AC2: Fresh project generates file
AC3: N/A (backup behavior removed)
AC4: N/A (no notification for skipped files)
"""
import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestAC1ExistingFileBackedUp:
    """AC1: Existing CLAUDE.md is NOT modified (BUG-021 supersedes BUG-020)."""

    def test_backup_created_when_file_exists(self, tmp_path):
        """BUG-021: Existing file is skipped, no backup created."""
        from pactkit.config import get_default_config
        from pactkit.generators.deployer import _generate_project_claude_md_if_missing

        # Create existing CLAUDE.md
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        original_content = "# My Custom Project\n\nDo not lose this."
        claude_md.write_text(original_content)

        # Create venv
        venv_dir = tmp_path / ".venv" / "bin"
        venv_dir.mkdir(parents=True)
        (venv_dir / "python3").touch()

        config = get_default_config()
        config['venv'] = {'auto_detect': True}

        with patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            _generate_project_claude_md_if_missing(config)

        # BUG-021: File should NOT be modified
        assert claude_md.read_text() == original_content
        # BUG-021: No backup should be created
        backup_file = claude_dir / "CLAUDE.md.bak"
        assert not backup_file.exists(), "No backup when skipping existing file"

    def test_new_claude_md_has_venv_section(self, tmp_path):
        """BUG-021: Existing file is preserved, not overwritten."""
        from pactkit.config import get_default_config
        from pactkit.generators.deployer import _generate_project_claude_md_if_missing

        # Create existing CLAUDE.md
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        original_content = "# Old content"
        claude_md.write_text(original_content)

        # Create venv
        venv_dir = tmp_path / ".venv" / "bin"
        venv_dir.mkdir(parents=True)
        (venv_dir / "python3").touch()

        config = get_default_config()
        config['venv'] = {'auto_detect': True}

        with patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            _generate_project_claude_md_if_missing(config)

        # BUG-021: File content should be unchanged
        assert claude_md.read_text() == original_content


class TestAC2FreshProjectUnchanged:
    """AC2: Fresh project (no existing CLAUDE.md) works as before."""

    def test_no_backup_when_no_existing_file(self, tmp_path):
        """No backup file created when CLAUDE.md doesn't exist."""
        from pactkit.config import get_default_config
        from pactkit.generators.deployer import _generate_project_claude_md_if_missing

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # Create venv
        venv_dir = tmp_path / ".venv" / "bin"
        venv_dir.mkdir(parents=True)
        (venv_dir / "python3").touch()

        config = get_default_config()
        config['venv'] = {'auto_detect': True}

        with patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            _generate_project_claude_md_if_missing(config)

        # Verify no backup exists
        backup_file = claude_dir / "CLAUDE.md.bak"
        assert not backup_file.exists(), "No backup should be created for fresh project"

        # But CLAUDE.md should exist
        claude_md = claude_dir / "CLAUDE.md"
        assert claude_md.exists()


class TestAC3BackupOverwritesPrevious:
    """AC3: N/A - Backup behavior removed by BUG-021."""

    def test_previous_backup_overwritten(self, tmp_path):
        """BUG-021: No backup when existing file is skipped."""
        from pactkit.config import get_default_config
        from pactkit.generators.deployer import _generate_project_claude_md_if_missing

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # Create existing CLAUDE.md
        claude_md = claude_dir / "CLAUDE.md"
        current_content = "# Current content"
        claude_md.write_text(current_content)

        # Create old backup (should remain untouched)
        backup_file = claude_dir / "CLAUDE.md.bak"
        old_backup_content = "# Old backup - should remain"
        backup_file.write_text(old_backup_content)

        config = get_default_config()

        with patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            _generate_project_claude_md_if_missing(config)

        # BUG-021: File skipped, backup not touched
        assert claude_md.read_text() == current_content
        assert backup_file.read_text() == old_backup_content


class TestAC4NotificationPrinted:
    """AC4: N/A - No notification when file is skipped (BUG-021)."""

    def test_backup_notification_printed(self, tmp_path, capsys):
        """BUG-021: No notification when existing file is skipped."""
        from pactkit.config import get_default_config
        from pactkit.generators.deployer import _generate_project_claude_md_if_missing

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        original_content = "# Existing content"
        claude_md.write_text(original_content)

        config = get_default_config()

        with patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            _generate_project_claude_md_if_missing(config)

        captured = capsys.readouterr()
        # BUG-021: No backup notification when file is skipped
        assert "Backed up CLAUDE.md" not in captured.out
        # File should be unchanged
        assert claude_md.read_text() == original_content

    def test_no_notification_when_no_backup_needed(self, tmp_path, capsys):
        """No backup notification when file doesn't exist."""
        from pactkit.config import get_default_config
        from pactkit.generators.deployer import _generate_project_claude_md_if_missing

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        config = get_default_config()

        with patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            _generate_project_claude_md_if_missing(config)

        captured = capsys.readouterr()
        assert "Backed up" not in captured.out
