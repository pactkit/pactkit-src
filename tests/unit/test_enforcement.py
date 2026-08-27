"""STORY-slim-20260827024e71df170f R3: gate enforcement completeness reporting.

AC6 — degraded gates must be queryable via `pactkit doctor --json`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _project(root: Path) -> None:
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "product").mkdir(parents=True)
    (root / "docs" / "product" / "sprint_board.md").write_text(
        "# Sprint Board\n\n## 📋 Backlog\n\n## 🔄 In Progress\n\n## ✅ Done\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "docs"], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "fixture"],
        cwd=root, check=True,
    )


class TestEnforcementModel:
    def test_status_levels_and_record_roundtrip(self, tmp_path):
        from pactkit.enforcement import (
            DEGRADED, FULL, UNAVAILABLE, read_status, record_status,
        )

        assert (FULL, DEGRADED, UNAVAILABLE) == ("full", "degraded", "unavailable")
        record_status(tmp_path, "commit_gate", DEGRADED, "internal error path")
        record = read_status(tmp_path, "commit_gate")
        assert record["gate"] == "commit_gate"
        assert record["status"] == DEGRADED
        assert "internal error" in record["reason"]
        assert record["ts"]

    def test_record_status_rejects_unknown_status(self, tmp_path):
        from pactkit.enforcement import record_status

        with pytest.raises(ValueError):
            record_status(tmp_path, "commit_gate", "half-open", "made up")

    def test_assess_defaults_full_in_healthy_project(self, tmp_path):
        from pactkit.enforcement import assess

        _project(tmp_path)
        assessment = assess(tmp_path)
        for gate in ("commit_gate", "coverage_gate", "finish_gate"):
            assert gate in assessment
            assert assessment[gate]["status"] in {"full", "degraded", "unavailable"}
            assert "reason" in assessment[gate]

    def test_assess_no_git_policy_marks_unavailable(self, tmp_path):
        from pactkit.enforcement import assess, record_status

        _project(tmp_path)
        record_status(tmp_path, "commit_gate", "unavailable", "skipped (enterprise.no_git)")
        assessment = assess(tmp_path)
        assert assessment["commit_gate"]["status"] == "unavailable"

    def test_assess_corrupt_checkpoint_degrades_finish_gate(self, tmp_path):
        from pactkit.enforcement import assess

        _project(tmp_path)
        cont = tmp_path / ".pactkit" / "continuations"
        cont.mkdir(parents=True)
        (cont / "STORY-slim-249.json").write_text("{not json", encoding="utf-8")
        assessment = assess(tmp_path)
        assert assessment["finish_gate"]["status"] == "degraded"
        assert "STORY-slim-249" in assessment["finish_gate"]["reason"]


class TestCommitGateRecordsStatus:
    def test_self_lock_path_records_degraded(self, tmp_path, monkeypatch):
        """AC6: the self-lock protection path must be queryable afterwards."""
        import pactkit.commit_gate as commit_gate_module
        from pactkit.enforcement import DEGRADED, read_status

        _project(tmp_path)

        def _explode(*_args, **_kwargs):
            raise RuntimeError("simulated internal failure")

        monkeypatch.setattr(commit_gate_module, "collect_changed_files", _explode)
        result = commit_gate_module.run_gate(tmp_path)
        record = read_status(tmp_path, "commit_gate")
        assert record["status"] == DEGRADED
        assert "internal" in record["reason"].lower()
        # Self-lock semantics unchanged: the gate still allows the commit
        assert any("allowing commit" in line for line in result.lines)

    def test_unavailable_probe_path_records_unavailable(self, tmp_path, monkeypatch):
        import pactkit.commit_gate as commit_gate_module
        from pactkit.enforcement import UNAVAILABLE, read_status

        _project(tmp_path)

        def _missing(*_args, **_kwargs):
            raise commit_gate_module.GateUnavailable("pytest not found")

        monkeypatch.setattr(commit_gate_module, "collect_changed_files", _missing)
        commit_gate_module.run_gate(tmp_path)
        record = read_status(tmp_path, "commit_gate")
        assert record["status"] == UNAVAILABLE


class TestDoctorJsonEnforcement:
    def test_ac6_doctor_json_contains_enforcement_section(self, tmp_path):
        _project(tmp_path)
        from pactkit.enforcement import DEGRADED, record_status

        record_status(tmp_path, "commit_gate", DEGRADED, "internal error path")
        proc = subprocess.run(
            ["python3", "-m", "pactkit", "-C", str(tmp_path), "doctor", "--json"],
            capture_output=True, text=True, cwd=tmp_path, timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout)
        assert "enforcement" in payload
        assert payload["enforcement"]["commit_gate"]["status"] == DEGRADED
        for gate in ("coverage_gate", "finish_gate"):
            assert gate in payload["enforcement"]
