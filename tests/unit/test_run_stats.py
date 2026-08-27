"""STORY-slim-20260827024e71df170f R2/R6: friction stats and event viewing.

AC4 stats aggregation + graceful degradation, AC10 `continuation events`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path



def _project(root: Path, story_id: str = "STORY-slim-247") -> None:
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


def _run_with_blocker(root: Path) -> None:
    """Drive one full Act cycle that includes a blocker episode."""
    from pactkit.continuation import ContinuationStore

    store = ContinuationStore(root)
    store.checkpoint("STORY-slim-247", step_id="preflight", evidence={"spec_lint": "pass"})
    store.checkpoint(
        "STORY-slim-247", step_id="red", status="blocked",
        evidence={"story_tests": {"exit_code": 1}},
        blocker="awaiting fixture decision", blocker_kind="user_input",
    )
    store.checkpoint("STORY-slim-247", step_id="red", evidence={"story_tests": {"exit_code": 1}})
    store.checkpoint("STORY-slim-247", step_id="green", evidence={"story_tests": {"exit_code": 0}})
    store.checkpoint(
        "STORY-slim-247", step_id="regression_lint",
        evidence={"regression": "pass", "lint": "pass"},
    )


class TestStatsAggregation:
    def test_ac4_json_report_contains_friction_metrics(self, tmp_path):
        from pactkit.run_stats import collect_runs, json_report

        _project(tmp_path)
        _run_with_blocker(tmp_path)
        runs = collect_runs(tmp_path)
        report = json_report(runs)
        assert report["runs"], "at least one run is aggregated"
        run = next(r for r in report["runs"] if r.get("story_id") == "STORY-slim-247")
        assert run["events"] == "available"
        assert run["event_count"] >= 6
        assert isinstance(run["duration_seconds"], (int, float))
        # Blocker dwell bucketed by kind
        assert "user_input" in run["blocker_dwell_seconds"]
        assert run["blocker_dwell_seconds"]["user_input"] >= 0
        # Step rework counter present
        assert isinstance(run["step_rework"], int)
        assert run["status"] == "in_progress"

    def test_ac4_run_without_events_degrades_gracefully(self, tmp_path):
        from pactkit.run_stats import collect_runs

        _project(tmp_path)
        # A pre-2.24 checkpoint with no event stream
        (tmp_path / ".pactkit" / "continuations").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".pactkit" / "continuations" / "STORY-slim-248.json").write_text(
            json.dumps({
                "schema_version": 1, "story_id": "STORY-slim-248",
                "command": "$project-act", "phase": "", "step_id": "preflight",
                "status": "in_progress", "evidence": {}, "fingerprints": {},
                "blocker": "", "blocker_kind": None, "updated_at": "2026-08-01T00:00:00+00:00",
            }),
            encoding="utf-8",
        )
        runs = collect_runs(tmp_path)
        old = next(r for r in runs if r.get("story_id") == "STORY-slim-248")
        assert old["events"] == "unavailable"

    def test_human_report_renders(self, tmp_path):
        from pactkit.run_stats import collect_runs, render_report

        _project(tmp_path)
        _run_with_blocker(tmp_path)
        text = render_report(collect_runs(tmp_path))
        assert "STORY-slim-247" in text
        assert "user_input" in text or "blocker" in text.lower()


class TestStatsCli:
    def test_stats_json_cli(self, tmp_path):
        _project(tmp_path)
        _run_with_blocker(tmp_path)
        proc = subprocess.run(
            ["python3", "-m", "pactkit", "-C", str(tmp_path), "stats", "--format", "json"],
            capture_output=True, text=True, cwd=tmp_path, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout)
        assert any(r.get("story_id") == "STORY-slim-247" for r in payload["runs"])

    def test_stats_human_cli(self, tmp_path):
        _project(tmp_path)
        _run_with_blocker(tmp_path)
        proc = subprocess.run(
            ["python3", "-m", "pactkit", "-C", str(tmp_path), "stats"],
            capture_output=True, text=True, cwd=tmp_path, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        assert "STORY-slim-247" in proc.stdout

    def test_ac10_continuation_events_cli(self, tmp_path):
        _project(tmp_path)
        _run_with_blocker(tmp_path)
        proc = subprocess.run(
            [
                "python3", "-m", "pactkit", "-C", str(tmp_path), "continuation", "events",
                "STORY-slim-247",
            ],
            capture_output=True, text=True, cwd=tmp_path, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        assert "step_entered" in proc.stdout
        assert "blocker_raised" in proc.stdout

    def test_ac10_continuation_events_empty_state(self, tmp_path):
        _project(tmp_path)
        proc = subprocess.run(
            [
                "python3", "-m", "pactkit", "-C", str(tmp_path), "continuation", "events",
                "STORY-slim-999",
            ],
            capture_output=True, text=True, cwd=tmp_path, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        assert "no events" in proc.stdout.lower() or "unavailable" in proc.stdout.lower()


class TestQaFollowups:
    """STORY session QA follow-ups: input validation + dwell pairing."""

    def test_events_cli_rejects_path_traversal_story_id(self, tmp_path):
        _project(tmp_path)
        proc = subprocess.run(
            [
                "python3", "-m", "pactkit", "-C", str(tmp_path), "continuation", "events",
                "../../etc/passwd",
            ],
            capture_output=True, text=True, cwd=tmp_path, timeout=60,
        )
        assert proc.returncode == 1
        assert "invalid Story ID" in (proc.stderr + proc.stdout)

    def test_dwell_measures_from_first_raise_in_episode(self, tmp_path):
        from pactkit.run_events import append_event, story_events_path
        from pactkit.run_stats import _summarize

        path = story_events_path(tmp_path, "STORY-slim-247")
        append_event(path, event="step_entered", story_id="STORY-slim-247", run_id=None)
        # Two consecutive raises without a clear: the episode starts at the FIRST
        append_event(
            path, event="blocker_raised", story_id="STORY-slim-247", run_id=None,
            step_id="red", status="blocked", detail={"blocker_kind": "user_input"},
        )
        append_event(
            path, event="blocker_raised", story_id="STORY-slim-247", run_id=None,
            step_id="red", status="blocked", detail={"blocker_kind": "user_input"},
        )
        from datetime import datetime, timedelta

        base = datetime.fromisoformat(_first_ts(path))
        # Simulate spacing by rewriting with explicit timestamps
        events = [
            {"ts": (base + timedelta(seconds=i)).isoformat(), "story_id": "STORY-slim-247",
             "run_id": None, "event": e, "step_id": "red", "status": "blocked",
             "detail": {"blocker_kind": "user_input"}}
            for i, e in enumerate(
                ["step_entered", "blocker_raised", "blocker_raised", "blocker_cleared"]
            )
        ]
        path.write_text(
            "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8",
        )
        summary = _summarize("STORY-slim-247", events, 0, kind="story",
                             story_id="STORY-slim-247", run_id=None)
        # Clear (t3) minus FIRST raise (t1) = 2s; the pre-fix code measured from the
        # second raise (t2) and reported 1s
        assert summary["blocker_dwell_seconds"]["user_input"] == 2.0


def _first_ts(path):
    from pactkit.run_events import read_events

    events, _ = read_events(path)
    return events[0]["ts"]
