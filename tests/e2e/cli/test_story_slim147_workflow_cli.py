"""CLI E2E for STORY-slim-147 generic workflows."""

import json
import os
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


def test_plan_workflow_cli_resumes_before_story_binding(tmp_path):
    _initialize_project(tmp_path)
    result = _run(
        "workflow", "start", "project-plan", "--evidence",
        json.dumps({"guard": "pass", "input_fingerprint": "abc"}), cwd=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    state = json.loads(result.stdout[result.stdout.index("{"):])
    run_id = state["run_id"]
    clarified = _run(
        "workflow", "checkpoint", run_id, "--step", "intent_clarified",
        "--evidence", json.dumps({"input_fingerprint": "abc", "answers": []}), cwd=tmp_path,
    )
    assert clarified.returncode == 0, clarified.stdout + clarified.stderr
    traced = _run(
        "workflow", "checkpoint", run_id, "--step", "archaeology",
        "--evidence", json.dumps({"trace": ["cli.main"]}), cwd=tmp_path,
    )
    assert traced.returncode == 0, traced.stdout + traced.stderr
    state_path = tmp_path / ".pactkit/continuations/runs" / f"{run_id}.json"
    before = state_path.read_bytes()
    resumed = _run("workflow", "resume", run_id, cwd=tmp_path)
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert json.loads(resumed.stdout)["next_step"] == "story_identified"
    assert state_path.read_bytes() == before


def test_registry_cli_reports_all_25_entries(tmp_path):
    result = _run("workflow", "registry", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert len(payload["entries"]) == 25
    assert payload["entries"]["project-check"]["persistence"] == "full"


def test_workflow_contract_reports_executable_done_lifecycle(tmp_path):
    result = _run("workflow", "contract", "project-done", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["steps"] == [
        "started", "audited", "governance_synced", "completed",
    ]
    assert payload["start_evidence_requirements"] == ["started=true"]
    assert "workflow start project-done" in payload["start"]
    assert "workflow checkpoint" in payload["checkpoint"]
    assert "workflow finish-guard" in payload["finish_guard"]
    assert payload["manual_operations"] == ["commit", "archive"]


def _initialize_project(root: Path) -> None:
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "pactkit.yaml").write_text("stack: python\n")
