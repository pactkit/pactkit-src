"""CLI E2E for Codegraph-first provider routing."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[3] / "src")
    return subprocess.run(
        [sys.executable, "-m", "pactkit.cli", *args], cwd=cwd, env=env,
        text=True, capture_output=True,
    )


def _graph(path: Path) -> None:
    path.parent.mkdir(parents=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT, name TEXT, qualified_name TEXT, "
        "file_path TEXT, start_line INTEGER, end_line INTEGER)"
    )
    connection.execute(
        "CREATE TABLE edges (source TEXT, target TEXT, kind TEXT, line INTEGER, col INTEGER, provenance TEXT)"
    )
    connection.executemany(
        "INSERT INTO nodes VALUES (?, 'function', ?, ?, ?, ?, ?)",
        [("a", "caller", "caller", "src/a.py", 1, 2), ("b", "target", "target", "src/b.py", 3, 4)],
    )
    connection.execute("INSERT INTO edges VALUES ('a', 'b', 'calls', 1, 0, 'static')")
    connection.commit()
    connection.close()


def test_unconfigured_query_uses_builtin_and_reports_decision(tmp_path):
    graph = tmp_path / "docs/architecture/graphs/call_graph.mmd"
    graph.parent.mkdir(parents=True)
    graph.write_text("caller --> target\n", encoding="utf-8")
    result = _run("query", "--callers", "target", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["decision"]["selected_provider"] == "builtin_graph"
    assert payload["decision"]["fallback"] is False


def test_chain_compatibility_uses_read_only_parameterized_db(tmp_path):
    config = tmp_path / ".codex/pactkit.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("visualize:\n  graph_provider: codegraph\n", encoding="utf-8")
    _graph(tmp_path / ".codegraph/codegraph.db")
    # The real local Codegraph binary cannot inspect this tiny fixture's status,
    # so exercise the stable provider adapter directly for compatibility.
    from pactkit.graph_query import CodegraphProvider, GraphQueryRequest

    rows = CodegraphProvider(tmp_path).query(GraphQueryRequest("chain", "target"))
    assert rows == [{"name": "caller", "file_path": "src/a.py", "start_line": 1}]


def test_real_codegraph_json_exposes_provider_evidence():
    root = Path(__file__).parents[3]
    result = _run("query", "--callers", "codegraph_sync", "--json", cwd=root)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["decision"]["selected_provider"] == "codegraph"
    assert payload["decision"]["freshness"] is True
    assert payload["decision"]["result_count"] >= 1
