"""STORY-slim-20260827eddbe9669c87: authorization audit pairs + outcome_unknown.

AC1/AC2/AC3 authorization audit, AC4/AC5 attempt fencing, AC6/AC7 recovery
semantics, AC8 stats decision counts.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _project(root: Path, story_id: str = "STORY-slim-260") -> None:
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "product").mkdir(parents=True)
    (root / "docs" / "specs" / f"{story_id}.md").write_text(
        f"# {story_id}\n\n"
        "| Field | Value |\n|---|---|\n"
        f"| ID | {story_id} |\n"
        "| Status | Draft |\n| Priority | P1 |\n| Release | 2.24.0 |\n"
        "\n## Requirements\n\n### R1: Test (MUST)\n\ntext\n"
        "\n## Acceptance Criteria\n\n### AC1: Test (R1)\n\n- **Given** x\n- **When** y\n- **Then** z\n"
        "\n## Security Scope\n\n| Check | Applicable | Reason |\n|---|---|---|\n| SEC-1 | N/A | test |\n",
        encoding="utf-8",
    )
    (root / "docs" / "product" / "sprint_board.md").write_text(
        "# Sprint Board\n\n## 📋 Backlog\n\n## 🔄 In Progress\n\n"
        f"### [{story_id}] Test\n- [ ] Task 1\n\n## ✅ Done\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "docs"], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "fixture"],
        cwd=root, check=True,
    )


class TestAuthorizationAuditEvents:
    def test_ac1_asked_granted_pair_for_authorization_blocker(self, tmp_path):
        from pactkit.continuation import ContinuationStore
        from pactkit.run_events import read_events, story_events_path

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-260", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint(
            "STORY-slim-260", step_id="red", status="blocked",
            evidence={"story_tests": {"exit_code": 1}},
            blocker="awaiting approval to modify production config",
            blocker_kind="authorization",
        )
        store.checkpoint("STORY-slim-260", step_id="red", evidence={"story_tests": {"exit_code": 1}})
        events, _ = read_events(story_events_path(tmp_path, "STORY-slim-260"))
        kinds = [e["event"] for e in events]
        assert "authorization_asked" in kinds
        assert "authorization_granted" in kinds
        asked_idx = kinds.index("authorization_asked")
        granted_idx = kinds.index("authorization_granted")
        assert asked_idx < granted_idx
        asked = events[asked_idx]
        assert "production config" in asked["detail"]["blocker"]

    def test_ac1_other_blocker_kinds_emit_no_authorization_events(self, tmp_path):
        from pactkit.continuation import ContinuationStore
        from pactkit.run_events import read_events, story_events_path

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-260", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint(
            "STORY-slim-260", step_id="red", status="blocked",
            evidence={"story_tests": {"exit_code": 1}},
            blocker="waiting for user fixture data",
            blocker_kind="user_input",
        )
        events, _ = read_events(story_events_path(tmp_path, "STORY-slim-260"))
        kinds = [e["event"] for e in events]
        assert "authorization_asked" not in kinds
        assert "authorization_granted" not in kinds


class TestDenyCommand:
    def _blocked_authorization(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-260", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint(
            "STORY-slim-260", step_id="red", status="blocked",
            evidence={"story_tests": {"exit_code": 1}},
            blocker="awaiting approval to modify production config",
            blocker_kind="authorization",
        )
        return store

    def test_ac2_deny_records_event_and_rewrites_blocker(self, tmp_path):
        from pactkit.run_events import read_events, story_events_path

        store = self._blocked_authorization(tmp_path)
        result = store.deny("STORY-slim-260", "scope too broad")
        assert result["status"] == "blocked"
        assert result["blocker"].startswith("denied:")
        assert "scope too broad" in result["blocker"]
        events, _ = read_events(story_events_path(tmp_path, "STORY-slim-260"))
        denied = [e for e in events if e["event"] == "authorization_denied"]
        assert len(denied) == 1
        assert "scope too broad" in denied[0]["detail"]["reason"]

    def test_ac2_double_deny_rejected(self, tmp_path):
        store = self._blocked_authorization(tmp_path)
        store.deny("STORY-slim-260", "no")
        from pactkit.continuation import ContinuationError

        with pytest.raises(ContinuationError, match="already denied"):
            store.deny("STORY-slim-260", "no again")

    def test_ac3_deny_requires_authorization_blocker(self, tmp_path):
        from pactkit.continuation import ContinuationError, ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-260", step_id="preflight", evidence={"spec_lint": "pass"})
        with pytest.raises(ContinuationError, match="blocked"):
            store.deny("STORY-slim-260", "no")

    def test_ac3_deny_cli_exit_codes(self, tmp_path):
        self._blocked_authorization(tmp_path)
        deny_ok = subprocess.run(
            ["python3", "-m", "pactkit", "-C", str(tmp_path), "continuation", "deny",
             "STORY-slim-260", "--reason", "scope too broad"],
            capture_output=True, text=True, cwd=tmp_path, timeout=60,
        )
        assert deny_ok.returncode == 0, deny_ok.stderr
        # Repeat deny must fail
        deny_again = subprocess.run(
            ["python3", "-m", "pactkit", "-C", str(tmp_path), "continuation", "deny",
             "STORY-slim-260", "--reason", "again"],
            capture_output=True, text=True, cwd=tmp_path, timeout=60,
        )
        assert deny_again.returncode == 1


class TestAttemptFencing:
    def test_ac4_completed_run_leaves_terminal_record(self, tmp_path):
        import pactkit.commit_gate as gate
        from pactkit.enforcement import read_status

        _project(tmp_path)
        gate.run_gate(tmp_path)
        record = read_status(tmp_path, "commit_gate")
        assert record is not None
        assert record["status"] != "running"

    def test_ac5_interrupted_run_leaves_open_fence(self, tmp_path, monkeypatch):
        import pactkit.commit_gate as gate
        from pactkit.enforcement import read_status

        _project(tmp_path)

        def _explode(*_args, **_kwargs):
            raise KeyboardInterrupt("simulated Ctrl-C")

        monkeypatch.setattr(gate, "collect_changed_files", _explode)
        with pytest.raises(KeyboardInterrupt):
            gate.run_gate(tmp_path)
        record = read_status(tmp_path, "commit_gate")
        assert record["status"] == "running"

    def test_record_attempt_and_status_overwrite(self, tmp_path):
        from pactkit.enforcement import FULL, read_status, record_attempt, record_status

        record_attempt(tmp_path, "commit_gate")
        assert read_status(tmp_path, "commit_gate")["status"] == "running"
        record_status(tmp_path, "commit_gate", FULL, "")
        assert read_status(tmp_path, "commit_gate")["status"] == FULL

    def test_corrupt_fence_reads_as_absent(self, tmp_path):
        from pactkit.enforcement import read_status, record_attempt

        record_attempt(tmp_path, "commit_gate")
        fence = tmp_path / ".pactkit" / "enforcement" / "commit_gate.json"
        fence.write_text("{broken", encoding="utf-8")
        assert read_status(tmp_path, "commit_gate") is None


class TestOutcomeUnknownRecovery:
    def _active_run(self, tmp_path):
        from pactkit.continuation import ContinuationStore

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-260", step_id="preflight", evidence={"spec_lint": "pass"})
        return store

    def test_ac6_open_fence_blocks_resume_and_finish_guard(self, tmp_path):
        from pactkit.enforcement import record_attempt

        store = self._active_run(tmp_path)
        record_attempt(tmp_path, "commit_gate")
        resolution = store.resume("STORY-slim-260")
        assert resolution["decision"] == "blocked"
        assert any("outcome unknown" in r for r in resolution["reasons"])

        from pactkit.continuation import ContinuationEngine

        guard = ContinuationEngine(tmp_path).finish_guard("STORY-slim-260")
        assert any("outcome unknown" in r for r in guard["reasons"])

    def test_ac6_terminal_record_unblocks(self, tmp_path):
        from pactkit.enforcement import FULL, record_attempt, record_status

        store = self._active_run(tmp_path)
        record_attempt(tmp_path, "commit_gate")
        assert store.resume("STORY-slim-260")["decision"] == "blocked"
        record_status(tmp_path, "commit_gate", FULL, "")
        resolution = store.resume("STORY-slim-260")
        assert resolution["decision"] == "resume_at"
        assert not any("outcome unknown" in r for r in resolution["reasons"])

    def test_ac7_no_fence_behaves_as_before(self, tmp_path):
        store = self._active_run(tmp_path)
        resolution = store.resume("STORY-slim-260")
        assert resolution["decision"] == "resume_at"
        assert resolution["reasons"] == []


class TestStatsAuthorizationCounts:
    def test_ac8_denied_scenario_counts(self, tmp_path):
        from pactkit.continuation import ContinuationStore
        from pactkit.run_stats import collect_runs, json_report

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-260", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint(
            "STORY-slim-260", step_id="red", status="blocked",
            evidence={"story_tests": {"exit_code": 1}},
            blocker="awaiting approval", blocker_kind="authorization",
        )
        store.deny("STORY-slim-260", "scope too broad")
        report = json_report(collect_runs(tmp_path))
        run = next(r for r in report["runs"] if r.get("story_id") == "STORY-slim-260")
        assert run["authorization_decisions"] == {"asked": 1, "granted": 0, "denied": 1}


class TestQaFollowupFenceLiveness:
    """Session QA P3: fence PID liveness disambiguates running vs crashed."""

    def test_dead_pid_reports_never_completed(self, tmp_path):
        import pactkit.continuation as continuation
        from pactkit.enforcement import record_attempt

        _project(tmp_path)
        record_attempt(tmp_path, "commit_gate")
        # Force a PID that cannot be alive
        fence = tmp_path / ".pactkit" / "enforcement" / "commit_gate.json"
        payload = json.loads(fence.read_text(encoding="utf-8"))
        payload["pid"] = 999999999
        fence.write_text(json.dumps(payload), encoding="utf-8")
        reason = continuation.verification_outcome_unknown(tmp_path)
        assert "outcome unknown" in reason
        assert "never completed" in reason

    def test_live_pid_reports_still_active(self, tmp_path):
        import os

        import pactkit.continuation as continuation
        from pactkit.enforcement import record_attempt

        _project(tmp_path)
        record_attempt(tmp_path, "commit_gate")
        fence = tmp_path / ".pactkit" / "enforcement" / "commit_gate.json"
        payload = json.loads(fence.read_text(encoding="utf-8"))
        payload["pid"] = os.getpid()  # this test process is definitely alive
        fence.write_text(json.dumps(payload), encoding="utf-8")
        reason = continuation.verification_outcome_unknown(tmp_path)
        assert "outcome unknown" in reason
        assert "still active" in reason
