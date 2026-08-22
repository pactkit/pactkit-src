"""Tests for context_gen.py — Agent Continuation (STORY-slim-071)."""
from __future__ import annotations

from pathlib import Path

import pytest

# Board template with standard sections
_BOARD_TEMPLATE = """\
# Sprint Board

## 📋 Backlog

## 🔄 In Progress

{in_progress}

## ✅ Done

- **STORY-slim-001**: First story
"""

_SPEC_TEMPLATE = """\
# STORY-slim-070: Test Story

| Field | Value |
|-------|-------|
| ID | STORY-slim-070 |
| Status | Draft |
| Priority | P1 |
| Release | 3.0.0 |

## Requirements

### R1: First requirement (MUST)

The implementation MUST preserve verified continuation state.

### R2: Second requirement (MUST)

The implementation MUST render completed acceptance criteria.

## Acceptance Criteria

### AC1: First Check (R1)

- **Given** precondition
- **When** action
- **Then** result

### AC2: Second Check (R1)

- **Given** precondition
- **When** action
- **Then** result

### AC3: Third Check (R2)

- **Given** precondition
- **When** action
- **Then** result

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Test fixture contains no credentials |
"""


@pytest.fixture()
def project_tree(tmp_path: Path) -> Path:
    """Create a minimal project tree for context gen."""
    (tmp_path / "docs" / "product").mkdir(parents=True)
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    (tmp_path / "docs" / "architecture" / "governance").mkdir(parents=True)
    (tmp_path / ".git").mkdir()  # Fake git dir to avoid subprocess errors
    return tmp_path


def _write_board(root: Path, in_progress: str = "") -> None:
    board = root / "docs" / "product" / "sprint_board.md"
    board.write_text(_BOARD_TEMPLATE.format(in_progress=in_progress))


# ---------------------------------------------------------------------------
# R1: Agent Continuation Section
# ---------------------------------------------------------------------------


class TestAgentContinuation:
    """R1: context.md includes ## Agent Continuation section."""

    def test_continuation_section_present_with_args(self, project_tree: Path) -> None:
        """AC1: continuation args → section has Last Command, Phase Reached."""
        _write_board(
            project_tree,
            "### [STORY-slim-070] Test Story\n- [ ] Task 1\n",
        )
        (project_tree / "docs" / "specs" / "STORY-slim-070.md").write_text(_SPEC_TEMPLATE)

        from pactkit.context_gen import generate_context

        content = generate_context(
            project_tree,
            command="pactkit context",
            continuation_args={
                "last_command": "/project-act STORY-slim-070",
                "phase": "Phase 3: step 2/5",
            },
        )
        assert "## Agent Continuation" in content
        assert "Last Command: /project-act STORY-slim-070" in content
        assert "Phase Reached: Phase 3: step 2/5" in content

    def test_continuation_with_blockers(self, project_tree: Path) -> None:
        """R1: blockers field present when provided."""
        _write_board(
            project_tree,
            "### [STORY-slim-070] Test Story\n- [ ] Task 1\n",
        )
        (project_tree / "docs" / "specs" / "STORY-slim-070.md").write_text(_SPEC_TEMPLATE)

        from pactkit.context_gen import generate_context

        content = generate_context(
            project_tree,
            command="pactkit context",
            continuation_args={
                "last_command": "/project-act STORY-slim-070",
                "phase": "Phase 2: TDD",
                "blockers": "RFC: R3 unclear",
            },
        )
        assert "Blockers: RFC: R3 unclear" in content

    def test_checkpoint_overrides_stale_explicit_handoff_and_marks_completed_acs(self, project_tree: Path) -> None:
        _write_board(
            project_tree,
            "### [STORY-slim-070] Test Story\n- [x] Task 1\n",
        )
        (project_tree / "docs" / "specs" / "STORY-slim-070.md").write_text(_SPEC_TEMPLATE)
        from pactkit.continuation import ContinuationStore
        from pactkit.context_gen import generate_context

        store = ContinuationStore(project_tree)
        store.checkpoint(
            "STORY-slim-070", step_id="preflight", evidence={"spec_lint": "pass"},
        )
        store.checkpoint(
            "STORY-slim-070", step_id="red", evidence={"story_tests": {"exit_code": 1}},
        )
        store.checkpoint(
            "STORY-slim-070", step_id="green", evidence={"story_tests": {"exit_code": 0}},
        )
        store.checkpoint(
            "STORY-slim-070", step_id="regression_lint",
            evidence={"regression": "pass", "lint": "pass"},
        )
        store.checkpoint(
            "STORY-slim-070", step_id="sync_coverage", status="completed",
            phase="Phase 4: complete",
            evidence={
                "spec_lint": "pass", "story_tests": {"exit_code": 0},
                "regression": "pass", "lint": "pass",
                "coverage": {"R1": ["test"], "R2": ["test"]},
                "acceptance_coverage": {"AC1": ["test"], "AC2": ["test"], "AC3": ["test"]},
                "board_tasks": ["Task 1"],
            },
        )
        content = generate_context(
            project_tree, command="pactkit context",
            continuation_args={"last_command": "/project-act STORY-slim-070", "phase": "stale"},
        )
        assert "Verified Continuation: STORY-slim-070" in content
        assert "Phase Reached: Phase 4: complete" in content
        assert "Phase Reached: stale" not in content
        assert "- [x] AC1" in content
        context_path = project_tree / "docs/product/context.md"
        context_path.write_text(content, encoding="utf-8")
        assert store.resume("STORY-slim-070")["reasons"] == ["checkpoint is completed"]

    def test_no_in_progress_shows_default(self, project_tree: Path) -> None:
        """AC7: no in-progress story → 'No active work session.'"""
        _write_board(project_tree, "")

        from pactkit.context_gen import generate_context

        content = generate_context(project_tree, command="pactkit context")
        assert "## Agent Continuation" in content
        assert "No active work session." in content

    def test_backward_compatible_without_continuation(self, project_tree: Path) -> None:
        """AC8: calling without continuation_args still adds default section."""
        _write_board(project_tree, "")

        from pactkit.context_gen import generate_context

        content = generate_context(project_tree, command="pactkit context")
        # All original sections still present
        assert "## Sprint Status" in content
        assert "## Current Stories" in content
        assert "## Next Recommended Action" in content
        # New section appended with default
        assert "## Agent Continuation" in content
        assert "No active work session." in content


