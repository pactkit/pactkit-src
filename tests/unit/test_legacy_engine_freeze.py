"""
STORY-slim-20260826cb37edfdd4da: freeze and isolate the legacy workflow
engine with a data-driven deletion track.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestCompatibilityShims:
    def test_public_import_paths_survive(self):
        """AC1: old import paths resolve to the legacy package modules."""
        import pactkit.host_continuation
        import pactkit.legacy.host_continuation
        import pactkit.legacy.workflow_engine
        import pactkit.workflow_engine

        assert pactkit.workflow_engine is pactkit.legacy.workflow_engine
        assert pactkit.host_continuation is pactkit.legacy.host_continuation

    def test_mock_patch_targets_keep_working(self):
        """The sys.modules alias means patching the old path patches the
        real module — existing tests depend on this."""
        from unittest import mock

        with mock.patch("pactkit.workflow_engine._fingerprint", lambda p: "x"):
            import pactkit.legacy.workflow_engine as impl

            assert impl._fingerprint(Path("/whatever")) == "x"

    def test_frozen_markers_present(self):
        """AC6: each legacy module declares the FROZEN policy."""
        from pactkit.legacy import host_continuation, workflow_engine

        assert "FROZEN" in workflow_engine.__doc__
        assert "FROZEN" in host_continuation.__doc__
        assert "deletion" in workflow_engine.__doc__.lower()


class TestProtocolsModule:
    def test_constant_single_source(self):
        """R2: the neutral module is the home; both consumers agree."""
        from pactkit.protocols import CORE_PROTOCOL_VERSION

        assert CORE_PROTOCOL_VERSION == 1
        import pactkit.deploy_manifest as dm

        assert dm.CORE_PROTOCOL_VERSION is CORE_PROTOCOL_VERSION


class TestUsageCounter:
    def test_counter_increments(self, tmp_path, monkeypatch):
        """AC3: explicit invocation increments the machine-local counter."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("PACTKIT_DISABLE_USAGE_COUNTING", raising=False)
        from pactkit.legacy.usage import record_legacy_usage

        record_legacy_usage("workflow")

        path = tmp_path / ".pactkit" / "legacy-engine-usage.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["workflow"]["count"] == 1
        assert data["workflow"]["last_seen"]

    def test_unknown_commands_not_counted(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from pactkit.legacy.usage import record_legacy_usage

        record_legacy_usage("something-else")

        assert not (tmp_path / ".pactkit" / "legacy-engine-usage.json").exists()

    def test_kill_switch_blocks_counting(self, tmp_path, monkeypatch):
        """Test invocations must not corrupt the deletion data."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("PACTKIT_DISABLE_USAGE_COUNTING", "1")
        from pactkit.legacy.usage import record_legacy_usage

        record_legacy_usage("workflow")

        assert not (tmp_path / ".pactkit" / "legacy-engine-usage.json").exists()

    def test_active_gates_not_counted(self, tmp_path, monkeypatch):
        """AC4: validate_managed_operation does not touch the counter."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("PACTKIT_DISABLE_USAGE_COUNTING", raising=False)
        from pactkit.continuation import ContinuationEngine

        engine = ContinuationEngine(tmp_path)
        try:
            engine.validate_managed_operation("board", "add_story")
        except Exception:
            pass  # validation verdict is irrelevant; only counter matters

        assert not (tmp_path / ".pactkit" / "legacy-engine-usage.json").exists()

    def test_doctor_surfaces_usage(self, tmp_path, monkeypatch):
        """AC5: doctor reports the invocation count."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("PACTKIT_DISABLE_USAGE_COUNTING", raising=False)
        from pactkit.doctor import check_legacy_engine_usage
        from pactkit.legacy.usage import record_legacy_usage

        record_legacy_usage("continuation")
        record_legacy_usage("continuation")

        result = check_legacy_engine_usage()
        assert result["total"] == 2
        assert result["per_command"] == {"continuation": 2}
        assert result["last_seen"]


class TestZeroBehaviorChange:
    def test_workflow_list_still_works(self, tmp_path):
        """AC2 smoke: the explicit entry point functions after the move."""
        import subprocess

        proc = subprocess.run(
            [sys.executable, "-m", "pactkit", "-C", str(tmp_path),
             "workflow", "registry"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path),
                 "PACTKIT_DISABLE_USAGE_COUNTING": "1"},
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_changelog_deprecation_notice(self):
        """AC7: the release notes declare the deletion candidate."""
        changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "deletion candidate" in changelog.lower()
        assert "legacy" in changelog.lower()
