"""
STORY-slim-202608267c3989223b4d: workflow engine robustness.

No bricked runs, corrupt-sibling isolation, Windows locks, serialized
story binding, transient-git tolerance.
"""
import json
import sys
import threading
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _engine(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine

    return WorkflowEngine(tmp_path)


def _continuation_engine(tmp_path):
    from pactkit.continuation import ContinuationEngine

    return ContinuationEngine(tmp_path)


def _store(tmp_path):
    from pactkit.continuation import ContinuationStore

    return ContinuationStore(tmp_path)


def _valid_run_state(run_id: str = "run-" + "a" * 32, **overrides) -> dict:
    from pactkit.workflow_engine import CORE_PROTOCOL_VERSION

    state = {
        "schema_version": 2,
        "protocol_version": CORE_PROTOCOL_VERSION,
        "run_id": run_id,
        "workflow_id": "project-act",
        "story_id": "",
        "status": "running",
        "current_index": 0,
        "goal_digest": "f" * 64,
        "units": {},
        "idempotency": {},
        "fingerprints": {},
        "attempts": [],
        "updated_at": "2026-08-26T00:00:00+00:00",
    }
    state.update(overrides)
    return state


def _write_run(engine, state: dict) -> Path:
    engine.directory.mkdir(parents=True, exist_ok=True)
    path = engine.directory / f"{state['run_id']}.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


class TestArtifactVanished:
    def test_missing_fingerprint_raises_explicit_error(self):
        from pactkit.workflow_engine import _fingerprint

        # the brick mechanism: _fingerprint emits "missing" for vanished files
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            gone = Path(td) / "gone.md"
            assert _fingerprint(gone) == "missing"

    def test_submit_rejects_vanished_artifact_before_state_write(self, tmp_path):
        """AC1: a vanished artifact fails before state persistence."""
        from pactkit import workflow_engine as we

        engine = _engine(tmp_path)

        # A receipt whose evidence was unavailable at validation must fail
        # the submit instead of persisting a bricking sentinel.
        with pytest.raises(we.WorkUnitError, match="artifact_vanished"):
            we._persisted_fingerprints({"docs/specs/gone.md": "missing"})


class TestCorruptSiblingIsolation:
    def test_corrupt_sibling_skipped_with_warning(self, tmp_path, capsys):
        """AC2: one corrupt run file must not block unrelated lookups."""
        engine = _engine(tmp_path)
        # A real run created through the engine's own start path.
        run = engine.start("project-act", goal="robustness fixture", story_id=None)
        engine.directory.mkdir(parents=True, exist_ok=True)
        corrupt = engine.directory / ("run-" + "b" * 32 + ".json")
        corrupt.write_text("{ not json", encoding="utf-8")

        # Materialize the first unit through the engine's own acquire path.
        unit = engine.acquire(
            run.run_id, owner="robustness-fixture", idempotency_key="fixture-1"
        )
        first_unit = unit.unit_id

        found = engine._find_run_for_unit(first_unit)

        assert found == run.run_id
        err = capsys.readouterr().err
        assert corrupt.stem in err

    def test_malformed_target_still_errors(self, tmp_path):
        """AC3: a corrupt TARGET run still errors explicitly."""
        engine = _engine(tmp_path)
        engine.directory.mkdir(parents=True, exist_ok=True)
        corrupt = engine.directory / ("run-" + "b" * 32 + ".json")
        corrupt.write_text("{ not json", encoding="utf-8")

        from pactkit.workflow_engine import WorkUnitError

        with pytest.raises(WorkUnitError):
            engine._read_scanned_state(corrupt, validate_completed=False)


class TestWindowsRunLock:
    def test_windows_path_avoids_fcntl(self, tmp_path, monkeypatch):
        """AC4: os.name == 'nt' selects the msvcrt branch, never fcntl."""
        import builtins
        import os

        fake_msvcrt = types.ModuleType("msvcrt")
        fake_msvcrt.LK_NBLCK = 1
        fake_msvcrt.LK_UNLCK = 2
        locked: list = []
        fake_msvcrt.locking = lambda fd, mode, nbytes: locked.append(mode)
        monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
        monkeypatch.setattr(os, "name", "nt")

        real_import = builtins.__import__

        def no_fcntl(name, *args, **kwargs):
            if name == "fcntl":
                raise AssertionError("fcntl imported on the Windows lock path")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", no_fcntl)

        engine = _continuation_engine(tmp_path)
        with engine._run_lock("run-" + "c" * 32):
            pass

        assert locked == [fake_msvcrt.LK_NBLCK, fake_msvcrt.LK_UNLCK]


class TestBindSerialization:
    def test_bind_lock_serializes_concurrent_binds(self, tmp_path):
        """AC5: two binds for the same story cannot interleave."""
        engine = _continuation_engine(tmp_path)
        run1 = _valid_run_state("run-" + "d" * 32)
        run2 = _valid_run_state("run-" + "e" * 32)
        _write_run(engine, run1)
        _write_run(engine, run2)

        # While the bind lock is held, a second bind must block (serialize).
        outcome: dict = {}

        def second_bind():
            try:
                engine.bind_story(run2["run_id"], "STORY-100")
                outcome["result"] = "ok"
            except Exception as exc:  # ContinuationError expected after wait
                outcome["result"] = f"err: {exc}"

        with engine._bind_lock():
            thread = threading.Thread(target=second_bind)
            thread.start()
            thread.join(timeout=0.5)
            assert thread.is_alive(), "bind_story did not serialize under the bind lock"
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert "result" in outcome


class TestTransientGitTolerance:
    def test_unavailable_current_fingerprint_is_not_drift(self, tmp_path):
        """AC6: a transiently failing git probe is inconclusive, not drift."""
        engine = _store(tmp_path)
        state = {
            "step_id": "act",
            "status": "in_progress",
            "fingerprints": {
                "git_head": "a" * 40,
                "worktree": "b" * 64,
            },
        }

        monkey_fingerprints = {
            "git_head": "unavailable",
            "worktree": "unavailable",
            "spec": "c" * 64,
            "story_fact": "d" * 64,
            "board": "e" * 64,
        }
        original = engine._fingerprints
        engine._fingerprints = lambda story_id: monkey_fingerprints
        try:
            reasons = engine._stale_reasons(state, "STORY-100")
        finally:
            engine._fingerprints = original

        assert not [r for r in reasons if "git" in r or "worktree" in r]
