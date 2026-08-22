"""CLI coverage for STORY-slim-146 continuation commands."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time


def _run(*args, cwd):
    return subprocess.run([sys.executable, "-m", "pactkit.cli", *args], cwd=cwd, text=True, capture_output=True)


def _project(tmp_path):
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    (tmp_path / "docs" / "product").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "STORY-slim-146.md").write_text(
        "# STORY-slim-146\n\n"
        "| Field | Value |\n|---|---|\n| ID | STORY-slim-146 |\n"
        "| Status | Draft |\n| Priority | P1 |\n| Release | 2.20.0 |\n\n"
        "## Requirements\n\n### R1: Test (MUST)\n\ntext\n\n"
        "## Acceptance Criteria\n\n### AC1: Test (R1)\n\n"
        "- **Given** x\n- **When** y\n- **Then** z\n\n"
        "## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n"
        "| SEC-1 | N/A | test |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "product" / "sprint_board.md").write_text("# Sprint Board\n", encoding="utf-8")


def test_checkpoint_then_resume_is_read_only(tmp_path):
    _project(tmp_path)
    evidence = json.dumps({"spec_lint": "pass"})
    checkpoint = _run("continuation", "checkpoint", "STORY-slim-146", "--step", "preflight", "--evidence", evidence, cwd=tmp_path)
    assert checkpoint.returncode == 0, checkpoint.stderr
    state = tmp_path / ".pactkit" / "continuations" / "STORY-slim-146.json"
    before = state.read_bytes()
    resume = _run("continuation", "resume", "STORY-slim-146", cwd=tmp_path)
    assert resume.returncode == 0, resume.stderr
    assert "next_step" in resume.stdout
    assert state.read_bytes() == before


def test_corrupt_checkpoint_is_reported_without_overwrite(tmp_path):
    _project(tmp_path)
    state = tmp_path / ".pactkit" / "continuations" / "STORY-slim-146.json"
    state.parent.mkdir(parents=True)
    state.write_text("broken", encoding="utf-8")
    result = _run("continuation", "resume", "STORY-slim-146", cwd=tmp_path)
    assert result.returncode == 1
    assert "Continuation error" in result.stdout
    assert state.read_text(encoding="utf-8") == "broken"


def test_status_and_resume_report_unverifiable_legacy_handoff(tmp_path):
    _project(tmp_path)
    context = tmp_path / "docs/product/context.md"
    context.write_text(
        "Last Command: /project-act STORY-slim-146\nPhase Reached: Phase 3\n",
        encoding="utf-8",
    )
    for action in ("status", "resume"):
        result = _run("continuation", action, "STORY-slim-146", cwd=tmp_path)
        assert result.returncode == 0, result.stdout
        assert "unverifiable legacy handoff" in result.stdout
        assert not (tmp_path / ".pactkit").exists()


def test_fresh_cli_archives_a_completed_checkpoint(tmp_path):
    _project(tmp_path)
    board = tmp_path / "docs/product/sprint_board.md"
    board.write_text("# Sprint Board\n\n## ✅ Done\n\n### [STORY-slim-146] Test\n- [x] Task\n", encoding="utf-8")
    boundaries = (
        ("preflight", {"spec_lint": "pass"}),
        ("red", {"story_tests": {"exit_code": 1}}),
        ("green", {"story_tests": {"exit_code": 0}}),
        ("regression_lint", {"regression": "pass", "lint": "pass"}),
    )
    for step, step_evidence in boundaries:
        result = _run("continuation", "checkpoint", "STORY-slim-146", "--step", step, "--evidence", json.dumps(step_evidence), cwd=tmp_path)
        assert result.returncode == 0, result.stdout
    evidence = json.dumps({"spec_lint": "pass", "story_tests": {"exit_code": 0}, "regression": "pass", "lint": "pass", "coverage": {"R1": ["test"]}, "acceptance_coverage": {"AC1": ["test"]}, "board_tasks": ["Task"]})
    completed = _run("continuation", "checkpoint", "STORY-slim-146", "--step", "sync_coverage", "--status", "completed", "--evidence", evidence, cwd=tmp_path)
    assert completed.returncode == 0, completed.stdout
    fresh = _run("continuation", "checkpoint", "STORY-slim-146", "--fresh", "--step", "preflight", "--evidence", json.dumps({"spec_lint": "pass"}), cwd=tmp_path)
    assert fresh.returncode == 0, fresh.stdout
    assert list((tmp_path / ".pactkit/continuations/history").glob("STORY-slim-146-*.json"))


def test_concurrent_cli_checkpoint_waits_for_story_lock(tmp_path):
    _project(tmp_path)
    lock_path = tmp_path / ".pactkit/continuations/STORY-slim-146.lock"
    lock_path.parent.mkdir(parents=True)
    handle = lock_path.open("a+b")
    if os.name == "nt":  # pragma: no cover - exercised on Windows CI
        import msvcrt

        handle.write(b"0")
        handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    process = subprocess.Popen(
        [sys.executable, "-m", "pactkit.cli", "continuation", "checkpoint",
         "STORY-slim-146", "--step", "preflight", "--evidence",
         json.dumps({"spec_lint": "pass"})],
        cwd=tmp_path, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        time.sleep(0.2)
        assert process.poll() is None
    finally:
        if os.name == "nt":  # pragma: no cover - exercised on Windows CI
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
    stdout, stderr = process.communicate(timeout=3)
    assert process.returncode == 0, stdout + stderr
    assert json.loads((tmp_path / ".pactkit/continuations/STORY-slim-146.json").read_text())["step_id"] == "preflight"
