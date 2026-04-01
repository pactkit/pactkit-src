"""Artifact cleaner — remove language-specific temp files (STORY-slim-014 R1).

Replaces the prompt-based cleanup from Done Phase 2.
"""
from __future__ import annotations

import shutil
from pathlib import Path

# Cleanup patterns per stack (canonical source: prompts/workflows.py LANG_PROFILES)
_CLEANUP_PATTERNS: dict[str, list[str]] = {
    "python": ["__pycache__", ".pytest_cache", "*.pyc"],
    "node": ["node_modules/.cache", ".next", "dist", "coverage"],
    "go": ["cover.out", "cover.html"],
    "java": ["target/", "build/", ".gradle/"],
}

# Stack detection markers (ordered by priority)
_STACK_MARKERS: list[tuple[str, str]] = [
    ("pyproject.toml", "python"),
    ("setup.py", "python"),
    ("setup.cfg", "python"),
    ("package.json", "node"),
    ("go.mod", "go"),
    ("pom.xml", "java"),
    ("build.gradle", "java"),
]


def detect_stacks(project_root: Path) -> list[str]:
    """Detect all project stacks from marker files.

    Scans root level first, then one level of subdirectories (monorepo support).
    Returns deduplicated list of stack names in _STACK_MARKERS order.
    Defaults to ['python'] if no markers found.
    """
    seen: set[str] = set()
    stacks: list[str] = []
    # 1. Root-level scan
    for marker_file, stack in _STACK_MARKERS:
        if (project_root / marker_file).exists() and stack not in seen:
            seen.add(stack)
            stacks.append(stack)
    # 2. Depth-1 subdirectory scan (STORY-slim-077: monorepo support)
    try:
        subdirs = [p for p in project_root.iterdir() if p.is_dir() and not p.name.startswith(".")]
    except OSError:
        subdirs = []
    for subdir in subdirs:
        for marker_file, stack in _STACK_MARKERS:
            if (subdir / marker_file).exists() and stack not in seen:
                seen.add(stack)
                stacks.append(stack)
    return stacks if stacks else ["python"]


def detect_stack(project_root: Path) -> str:
    """Detect primary project stack from marker files.

    Backward-compatible wrapper — returns the first detected stack.
    """
    return detect_stacks(project_root)[0]


def clean_artifacts(
    project_root: Path,
    stack: str = "auto",
    dry_run: bool = False,
) -> list[Path]:
    """Remove language-specific temp artifacts.

    Args:
        project_root: Project root directory.
        stack: Language stack ('python', 'node', 'go', 'java', 'auto').
        dry_run: If True, list files without deleting.

    Returns:
        List of removed (or would-be-removed) paths.
    """
    if stack == "auto":
        stack = detect_stack(project_root)

    patterns = _CLEANUP_PATTERNS.get(stack, [])
    removed: list[Path] = []

    for pattern in patterns:
        if "*" in pattern:
            # Glob pattern (e.g., "*.pyc")
            for match in project_root.rglob(pattern):
                removed.append(match)
                if not dry_run:
                    if match.is_dir():
                        shutil.rmtree(match)
                    else:
                        match.unlink()
        else:
            # Directory or file name (e.g., "__pycache__", ".pytest_cache")
            clean_name = pattern.rstrip("/")
            for match in project_root.rglob(clean_name):
                removed.append(match)
                if not dry_run:
                    if match.is_dir():
                        shutil.rmtree(match)
                    else:
                        match.unlink()

    return removed
