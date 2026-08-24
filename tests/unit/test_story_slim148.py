"""STORY-slim-148: sharded governance facts and projections."""

from pathlib import Path
import subprocess

import pytest

def test_story_repository_updates_one_record_and_board_is_projection(tmp_path):
    from pactkit.governance import BoardRenderer, StoryRepository

    repo = StoryRepository(tmp_path)
    repo.add("STORY-slim-147-a1b2", "First", ["one", "two"])
    repo.add("STORY-slim-148-c3d4", "Second", ["other"])
    repo.complete_task("STORY-slim-147-a1b2", "one")
    assert set(p.name for p in repo.directory.glob("*.yaml")) == {
        "STORY-slim-147-a1b2.yaml", "STORY-slim-148-c3d4.yaml"
    }
    first = repo.load("STORY-slim-147-a1b2")
    second = repo.load("STORY-slim-148-c3d4")
    assert first["tasks"][0]["completed"] is True
    assert second["tasks"][0]["completed"] is False
    renderer = BoardRenderer(repo)
    assert renderer.render() == renderer.render()
    assert "STORY-slim-147-a1b2" in renderer.render()


def test_lesson_repository_creates_distinct_records_and_context_reads_them(tmp_path):
    from pactkit.governance import LessonRepository

    repo = LessonRepository(tmp_path)
    first = repo.add("STORY-slim-147-a1b2", "Use `atomic_write()` in src/x.py", "src/x.py")
    second = repo.add("STORY-slim-148-c3d4", "Use `safe_load()` in src/y.py", "src/y.py")
    assert first["path"] != second["path"]
    assert len(list(repo.directory.glob("*.md"))) == 2
    assert len(repo.recent()) == 2


def test_next_ids_from_same_snapshot_are_unique_and_backward_compatible(tmp_path):
    from pactkit.id_generator import ITEM_ID_RE, generate_item_id

    ids = {generate_item_id(tmp_path, "slim") for _ in range(1000)}
    assert len(ids) == 1000
    assert all(ITEM_ID_RE.fullmatch(item_id) for item_id in ids)
    assert ITEM_ID_RE.fullmatch("STORY-slim-148")


def test_context_default_path_is_local_and_ignored(tmp_path):
    from pactkit.context_gen import context_output_path

    assert context_output_path(tmp_path) == tmp_path / ".pactkit/context.md"


def test_legacy_migration_dry_run_and_install(tmp_path):
    from pactkit.governance import GovernanceMigrator, StoryRepository

    product = tmp_path / "docs/product"
    product.mkdir(parents=True)
    board = product / "sprint_board.md"
    board.write_text(
        "# Sprint Board\n\n## 📋 Backlog\n\n### [STORY-slim-001] One\n"
        "> Spec: docs/specs/STORY-slim-001.md\n\n- [ ] Task\n\n"
        "## 🔄 In Progress\n\n## ✅ Done\n", encoding="utf-8",
    )
    migrator = GovernanceMigrator(tmp_path)
    report = migrator.migrate(dry_run=True)
    assert report["stories"] == 1
    assert not (product / "stories").exists()
    migrator.migrate(dry_run=False)
    assert StoryRepository(tmp_path).load("STORY-slim-001")["title"] == "One"
    assert board.exists()


def test_migration_reconciles_story_facts_independent_of_board_order(tmp_path):
    """Board section/order is presentation, not part of Story fact identity."""
    from pactkit.governance import GovernanceMigrator, StoryRepository

    product = tmp_path / "docs/product"
    product.mkdir(parents=True)
    (product / "sprint_board.md").write_text(
        "# Sprint Board\n\n## 📋 Backlog\n\n"
        "### [STORY-slim-200] Later\n- [ ] later task\n\n"
        "### [HOTFIX-slim-100] Earlier alphabetically\n- [x] fixed\n\n"
        "## 🔄 In Progress\n\n## ✅ Done\n",
        encoding="utf-8",
    )

    report = GovernanceMigrator(tmp_path).migrate(dry_run=False)

    assert report["stories"] == 2
    assert [record["id"] for record in StoryRepository(tmp_path).list()] == [
        "HOTFIX-slim-100",
        "STORY-slim-200",
    ]


