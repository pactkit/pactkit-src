"""STORY-slim-149: Codegraph-first graph provider routing."""

from pathlib import Path
import subprocess
import threading
import time

import pytest


class FakeProvider:
    def __init__(self, name, *, health=None, sync_result=None, result=None):
        self.name = name
        self.health_result = health or {"available": True, "fresh": True, "warnings": []}
        self.sync_result = sync_result
        self.result = result or []
        self.calls = []

    def health(self):
        self.calls.append("health")
        return self.health_result

    def sync(self):
        self.calls.append("sync")
        return self.sync_result or self.health_result

    def query(self, request):
        self.calls.append(("query", request.kind, request.target))
        return self.result


def test_codegraph_is_mandatory_when_configured():
    from pactkit.graph_query import GraphProviderRouter, GraphQueryRequest

    codegraph = FakeProvider("codegraph", result=[])
    builtin = FakeProvider("builtin_graph", result=[{"name": "wrong"}])
    result = GraphProviderRouter({"codegraph": codegraph, "builtin_graph": builtin}).query(
        GraphQueryRequest("callers", "missing"), configured_provider="codegraph"
    )
    assert result.status == "valid_empty"
    assert result.decision.selected_provider == "codegraph"
    assert builtin.calls == []


def test_failure_is_closed_unless_fallback_is_explicit():
    from pactkit.graph_query import GraphProviderError, GraphProviderRouter, GraphQueryRequest

    broken = FakeProvider("codegraph", health={"available": False, "fresh": False, "reason": "binary_missing"})
    builtin = FakeProvider("builtin_graph", result=[{"name": "fallback"}])
    router = GraphProviderRouter({"codegraph": broken, "builtin_graph": builtin})
    request = GraphQueryRequest("callers", "foo")
    try:
        router.query(request, configured_provider="codegraph")
    except GraphProviderError as exc:
        assert exc.reason_code == "binary_missing"
    else:
        raise AssertionError("configured Codegraph failure must fail closed")
    result = router.query(request, configured_provider="codegraph", allow_fallback=True)
    assert result.decision.selected_provider == "builtin_graph"
    assert result.decision.fallback_reason == "binary_missing"


def test_stale_index_syncs_once_and_exposes_old_engine_warning():
    from pactkit.graph_query import GraphProviderRouter, GraphQueryRequest

    provider = FakeProvider(
        "codegraph",
        health={"available": True, "fresh": False, "warnings": ["index_old_engine"]},
        sync_result={"available": True, "fresh": True, "warnings": ["index_old_engine"]},
        result=[{"name": "caller"}],
    )
    result = GraphProviderRouter({"codegraph": provider}).query(
        GraphQueryRequest("callers", "foo"), configured_provider="codegraph"
    )
    assert provider.calls.count("sync") == 1
    assert "index_old_engine" in result.decision.warnings


def test_stale_index_that_remains_stale_after_sync_fails_closed():
    from pactkit.graph_query import GraphProviderError, GraphProviderRouter, GraphQueryRequest

    provider = FakeProvider(
        "codegraph",
        health={"available": True, "fresh": False, "reason": "index_stale", "warnings": []},
    )
    router = GraphProviderRouter({"codegraph": provider})

    with pytest.raises(GraphProviderError) as exc_info:
        router.query(GraphQueryRequest("callers", "foo"), configured_provider="codegraph")

    assert exc_info.value.reason_code == "sync_incomplete"
    assert provider.calls.count("sync") == 1
    assert not any(isinstance(call, tuple) and call[0] == "query" for call in provider.calls)


def test_unconfigured_project_uses_builtin_without_error():
    from pactkit.graph_query import GraphProviderRouter, GraphQueryRequest

    builtin = FakeProvider("builtin_graph", result=[])
    result = GraphProviderRouter({"builtin_graph": builtin}).query(
        GraphQueryRequest("impact", "foo"), configured_provider=None
    )
    assert result.decision.selected_provider == "builtin_graph"
    assert result.status == "valid_empty"


def test_codegraph_provider_reports_real_index_status():
    from pactkit.graph_query import CodegraphProvider

    provider = CodegraphProvider(Path.cwd())
    health = provider.health()
    assert health["available"] is True
    assert health["version"]
    if not health["fresh"]:
        health = provider.sync()
    assert health["fresh"] is True


def test_codegraph_db_override_must_stay_inside_project_index(tmp_path):
    from pactkit.graph_query import CodegraphProvider

    outside = tmp_path.parent / "outside-codegraph.db"
    outside.write_bytes(b"not a database")

    with pytest.raises(ValueError, match="project .codegraph directory"):
        CodegraphProvider(tmp_path, db_path=outside)

    inside = tmp_path / ".codegraph" / "alternate.db"
    provider = CodegraphProvider(tmp_path, db_path=inside)
    assert provider.db_path == inside.resolve()


def test_explicit_fallback_uses_text_search_after_builtin_failure():
    from pactkit.graph_query import GraphProviderRouter, GraphQueryRequest

    codegraph = FakeProvider(
        "codegraph",
        health={"available": False, "fresh": False, "reason": "db_missing"},
    )
    builtin = FakeProvider(
        "builtin_graph",
        health={"available": False, "fresh": False, "reason": "graph_missing"},
    )
    text_search = FakeProvider("text_search", result=[{"path": "src/a.py", "line": 4}])
    result = GraphProviderRouter({
        "codegraph": codegraph, "builtin_graph": builtin, "text_search": text_search,
    }).query(
        GraphQueryRequest("callers", "target"),
        configured_provider="codegraph",
        allow_fallback=True,
    )
    assert result.decision.selected_provider == "text_search"
    assert result.decision.fallback_chain == ["codegraph", "builtin_graph", "text_search"]
    assert result.decision.fallback_reason == "db_missing"


