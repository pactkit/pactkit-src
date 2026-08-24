"""Decentralized item ID generation for parallel branches."""
from __future__ import annotations

import re
import secrets
from pathlib import Path

ITEM_ID_PATTERN = (
    r"(?:STORY|HOTFIX|BUG)(?:-[a-z]+)?-"
    r"(?:\d{8}[0-9a-f]{12}|\d+(?:-[0-9a-f]{4,32})?)"
)
ITEM_ID_RE = re.compile(rf"^{ITEM_ID_PATTERN}$")


def generate_item_id(specs_dir: Path, developer: str, item_type: str = "STORY") -> str:
    """Generate a time-prefixed item ID safe across parallel branches.

    Args:
        specs_dir: Path to docs/specs/ directory.
        developer: Developer name from pactkit.yaml (empty = no prefix).

    Returns:
        New entropy-bearing ID; historical sequential IDs remain readable.
    """
    del specs_dir  # uniqueness does not depend on a branch-local snapshot
    if developer and not re.fullmatch(r"[a-z]+", developer):
        raise ValueError("developer must contain lowercase ASCII letters only")
    if item_type not in {"STORY", "HOTFIX", "BUG"}:
        raise ValueError("item_type must be STORY, HOTFIX, or BUG")
    from datetime import datetime, timezone

    prefix = f"{item_type}-{developer}-" if developer else f"{item_type}-"
    return prefix + datetime.now(timezone.utc).strftime("%Y%m%d") + secrets.token_hex(6)
