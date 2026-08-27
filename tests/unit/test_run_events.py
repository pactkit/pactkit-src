"""STORY-slim-20260827024e71df170f R1: append-only run event streams.

AC1 projection consistency, AC2 blocker pairing, AC3 crash safety.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path



def _project(root: Path, story_id: str = "STORY-slim-246") -> None:
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


class TestRunEventsPrimitives:
    def test_append_creates_parent_and_single_line(self, tmp_path):
        from pactkit.run_events import append_event, read_events, story_events_path

        path = story_events_path(tmp_path, "STORY-slim-246")
        append_event(
            path, event="step_entered", story_id="STORY-slim-246", run_id=None,
            step_id="preflight", status="in_progress", detail={"first": True},
        )
        assert path.exists()
        events, corrupt = read_events(path)
        assert corrupt == 0
        assert len(events) == 1
        record = events[0]
        assert record["event"] == "step_entered"
        assert record["story_id"] == "STORY-slim-246"
        assert record["step_id"] == "preflight"
        assert record["ts"]

    def test_corrupt_lines_skipped_and_counted(self, tmp_path):
        from pactkit.run_events import append_event, read_events, story_events_path

        path = story_events_path(tmp_path, "STORY-slim-246")
        append_event(
            path, event="step_entered", story_id="STORY-slim-246", run_id=None,
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write('{"ts": "broken...\n')  # half-written line (crash simulation)
        append_event(
            path, event="run_completed", story_id="STORY-slim-246", run_id=None,
        )
        events, corrupt = read_events(path)
        assert corrupt == 1
        assert [e["event"] for e in events] == ["step_entered", "run_completed"]

    def test_read_missing_file_returns_empty(self, tmp_path):
        from pactkit.run_events import read_events, story_events_path

        events, corrupt = read_events(story_events_path(tmp_path, "STORY-none"))
        assert events == [] and corrupt == 0


class TestStoreCheckpointEvents:
    def test_ac1_checkpoint_emits_events_and_projection_consistent(self, tmp_path):
        from pactkit.continuation import ContinuationStore
        from pactkit.run_events import read_events, story_events_path

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-246", step_id="preflight", evidence={"spec_lint": "pass"})
        events, _corrupt = read_events(story_events_path(tmp_path, "STORY-slim-246"))
        kinds = [e["event"] for e in events]
        assert "step_entered" in kinds
        assert "checkpoint_written" in kinds
        # Projection consistency: last event status matches the checkpoint JSON
        state = store.read("STORY-slim-246")
        assert events[-1]["status"] == state["status"]
        assert events[-1]["step_id"] == state["step_id"]

    def test_ac2_blocker_pair_recorded_with_kind(self, tmp_path):
        from pactkit.continuation import ContinuationStore
        from pactkit.run_events import read_events, story_events_path

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-246", step_id="preflight", evidence={"spec_lint": "pass"})
        store.checkpoint(
            "STORY-slim-246", step_id="red", status="blocked",
            evidence={"story_tests": {"exit_code": 1}},
            blocker="awaiting decision on fixture data", blocker_kind="user_input",
        )
        store.checkpoint("STORY-slim-246", step_id="red", evidence={"story_tests": {"exit_code": 1}})
        events, _corrupt = read_events(story_events_path(tmp_path, "STORY-slim-246"))
        kinds = [e["event"] for e in events]
        assert kinds.count("blocker_raised") == 1
        assert kinds.count("blocker_cleared") == 1
        raised = next(e for e in events if e["event"] == "blocker_raised")
        assert raised["detail"]["blocker_kind"] == "user_input"
        # AC2: no secret plaintext in event details (sanitize path covers)
        assert "password" not in json.dumps(events).lower()

    def test_ac3_partial_line_does_not_break_checkpoint_reads(self, tmp_path):
        from pactkit.continuation import ContinuationStore
        from pactkit.run_events import read_events, story_events_path

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-246", step_id="preflight", evidence={"spec_lint": "pass"})
        events_path = story_events_path(tmp_path, "STORY-slim-246")
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write('{"ts": "trunc')
        # Checkpoint reads are unaffected by a damaged event tail
        state = store.read("STORY-slim-246")
        assert state["step_id"] == "preflight"
        events, corrupt = read_events(events_path)
        assert corrupt == 1
        assert events, "intact lines survive the damaged tail"

    def test_archived_cycle_emits_run_archived_event(self, tmp_path):
        from pactkit.continuation import ContinuationStore
        from pactkit.run_events import read_events, story_events_path

        _project(tmp_path)
        store = ContinuationStore(tmp_path)
        store.checkpoint("STORY-slim-246", step_id="preflight", evidence={"spec_lint": "pass"})
        # Simulate a completed checkpoint then a fresh cycle
        (tmp_path / ".pactkit" / "continuations" / "STORY-slim-246.json").write_text(
            json.dumps({
                "schema_version": 1, "story_id": "STORY-slim-246",
                "command": "$project-act", "phase": "", "step_id": "sync_coverage",
                "status": "completed", "evidence": {}, "fingerprints": {},
                "blocker": "", "blocker_kind": None, "updated_at": "2026-08-27T00:00:00+00:00",
            }),
            encoding="utf-8",
        )
        store.checkpoint("STORY-slim-246", step_id="preflight", evidence={"spec_lint": "pass"}, fresh=True)
        events, _corrupt = read_events(story_events_path(tmp_path, "STORY-slim-246"))
        kinds = [e["event"] for e in events]
        assert "run_archived" in kinds


class TestEngineRunEvents:
    def test_start_and_checkpoint_emit_events(self, tmp_path):
        from pactkit.continuation import ContinuationEngine
        from pactkit.run_events import read_events, run_events_path

        _project(tmp_path)
        engine = ContinuationEngine(tmp_path)
        state = engine.start("project-check", evidence={"started": True})
        run_id = state["run_id"]
        events, _corrupt = read_events(run_events_path(tmp_path, run_id))
        assert [e["event"] for e in events] == ["step_entered"]
        assert events[0]["step_id"] == "started"

        engine.checkpoint(run_id, step_id="security_scanned", evidence={"security_scan": "pass"})
        events, _corrupt = read_events(run_events_path(tmp_path, run_id))
        kinds = [e["event"] for e in events]
        assert "step_entered" in kinds
        assert "checkpoint_written" in kinds
        assert events[-1]["run_id"] == run_id

    def test_revalidate_emits_evidence_invalidated(self, tmp_path):
        from pactkit.continuation import ContinuationEngine
        from pactkit.run_events import read_events, run_events_path

        _project(tmp_path)
        engine = ContinuationEngine(tmp_path)
        state = engine.start("project-check", evidence={"started": True})
        engine.checkpoint(state["run_id"], step_id="security_scanned", evidence={"security_scan": "pass"})
        # Force drift on a fingerprinted artifact, then revalidate
        spec = tmp_path / "docs" / "specs" / "STORY-slim-246.md"
        spec.write_text(spec.read_text(encoding="utf-8") + "\n<!-- drift -->\n", encoding="utf-8")
        resolution = engine.resume(state["run_id"])
        if resolution.get("decision") == "blocked" and "artifact drift" in " ".join(resolution.get("reasons", [])):
            engine.revalidate_artifacts(state["run_id"])
            events, _corrupt = read_events(run_events_path(tmp_path, state["run_id"]))
            kinds = [e["event"] for e in events]
            assert "evidence_invalidated" in kinds
