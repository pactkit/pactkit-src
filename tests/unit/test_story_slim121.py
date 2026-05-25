"""Tests for STORY-slim-121: call graph SQLite output with pactkit query CLI."""
import sqlite3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_path, sqlite_output=None):
    """Create a minimal project structure with optional pactkit.yaml."""
    graphs_dir = tmp_path / "docs" / "architecture" / "graphs"
    graphs_dir.mkdir(parents=True)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    if sqlite_output is not None:
        yaml_content = f"visualize:\n  sqlite_output: {'true' if sqlite_output else 'false'}\n"
        (claude_dir / "pactkit.yaml").write_text(yaml_content)
    return tmp_path


def _make_db(db_path, edges):
    """Create a call_graph.db with given edges list of (caller, callee)."""
    nodes = set()
    for caller, callee in edges:
        nodes.add(caller)
        nodes.add(callee)
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE nodes (id TEXT PRIMARY KEY, file TEXT, kind TEXT)")
    con.execute("CREATE TABLE edges (caller TEXT, callee TEXT)")
    con.execute("CREATE INDEX idx_callee ON edges(callee)")
    con.execute("CREATE INDEX idx_caller ON edges(caller)")
    con.executemany("INSERT INTO nodes VALUES (?, '', 'function')", [(n,) for n in nodes])
    con.executemany("INSERT INTO edges VALUES (?, ?)", edges)
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# R1: pactkit.yaml toggle
# ---------------------------------------------------------------------------

class TestSqliteConfig:
    def test_default_false_when_absent(self, tmp_path):
        """_load_sqlite_config returns False when pactkit.yaml has no sqlite_output."""
        from pactkit.skills.visualize import _load_sqlite_config
        _make_project(tmp_path, sqlite_output=None)
        assert _load_sqlite_config(tmp_path) is False

    def test_true_when_enabled(self, tmp_path):
        """_load_sqlite_config returns True when visualize.sqlite_output: true."""
        from pactkit.skills.visualize import _load_sqlite_config
        _make_project(tmp_path, sqlite_output=True)
        assert _load_sqlite_config(tmp_path) is True

    def test_false_when_disabled(self, tmp_path):
        """_load_sqlite_config returns False when visualize.sqlite_output: false."""
        from pactkit.skills.visualize import _load_sqlite_config
        _make_project(tmp_path, sqlite_output=False)
        assert _load_sqlite_config(tmp_path) is False

    def test_default_config_has_sqlite_output_false(self):
        """get_default_config includes visualize.sqlite_output = False."""
        from pactkit.config import get_default_config
        cfg = get_default_config()
        assert cfg["visualize"]["sqlite_output"] is False


# ---------------------------------------------------------------------------
# R2: _write_sqlite_db
# ---------------------------------------------------------------------------

class TestWriteSqliteDb:
    def test_creates_db_with_nodes_and_edges(self, tmp_path):
        """_write_sqlite_db creates call_graph.db with nodes and edges tables."""
        from pactkit.skills.visualize import _write_sqlite_db
        db_path = tmp_path / "call_graph.db"
        func_registry = {"mod.foo": "mod.py", "mod.bar": "mod.py"}
        rel_edges = [("mod.foo", "mod.bar")]
        _write_sqlite_db(db_path, func_registry, rel_edges)
        assert db_path.exists()
        con = sqlite3.connect(db_path)
        nodes = {r[0] for r in con.execute("SELECT id FROM nodes")}
        edges = list(con.execute("SELECT caller, callee FROM edges"))
        con.close()
        assert "mod.foo" in nodes
        assert "mod.bar" in nodes
        assert ("mod.foo", "mod.bar") in edges

    def test_atomic_write_no_partial_file(self, tmp_path):
        """_write_sqlite_db writes atomically — no .tmp leftover after success."""
        from pactkit.skills.visualize import _write_sqlite_db
        db_path = tmp_path / "call_graph.db"
        _write_sqlite_db(db_path, {"a.f": "a.py"}, [])
        assert db_path.exists()
        assert not (tmp_path / "call_graph.db.tmp").exists()

    def test_indexes_created(self, tmp_path):
        """_write_sqlite_db creates indexes on caller and callee columns."""
        from pactkit.skills.visualize import _write_sqlite_db
        db_path = tmp_path / "call_graph.db"
        _write_sqlite_db(db_path, {"a.f": "a.py", "b.g": "b.py"}, [("a.f", "b.g")])
        con = sqlite3.connect(db_path)
        indexes = {r[1] for r in con.execute("SELECT type, name FROM sqlite_master WHERE type='index'")}
        con.close()
        assert "idx_callee" in indexes
        assert "idx_caller" in indexes

    def test_overwrites_existing_db(self, tmp_path):
        """_write_sqlite_db replaces stale db on re-run."""
        from pactkit.skills.visualize import _write_sqlite_db
        db_path = tmp_path / "call_graph.db"
        _write_sqlite_db(db_path, {"a.f": "a.py"}, [])
        _write_sqlite_db(db_path, {"b.g": "b.py"}, [])
        con = sqlite3.connect(db_path)
        nodes = {r[0] for r in con.execute("SELECT id FROM nodes")}
        con.close()
        assert "b.g" in nodes
        assert "a.f" not in nodes  # old data replaced


