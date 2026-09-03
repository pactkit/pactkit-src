"""HOTFIX 2026-09-03: `pactkit visualize --lazy` must sync codegraph.

The Act Phase 4 doc promise "codegraph sync is handled automatically" was
never wired: the skip path required an explicit --sync flag nobody passed,
and the run path (run_visualize_graphs) had no sync call at all — the db
went silently stale after every source change. Both paths now sync.
"""

import subprocess
import sys
from pathlib import Path


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (root / ".claude").mkdir()
    (root / ".claude" / "pactkit.yaml").write_text("stack: python\n", encoding="utf-8")
    (root / ".codegraph").mkdir()
    (root / ".codegraph" / "codegraph.db").write_bytes(b"")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, env={
        **__import__("os").environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    })
    subprocess.run(["git", "commit", "-qm", "init"], cwd=root, check=True, env={
        **__import__("os").environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    })
    return root


class TestVisualizeSyncsCodegraph:
    def test_skip_path_syncs_without_flag(self, tmp_path, monkeypatch):
        """No source changes (lazy skip) — codegraph sync STILL runs."""
        import pactkit.lazy_visualize as lv

        root = _project(tmp_path)
        calls = []
        monkeypatch.setattr(lv, "codegraph_sync", lambda r: calls.append(r) or (True, "synced"))
        proc = subprocess.run(
            [sys.executable, "-m", "pactkit", "-C", str(root), "visualize", "--lazy"],
            cwd=root, capture_output=True, text=True, timeout=60,
        )
        assert "up-to-date" in proc.stdout.lower() or proc.returncode == 0
        # The CLI imports codegraph_sync inside the handler; the monkeypatch
        # above covers same-process calls — for subprocess, assert via the
        # observable: the fixed CLI prints the sync line.
        assert "synced" in proc.stdout or "codegraph" in proc.stdout or calls

    def test_run_path_syncs_after_graphs(self, tmp_path):
        """Source changed (lazy runs graphs) — codegraph sync runs too."""
        root = _project(tmp_path)
        (root / "src" / "mod.py").write_text("x = 2\n", encoding="utf-8")
        (root / "docs" / "architecture" / "graphs").mkdir(parents=True)
        (root / "docs" / "architecture" / "graphs" / "code_graph.mmd").write_text(
            "graph TD\n", encoding="utf-8",
        )
        proc = subprocess.run(
            [sys.executable, "-m", "pactkit", "-C", str(root), "visualize", "--lazy"],
            cwd=root, capture_output=True, text=True, timeout=120,
        )
        # skip-path prints reason; run path regenerates then syncs — either
        # way the fix guarantees a sync attempt, visible as the 🔄 line or
        # the "skipped"/"not installed" codegraph message (fake env has no
        # codegraph binary — the message proves the call happened).
        combined = proc.stdout + proc.stderr
        assert "codegraph" in combined.lower(), (
            f"no codegraph activity in output: {combined[:300]}"
        )
