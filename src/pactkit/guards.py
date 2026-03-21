"""Init guard — deterministic project readiness check (STORY-slim-014 R1).

Replaces the prompt-based Init Guard from Plan Phase 0.5.
"""
from __future__ import annotations

from pathlib import Path

from pactkit.config import find_pactkit_yaml


def check_init_markers(project_root: Path) -> tuple[bool, list[str]]:
    """Check whether the project has been initialized with PactKit.

    Checks 3 markers:
        1. pactkit.yaml exists (via find_pactkit_yaml)
        2. docs/product/sprint_board.md exists
        3. docs/architecture/graphs/ directory exists

    Returns:
        (ok, missing) — True if all present, list of missing marker descriptions.
    """
    missing: list[str] = []

    # 1. pactkit.yaml
    if find_pactkit_yaml(project_root) is None:
        missing.append("pactkit.yaml not found (run `pactkit init`)")

    # 2. Sprint board
    board = project_root / "docs" / "product" / "sprint_board.md"
    if not board.exists():
        missing.append("docs/product/sprint_board.md not found (run `/project-init`)")

    # 3. Architecture graphs dir
    graphs = project_root / "docs" / "architecture" / "graphs"
    if not graphs.is_dir():
        missing.append("docs/architecture/graphs/ not found (run `/project-init`)")

    return (len(missing) == 0, missing)