# ---------------------------------------------------------------------------
# R3: Done Clears Continuation
# ---------------------------------------------------------------------------


class TestDoneClearsContinuation:
    """R3: calling without continuation_args clears to default."""

    def test_no_continuation_args_shows_default(self, project_tree: Path) -> None:
        """AC5: generate_context() without continuation_args → default message."""
        _write_board(
            project_tree,
            "### [STORY-slim-070] Test Story\n- [ ] Task 1\n",
        )

        from pactkit.context_gen import generate_context

        # No continuation_args = "Done cleared it"
        content = generate_context(project_tree, command="pactkit context")
        assert "No active work session." in content


# ---------------------------------------------------------------------------
# R4: Sprint Contract Extraction
# ---------------------------------------------------------------------------


class TestSprintContract:
    """R4: extract AC titles from spec as checklist."""

    def test_extracts_ac_titles(self, project_tree: Path) -> None:
        """AC6: Sprint Contract shows AC titles as checklist."""
        _write_board(
            project_tree,
            "### [STORY-slim-070] Test Story\n- [ ] Task 1\n",
        )
        (project_tree / "docs" / "specs" / "STORY-slim-070.md").write_text(_SPEC_TEMPLATE)

        from pactkit.context_gen import _extract_sprint_contract

        contract = _extract_sprint_contract(
            project_tree / "docs" / "specs" / "STORY-slim-070.md",
        )
        assert "AC1: First Check" in contract
        assert "AC2: Second Check" in contract
        assert "AC3: Third Check" in contract
        # Should be unchecked by default
        assert "- [ ] AC1" in contract

    def test_sprint_contract_in_full_output(self, project_tree: Path) -> None:
        """AC1+AC6: continuation with story → Sprint Contract in output."""
        _write_board(
            project_tree,
            "### [STORY-slim-070] Test Story\n- [ ] Task 1\n",
        )
        (project_tree / "docs" / "specs" / "STORY-slim-070.md").write_text(_SPEC_TEMPLATE)

        from pactkit.context_gen import generate_context

        content = generate_context(
            project_tree,
            command="pactkit context",
            continuation_args={
                "last_command": "/project-act STORY-slim-070",
                "phase": "Phase 3: step 1/5",
            },
        )
        assert "### Sprint Contract" in content
        assert "AC1:" in content

    def test_no_spec_file_no_contract(self, project_tree: Path) -> None:
        """Edge: story in progress but spec file missing → no contract section."""
        _write_board(
            project_tree,
            "### [STORY-slim-099] Unknown Story\n- [ ] Task 1\n",
        )

        from pactkit.context_gen import generate_context

        content = generate_context(
            project_tree,
            command="pactkit context",
            continuation_args={
                "last_command": "/project-act STORY-slim-099",
                "phase": "Phase 1",
            },
        )
        assert "## Agent Continuation" in content
        assert "Sprint Contract" not in content


# ---------------------------------------------------------------------------
# R5: Schema Update
# ---------------------------------------------------------------------------


class TestSchemaUpdate:
    """R5: CONTEXT_SECTIONS includes the new section."""

    def test_continuation_in_context_sections(self) -> None:
        from pactkit.schemas import CONTEXT_SECTIONS

        assert "## Agent Continuation" in CONTEXT_SECTIONS

    def test_continuation_constant_exists(self) -> None:
        from pactkit.schemas import CONTEXT_SECTION_CONTINUATION

        assert CONTEXT_SECTION_CONTINUATION == "## Agent Continuation"


# ---------------------------------------------------------------------------
# SEC-1: Input Validation
# ---------------------------------------------------------------------------


class TestInputSanitization:
    """SEC-1: free-text CLI args sanitized before writing."""

    def test_multiline_input_collapsed(self, project_tree: Path) -> None:
        """SEC-1: newlines in --phase should not break markdown structure."""
        _write_board(
            project_tree,
            "### [STORY-slim-070] Test Story\n- [ ] Task 1\n",
        )
        (project_tree / "docs" / "specs" / "STORY-slim-070.md").write_text(_SPEC_TEMPLATE)

        from pactkit.context_gen import generate_context

        content = generate_context(
            project_tree,
            command="pactkit context",
            continuation_args={
                "last_command": "/project-act STORY-slim-070",
                "phase": "Phase 3\n## Injected Section\nEvil content",
            },
        )
        # Should not contain the injected section header
        assert "## Injected Section" not in content
        assert "Evil content" not in content
