"""Story ID generator — deterministic next-ID logic (STORY-slim-014 R1).

Replaces the prompt-based ID generation from Plan Phase 3.1.
"""
from __future__ import annotations

import re
import secrets
from pathlib import Path

ITEM_ID_PATTERN = (
    r"(?:STORY|HOTFIX|BUG)(?:-[a-z]+)?-"
    r"(?:\d+(?:-[0-9a-f]{4,32})?|\d{8}[0-9a-f]{12})"
)
ITEM_ID_RE = re.compile(rf"^{ITEM_ID_PATTERN}$")


def next_story_id(specs_dir: Path, developer: str) -> str:
    """Generate a decentralized Story ID safe across parallel branches.

    Args:
        specs_dir: Path to docs/specs/ directory.
        developer: Developer name from pactkit.yaml (empty = no prefix).

    Returns:
        New entropy-bearing ID; historical sequential IDs remain readable.
    """
    del specs_dir  # uniqueness does not depend on a branch-local snapshot
    if developer and not re.fullmatch(r"[a-z]+", developer):
        raise ValueError("developer must contain lowercase ASCII letters only")
    from datetime import datetime, timezone

    prefix = f"STORY-{developer}-" if developer else "STORY-"
    return prefix + datetime.now(timezone.utc).strftime("%Y%m%d") + secrets.token_hex(6)
