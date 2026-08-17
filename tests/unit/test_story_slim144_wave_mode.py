"""Tests for STORY-slim-144: spec-graph --json + SPRINT_PROMPT wave mode.

AC1: --json emits {waves, conflicts} with sorted deterministic ordering
AC2: cycle under --json -> non-zero exit, stderr names cycle
AC3: mode detection in SPRINT_PROMPT (args -> single-story; empty -> wave mode)
AC4: scheduling policy encoded (declared Touches, max_parallel cap, serialized tail)
AC5: wave gate + failure policy + pre-dispatch wave plan
"""

from __future__ import annotations

import json
import textwrap

import pytest

from pactkit import spec_graph
from pactkit.prompts import workflows


def _spec(story_id, depends="None", touches="`a.py`", status="Draft"):
    surface = textwrap.dedent(
        f"""\
        | Field | Value |
        |-------|-------|
        | Depends on | {depends} |
        | Provides | None |
        | Touches | {touches} |
        | Conflict risk | LOW |"""
    )
    return textwrap.dedent(
        f"""\
        # {story_id}: Demo

        | Field | Value |
        |-------|-------|
        | ID | {story_id} |
        | Status | {status} |
        | Priority | P1 |
        | Release | 2.19.0 |

        ## Requirements

        ### R1: X (MUST)

        MUST x.

        ## Acceptance Criteria

        ### AC1: X (R1)

        - **Given** a
        - **When** b
        - **Then** c

        ## Security Scope

        | Check | Applicable | Reason |
        |-------|------------|--------|
        | SEC-1 | N/A | t |
        """
    ) + f"\n## Dependency Surface\n\n{surface}\n"


@pytest.fixture
def three_specs(tmp_path):
    """A (touches a.py) <- B; C (touches a.py) — wave1={A,C} conflict, wave2={B}."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "STORY-slim-810.md").write_text(_spec("STORY-slim-810"))
    (specs / "STORY-slim-811.md").write_text(
        _spec("STORY-slim-811", depends="STORY-slim-810", touches="`b.py`"))
    (specs / "STORY-slim-812.md").write_text(_spec("STORY-slim-812"))
    return specs


class TestJsonOutput:
    def test_json_shape_and_determinism(self, three_specs, capsys):
        rc = spec_graph.main(["--specs-dir", str(three_specs), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["waves"] == [["STORY-slim-810", "STORY-slim-812"], ["STORY-slim-811"]]
        assert len(data["conflicts"]) == 1
        c = data["conflicts"][0]
        assert c == {
            "story_a": "STORY-slim-810",
            "story_b": "STORY-slim-812",
            "shared": "a.py",
            "same_wave": True,
        }
        # deterministic: second run byte-identical
        spec_graph.main(["--specs-dir", str(three_specs), "--json"])
        out2 = capsys.readouterr().out
        spec_graph.main(["--specs-dir", str(three_specs), "--json"])
        assert capsys.readouterr().out == out2

    def test_json_cycle_error(self, tmp_path, capsys):
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "STORY-slim-820.md").write_text(
            _spec("STORY-slim-820", depends="STORY-slim-821"))
        (specs / "STORY-slim-821.md").write_text(
            _spec("STORY-slim-821", depends="STORY-slim-820"))
        rc = spec_graph.main(["--specs-dir", str(specs), "--json"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "STORY-slim-820" in err or "STORY-slim-821" in err

    def test_json_empty(self, tmp_path, capsys):
        specs = tmp_path / "specs"
        specs.mkdir()
        rc = spec_graph.main(["--specs-dir", str(specs), "--json"])
        assert rc == 0
        assert json.loads(capsys.readouterr().out) == {"waves": [], "conflicts": []}


class TestSprintWavePrompt:
    """AC3-AC5: SPRINT_PROMPT encodes wave mode policy (content assertions)."""

    def test_mode_detection(self):
        p = workflows.SPRINT_PROMPT
        assert "wave mode" in p.lower()
        # non-empty args -> single-story preserved
        assert "single-story" in p.lower() or "single story" in p.lower()

    def test_scheduling_policy(self):
        p = workflows.SPRINT_PROMPT
        assert "spec-graph --json" in p
        assert "max_parallel" in p
        # safe-by-default: undeclared Touches serialize
        assert "serialize" in p.lower() or "serialized" in p.lower()

    def test_wave_gate_and_failure_policy(self):
        p = workflows.SPRINT_PROMPT
        lower = p.lower()
        assert "wave gate" in lower or ("wave" in lower and "merged" in lower)
        assert "never auto-retry" in lower or "no auto-retry" in lower or "NEVER auto-retry" in p
        assert "git merge --abort" in p

    def test_wave_plan_before_dispatch(self):
        assert "wave plan" in workflows.SPRINT_PROMPT.lower()

    def test_single_story_mode_preserved(self):
        """Existing single-story markers must survive the edit."""
        p = workflows.SPRINT_PROMPT
        assert "pactkit next-id" in p
        assert "TeamCreate" in p
