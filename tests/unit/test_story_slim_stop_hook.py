import json

import pytest


def _start(engine, workflow="project-plan"):
    evidence = (
        {"guard": "pass", "input_fingerprint": "abc"}
        if workflow == "project-plan"
        else {"started": True}
    )
    return engine.start(workflow, evidence=evidence)


def test_session_binding_resolves_active_run_without_storing_raw_session(tmp_path):
    from pactkit.continuation import ContinuationEngine

    engine = ContinuationEngine(tmp_path)
    state = _start(engine)
    engine.bind_host_session(state["run_id"], session_id="session-secret", turn_id="turn-1")

    resolved = engine.resolve_host_run(session_id="session-secret", turn_id="turn-2")

    assert resolved["run_id"] == state["run_id"]
    assert resolved["step_id"] == "preflight"
    persisted = engine.read(state["run_id"])["host_binding"]
    assert persisted["session_ref"].startswith("sha256:")
    assert "session-secret" not in json.dumps(persisted)


def test_host_resolution_uses_unique_active_fallback_and_rejects_ambiguity(tmp_path):
    from pactkit.continuation import ContinuationEngine, ContinuationError

    engine = ContinuationEngine(tmp_path)
    only = _start(engine)
    assert engine.resolve_host_run(session_id="unknown")["run_id"] == only["run_id"]
    _start(engine, "project-debug")

    with pytest.raises(ContinuationError, match="multiple active workflow runs"):
        engine.resolve_host_run(session_id="unknown")


@pytest.mark.parametrize("payload", ["[]", "null"])
def test_host_resolution_rejects_non_object_workflow_checkpoint(tmp_path, payload):
    from pactkit.continuation import ContinuationEngine, ContinuationError

    engine = ContinuationEngine(tmp_path)
    engine.directory.mkdir(parents=True)
    (engine.directory / f"run-{'0' * 32}.json").write_text(payload, encoding="utf-8")

    with pytest.raises(ContinuationError, match="corrupt workflow checkpoint"):
        engine.resolve_host_run(session_id="unknown")


def test_host_resolution_rejects_non_object_session_binding(tmp_path):
    from pactkit.continuation import ContinuationEngine, ContinuationError

    engine = ContinuationEngine(tmp_path)
    binding = engine._host_binding_path(engine._host_reference("session-1", "session ID"))
    binding.parent.mkdir(parents=True)
    binding.write_text("[]", encoding="utf-8")

    with pytest.raises(ContinuationError, match="corrupt host session binding"):
        engine.resolve_host_run(session_id="session-1")


def test_host_resolution_prefers_generic_run_identifier_for_project_act(tmp_path):
    from pactkit.continuation import ContinuationEngine

    engine = ContinuationEngine(tmp_path)
    state = engine.start(
        "project-act",
        evidence={
            "spec_lint": "pass",
            "graph_provider": {
                "requested_provider": "codegraph", "selected_provider": "codegraph",
                "availability": True, "freshness": True, "query_kind": "explore",
                "query_target": "hook", "result_count": 1, "fallback": False,
                "reason_code": "ok",
            },
        },
    )
    engine.bind_story(state["run_id"], "STORY-slim-999")
    engine.bind_host_session(state["run_id"], session_id="session-1", turn_id="turn-1")

    resolved = engine.resolve_host_run(session_id="session-1")

    assert resolved["identifier"] == state["run_id"]


def test_completed_generic_act_is_not_overridden_by_legacy_drift(tmp_path):
    from pactkit.continuation import ContinuationEngine, ContinuationStore
    from pactkit.host_continuation import HostCapabilities, HostContinuationRunner

    story = "STORY-slim-998"
    engine = ContinuationEngine(tmp_path)
    state = engine.start("project-act", evidence={"spec_lint": "pass"})
    engine.bind_story(state["run_id"], story)
    engine.bind_host_session(state["run_id"], session_id="session-1")
    for step in ("red", "green", "regression_lint"):
        engine.checkpoint(state["run_id"], step_id=step, evidence={})
    engine.checkpoint(
        state["run_id"], step_id="sync_coverage", status="completed", evidence={},
    )
    (tmp_path / "docs/specs").mkdir(parents=True)
    (tmp_path / "docs/product").mkdir(parents=True)
    (tmp_path / "docs/specs" / f"{story}.md").write_text(
        f"# {story}: Test\n\n| Field | Value |\n|---|---|\n"
        f"| ID | {story} |\n| Status | Draft |\n| Priority | P1 |\n| Release | 1.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n"
        "- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n"
        "| SEC-1 | N/A | test |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/product/sprint_board.md").write_text("board")
    ContinuationStore(tmp_path).checkpoint(
        story, step_id="preflight", evidence={"spec_lint": "pass"},
    )
    (tmp_path / "docs/specs" / f"{story}.md").write_text("drifted")
    resolved = engine.resolve_host_run(session_id="session-1")
    runner = HostContinuationRunner(
        engine, HostCapabilities(completion_hook=True, session_reentry=True),
    )

    decision = runner.after_model_turn(resolved["identifier"], session_locator="session-1")

    assert decision["decision"] == "done"
    assert engine.read(state["run_id"])["status"] == "completed"


