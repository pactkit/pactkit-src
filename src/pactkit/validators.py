"""Document structure validators — R2 (STORY-slim-014).

Validate document structure against schemas defined in pactkit.schemas.
All three validators follow the same contract:
    - Return an empty list on success.
    - Return a list of human-readable error strings on failure.
"""

from __future__ import annotations

import re
from pathlib import Path

from pactkit.schemas import (
    ADR_REQUIRED_METADATA_FIELDS,
    ADR_REQUIRED_SECTIONS,
    ADR_STATUSES,
    CONTEXT_HEADER,
    CONTEXT_SECTIONS,
    LESSONS_MAX_ROWS,
    LESSONS_TABLE_HEADER,
    LESSONS_TABLE_SEPARATOR,
    TEST_CASE_KEYWORDS,
    TEST_CASE_SCENARIO_PATTERN,
)


def lint_context(path: Path) -> list[str]:
    """Validate context.md structure.

    Checks:
    - File exists.
    - CONTEXT_HEADER is present.
    - All CONTEXT_SECTIONS headers are present.

    Returns:
        List of error messages; empty list means the file is valid.
    """
    errors: list[str] = []

    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"File not found: {path}"]
    except OSError as exc:
        return [f"Cannot read file {path}: {exc}"]

    if CONTEXT_HEADER not in content:
        errors.append(f"Missing header: '{CONTEXT_HEADER}'")

    for section in CONTEXT_SECTIONS:
        if section not in content:
            errors.append(f"Missing section: '{section}'")

    return errors


def lint_lessons(path: Path) -> list[str]:
    """Validate lessons.md structure.

    Checks:
    - File exists.
    - LESSONS_TABLE_HEADER is present.
    - LESSONS_TABLE_SEPARATOR is present.

    Returns:
        List of error messages; empty list means the file is valid.
    """
    errors: list[str] = []

    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"File not found: {path}"]
    except OSError as exc:
        return [f"Cannot read file {path}: {exc}"]

    if LESSONS_TABLE_HEADER not in content:
        errors.append(f"Missing table header: '{LESSONS_TABLE_HEADER}'")

    if LESSONS_TABLE_SEPARATOR not in content:
        errors.append(f"Missing table separator: '{LESSONS_TABLE_SEPARATOR}'")

    # Validate row column count (3 columns per LESSONS_ROW_FORMAT)
    lines = content.splitlines()
    in_table = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == LESSONS_TABLE_SEPARATOR:
            in_table = True
            continue
        if in_table and stripped.startswith("|") and stripped.endswith("|"):
            # A proper 3-col row like "| a | b | c |" splits to ['', ' a ', ' b ', ' c ', '']
            col_count = len(stripped.split("|")) - 2  # subtract leading/trailing empty
            if col_count != 3:
                errors.append(
                    f"Line {i}: expected 3 columns but found {col_count}"
                )
        elif in_table and not stripped.startswith("|"):
            # End of table
            break

    # STORY-slim-075 R4: Warn if row count exceeds LESSONS_MAX_ROWS (non-blocking)
    row_count = sum(
        1
        for line in lines
        if line.strip().startswith("|")
        and re.search(r"\d{4}-\d{2}-\d{2}", line)
    )
    if row_count > LESSONS_MAX_ROWS:
        errors.append(
            f"Row count ({row_count}) exceeds max ({LESSONS_MAX_ROWS}) — consider running rotation"
        )

    return errors


def lint_testcase(path: Path) -> list[str]:
    """Validate test case file structure.

    Checks:
    - File exists.
    - At least one match for TEST_CASE_SCENARIO_PATTERN (e.g. '## TC-01:').
    - All TEST_CASE_KEYWORDS are present (e.g. '**Given**', '**When**', '**Then**').

    Returns:
        List of error messages; empty list means the file is valid.
    """
    errors: list[str] = []

    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"File not found: {path}"]
    except OSError as exc:
        return [f"Cannot read file {path}: {exc}"]

    if not re.search(TEST_CASE_SCENARIO_PATTERN, content):
        errors.append(
            f"No scenario headings found. Expected pattern matching '{TEST_CASE_SCENARIO_PATTERN}' "
            "(e.g. '## TC-01: ...')"
        )

    for keyword in TEST_CASE_KEYWORDS:
        if keyword not in content:
            errors.append(f"Missing keyword: '{keyword}'")

    return errors


def lint_adr(path: Path) -> list[str]:
    """Validate an ADR file structure (STORY-slim-2026090333d6b72f7645).

    Checks:
    - File exists.
    - All ADR_REQUIRED_METADATA_FIELDS rows are present.
    - Status is one of ADR_STATUSES.
    - All ADR_REQUIRED_SECTIONS are present.
    - Supersession consistency: a declared Supersedes target must exist and
      carry a back-referencing Superseded-by; a superseded ADR must say by whom.

    Returns:
        List of error messages; empty list means the file is valid.
    """
    errors: list[str] = []

    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"File not found: {path}"]
    except OSError as exc:
        return [f"Cannot read file {path}: {exc}"]

    for field in ADR_REQUIRED_METADATA_FIELDS:
        if f"| {field} " not in content:
            errors.append(f"Missing metadata field: '{field}'")

    status_match = re.search(r"\|\s*Status\s*\|\s*(\S+)\s*\|", content)
    if not status_match:
        errors.append("Missing Status value in metadata table")
    elif status_match.group(1) not in ADR_STATUSES:
        errors.append(
            f"Invalid Status '{status_match.group(1)}' — expected one of {', '.join(ADR_STATUSES)}"
        )

    for section in ADR_REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"Missing section: '{section}'")

    own_id = path.stem
    supersedes_match = re.search(r"\|\s*Supersedes\s*\|\s*([^|\s][^|]*?)\s*\|", content)
    supersedes = supersedes_match.group(1).strip() if supersedes_match else "None"
    if supersedes != "None":
        target = path.parent / f"{supersedes}.md"
        if not target.exists():
            errors.append(f"Supersedes target not found: {supersedes}")
        else:
            target_text = target.read_text(encoding="utf-8")
            if f"| Superseded-by | {own_id} |" not in target_text:
                errors.append(
                    f"Supersedes target '{supersedes}' lacks back-reference "
                    f"'| Superseded-by | {own_id} |' — re-run create_adr or fix manually"
                )

    superseded_by_match = re.search(r"\|\s*Superseded-by\s*\|\s*(\S+)\s*\|", content)
    if status_match and status_match.group(1) == "superseded":
        if not superseded_by_match or superseded_by_match.group(1) == "None":
            errors.append("Status is 'superseded' but Superseded-by is not set")

    return errors
