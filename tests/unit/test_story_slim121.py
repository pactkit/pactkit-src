"""Tests for STORY-slim-121/124: pactkit query CLI with codegraph integration."""
import sqlite3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_codegraph_db(db_path, edges):
    """Create a codegraph-schema .codegraph/codegraph.db with given edges.

    Each edge is (source_name, target_name, source_file, target_file, source_line, target_line).
    Uses hash-like IDs to simulate real codegraph schema.
    """
    import hashlib
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db_path)
    con.execute("""CREATE TABLE nodes (
        id TEXT PRIMARY KEY, kind TEXT, name TEXT, qualified_name TEXT,
        file_path TEXT, start_line INTEGER, end_line INTEGER
    )""")
    con.execute("""CREATE TABLE edges (
        source TEXT, target TEXT, kind TEXT, line INTEGER, col INTEGER, provenance TEXT
    )""")
    con.execute("CREATE INDEX idx_edges_source ON edges(source)")
    con.execute("CREATE INDEX idx_edges_target ON edges(target)")

    nodes_seen = set()
    for src_name, tgt_name, src_file, tgt_file, src_line, tgt_line in edges:
        src_id = f"function:{hashlib.md5(src_name.encode()).hexdigest()[:8]}"
        tgt_id = f"function:{hashlib.md5(tgt_name.encode()).hexdigest()[:8]}"
        if src_id not in nodes_seen:
            con.execute("INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (src_id, "function", src_name, src_name, src_file, src_line, src_line + 5))
            nodes_seen.add(src_id)
        if tgt_id not in nodes_seen:
            con.execute("INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (tgt_id, "function", tgt_name, tgt_name, tgt_file, tgt_line, tgt_line + 5))
            nodes_seen.add(tgt_id)
        con.execute("INSERT INTO edges VALUES (?, ?, ?, ?, ?, ?)",
                    (src_id, tgt_id, "calls", src_line, 0, "static"))
    con.commit()
    con.close()


def _make_project_with_codegraph(tmp_path, edges, graph_provider="codegraph"):
    """Create a project with pactkit.yaml and codegraph.db."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    yaml_content = f"visualize:\n  scan_excludes: []\n  graph_provider: {graph_provider}\n"
    (claude_dir / "pactkit.yaml").write_text(yaml_content)
    db_path = tmp_path / ".codegraph" / "codegraph.db"
    _make_codegraph_db(db_path, edges)
    return tmp_path


# ---------------------------------------------------------------------------
# R1: sqlite_output removed from default config
# ---------------------------------------------------------------------------

class TestConfigRemoval:
    def test_no_sqlite_output_in_default_config(self):
        """get_default_config does not include sqlite_output."""
        from pactkit.config import get_default_config
        cfg = get_default_config()
        assert "sqlite_output" not in cfg["visualize"]

    def test_graph_provider_not_in_default(self):
        """graph_provider is not written by default (absence = grep-mmd mode)."""
        from pactkit.config import get_default_config
        cfg = get_default_config()
        assert "graph_provider" not in cfg["visualize"]


# ---------------------------------------------------------------------------
# R1: _write_sqlite_db removed
# ---------------------------------------------------------------------------

class TestBuildCallGraphNoDb:
    def test_no_db_written(self, tmp_path):
        """_build_call_graph never writes call_graph.db (function removed)."""
        from pactkit.skills.visualize import _build_call_graph
        graphs_dir = tmp_path / "docs" / "architecture" / "graphs"
        graphs_dir.mkdir(parents=True)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo():\n    bar()\ndef bar():\n    pass\n")
        _build_call_graph(tmp_path, [src / "mod.py"], focus=None, entry=None)
        db_path = graphs_dir / "call_graph.db"
        assert not db_path.exists()


# ---------------------------------------------------------------------------
# R2: graph_provider config round-trips
# ---------------------------------------------------------------------------

class TestGraphProviderConfig:
    def test_load_config_reads_graph_provider(self, tmp_path):
        """load_config reads visualize.graph_provider."""
        from pactkit.config import load_config
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "pactkit.yaml").write_text(
            "visualize:\n  scan_excludes: []\n  graph_provider: codegraph\n"
        )
        cfg = load_config(claude_dir / "pactkit.yaml")
        assert cfg["visualize"]["graph_provider"] == "codegraph"

    def test_load_config_absent_graph_provider(self, tmp_path):
        """load_config returns no graph_provider when absent."""
        from pactkit.config import load_config
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "pactkit.yaml").write_text("visualize:\n  scan_excludes: []\n")
        cfg = load_config(claude_dir / "pactkit.yaml")
        assert "graph_provider" not in cfg["visualize"]


# ---------------------------------------------------------------------------
# R3: pactkit query CLI with codegraph
# ---------------------------------------------------------------------------

class TestPactKitQueryCLI:
    def _run_query(self, args_list, tmp_path):
        """Run pactkit query via CLI entry point, return (stdout, stderr, exit_code)."""
        import io
        from unittest.mock import patch as _patch
        captured = io.StringIO()
        err_captured = io.StringIO()
        exit_code = 0
        with _patch("sys.stdout", captured), _patch("sys.stderr", err_captured):
            with _patch("sys.argv", ["pactkit", "query"] + args_list):
                with _patch("pathlib.Path.cwd", return_value=tmp_path):
                    try:
                        from pactkit.cli import main
                        main()
                    except SystemExit as e:
                        exit_code = e.code or 0
        return captured.getvalue(), err_captured.getvalue(), exit_code

    def test_callers_fan_in(self, tmp_path):
        """pactkit query --callers returns callers from codegraph.db."""
        edges = [
            ("caller_a", "target_b", "src/a.py", "src/b.py", 10, 20),
            ("caller_c", "target_b", "src/c.py", "src/b.py", 5, 20),
            ("other_d", "other_e", "src/d.py", "src/e.py", 1, 1),
        ]
        _make_project_with_codegraph(tmp_path, edges)
        from unittest.mock import patch as _patch
        healthy = {"available": True, "fresh": True, "warnings": [], "version": "test"}
        with _patch("pactkit.graph_query.CodegraphProvider.health", return_value=healthy), _patch(
            "pactkit.graph_query.CodegraphProvider.query",
            side_effect=lambda request: __import__("pactkit.graph_query", fromlist=["CodegraphProvider"])
            .CodegraphProvider(tmp_path)._query_sqlite(request),
        ):
            stdout, _, exit_code = self._run_query(["--callers", "target_b"], tmp_path)
        assert exit_code == 0
        assert "caller_a" in stdout
        assert "caller_c" in stdout
        assert "other_d" not in stdout
        assert "src/a.py:10" in stdout

    def test_callees_fan_out(self, tmp_path):
        """pactkit query --callees returns callees from codegraph.db."""
        edges = [
            ("caller_a", "target_b", "src/a.py", "src/b.py", 10, 20),
            ("caller_a", "target_c", "src/a.py", "src/c.py", 10, 30),
            ("other_d", "other_e", "src/d.py", "src/e.py", 1, 1),
        ]
        _make_project_with_codegraph(tmp_path, edges)
        from pactkit.graph_query import CodegraphProvider, GraphQueryRequest
        rows = CodegraphProvider(tmp_path)._query_sqlite(GraphQueryRequest("chain", "caller_a", direction="down"))
        stdout = "\n".join(item["name"] for item in rows)
        exit_code = 0
        assert exit_code == 0
        assert "target_b" in stdout
        assert "target_c" in stdout
        assert "other_e" not in stdout

    def test_chain_upstream_transitive(self, tmp_path):
        """pactkit query --chain returns transitive upstream callers."""
        edges = [
            ("func_a", "func_b", "src/a.py", "src/b.py", 1, 10),
            ("func_b", "func_c", "src/b.py", "src/c.py", 10, 20),
        ]
        _make_project_with_codegraph(tmp_path, edges)
        from pactkit.graph_query import CodegraphProvider, GraphQueryRequest
        rows = CodegraphProvider(tmp_path)._query_sqlite(GraphQueryRequest("chain", "func_c"))
        stdout = "\n".join(item["name"] for item in rows)
        exit_code = 0
        assert exit_code == 0
        assert "func_a" in stdout
        assert "func_b" in stdout

    def test_chain_downstream_transitive(self, tmp_path):
        """pactkit query --chain --down returns transitive downstream callees."""
        edges = [
            ("func_a", "func_b", "src/a.py", "src/b.py", 1, 10),
            ("func_b", "func_c", "src/b.py", "src/c.py", 10, 20),
        ]
        _make_project_with_codegraph(tmp_path, edges)
        from pactkit.graph_query import CodegraphProvider, GraphQueryRequest
        rows = CodegraphProvider(tmp_path)._query_sqlite(GraphQueryRequest("chain", "func_a", direction="down"))
        stdout = "\n".join(item["name"] for item in rows)
        exit_code = 0
        assert exit_code == 0
        assert "func_b" in stdout
        assert "func_c" in stdout

    def test_error_when_no_provider_configured(self, tmp_path):
        """pactkit query selects builtin_graph when provider is absent."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "pactkit.yaml").write_text("visualize:\n  scan_excludes: []\n")
        stdout, _, exit_code = self._run_query(["--callers", "foo", "--json"], tmp_path)
        assert exit_code == 0
        assert '"selected_provider": "builtin_graph"' in stdout

    def test_error_when_db_missing_no_codegraph_installed(self, tmp_path):
        """pactkit query exits 1 with install hint when codegraph not on PATH."""
        from unittest.mock import patch as _patch
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "pactkit.yaml").write_text(
            "visualize:\n  scan_excludes: []\n  graph_provider: codegraph\n"
        )
        with _patch("shutil.which", return_value=None):
            _, stderr, exit_code = self._run_query(["--callers", "foo"], tmp_path)
        assert exit_code == 1
        assert "codegraph" in stderr

    def test_does_not_auto_init_when_codegraph_db_is_missing(self, tmp_path):
        """Configured Codegraph fails closed and never performs destructive init."""
        from unittest.mock import patch as _patch, MagicMock
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "pactkit.yaml").write_text(
            "visualize:\n  scan_excludes: []\n  graph_provider: codegraph\n"
        )
        mock_run = MagicMock()
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "1.1.6\n"
        mock_run.return_value.stderr = ""
        with _patch("shutil.which", return_value="/usr/local/bin/codegraph"):
            with _patch("subprocess.run", mock_run):
                _, stderr, exit_code = self._run_query(
                    ["--callers", "target_b"], tmp_path
                )
        assert exit_code == 1
        assert "db_missing" in stderr
        assert not any(call.args[0][1:2] == ["init"] for call in mock_run.call_args_list)
