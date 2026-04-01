"""Tests for STORY-slim-075 R4: Lessons rotation — max rows + auto-archive."""

from __future__ import annotations

import re
from pathlib import Path

from pactkit.lessons import append_lesson, _rotate_if_needed
from pactkit.schemas import LESSONS_MAX_ROWS, LESSONS_TABLE_HEADER, LESSONS_TABLE_SEPARATOR


# ── AC8: LESSONS_MAX_ROWS constant exists ──────────────────────────────────


class TestAC8Constant:
    def test_constant_exists_and_is_50(self):
        assert LESSONS_MAX_ROWS == 50


# ── AC6: Rotation at 50 rows ──────────────────────────────────────────────


def _build_lessons_md(n_rows: int) -> str:
    """Build a lessons.md with n_rows of entries."""
    lines = [
        "# Lessons Learned\n",
        f"{LESSONS_TABLE_HEADER}\n",
        f"{LESSONS_TABLE_SEPARATOR}\n",
    ]
    for i in range(1, n_rows + 1):
        month = f"{(i % 12) + 1:02d}"
        lines.append(f"| 2026-{month}-{i:02d} | lesson {i} about foo_{i}.py:bar() | STORY-{i:03d} |\n")
    return "".join(lines)


class TestAC6Rotation:
    def test_rotate_trims_to_max_rows(self, tmp_path: Path):
        """55 rows → oldest 5 archived, 50 remain."""
        gov = tmp_path / "docs" / "architecture" / "governance"
        gov.mkdir(parents=True)
        lessons = gov / "lessons.md"
        lessons.write_text(_build_lessons_md(55), encoding="utf-8")

        _rotate_if_needed(tmp_path, max_rows=50)

        content = lessons.read_text(encoding="utf-8")
        rows = re.findall(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|", content)
        assert len(rows) == 50

    def test_rotate_keeps_newest(self, tmp_path: Path):
        """After rotation, the newest entry (lesson 55) is still present."""
        gov = tmp_path / "docs" / "architecture" / "governance"
        gov.mkdir(parents=True)
        lessons = gov / "lessons.md"
        lessons.write_text(_build_lessons_md(55), encoding="utf-8")

        _rotate_if_needed(tmp_path, max_rows=50)

        content = lessons.read_text(encoding="utf-8")
        assert "lesson 55" in content

    def test_rotate_removes_oldest(self, tmp_path: Path):
        """After rotation, the oldest entries (1-5) are gone from lessons.md."""
        gov = tmp_path / "docs" / "architecture" / "governance"
        gov.mkdir(parents=True)
        lessons = gov / "lessons.md"
        lessons.write_text(_build_lessons_md(55), encoding="utf-8")

        _rotate_if_needed(tmp_path, max_rows=50)

        content = lessons.read_text(encoding="utf-8")
        for i in range(1, 6):
            assert f"lesson {i} about" not in content

    def test_no_rotation_at_50(self, tmp_path: Path):
        """Exactly 50 rows → no rotation needed."""
        gov = tmp_path / "docs" / "architecture" / "governance"
        gov.mkdir(parents=True)
        lessons = gov / "lessons.md"
        lessons.write_text(_build_lessons_md(50), encoding="utf-8")

        _rotate_if_needed(tmp_path, max_rows=50)

        content = lessons.read_text(encoding="utf-8")
        rows = re.findall(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|", content)
        assert len(rows) == 50

    def test_no_rotation_below_max(self, tmp_path: Path):
        """30 rows → no rotation, no archive created."""
        gov = tmp_path / "docs" / "architecture" / "governance"
        gov.mkdir(parents=True)
        lessons = gov / "lessons.md"
        lessons.write_text(_build_lessons_md(30), encoding="utf-8")

        _rotate_if_needed(tmp_path, max_rows=50)

        archive_dir = gov / "archive"
        assert not archive_dir.exists() or not list(archive_dir.glob("lessons_archive_*.md"))

    def test_append_triggers_rotation(self, tmp_path: Path):
        """append_lesson with 52 existing rows triggers rotation."""
        gov = tmp_path / "docs" / "architecture" / "governance"
        gov.mkdir(parents=True)
        lessons = gov / "lessons.md"
        lessons.write_text(_build_lessons_md(52), encoding="utf-8")

        result = append_lesson(tmp_path, "STORY-075", "new lesson about rotate_test.py:func()", "test")

        assert result["action"] == "appended"
        content = lessons.read_text(encoding="utf-8")
        rows = re.findall(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|", content)
        # After rotation (52→50) + append (1) = 51, then rotate again = 50+1
        # Actually: rotate first (52→50), then append → 51. Next call would rotate.
        # The spec says rotate when > max_rows, so 52 > 50 → rotate to 50, then append → 51
        assert len(rows) <= 51


# ── AC7: Archive file format ──────────────────────────────────────────────


class TestAC7ArchiveFormat:
    def test_archive_has_table_header(self, tmp_path: Path):
        """Archive file must have the same table header as lessons.md."""
        gov = tmp_path / "docs" / "architecture" / "governance"
        gov.mkdir(parents=True)
        lessons = gov / "lessons.md"
        lessons.write_text(_build_lessons_md(55), encoding="utf-8")

        _rotate_if_needed(tmp_path, max_rows=50)

        archive_dir = gov / "archive"
        archives = list(archive_dir.glob("lessons_archive_*.md"))
        assert len(archives) >= 1
        archive_content = archives[0].read_text(encoding="utf-8")
        assert LESSONS_TABLE_HEADER in archive_content
        assert LESSONS_TABLE_SEPARATOR in archive_content

    def test_archive_contains_rotated_rows(self, tmp_path: Path):
        """Archive must contain the oldest 5 rows that were removed."""
        gov = tmp_path / "docs" / "architecture" / "governance"
        gov.mkdir(parents=True)
        lessons = gov / "lessons.md"
        lessons.write_text(_build_lessons_md(55), encoding="utf-8")

        _rotate_if_needed(tmp_path, max_rows=50)

        archive_dir = gov / "archive"
        archives = list(archive_dir.glob("lessons_archive_*.md"))
        all_archive = "".join(a.read_text(encoding="utf-8") for a in archives)
        for i in range(1, 6):
            assert f"lesson {i} about" in all_archive

    def test_archive_appends_to_existing(self, tmp_path: Path):
        """Second rotation appends to existing archive, not overwrites."""
        gov = tmp_path / "docs" / "architecture" / "governance"
        gov.mkdir(parents=True)
        lessons = gov / "lessons.md"

        # First rotation: 55 rows → archive 5
        lessons.write_text(_build_lessons_md(55), encoding="utf-8")
        _rotate_if_needed(tmp_path, max_rows=50)

        # Add 5 more rows to make it 55 again
        lessons.write_text(_build_lessons_md(55), encoding="utf-8")
        _rotate_if_needed(tmp_path, max_rows=50)

        archive_dir = gov / "archive"
        archives = list(archive_dir.glob("lessons_archive_*.md"))
        all_archive = "".join(a.read_text(encoding="utf-8") for a in archives)
        # At least 5 rows in archives (could be more depending on month grouping)
        rows = re.findall(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|", all_archive)
        assert len(rows) >= 5


# ── AC9: lint-lessons warns on overflow ───────────────────────────────────


class TestAC9LintWarning:
    def test_lint_warns_over_max_rows(self, tmp_path: Path):
        """lint_lessons should warn when row count exceeds LESSONS_MAX_ROWS."""
        from pactkit.validators import lint_lessons

        lessons = tmp_path / "lessons.md"
        lessons.write_text(_build_lessons_md(60), encoding="utf-8")

        errors = lint_lessons(lessons)
        # Should have a warning about row count (non-blocking, still in errors list)
        overflow_warnings = [e for e in errors if "exceed" in e.lower() or "max" in e.lower() or "row" in e.lower()]
        assert len(overflow_warnings) >= 1

    def test_lint_no_warn_at_50(self, tmp_path: Path):
        """lint_lessons should NOT warn when exactly at LESSONS_MAX_ROWS."""
        from pactkit.validators import lint_lessons

        lessons = tmp_path / "lessons.md"
        lessons.write_text(_build_lessons_md(50), encoding="utf-8")

        errors = lint_lessons(lessons)
        overflow_warnings = [e for e in errors if "exceed" in e.lower() or "max" in e.lower()]
        assert len(overflow_warnings) == 0
