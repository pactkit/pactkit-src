"""Context generator — produce docs/product/context.md from board + git + lessons.

Implements the canonical format from schemas.py:CONTEXT_SECTIONS (STORY-slim-014 R1).
Replaces the prompt-based context.md generation from Done Phase 4.5.

The function generate_context() returns a string; it does NOT write the file.
The caller is responsible for persisting the result.
"""
from __future__ import annotations

import datetime
import re
import subprocess
from pathlib import Path

from pactkit.schemas import (
    BOARD_SECTION_BACKLOG,
    BOARD_SECTION_DONE,
    BOARD_SECTION_IN_PROGRESS,
    CONTEXT_HEADER,
    CONTEXT_SECTION_CONTINUATION,
    CONTEXT_SECTIONS,
    LESSONS_TABLE_HEADER,
)

# Pattern to detect story title lines (### [STORY-...] or ### STORY-...)
_STORY_TITLE_RE = re.compile(r"^#{3,4}\s+\[?(?:STORY|HOTFIX|BUG)-", re.MULTILINE)


def context_output_path(project_root: Path) -> Path:
    """Return the ignored local Context projection path."""
    return project_root.resolve() / ".pactkit" / "context.md"


# ---------------------------------------------------------------------------
# Board parsing helpers
# ---------------------------------------------------------------------------

def _parse_board(board_text: str) -> dict[str, int]:
    """Return counts for each board section: backlog, in_progress, done."""
    sections = {
        "backlog": 0,
        "in_progress": 0,
        "done": 0,
    }

    # Find section boundaries
    bp = board_text.find(BOARD_SECTION_BACKLOG)
    ip = board_text.find(BOARD_SECTION_IN_PROGRESS)
    dp = board_text.find(BOARD_SECTION_DONE)

    if bp == -1 or ip == -1 or dp == -1:
        return sections

    backlog_chunk = board_text[bp:ip]
    in_progress_chunk = board_text[ip:dp]
    done_chunk = board_text[dp:]

    sections["backlog"] = len(_STORY_TITLE_RE.findall(backlog_chunk))
    sections["in_progress"] = len(_STORY_TITLE_RE.findall(in_progress_chunk))
    sections["done"] = len(_STORY_TITLE_RE.findall(done_chunk))

    return sections


def _parse_active_stories(board_text: str) -> list[str]:
    """Return a list of 'STORY-ID: title' lines for In Progress stories."""
    ip = board_text.find(BOARD_SECTION_IN_PROGRESS)
    dp = board_text.find(BOARD_SECTION_DONE)
    if ip == -1:
        return []
    chunk = board_text[ip:dp] if dp != -1 else board_text[ip:]

    stories = []
    title_re = re.compile(r"^#{3,4}\s+\[?([A-Z]+-[a-zA-Z0-9-]+)\]?\s*(.*)", re.MULTILINE)
    for m in title_re.finditer(chunk):
        sid = m.group(1)
        title = m.group(2).strip()
        stories.append(f"- {sid}: {title}")
    return stories


