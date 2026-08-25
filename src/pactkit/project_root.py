"""Canonical PactKit project-root discovery.

Project state must never be rooted at an arbitrary process working directory.
This module is the single boundary used by CLI commands and hooks before they
read or write project-local state.
"""

from __future__ import annotations

from pathlib import Path

from pactkit.profiles import PACTKIT_YAML_CANDIDATES


class ProjectRootNotFound(ValueError):
    """Raised when no initialized PactKit project owns a path."""


def _is_initialized(root: Path) -> bool:
    if any((root / candidate).is_file() for candidate in PACTKIT_YAML_CANDIDATES):
        return True
    # Backward-compatible markers for projects initialized before a local
    # pactkit.yaml was mandatory. A single canonical governance path is
    # sufficient because lightweight commands historically support partial
    # projects (for example, spec-lint with only docs/specs present).
    governance = root / "docs"
    legacy_markers = (
        governance / "product" / "sprint_board.md",
        governance / "specs",
        governance / "test_cases",
        governance / "architecture" / "graphs",
        governance / "architecture" / "governance",
    )
    if any(marker.exists() for marker in legacy_markers):
        return True
    state = root / ".pactkit"
    return any((state / child).is_dir() for child in ("continuations", "workflow-runs"))


def resolve_project_root(start: Path | str | None = None, *, explicit: Path | str | None = None) -> Path:
    """Return the nearest initialized PactKit project ancestor.

    An explicit root is authoritative but is still validated.  Discovery uses
    PactKit markers instead of a bare Git root so running in an unrelated
    repository cannot create project state there.
    """
    if explicit is not None:
        candidate = Path(explicit).expanduser().resolve()
        if not _is_initialized(candidate):
            raise ProjectRootNotFound(
                f"{candidate} is not an initialized PactKit project; no pactkit.yaml marker found"
            )
        return candidate

    current = Path(start or Path.cwd()).expanduser().resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if _is_initialized(candidate):
            return candidate
    raise ProjectRootNotFound(
        f"PactKit project root not found from {current}; run inside an initialized project "
        "or pass --project-root"
    )