def test_text_search_provider_returns_normalized_bounded_results(tmp_path, monkeypatch):
    from pactkit.graph_query import GraphQueryRequest, TextSearchProvider

    monkeypatch.setattr("pactkit.graph_query.shutil.which", lambda command: "/usr/bin/rg")
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        return subprocess.CompletedProcess(
            command, 0,
            stdout="src/a.py:4:target()\nsrc/b.py:9:target()\n", stderr="",
        )

    monkeypatch.setattr("pactkit.graph_query.subprocess.run", fake_run)
    results = TextSearchProvider(tmp_path).query(GraphQueryRequest("callers", "target", limit=1))
    assert results == [{"path": "src/a.py", "line": 4, "text": "target()"}]
    assert observed["command"][-2:] == ["--", "target"]
    assert "--fixed-strings" in observed["command"]


def test_concurrent_stale_sync_is_serialized_and_second_rechecks_health(tmp_path, monkeypatch):
    from pactkit.graph_query import CodegraphProvider

    state = {"fresh": False, "syncs": 0}
    entered = threading.Event()

    def fake_health(self):
        return {"available": True, "fresh": state["fresh"], "reason": "ok", "warnings": []}

    def fake_run(self, *args):
        assert args[0] == "sync"
        state["syncs"] += 1
        entered.set()
        time.sleep(0.05)
        state["fresh"] = True
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(CodegraphProvider, "health", fake_health)
    monkeypatch.setattr(CodegraphProvider, "_run", fake_run)
    providers = [CodegraphProvider(tmp_path), CodegraphProvider(tmp_path)]
    results = []
    first = threading.Thread(target=lambda: results.append(providers[0].sync()))
    second = threading.Thread(target=lambda: results.append(providers[1].sync()))
    first.start()
    assert entered.wait(timeout=1)
    second.start()
    first.join(timeout=2)
    second.join(timeout=2)
    assert state["syncs"] == 1
    assert len(results) == 2
    assert all(result["fresh"] for result in results)


def _configured_codegraph_project(root):
    config = root / ".codex/pactkit.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("visualize:\n  graph_provider: codegraph\n", encoding="utf-8")


@pytest.mark.parametrize(
    "validator_factory,step",
    [("plan", "archaeology"), ("act", "preflight")],
)
def test_plan_and_act_reject_missing_or_forged_provider_evidence(tmp_path, validator_factory, step):
    from pactkit.workflow_validators import (
        WorkflowEvidenceError, act_validator, plan_validator,
    )

    _configured_codegraph_project(tmp_path)
    validator = plan_validator(tmp_path) if validator_factory == "plan" else act_validator(tmp_path)
    state = {"story_id": "STORY-slim-149"}
    base = {"trace": ["src/pactkit/graph_query.py:GraphProviderRouter"]} if step == "archaeology" else {}
    with pytest.raises(WorkflowEvidenceError, match="provider evidence"):
        validator.validate(state, step, base, "in_progress")
    forged = {
        **base,
        "graph_provider": {
            "requested_provider": "codegraph",
            "selected_provider": "builtin_graph",
            "freshness": True,
            "fallback": True,
        },
    }
    with pytest.raises(WorkflowEvidenceError, match="fallback evidence"):
        validator.validate(state, step, forged, "in_progress")


def test_legacy_act_checkpoint_enforces_configured_provider_evidence(tmp_path):
    from pactkit.continuation import ContinuationError, ContinuationStore

    story_id = "STORY-slim-149"
    _configured_codegraph_project(tmp_path)
    spec = tmp_path / "docs/specs" / f"{story_id}.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        f"# {story_id}\n\n| Field | Value |\n|---|---|\n"
        f"| ID | {story_id} |\n| Status | Draft |\n| Priority | P0 |\n| Release | 2.21.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\n\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n\n"
        "- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n| SEC-1 | N/A | test |\n",
        encoding="utf-8",
    )

    with pytest.raises(ContinuationError, match="provider evidence"):
        ContinuationStore(tmp_path).checkpoint(
            story_id, step_id="preflight", evidence={"spec_lint": "pass"},
        )


def test_authorized_fallback_provider_evidence_is_accepted(tmp_path):
    from pactkit.workflow_validators import plan_validator

    _configured_codegraph_project(tmp_path)
    plan_validator(tmp_path).validate(
        {"story_id": "STORY-slim-149"},
        "archaeology",
        {
            "trace": ["src/pactkit/graph_query.py:GraphProviderRouter"],
            "graph_provider": {
                "requested_provider": "codegraph",
                "selected_provider": "text_search",
                "availability": True,
                "freshness": True,
                "query_kind": "explore",
                "query_target": "GraphProviderRouter",
                "result_count": 1,
                "fallback": True,
                "fallback_reason": "db_missing",
                "fallback_chain": ["codegraph", "builtin_graph", "text_search"],
                "reason_code": "fallback",
            },
        },
        "in_progress",
    )


def test_doctor_reports_codegraph_diagnostics(tmp_path, monkeypatch):
    from pactkit.doctor import check_graph_provider

    _configured_codegraph_project(tmp_path)
    monkeypatch.setattr(
        "pactkit.graph_query.CodegraphProvider.health",
        lambda self: {
            "available": True, "fresh": False, "reason": "index_stale",
            "version": "codegraph 1.1.6", "warnings": ["index_old_engine"],
        },
    )
    result = check_graph_provider(tmp_path)
    assert result == {
        "configured": "codegraph", "selected": "codegraph",
        "available": True, "fresh": False, "reason": "index_stale",
        "version": "codegraph 1.1.6", "warnings": ["index_old_engine"],
    }