# ---------------------------------------------------------------------------
# R1 AC1: default mode writes no .db
# ---------------------------------------------------------------------------

class TestBuildCallGraphNoSqlite:
    def test_no_db_when_sqlite_disabled(self, tmp_path):
        """_build_call_graph does not create .db when sqlite_output is false."""
        from pactkit.skills.visualize import _build_call_graph
        _make_project(tmp_path, sqlite_output=False)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo():\n    bar()\ndef bar():\n    pass\n")
        _build_call_graph(tmp_path, [src / "mod.py"], focus=None, entry=None)
        db_path = tmp_path / "docs" / "architecture" / "graphs" / "call_graph.db"
        assert not db_path.exists()


# ---------------------------------------------------------------------------
# R2 AC2: db written when enabled
# ---------------------------------------------------------------------------

class TestBuildCallGraphWithSqlite:
    def test_db_written_when_enabled(self, tmp_path):
        """_build_call_graph writes call_graph.db when sqlite_output is true."""
        from pactkit.skills.visualize import _build_call_graph
        _make_project(tmp_path, sqlite_output=True)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo():\n    bar()\ndef bar():\n    pass\n")
        _build_call_graph(tmp_path, [src / "mod.py"], focus=None, entry=None)
        db_path = tmp_path / "docs" / "architecture" / "graphs" / "call_graph.db"
        assert db_path.exists()

    def test_db_edge_count_matches_resolved_edges(self, tmp_path):
        """db edge count matches resolved edges in the call graph."""
        from pactkit.skills.visualize import _build_call_graph
        _make_project(tmp_path, sqlite_output=True)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "def foo():\n    bar()\n    baz()\ndef bar():\n    pass\ndef baz():\n    pass\n"
        )
        _build_call_graph(tmp_path, [src / "mod.py"], focus=None, entry=None)
        db_path = tmp_path / "docs" / "architecture" / "graphs" / "call_graph.db"
        con = sqlite3.connect(db_path)
        count = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        con.close()
        assert count >= 2  # foo→bar and foo→baz resolved


# ---------------------------------------------------------------------------
# R4: pactkit query CLI
# ---------------------------------------------------------------------------

