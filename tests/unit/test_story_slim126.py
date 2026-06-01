"""Tests for STORY-slim-126: codegraph sync code enforcement."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

from pactkit.lazy_visualize import codegraph_sync


class TestCodegraphSync:
    """AC2, AC3: codegraph_sync function behavior."""

    def test_skips_when_no_codegraph_dir(self, tmp_path: Path):
        """AC2: no .codegraph/ directory → no sync attempted."""
        synced, msg = codegraph_sync(tmp_path)
        assert synced is False
        assert "no .codegraph" in msg.lower() or "not found" in msg.lower()

    def test_skips_when_binary_missing(self, tmp_path: Path):
        """AC3: .codegraph/ exists but codegraph not on PATH."""
        (tmp_path / ".codegraph").mkdir()
        with patch("shutil.which", return_value=None):
            synced, msg = codegraph_sync(tmp_path)
        assert synced is False
        assert "not installed" in msg.lower()

    def test_runs_sync_when_available(self, tmp_path: Path):
        """AC1: .codegraph/ exists and codegraph on PATH → sync runs."""
        (tmp_path / ".codegraph").mkdir()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Synced 3 files\n"

        with patch("shutil.which", return_value="/usr/bin/codegraph"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                synced, msg = codegraph_sync(tmp_path)

        assert synced is True
        mock_run.assert_called_once_with(
            ["codegraph", "sync", str(tmp_path)],
            capture_output=True,
            text=True,
        )

    def test_returns_false_on_nonzero_exit(self, tmp_path: Path):
        """codegraph sync fails → returns (False, error message)."""
        (tmp_path / ".codegraph").mkdir()
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Lock file exists\n"

        with patch("shutil.which", return_value="/usr/bin/codegraph"):
            with patch("subprocess.run", return_value=mock_result):
                synced, msg = codegraph_sync(tmp_path)

        assert synced is False
        assert "failed" in msg.lower() or "lock" in msg.lower()


class TestVisualizeFunctionsCallSync:
    """AC1: run_visualize_graphs and run_visualize_single call codegraph_sync."""

    def test_run_visualize_graphs_calls_sync(self, tmp_path: Path):
        """After graph generation, codegraph_sync is called."""
        with patch("pactkit.lazy_visualize.codegraph_sync", return_value=(True, "synced")) as mock_sync:
            with patch("subprocess.run"):
                # visualize.py won't exist in tmp, so it returns early
                from pactkit.lazy_visualize import run_visualize_graphs
                run_visualize_graphs(tmp_path)

        mock_sync.assert_called_once_with(tmp_path)

    def test_run_visualize_single_calls_sync(self, tmp_path: Path):
        """After single-mode graph generation, codegraph_sync is called."""
        with patch("pactkit.lazy_visualize.codegraph_sync", return_value=(True, "synced")) as mock_sync:
            with patch("subprocess.run"):
                from pactkit.lazy_visualize import run_visualize_single
                run_visualize_single(tmp_path, "file")

        mock_sync.assert_called_once_with(tmp_path)


class TestPromptInstructionsRemoved:
    """AC5: prompt templates no longer contain codegraph sync instructions."""

    def test_no_codegraph_sync_instructions_in_commands(self):
        """commands.py should not have 'If .codegraph/ exists, run codegraph sync'."""
        from pactkit.prompts import commands
        import inspect
        source = inspect.getsource(commands)
        assert "If `.codegraph/` exists, run `codegraph sync`" not in source
        assert 'If `.codegraph/` exists, also run `codegraph sync`' not in source

    def test_no_raw_codegraph_sync_instruction_in_workflows(self):
        """workflows.py should not instruct to run `codegraph sync` directly."""
        from pactkit.prompts import workflows
        import inspect
        source = inspect.getsource(workflows)
        assert "run `codegraph sync`" not in source
        assert "If `.codegraph/` exists, run `codegraph sync`" not in source
