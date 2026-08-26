"""
STORY-slim-20260826f9492ab32c3d: pactkit.yaml read/sync precedence unification.

The sync source must be the copy readers actually load (first existing in
PACTKIT_YAML_CANDIDATES), writes must be atomic, and divergence must be
visible.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pactkit.config import find_pactkit_yaml, sync_config_copies


def _make(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class TestSyncFromEffective:
    def test_effective_copy_propagates_not_claude(self, tmp_path):
        """AC1: the copy being read is the copy being propagated."""
        opencode = _make(tmp_path, ".opencode/pactkit.yaml", 'developer: "edited-here"\n')
        claude = _make(tmp_path, ".claude/pactkit.yaml", 'developer: "stale"\n')

        synced = sync_config_copies(tmp_path)

        assert opencode.read_text(encoding="utf-8") == 'developer: "edited-here"\n'
        assert claude in synced
        assert claude.read_text(encoding="utf-8") == 'developer: "edited-here"\n'

    def test_sync_source_equals_find_pactkit_yaml(self, tmp_path):
        """AC2: readers and sync agree on the effective copy."""
        _make(tmp_path, ".claude/pactkit.yaml", "stack: python\nold: value\n")
        _make(tmp_path, ".codex/pactkit.yaml", "stack: python\n")

        effective = find_pactkit_yaml(tmp_path)
        synced = sync_config_copies(tmp_path)

        # The effective copy (first in PACTKIT_YAML_CANDIDATES: codex before
        # classic) is never the one being overwritten.
        assert effective is not None
        assert effective not in synced
        assert Path(synced[0]).name == "pactkit.yaml"
        assert effective.read_text(encoding="utf-8") == synced[0].read_text(encoding="utf-8")

    def test_user_edits_to_effective_copy_survive_update(self, tmp_path):
        """The headline scenario: edits to the loaded copy are never destroyed."""
        opencode = _make(tmp_path, ".opencode/pactkit.yaml", "stack: python\n")
        _make(tmp_path, ".claude/pactkit.yaml", "stack: python\n")

        opencode.write_text("stack: python\ndeveloper: \"slim\"\n", encoding="utf-8")
        sync_config_copies(tmp_path)

        assert 'developer: "slim"' in opencode.read_text(encoding="utf-8")


class TestAtomicSync:
    def test_crash_mid_sync_leaves_copies_intact(self, tmp_path, monkeypatch):
        """AC3: interrupted sync must not truncate any copy."""
        import os

        _make(tmp_path, ".codex/pactkit.yaml", "stack: python\n")
        claude = _make(tmp_path, ".claude/pactkit.yaml", "original: content\n")

        def exploding_replace(src, dst):
            raise OSError("simulated crash between write and replace")

        monkeypatch.setattr(os, "replace", exploding_replace)

        try:
            sync_config_copies(tmp_path)
        except OSError:
            pass

        assert claude.read_text(encoding="utf-8") == "original: content\n"


class TestDivergenceVisibility:
    def test_overwrite_is_reported(self, tmp_path, capsys):
        """AC4: silent destruction becomes visible."""
        _make(tmp_path, ".codex/pactkit.yaml", "stack: python\n")
        _make(tmp_path, ".claude/pactkit.yaml", "developer: stale\n")

        sync_config_copies(tmp_path)

        out = capsys.readouterr().out
        assert "overwriting" in out
        assert ".claude/pactkit.yaml" in out