def _parse_recent_completions(board_text: str, n: int = 3) -> list[str]:
    """Return the last *n* completed stories as 'STORY-ID: title' lines."""
    dp = board_text.find(BOARD_SECTION_DONE)
    if dp == -1:
        return []
    chunk = board_text[dp:]

    stories = []
    title_re = re.compile(r"^#{3,4}\s+\[?([A-Z]+-[a-zA-Z0-9-]+)\]?\s*(.*)", re.MULTILINE)
    for m in title_re.finditer(chunk):
        sid = m.group(1)
        title = m.group(2).strip()
        stories.append(f"- {sid}: {title}")
    return stories[-n:]


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _get_git_branches(project_root: Path) -> str:
    """Return a string describing active branches from `git branch`."""
    try:
        result = subprocess.run(
            ["git", "branch"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip() or "None"
    except Exception:
        pass
    return "None"


# ---------------------------------------------------------------------------
# Lessons helpers
# ---------------------------------------------------------------------------

def _parse_last_lessons(lessons_path: Path, n: int = 5) -> list[str]:
    """Extract the last *n* data rows from the lessons Markdown table."""
    if not lessons_path.exists():
        return []

    text = lessons_path.read_text(encoding="utf-8")
    rows = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and LESSONS_TABLE_HEADER.split("|")[1].strip() in stripped:
            in_table = True
            continue
        if in_table:
            if stripped.startswith("|---"):
                continue
            if stripped.startswith("|") and stripped.endswith("|"):
                # Extract lesson column (column index 2, 1-based)
                cols = [c.strip() for c in stripped.strip("|").split("|")]
                if len(cols) >= 2:
                    rows.append(f"- {cols[1]}")
            elif stripped == "":
                # blank line may signal end of table; continue to pick up all rows
                pass
            else:
                in_table = False

    return rows[-n:]


# ---------------------------------------------------------------------------
# Agent Continuation helpers (STORY-slim-071)
# ---------------------------------------------------------------------------

# Pattern to extract AC titles: ### AC1: Title (R1)
_AC_TITLE_RE = re.compile(r"^###\s+(AC\d+:\s*.+?)(?:\s*\(R\d+\))?\s*$", re.MULTILINE)

# Pattern to extract story ID from command string
_STORY_ID_FROM_CMD_RE = re.compile(r"((?:STORY|BUG|HOTFIX)-[\w]+-\d+)")


def _sanitize_text(text: str) -> str:
    """Sanitize free-text input: keep only the first line, strip markdown headers."""
    # Take only the first line to prevent injection of markdown structure
    first_line = text.split("\n")[0]
    # Remove any markdown header markers
    sanitized = re.sub(r"#{1,6}\s+", "", first_line)
    return sanitized.strip()


def _extract_sprint_contract(spec_path: Path, completed_acs: set[str] | None = None) -> str:
    """Extract AC titles from a spec file as a markdown checklist.

    Returns a string like:
        ### Sprint Contract (STORY-slim-070)
        - [ ] AC1: First Check
        - [ ] AC2: Second Check
    """
    if not spec_path.exists():
        return ""

    text = spec_path.read_text(encoding="utf-8")
    ac_matches = _AC_TITLE_RE.findall(text)
    if not ac_matches:
        return ""

    # Extract story ID from filename
    stem = spec_path.stem
    lines = [f"### Sprint Contract ({stem})"]
    completed_acs = completed_acs or set()
    for ac_title in ac_matches:
        ac_id = ac_title.split(":", 1)[0]
        marker = "x" if ac_id in completed_acs else " "
        lines.append(f"- [{marker}] {ac_title}")

    return "\n".join(lines)


def _checkpoint_continuation(project_root: Path, story_id: str) -> str | None:
    """Render authoritative checkpoint state, or None for legacy handoff."""
    try:
        from pactkit.continuation import ContinuationStore

        store = ContinuationStore(project_root)
        state = store.read(story_id)
        if state is None:
            return None
        decision = store.resume(story_id)
    except Exception:
        return None

    lines = [
        f"Verified Continuation: {story_id}",
        f"Status: {state['status']}",
        f"Phase Reached: {state['phase']}",
        f"Safe Boundary: {state['step_id']}",
    ]
    if decision["decision"] == "resume_at":
        lines.append(f"Next Safe Step: {decision['next_step']}")
    else:
        lines.append("Continuation requires verification: " + "; ".join(decision["reasons"]))

    spec_path = project_root / "docs" / "specs" / f"{story_id}.md"
    completed_acs: set[str] = set()
    if state["status"] == "completed":
        coverage = state["evidence"].get("acceptance_coverage", {})
        if isinstance(coverage, dict):
            completed_acs = set(coverage)
    contract = _extract_sprint_contract(spec_path, completed_acs)
    if contract:
        lines.extend(("", contract))
    return "\n".join(lines)


def _generate_continuation(
    project_root: Path,
    board_text: str,
    continuation_args: dict[str, str] | None,
) -> str:
    """Generate the Agent Continuation section content.

    Args:
        project_root: Project root directory.
        board_text: The sprint board content (for detecting in-progress stories).
        continuation_args: Dict with keys 'last_command', 'phase', 'blockers'.
            If None, returns the default "no active session" message.

    Returns:
        Content for the ## Agent Continuation section (without the header).
    """
    if continuation_args is None:
        # STORY-slim-146: checkpoint state is authoritative when available;
        # legacy projects retain the original no-session response.
        active = _parse_active_stories(board_text)
        if active:
            story_match = _STORY_ID_FROM_CMD_RE.search(active[0])
            if story_match:
                checkpoint = _checkpoint_continuation(project_root, story_match.group(1))
                if checkpoint:
                    return checkpoint
        return "No active work session."

    last_cmd = _sanitize_text(continuation_args.get("last_command", "unknown"))
    phase = _sanitize_text(continuation_args.get("phase", "unknown"))
    blockers = continuation_args.get("blockers")

    lines = [
        f"Last Command: {last_cmd}",
        f"Phase Reached: {phase}",
    ]

    if blockers:
        lines.append(f"Blockers: {_sanitize_text(blockers)}")

    # Extract story ID from the command to find spec
    story_match = _STORY_ID_FROM_CMD_RE.search(last_cmd)
    if story_match:
        story_id = story_match.group(1)
        checkpoint = _checkpoint_continuation(project_root, story_id)
        if checkpoint:
            return checkpoint
        spec_path = project_root / "docs" / "specs" / f"{story_id}.md"
        contract = _extract_sprint_contract(spec_path)
        if contract:
            lines.append("")
            lines.append(contract)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def generate_context(
    project_root: Path,
    command: str = "pactkit context",
    continuation_args: dict[str, str] | None = None,
) -> str:
    """Generate the contents of docs/product/context.md.

    Reads the sprint board, git branch list, and lessons file, then composes
    the canonical context.md format defined in schemas.py:CONTEXT_SECTIONS.

    Args:
        project_root: Absolute path to the project root directory.
        command: The command name to include in the "Last updated" header.

    Returns:
        The full context.md content as a string. Does NOT write to disk.
    """
    timestamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    # ---- Story facts (legacy Board is read-only fallback during migration) ----
    from pactkit.governance import BoardRenderer, LessonRepository, StoryRepository

    story_repo = StoryRepository(project_root)
    records = story_repo.list()
    board_path = project_root / "docs" / "product" / "sprint_board.md"
    board_found = bool(records) or board_path.exists()
    board_text = BoardRenderer(story_repo).render() if records else (
        board_path.read_text(encoding="utf-8") if board_path.exists() else ""
    )

    if board_found:
        counts = _parse_board(board_text)
        sprint_status_line = (
            f"Backlog: {counts['backlog']} | "
            f"In Progress: {counts['in_progress']} | "
            f"Done: {counts['done']} stories"
        )
    else:
        sprint_status_line = "No board found (run `/project-init` to create sprint_board.md)"

    active_stories = _parse_active_stories(board_text) if board_found else []
    recent_completions = _parse_recent_completions(board_text) if board_found else []

    # ---- Git branches ----
    branches = _get_git_branches(project_root)

    # ---- Lessons ----
    lesson_records = LessonRepository(project_root).recent()
    if lesson_records:
        lessons = [f"- {record['text']}" for record in reversed(lesson_records)]
    else:
        lessons_path = project_root / "docs" / "architecture" / "governance" / "lessons.md"
        lessons = _parse_last_lessons(lessons_path)

    # ---- Compose output ----
    lines: list[str] = [
        CONTEXT_HEADER,
        f"> Last updated: {timestamp} by {command}",
        "",
        CONTEXT_SECTIONS[0],  # ## Sprint Status
        sprint_status_line,
        "",
        CONTEXT_SECTIONS[1],  # ## Current Stories
    ]
    if active_stories:
        lines.extend(active_stories)
    else:
        lines.append("None")
    lines.append("")

    lines.append(CONTEXT_SECTIONS[2])  # ## Recent Completions
    if recent_completions:
        lines.extend(recent_completions)
    else:
        lines.append("None")
    lines.append("")

    lines.append(CONTEXT_SECTIONS[3])  # ## Active Branches
    lines.append(branches)
    lines.append("")

    lines.append(CONTEXT_SECTIONS[4])  # ## Key Decisions
    if lessons:
        lines.extend(lessons)
    else:
        lines.append("None")
    lines.append("")

    lines.append(CONTEXT_SECTIONS[5])  # ## Next Recommended Action
    if active_stories:
        lines.append("`/project-act` (stories in progress)")
    elif counts.get("backlog", 0) if board_found else False:
        lines.append("`/project-plan`")
    else:
        lines.append("`/project-design`")
    lines.append("")

    # ---- Agent Continuation (STORY-slim-071) ----
    lines.append(CONTEXT_SECTION_CONTINUATION)
    continuation_content = _generate_continuation(
        project_root, board_text, continuation_args,
    )
    lines.append(continuation_content)
    lines.append("")

    return "\n".join(lines)
