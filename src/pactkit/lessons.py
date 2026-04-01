"""Lesson auto-append with specificity check and dedup (STORY-slim-017 R1)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from pactkit.schemas import (
    LESSONS_MAX_ROWS,
    LESSONS_ROW_FORMAT,
    LESSONS_TABLE_HEADER,
    LESSONS_TABLE_SEPARATOR,
)


def _is_specific(text: str) -> bool:
    """Check if text references a concrete file, function, or code pattern."""
    patterns = [
        r"\.\w{2,4}\b",      # file extensions (.py, .ts, .go, .java)
        r"\w+\(\)",           # function calls foo()
        r"\w+/\w+",          # path-like patterns
        r"`[^`]+`",           # inline code
    ]
    return any(re.search(p, text) for p in patterns)


def _jaccard_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity on word sets."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _get_last_n_entries(text: str, n: int = 5) -> list[str]:
    """Extract the last N lesson texts from lessons.md content."""
    rows = re.findall(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*(.+?)\s*\|[^|]*\|", text)
    return rows[-n:] if rows else []


def _is_duplicate(text: str, recent_entries: list[str], threshold: float = 0.5) -> bool:
    """Check if text is too similar to any recent entry."""
    for entry in recent_entries:
        if _jaccard_similarity(text, entry) >= threshold:
            return True
    return False


def _rotate_if_needed(project_root: Path, max_rows: int = LESSONS_MAX_ROWS) -> None:
    """Rotate lessons.md if row count exceeds max_rows.

    Moves the oldest entries to docs/architecture/governance/archive/lessons_archive_YYYYMM.md.
    Atomic: read → split → write archive → write truncated lessons.md.
    """
    lessons_path = project_root / "docs" / "architecture" / "governance" / "lessons.md"
    if not lessons_path.exists():
        return

    content = lessons_path.read_text(encoding="utf-8")
    # Extract all data rows (lines starting with | and containing a date)
    lines = content.splitlines(keepends=True)

    header_lines: list[str] = []
    data_rows: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped == LESSONS_TABLE_SEPARATOR:
            header_lines.append(line)
            in_table = True
            continue
        if in_table and stripped.startswith("|") and re.search(r"\d{4}-\d{2}-\d{2}", stripped):
            data_rows.append(line)
        else:
            if not in_table:
                header_lines.append(line)

    if len(data_rows) <= max_rows:
        return

    # Split: oldest go to archive, newest stay
    overflow_count = len(data_rows) - max_rows
    overflow_rows = data_rows[:overflow_count]
    keep_rows = data_rows[overflow_count:]

    # Group overflow rows by month for archive files
    month_groups: dict[str, list[str]] = {}
    for row in overflow_rows:
        m = re.search(r"(\d{4}-\d{2})", row)
        month_key = m.group(1).replace("-", "") if m else date.today().strftime("%Y%m")
        month_groups.setdefault(month_key, []).append(row)

    # Write archive files (append to existing if present)
    archive_dir = project_root / "docs" / "architecture" / "governance" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    for month_key, rows in month_groups.items():
        archive_path = archive_dir / f"lessons_archive_{month_key}.md"
        if archive_path.exists():
            # Append rows to existing archive
            with open(archive_path, "a", encoding="utf-8") as f:
                for row in rows:
                    f.write(row if row.endswith("\n") else row + "\n")
        else:
            # Create new archive with header
            with open(archive_path, "w", encoding="utf-8") as f:
                f.write(f"# Lessons Archive ({month_key[:4]}-{month_key[4:]})\n\n")
                f.write(LESSONS_TABLE_HEADER + "\n")
                f.write(LESSONS_TABLE_SEPARATOR + "\n")
                for row in rows:
                    f.write(row if row.endswith("\n") else row + "\n")

    # Write truncated lessons.md
    with open(lessons_path, "w", encoding="utf-8") as f:
        for line in header_lines:
            f.write(line if line.endswith("\n") else line + "\n")
        for row in keep_rows:
            f.write(row if row.endswith("\n") else row + "\n")


def append_lesson(
    project_root: Path,
    story_id: str,
    text: str,
    context: str = "",
) -> dict:
    """Append a lesson to lessons.md if it passes specificity and dedup checks.

    Returns:
        {"action": "appended"|"skipped", "reason": str}
    """
    lessons_path = project_root / "docs" / "architecture" / "governance" / "lessons.md"

    if not lessons_path.exists():
        return {"action": "skipped", "reason": "lessons.md not found"}

    if not _is_specific(text):
        return {"action": "skipped", "reason": "not specific enough — no file/function reference"}

    content = lessons_path.read_text(encoding="utf-8")
    recent = _get_last_n_entries(content)

    if _is_duplicate(text, recent):
        return {"action": "skipped", "reason": "duplicate of recent entry"}

    # Rotate before appending to stay within LESSONS_MAX_ROWS
    _rotate_if_needed(project_root)

    # Auto-repair: insert table header if missing
    content = lessons_path.read_text(encoding="utf-8")
    if LESSONS_TABLE_SEPARATOR not in content:
        with open(lessons_path, "a", encoding="utf-8") as f:
            if not content.endswith("\n"):
                f.write("\n")
            f.write(LESSONS_TABLE_HEADER + "\n")
            f.write(LESSONS_TABLE_SEPARATOR + "\n")

    today = date.today().isoformat()
    ctx = context if context else story_id
    row = LESSONS_ROW_FORMAT.format(date=today, lesson=text, context=ctx) + "\n"

    with open(lessons_path, "a", encoding="utf-8") as f:
        f.write(row)

    return {"action": "appended", "reason": f"lesson added for {story_id}"}
