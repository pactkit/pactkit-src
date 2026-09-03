"""Accept .pactkit-new deployment candidates and record ownership digests.

STORY-slim-20260903a24e1ece0d7f (PM-20260903 follow-up). The deployer
preserves user-modified files and writes ``.pactkit-new`` candidates; a
manual ``mv`` accepts the content but never updates the ownership ledgers,
so the next content change produces another candidate — a treadmill
observed three times on 2026-09-03. This module makes acceptance
first-class: move the candidate over the original AND record the digest in
both ledgers (command-manifest references table for
``skills/*/references/**`` paths, ``.pactkit-deployed.json`` files map
otherwise), so the next deploy can prove ownership and update in place.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pactkit.utils import atomic_write

_COMMAND_MANIFEST = ".pactkit-command-manifest.json"
_DEPLOY_MANIFEST = ".pactkit-deployed.json"
_CANDIDATE_SUFFIX = ".pactkit-new"


def _is_reference_path(relative: str) -> bool:
    return "references" in relative.split("/")


def _update_command_manifest(root: Path, relative: str, digest: str) -> None:
    path = root / "skills" / _COMMAND_MANIFEST
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {"version": 2, "commands": {}, "references": {}}
    if not isinstance(payload, dict):
        payload = {"version": 2, "commands": {}, "references": {}}
    references = payload.get("references")
    if not isinstance(references, dict):
        references = {}
    references[relative] = digest
    payload["references"] = dict(sorted(references.items()))
    payload.setdefault("version", 2)
    payload.setdefault("commands", {})
    atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _update_deploy_manifest(root: Path, relative: str, digest: str) -> None:
    path = root / _DEPLOY_MANIFEST
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    files = payload.get("files")
    if not isinstance(files, dict):
        files = {}
    files[relative] = digest
    payload["files"] = dict(sorted(files.items()))
    atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def accept_candidates(root: Path) -> int:
    """Accept every ``*.pactkit-new`` candidate under *root*.

    Returns the number of accepted candidates.
    """
    root = Path(root)
    accepted = 0
    for candidate in sorted(root.rglob(f"*{_CANDIDATE_SUFFIX}")):
        if not candidate.is_file():
            continue
        target = candidate.with_name(candidate.name[: -len(_CANDIDATE_SUFFIX)])
        if target.exists() and not target.is_file():
            # A directory or special file is never ours to replace.
            continue
        content = candidate.read_bytes()
        target.write_bytes(content)
        candidate.unlink()
        digest = hashlib.sha256(content).hexdigest()
        relative = target.relative_to(root).as_posix()
        if _is_reference_path(relative):
            _update_command_manifest(root, relative, digest)
        else:
            _update_deploy_manifest(root, relative, digest)
        accepted += 1
    return accepted


def default_roots() -> list[Path]:
    """Deploy roots to scan when --root is not given (doctor probe set)."""
    from pactkit.doctor import DEPLOY_PROBE_PATHS

    home = Path.home()
    cwd = Path.cwd()
    roots: list[Path] = []
    for template in DEPLOY_PROBE_PATHS:
        path = Path(template.format(home=home, root=cwd))
        if path.is_dir() and path not in roots:
            roots.append(path)
    return roots