class TestPactKitQueryCLI:
    def _run_query(self, args_list, db_path=None, tmp_path=None):
        """Run pactkit query via CLI entry point, return (stdout, exit_code)."""
        import io
        from unittest.mock import patch as _patch
        captured = io.StringIO()
        exit_code = 0
        with _patch("sys.stdout", captured):
            with _patch("sys.argv", ["pactkit", "query"] + args_list):
                if tmp_path:
                    with _patch("pathlib.Path.cwd", return_value=tmp_path):
                        try:
                            from pactkit.cli import main
                            main()
                        except SystemExit as e:
                            exit_code = e.code or 0
                else:
                    try:
                        from pactkit.cli import main
                        main()
                    except SystemExit as e:
                        exit_code = e.code or 0
        return captured.getvalue(), exit_code

    def test_callers_fan_in(self, tmp_path):
        """pactkit query --callers B returns all callers of B."""
        db_path = tmp_path / "docs" / "architecture" / "graphs" / "call_graph.db"
        db_path.parent.mkdir(parents=True)
        _make_db(db_path, [("A", "B"), ("C", "B"), ("D", "E")])
        import io
        from unittest.mock import patch as _patch
        captured = io.StringIO()
        err_captured = io.StringIO()
        with _patch("sys.stdout", captured), _patch("sys.stderr", err_captured):
            with _patch("sys.argv", ["pactkit", "query", "--callers", "B"]):
                with _patch("pathlib.Path.cwd", return_value=tmp_path):
                    try:
                        from pactkit.cli import main
                        main()
                    except SystemExit:
                        pass
        output = captured.getvalue()
        assert "A" in output
        assert "C" in output
        assert "D" not in output

    def test_callees_fan_out(self, tmp_path):
        """pactkit query --callees A returns all callees of A."""
        db_path = tmp_path / "docs" / "architecture" / "graphs" / "call_graph.db"
        db_path.parent.mkdir(parents=True)
        _make_db(db_path, [("A", "B"), ("A", "C"), ("D", "E")])
        import io
        from unittest.mock import patch as _patch
        captured = io.StringIO()
        with _patch("sys.stdout", captured), _patch("sys.stderr", io.StringIO()):
            with _patch("sys.argv", ["pactkit", "query", "--callees", "A"]):
                with _patch("pathlib.Path.cwd", return_value=tmp_path):
                    try:
                        from pactkit.cli import main
                        main()
                    except SystemExit:
                        pass
        output = captured.getvalue()
        assert "B" in output
        assert "C" in output
        assert "E" not in output

    def test_chain_upstream_transitive(self, tmp_path):
        """pactkit query --chain C returns all upstream callers (A→B→C)."""
        db_path = tmp_path / "docs" / "architecture" / "graphs" / "call_graph.db"
        db_path.parent.mkdir(parents=True)
        _make_db(db_path, [("A", "B"), ("B", "C")])
        import io
        from unittest.mock import patch as _patch
        captured = io.StringIO()
        with _patch("sys.stdout", captured), _patch("sys.stderr", io.StringIO()):
            with _patch("sys.argv", ["pactkit", "query", "--chain", "C"]):
                with _patch("pathlib.Path.cwd", return_value=tmp_path):
                    try:
                        from pactkit.cli import main
                        main()
                    except SystemExit:
                        pass
        output = captured.getvalue()
        assert "A" in output
        assert "B" in output

    def test_chain_downstream_transitive(self, tmp_path):
        """pactkit query --chain A --down returns all downstream callees (A→B→C)."""
        db_path = tmp_path / "docs" / "architecture" / "graphs" / "call_graph.db"
        db_path.parent.mkdir(parents=True)
        _make_db(db_path, [("A", "B"), ("B", "C")])
        import io
        from unittest.mock import patch as _patch
        captured = io.StringIO()
        with _patch("sys.stdout", captured), _patch("sys.stderr", io.StringIO()):
            with _patch("sys.argv", ["pactkit", "query", "--chain", "A", "--down"]):
                with _patch("pathlib.Path.cwd", return_value=tmp_path):
                    try:
                        from pactkit.cli import main
                        main()
                    except SystemExit:
                        pass
        output = captured.getvalue()
        assert "B" in output
        assert "C" in output

    def test_missing_db_exits_with_error(self, tmp_path):
        """pactkit query exits 1 with helpful message when call_graph.db missing."""
        import io
        from unittest.mock import patch as _patch
        err_captured = io.StringIO()
        exit_code = 0
        with _patch("sys.stdout", io.StringIO()), _patch("sys.stderr", err_captured):
            with _patch("sys.argv", ["pactkit", "query", "--callers", "foo"]):
                with _patch("pathlib.Path.cwd", return_value=tmp_path):
                    try:
                        from pactkit.cli import main
                        main()
                    except SystemExit as e:
                        exit_code = e.code
        assert exit_code == 1
        err_output = err_captured.getvalue()
        assert "sqlite_output" in err_output or "visualize" in err_output
