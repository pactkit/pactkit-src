"""Tests for BUG-020: CLAUDE.md backup and regenerate strategy.

AC1: Existing file backed up
AC2: Fresh project unchanged
AC3: Backup overwrites previous backup
AC4: Notification printed
"""
import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestAC1ExistingFileBackedUp:
    """AC1: Existing CLAUDE.md is backed up before regeneration."""

    def test_backup_created_when_file_exists(self, tmp_path):
        """Backup file created when CLAUDE.md exists."""
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

        # Verify backup was created
        backup_file = claude_dir / "CLAUDE.md.bak"
        assert backup_file.exists(), "Backup file should be created"
        assert backup_file.read_text() == original_content

    def test_new_claude_md_has_venv_section(self, tmp_path):
        """After backup, new CLAUDE.md contains venv section."""
        from pactkit.config import get_default_config
        from pactkit.generators.deployer import _generate_project_claude_md_if_missing

        # Create existing CLAUDE.md
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text("# Old content")

        # Create venv
        venv_dir = tmp_path / ".venv" / "bin"
        venv_dir.mkdir(parents=True)
        (venv_dir / "python3").touch()

        config = get_default_config()
        config['venv'] = {'auto_detect': True}

        with patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            _generate_project_claude_md_if_missing(config)

        # Verify new file has venv section
        new_content = claude_md.read_text()
        assert "## Virtual Environment" in new_content
        assert ".venv/bin/python3" in new_content


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
    """AC3: Backup overwrites previous backup."""

    def test_previous_backup_overwritten(self, tmp_path):
        """Previous .bak file is overwritten."""
        from pactkit.config import get_default_config
        from pactkit.generators.deployer import _generate_project_claude_md_if_missing

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # Create existing CLAUDE.md
        claude_md = claude_dir / "CLAUDE.md"
        current_content = "# Current content"
        claude_md.write_text(current_content)

        # Create old backup
        backup_file = claude_dir / "CLAUDE.md.bak"
        backup_file.write_text("# Old backup - should be replaced")

        config = get_default_config()

        with patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            _generate_project_claude_md_if_missing(config)

        # Verify backup contains current content, not old backup
        assert backup_file.read_text() == current_content


class TestAC4NotificationPrinted:
    """AC4: Notification printed when backup is created."""

    def test_backup_notification_printed(self, tmp_path, capsys):
        """Backup notification appears in output."""
        from pactkit.config import get_default_config
        from pactkit.generators.deployer import _generate_project_claude_md_if_missing

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text("# Existing content")

        config = get_default_config()

        with patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            _generate_project_claude_md_if_missing(config)

        captured = capsys.readouterr()
        assert "Backed up CLAUDE.md" in captured.out or "CLAUDE.md.bak" in captured.out

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