def _legacy_governance_fixture(tmp_path):
    product = tmp_path / "docs/product"
    governance = tmp_path / "docs/architecture/governance"
    archive = governance / "archive"
    product.mkdir(parents=True)
    archive.mkdir(parents=True)
    (product / "sprint_board.md").write_text(
        "# Sprint Board\n\n## 📋 Backlog\n\n"
        "### [STORY-slim-001] One\n> Spec: docs/specs/STORY-slim-001.md\n\n"
        "- [ ] open\n\n## 🔄 In Progress\n\n"
        "### [STORY-slim-002] Two\n> Spec: docs/specs/STORY-slim-002.md\n\n"
        "- [x] finished\n- [ ] pending\n\n## ✅ Done\n\n"
        "### [STORY-slim-003] Three\n> Spec: docs/specs/STORY-slim-003.md\n\n"
        "- [x] complete\n",
        encoding="utf-8",
    )
    header = "# Lessons Learned\n\n| Date | Lesson | Context |\n|------|--------|---------|\n"
    (governance / "lessons.md").write_text(
        header
        + "| 2026-08-20 | Keep `alpha()` atomic | STORY-slim-001 |\n"
        + "| 2026-08-21 | Duplicate text is historical evidence | src/a.py |\n",
        encoding="utf-8",
    )
    (archive / "lessons_archive_202607.md").write_text(
        header
        + "| 2026-07-01 | Archive uses `safe_load()` | STORY-slim-002 |\n"
        + "| 2026-07-02 | Duplicate text is historical evidence | src/a.py |\n",
        encoding="utf-8",
    )
    (product / "context.md").write_text("legacy context\n", encoding="utf-8")


def test_migration_stages_and_reconciles_current_and_archived_lessons(tmp_path):
    from pactkit.governance import GovernanceMigrator, LessonRepository, StoryRepository

    _legacy_governance_fixture(tmp_path)
    legacy = {path: path.read_bytes() for path in tmp_path.rglob("*.md")}
    dry_run = GovernanceMigrator(tmp_path).migrate(dry_run=True)
    assert dry_run["stories"] == 3
    assert dry_run["lessons"] == 4
    assert not (tmp_path / "docs/product/stories").exists()
    assert not (tmp_path / "docs/architecture/governance/lessons").exists()

    report = GovernanceMigrator(tmp_path).migrate(dry_run=False)
    stories = StoryRepository(tmp_path).list()
    lessons = LessonRepository(tmp_path).recent(limit=10)
    assert report["stories"] == len(stories) == 3
    assert report["lessons"] == len(lessons) == 4
    assert [story["status"] for story in stories] == ["backlog", "in_progress", "done"]
    assert sum(lesson["text"] == "Duplicate text is historical evidence" for lesson in lessons) == 2
    assert {lesson["date"] for lesson in lessons} == {"2026-07-01", "2026-07-02", "2026-08-20", "2026-08-21"}
    assert all(path.read_bytes() == content for path, content in legacy.items())


def test_migration_rolls_back_first_directory_when_second_install_fails(tmp_path, monkeypatch):
    from pactkit.governance import GovernanceError, GovernanceMigrator

    _legacy_governance_fixture(tmp_path)
    legacy = {path: path.read_bytes() for path in tmp_path.rglob("*.md")}
    original_replace = Path.replace

    def fail_lesson_install(path, target):
        if Path(target).name == "lessons":
            raise OSError("injected lesson install failure")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_lesson_install)
    with pytest.raises(GovernanceError, match="rolled back"):
        GovernanceMigrator(tmp_path).migrate(dry_run=False)

    assert not (tmp_path / "docs/product/stories").exists()
    assert not (tmp_path / "docs/architecture/governance/lessons").exists()
    assert all(path.read_bytes() == content for path, content in legacy.items())


def _git(repo, *args, check=True):
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=check,
    )


