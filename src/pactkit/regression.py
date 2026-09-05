"""Regression decision tree — classify changed files to decide test scope (STORY-slim-014 R1).

Replaces the prompt-based regression decision from Done Phase 2.5.
STORY-slim-20260905efced66ebc9c adds verification fingerprints: Act records the
code state when its regression run is green, Done compares against that record
instead of guessing a diff base like HEAD~1.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pactkit.id_generator import ITEM_ID_RE
from pactkit.utils import atomic_write

# Files that match these patterns are considered "doc-only" — safe to skip tests.
# HOTFIX-slim-20260901469666ef23a8: repo/agent metadata (.gitignore,
# .claude/**, .codex/**) carries no runtime code — a design-baseline or
# governance commit containing them must not lose the doc-only skip.
_DOC_ONLY_PATTERNS: tuple[str, ...] = (
    "docs/**",
    "*.md",
    "README*",
    "*.txt",
    ".gitignore",
    ".claude/**",
    ".codex/**",
    # STORY-slim-20260905efced66ebc9c R5: .pactkit/ holds local projections
    # (context, preflight receipts, verification records, events).  They must
    # not appear in the verification fingerprint — recording a fingerprint
    # would otherwise invalidate itself in repos that do not ignore .pactkit/.
    ".pactkit/**",
)
# tests/** is deliberately NOT doc-only: a commit that modifies tests must
# run them (STORY-slim-20260826ce35b77ce005 R5).

# Version/dependency manifest files that trigger full regression.
_VERSION_FILES: frozenset[str] = frozenset(
    [
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
    ]
)


def _is_doc_only(path: str) -> bool:
    """Return True if *path* matches any doc-only pattern."""
    # Normalise separators
    norm = path.replace("\\", "/")
    for pattern in _DOC_ONLY_PATTERNS:
        # fnmatch handles * but not ** — handle ** via startswith trick
        if "**" in pattern:
            prefix = pattern.split("**")[0].rstrip("/")
            if norm.startswith(prefix + "/") or norm == prefix:
                return True
        else:
            if fnmatch.fnmatch(norm, pattern) or fnmatch.fnmatch(norm.split("/")[-1], pattern):
                return True
    return False


def _is_version_file(path: str) -> bool:
    """Return True if *path* is a known version/dependency manifest (basename only)."""
    basename = path.replace("\\", "/").rsplit("/", 1)[-1]
    return basename in _VERSION_FILES


def classify_changes(changed_files: list[str]) -> tuple[str, str]:
    """Classify a list of changed file paths and decide the regression strategy.

    Decision tree (in priority order):
        1. Empty list or ALL files are doc-only → ('skip', 'doc-only change')
        2. ANY file is a version/dependency manifest → ('full', 'version/dependency change')
        3. Default → ('impact', 'run mapped tests')

    Args:
        changed_files: List of file paths as returned by ``git diff --name-only``.

    Returns:
        (strategy, reason) where strategy is one of 'skip', 'full', or 'impact'.
    """
    if not changed_files:
        return ("skip", "doc-only change")

    if all(_is_doc_only(f) for f in changed_files):
        return ("skip", "doc-only change")

    if any(_is_version_file(f) for f in changed_files):
        return ("full", "version/dependency change")

    return ("impact", "run mapped tests")


# ---------------------------------------------------------------------------
# Verification fingerprints (STORY-slim-20260905efced66ebc9c R5)
# ---------------------------------------------------------------------------

VERIFICATION_SCHEMA_VERSION = 1


def verification_path(root: Path, story_id: str) -> Path:
    """Local projection path for one story's verification record."""
    return Path(root) / ".pactkit" / "verification" / f"{story_id}.json"


def _validated_story_id(story_id: str) -> str:
    """Reject anything that is not a bare item ID (it becomes a filename)."""
    if not ITEM_ID_RE.fullmatch(story_id):
        raise ValueError(f"invalid story id: {story_id!r}")
    return story_id


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
    )


def _dirty_state(root: Path) -> list[tuple[str, str]]:
    """(path, status:content-hash) for dirty/untracked non-doc-only files.

    Doc-only files are excluded: they never invalidate test evidence.  The
    content hash (not just the path) is required — a file dirty at record
    time and dirty again now with different content must read as changed.
    """
    result = _git(root, "status", "--porcelain")
    if result.returncode != 0:
        return []
    entries: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2].strip()
        path = line[3:].strip().strip('"')
        if " -> " in path:  # rename entries: the new path is what exists now
            path = path.split(" -> ")[1]
        if not path or _is_doc_only(path):
            continue
        target = Path(root) / path
        digest = (
            hashlib.sha256(target.read_bytes()).hexdigest()
            if target.is_file() else "deleted"
        )
        entries.append((path, f"{status}:{digest}"))
    return sorted(entries)


def _fingerprint(commit: str | None, state: list[tuple[str, str]]) -> str:
    payload = f"{commit or ''}\n" + "\n".join(f"{path} {marker}" for path, marker in state)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def record_verification(root: Path, story_id: str) -> str:
    """Stamp the code state after a green regression run.

    Returns a human-readable summary.  Without git the record degrades to a
    notice (exit-friendly): a missing record never blocks Done — it falls
    back to plain diff classification.
    """
    _validated_story_id(story_id)
    head = _git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        return "Record: unavailable (not a git repository) — Done will classify without a fingerprint"
    commit = head.stdout.strip()
    state = _dirty_state(root)
    record = {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "story_id": story_id,
        "commit": commit,
        "files": [path for path, _ in state],
        "state": [[path, marker] for path, marker in state],
        "fingerprint": _fingerprint(commit, state),
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path = verification_path(root, story_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return (
        f"Record: {commit[:12]} + {len(state)} dirty source/test file(s)"
        f" -> {path.name}"
    )


def check_verification(root: Path, story_id: str) -> str:
    """Compare the current code state against the recorded fingerprint.

    VERIFIED-CURRENT — reuse the recorded regression evidence
    STALE — {files}: the listed source/test files changed since the record
    NO-RECORD — nothing recorded; Done falls back to diff classification
    """
    _validated_story_id(story_id)
    path = verification_path(root, story_id)
    if not path.is_file():
        return "NO-RECORD — no verification record; classify changes with git diff"
    record = json.loads(path.read_text(encoding="utf-8"))
    head = _git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        return "STALE — git unavailable; classify changes with standard tools"
    commit = head.stdout.strip()
    current = _dirty_state(root)
    if record.get("fingerprint") == _fingerprint(commit, current):
        return "VERIFIED-CURRENT — reuse the recorded regression evidence"
    recorded_state = {path: marker for path, marker in record.get("state", [])}
    current_state = dict(current)
    changed = {
        path
        for path, marker in current_state.items()
        if recorded_state.get(path) != marker
    }
    changed.update(path for path in recorded_state if path not in current_state)
    if record.get("commit") and record["commit"] != commit:
        diff = _git(root, "diff", "--name-only", record["commit"], commit)
        if diff.returncode == 0:
            changed.update(
                f for f in diff.stdout.splitlines() if f and not _is_doc_only(f)
            )
    listed = ", ".join(sorted(changed)) or "dirty state differs"
    return f"STALE — source/test changed since verification: {listed}"
