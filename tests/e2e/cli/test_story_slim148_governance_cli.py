"""CLI E2E for sharded governance facts."""

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


def _json_output(result: subprocess.CompletedProcess[str]) -> dict | list:
    assert result.returncode == 0, result.stdout + result.stderr
    offset = min((index for index in (result.stdout.find("{"), result.stdout.find("[")) if index >= 0))
    return json.loads(result.stdout[offset:])


def test_story_commands_do_not_write_board_projection(tmp_path):
    product = tmp_path / "docs/product"
    product.mkdir(parents=True)
    board = product / "sprint_board.md"
    board.write_text("legacy projection\n", encoding="utf-8")
    original = board.read_bytes()
    story_id = "STORY-slim-148-c3d4"

    _json_output(_run("board", "add", story_id, "Sharded facts", "one|two", cwd=tmp_path))
    _json_output(_run("board", "move", story_id, "in_progress", cwd=tmp_path))
    _json_output(_run("board", "complete-task", story_id, "one", cwd=tmp_path))

    assert board.read_bytes() == original
    record = product / "stories" / f"{story_id}.yaml"
    assert record.is_file()
    assert "completed: true" in record.read_text(encoding="utf-8")

    render = _run("board", "render", cwd=tmp_path)
    assert render.returncode == 0, render.stdout + render.stderr
    assert story_id in board.read_text(encoding="utf-8")
    assert _run("board", "render", "--check", cwd=tmp_path).returncode == 0
    board.write_text("stale\n", encoding="utf-8")
    assert _run("board", "render", "--check", cwd=tmp_path).returncode == 1


def test_lesson_and_context_use_unshared_paths(tmp_path):
    result = _run(
        "lesson-append", "--story", "STORY-slim-148-c3d4",
        "--text", "Use atomic_write() in src/pactkit/governance.py",
        "--context", "src/pactkit/governance.py", cwd=tmp_path,
    )
    assert _json_output(result)["action"] == "appended"
    lessons = list((tmp_path / "docs/architecture/governance/lessons").glob("*.md"))
    assert len(lessons) == 1
    assert not (tmp_path / "docs/architecture/governance/lessons.md").exists()

    context = _run("context", cwd=tmp_path)
    assert context.returncode == 0, context.stdout + context.stderr
    assert (tmp_path / ".pactkit/context.md").is_file()
    assert not (tmp_path / "docs/product/context.md").exists()


def test_migration_cli_is_dry_run_by_default(tmp_path):
    product = tmp_path / "docs/product"
    product.mkdir(parents=True)
    board = product / "sprint_board.md"
    board.write_text(
        "# Sprint Board\n\n## 📋 Backlog\n\n### [STORY-slim-001] One\n"
        "> Spec: docs/specs/STORY-slim-001.md\n\n- [ ] Task\n\n"
        "## 🔄 In Progress\n\n## ✅ Done\n", encoding="utf-8",
    )
    report = _json_output(_run("governance", "migrate", cwd=tmp_path))
    assert report["dry_run"] is True
    assert not (product / "stories").exists()
    applied = _json_output(_run("governance", "migrate", "--apply", cwd=tmp_path))
    assert applied["legacy_preserved"] is True
    assert (product / "stories/STORY-slim-001.yaml").is_file()
    assert board.is_file()