def test_distinct_story_and_lesson_facts_merge_without_shared_file_conflict(tmp_path):
    from pactkit.governance import LessonRepository, StoryRepository

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "PactKit Tests")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "base")

    left = tmp_path / "left"
    right = tmp_path / "right"
    _git(repo, "worktree", "add", "-qb", "left", str(left), "HEAD")
    _git(repo, "worktree", "add", "-qb", "right", str(right), "HEAD")
    StoryRepository(left).add("STORY-slim-101-a1b2", "Left", ["left task"] )
    LessonRepository(left).add("STORY-slim-101-a1b2", "Use `left()` in src/left.py")
    StoryRepository(right).add("STORY-slim-102-c3d4", "Right", ["right task"] )
    LessonRepository(right).add("STORY-slim-102-c3d4", "Use `right()` in src/right.py")
    for worktree, message in ((left, "left facts"), (right, "right facts")):
        _git(worktree, "add", "docs")
        _git(worktree, "commit", "-qm", message)

    _git(repo, "merge", "--no-edit", "left")
    merged = _git(repo, "merge", "--no-edit", "right")
    assert merged.returncode == 0
    assert len(StoryRepository(repo).list()) == 2
    assert len(LessonRepository(repo).recent(limit=10)) == 2
    assert not (repo / "docs/product/sprint_board.md").exists()
    assert not (repo / "docs/architecture/governance/lessons.md").exists()


def test_same_story_fact_keeps_real_git_conflict(tmp_path):
    from pactkit.governance import StoryRepository

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "PactKit Tests")
    StoryRepository(repo).add("STORY-slim-100-a1b2", "Shared", ["one", "two"] )
    _git(repo, "add", "docs")
    _git(repo, "commit", "-qm", "base")
    left = tmp_path / "left"
    right = tmp_path / "right"
    _git(repo, "worktree", "add", "-qb", "left", str(left), "HEAD")
    _git(repo, "worktree", "add", "-qb", "right", str(right), "HEAD")
    left_record = StoryRepository(left).load("STORY-slim-100-a1b2")
    right_record = StoryRepository(right).load("STORY-slim-100-a1b2")
    left_record["status"] = "in_progress"
    right_record["status"] = "done"
    StoryRepository(left)._write(left_record)
    StoryRepository(right)._write(right_record)
    for worktree, message in ((left, "left edit"), (right, "right edit")):
        _git(worktree, "add", "docs")
        _git(worktree, "commit", "-qm", message)
    _git(repo, "merge", "--no-edit", "left")
    conflict = _git(repo, "merge", "--no-edit", "right", check=False)
    assert conflict.returncode != 0
    assert "UU docs/product/stories/STORY-slim-100-a1b2.yaml" in _git(repo, "status", "--short").stdout


def test_act_continuation_uses_story_fact_for_drift_and_completion(tmp_path):
    from pactkit.continuation import ContinuationStore
    from pactkit.governance import StoryRepository

    story_id = "STORY-slim-148-c3d4"
    spec = tmp_path / "docs/specs" / f"{story_id}.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        f"# {story_id}\n\n| Field | Value |\n|---|---|\n"
        f"| ID | {story_id} |\n| Status | Draft |\n| Priority | P1 |\n| Release | 2.21.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\n\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n\n"
        "- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n| SEC-1 | N/A | test |\n",
        encoding="utf-8",
    )
    repository = StoryRepository(tmp_path)
    repository.add(story_id, "Sharded continuation", ["implement"])
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "docs"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com",
         "commit", "-qm", "fixture"],
        cwd=tmp_path, check=True,
    )
    store = ContinuationStore(tmp_path)
    store.checkpoint(story_id, step_id="preflight", evidence={"spec_lint": "pass"})
    repository.move(story_id, "in_progress")
    assert "story fact fingerprint changed" in store.resume(story_id)["reasons"]

    store.path_for(story_id).unlink()
    store.checkpoint(story_id, step_id="preflight", evidence={"spec_lint": "pass"})
    store.checkpoint(story_id, step_id="red", evidence={"story_tests": {"exit_code": 1}})
    store.checkpoint(story_id, step_id="green", evidence={"story_tests": {"exit_code": 0}})
    store.checkpoint(
        story_id, step_id="regression_lint",
        evidence={"regression": "pass", "lint": "pass"},
    )
    repository.complete_task(story_id, "implement")
    completion = {
        "spec_lint": "pass", "story_tests": {"exit_code": 0},
        "regression": "pass", "lint": "pass",
        "coverage": {"R1": ["tests/unit/test_story_slim148.py"]},
        "acceptance_coverage": {"AC1": ["tests/unit/test_story_slim148.py"]},
        "board_tasks": ["implement"],
    }
    store._validate_completion("sync_coverage", completion, story_id)
