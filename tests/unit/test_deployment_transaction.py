from pathlib import Path

import pytest

from pactkit.deployment_transaction import rollback_paths


def test_rollback_paths_restores_existing_and_removes_new_artifacts(tmp_path):
    managed_dir = tmp_path / "managed"
    existing = managed_dir / "existing.txt"
    existing.parent.mkdir()
    existing.write_bytes(b"before\x00")
    new_file = tmp_path / "new.txt"

    with pytest.raises(OSError, match="forced deployment failure"):
        with rollback_paths((managed_dir, new_file)):
            existing.write_bytes(b"after")
            (managed_dir / "added.txt").write_text("added", encoding="utf-8")
            new_file.write_text("new", encoding="utf-8")
            raise OSError("forced deployment failure")

    assert existing.read_bytes() == b"before\x00"
    assert not (managed_dir / "added.txt").exists()
    assert not new_file.exists()


def test_rollback_paths_keeps_successful_changes(tmp_path):
    managed = tmp_path / "managed.txt"
    managed.write_text("before", encoding="utf-8")

    with rollback_paths((managed,)):
        managed.write_text("after", encoding="utf-8")

    assert managed.read_text(encoding="utf-8") == "after"


def test_rollback_paths_deduplicates_nested_targets(tmp_path):
    parent = tmp_path / "managed"
    child = parent / "child.txt"
    child.parent.mkdir()
    child.write_text("before", encoding="utf-8")

    with pytest.raises(RuntimeError):
        with rollback_paths((child, parent, Path(parent))):
            child.write_text("after", encoding="utf-8")
            raise RuntimeError("rollback")

    assert child.read_text(encoding="utf-8") == "before"
