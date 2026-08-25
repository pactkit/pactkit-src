"""Filesystem rollback boundary for multi-file adapter deployments."""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _minimal_paths(paths: Iterable[Path]) -> list[Path]:
    """Return unique absolute paths with descendants covered by parents removed."""
    ordered = sorted(
        {Path(path).absolute() for path in paths},
        key=lambda item: (len(item.parts), str(item)),
    )
    result: list[Path] = []
    for path in ordered:
        if any(path == parent or path.is_relative_to(parent) for parent in result):
            continue
        result.append(path)
    return result


@contextmanager
def rollback_paths(paths: Iterable[Path]) -> Iterator[None]:
    """Restore selected files/directories if a deployment step raises.

    Callers must list only paths they are authorized to mutate. Directories are
    copied with symlinks preserved, so rollback never follows a user symlink.
    """
    selected = _minimal_paths(paths)
    with tempfile.TemporaryDirectory(prefix="pactkit-deploy-backup-") as temp:
        backup_root = Path(temp)
        snapshots: list[tuple[Path, Path, str]] = []
        for index, path in enumerate(selected):
            backup = backup_root / str(index)
            if path.is_symlink():
                backup.symlink_to(path.readlink(), target_is_directory=path.is_dir())
                kind = "symlink"
            elif path.is_dir():
                shutil.copytree(path, backup, symlinks=True)
                kind = "dir"
            elif path.is_file():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup, follow_symlinks=False)
                kind = "file"
            else:
                kind = "missing"
            snapshots.append((path, backup, kind))

        try:
            yield
        except Exception:
            for path, _backup, _kind in reversed(snapshots):
                _remove_path(path)
            for path, backup, kind in snapshots:
                if kind == "missing":
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                if kind == "dir":
                    shutil.copytree(backup, path, symlinks=True)
                elif kind == "symlink":
                    path.symlink_to(backup.readlink(), target_is_directory=backup.is_dir())
                else:
                    shutil.copy2(backup, path, follow_symlinks=False)
            raise