def test_legacy_act_host_runner_hands_off_without_blocking_on_no_progress(tmp_path):
    from pactkit.continuation import ContinuationEngine, ContinuationStore
    from pactkit.host_continuation import HostCapabilities, HostContinuationRunner

    story = "STORY-slim-999"
    (tmp_path / "docs/specs").mkdir(parents=True)
    (tmp_path / "docs/product").mkdir(parents=True)
    (tmp_path / "docs/specs" / f"{story}.md").write_text(
        f"# {story}: Test\n\n| Field | Value |\n|---|---|\n"
        f"| ID | {story} |\n| Status | Draft |\n| Priority | P1 |\n| Release | 1.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n"
        "- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n"
        "| SEC-1 | N/A | test |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/product/sprint_board.md").write_text("# board", encoding="utf-8")
    ContinuationStore(tmp_path).checkpoint(
        story, step_id="preflight", evidence={"spec_lint": "pass"},
    )
    runner = HostContinuationRunner(
        ContinuationEngine(tmp_path),
        HostCapabilities(completion_hook=True, session_reentry=True),
    )

    first = runner.after_model_turn(story, session_locator="session-1")
    second = runner.after_model_turn(story, session_locator="session-1")

    assert first["decision"] == "resume_session"
    assert second["decision"] == "await_user"
    assert second["reason_code"] == "no_progress"
    assert ContinuationStore(tmp_path).read(story)["status"] == "in_progress"


def test_doctor_reports_codex_current_session_execution(tmp_path, monkeypatch):
    from pactkit.doctor import check_codex_execution_capability

    fake_home = tmp_path / "home"
    codex_root = fake_home / ".codex"
    codex_root.mkdir(parents=True)
    monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)
    (codex_root / ".pactkit-deployed.json").write_text(json.dumps({
        "format": "codex",
        "workflow_continuation": {
            "execution_mode": "portable",
            "session_execution": "native_current_session",
            "finish_guard_supported": False,
            "guarantee_level": "portable",
        },
    }), encoding="utf-8")

    result = check_codex_execution_capability()

    assert result == {
        "execution_mode": "portable",
        "session_execution": "native_current_session",
        "background_execution": False,
        "thread_resume": False,
        "finish_guard_supported": False,
        "guarantee_level": "portable",
        "warnings": [],
    }


def test_doctor_without_codex_manifest_reports_portable_current_session(tmp_path):
    from pactkit.doctor import check_codex_execution_capability

    result = check_codex_execution_capability(tmp_path / "missing-codex-root")

    assert result["guarantee_level"] == "portable"
    assert result["session_execution"] == "native_current_session"
    assert result["background_execution"] is False


def test_doctor_ignores_stale_hook_data_from_legacy_manifest(tmp_path):
    from pactkit.doctor import check_codex_execution_capability

    manifest = tmp_path / ".pactkit-deployed.json"
    manifest.write_text(json.dumps({
        "workflow_continuation": {
            "hook_installed": False,
            "hook_trusted": True,
            "hook_observed": True,
            "continuation_validated": True,
            "guarantee_level": "guided",
        },
    }), encoding="utf-8")

    result = check_codex_execution_capability(tmp_path)

    assert result["execution_mode"] == "portable"
    assert result["session_execution"] == "native_current_session"
    assert result["background_execution"] is False
    assert result["thread_resume"] is False


def test_doctor_normalizes_retired_runner_capabilities_from_old_manifest(tmp_path):
    from pactkit.doctor import check_codex_execution_capability

    (tmp_path / ".pactkit-deployed.json").write_text(json.dumps({
        "workflow_continuation": {
            "execution_mode": "resumable",
            "session_execution": "background_runner",
            "finish_guard_supported": True,
            "guarantee_level": "resumable",
        },
    }), encoding="utf-8")

    result = check_codex_execution_capability(tmp_path)

    assert result["execution_mode"] == "portable"
    assert result["session_execution"] == "native_current_session"
    assert result["finish_guard_supported"] is False
    assert result["guarantee_level"] == "portable"
    assert result["warnings"] == [
        "Codex execution manifest describes retired runner capabilities; "
        "using native current-session execution",
    ]


@pytest.mark.parametrize("payload", ["[]", "null", '"manifest"'])
def test_doctor_rejects_non_object_codex_manifest(tmp_path, payload):
    from pactkit.doctor import check_codex_execution_capability

    (tmp_path / ".pactkit-deployed.json").write_text(payload, encoding="utf-8")

    result = check_codex_execution_capability(tmp_path)

    assert result["guarantee_level"] == "portable"
    assert result["warnings"] == [
        "Codex execution manifest unreadable — re-run `pactkit update`",
    ]
