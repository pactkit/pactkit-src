"""Tests for STORY-slim-114: Act Phase 4 Journey Sync.

Acceptance Criteria:
- AC1: Journey Sync step exists in Act Phase 4
- AC2: Skip condition for missing journey.md
- AC3: Skip condition for missing Journey Segment in Spec
- AC4: Triggered when both conditions met
- AC5: Plan Phase 3.2a has conditional Journey Segment generation
"""

def _prompts():
    """Lazy import to pick up source changes."""
    import importlib

    import pactkit.prompts.commands as cmd_mod

    importlib.reload(cmd_mod)
    return cmd_mod


# ---------------------------------------------------------------------------
# AC1: Journey Sync step exists in Act Phase 4
# ---------------------------------------------------------------------------
class TestAC1JourneySyncExists:
    def test_act_phase4_has_journey_sync(self):
        cmd = _prompts()
        act = cmd.COMMANDS_CONTENT["project-act.md"]
        assert "Journey Sync" in act, (
            "Act Phase 4 must contain a 'Journey Sync' step"
        )

    def test_journey_sync_is_conditional(self):
        cmd = _prompts()
        act = cmd.COMMANDS_CONTENT["project-act.md"]
        assert "Conditional" in act and "Journey Sync" in act, (
            "Journey Sync must be marked as Conditional"
        )

    def test_journey_sync_after_visualize(self):
        """Journey Sync must appear after visualize step in Phase 4."""
        cmd = _prompts()
        act = cmd.COMMANDS_CONTENT["project-act.md"]
        vis_pos = act.find("pactkit visualize --lazy")
        journey_pos = act.find("Journey Sync")
        assert vis_pos < journey_pos, (
            "Journey Sync must come after visualize in Phase 4"
        )

    def test_journey_sync_before_board_update(self):
        """Journey Sync must appear before board update in Phase 4."""
        cmd = _prompts()
        act = cmd.COMMANDS_CONTENT["project-act.md"]
        journey_pos = act.find("Journey Sync")
        board_pos = act.find("Update Board")
        assert journey_pos < board_pos, (
            "Journey Sync must come before Board Update in Phase 4"
        )


# ---------------------------------------------------------------------------
# AC2 & AC3: Skip conditions
# ---------------------------------------------------------------------------
class TestAC2AC3SkipConditions:
    def test_skip_if_no_journey_md(self):
        """Must skip if docs/e2e/journey.md does not exist."""
        cmd = _prompts()
        act = cmd.COMMANDS_CONTENT["project-act.md"]
        assert "journey.md" in act and "not exist" in act.lower() or "does not exist" in act.lower(), (
            "Journey Sync must have skip condition for missing journey.md"
        )

    def test_skip_if_no_journey_segment_section(self):
        """Must skip if Spec has no Journey Segment section."""
        cmd = _prompts()
        act = cmd.COMMANDS_CONTENT["project-act.md"]
        assert "Journey Segment" in act, (
            "Journey Sync must reference '## Journey Segment' section as skip condition"
        )


# ---------------------------------------------------------------------------
# AC4: Triggered behavior
# ---------------------------------------------------------------------------
class TestAC4TriggerBehavior:
    def test_reads_journey_md_when_triggered(self):
        cmd = _prompts()
        act = cmd.COMMANDS_CONTENT["project-act.md"]
        lower = act.lower()
        assert "read" in lower and "journey.md" in lower, (
            "Journey Sync must instruct to Read journey.md"
        )

    def test_uses_edit_not_write(self):
        """R5: Must use Edit (incremental), not Write (full replace)."""
        cmd = _prompts()
        act = cmd.COMMANDS_CONTENT["project-act.md"]
        journey_section_start = act.find("Journey Sync")
        journey_section = act[journey_section_start:journey_section_start + 800]
        assert "Edit" in journey_section, (
            "Journey Sync must use Edit for incremental updates"
        )


# ---------------------------------------------------------------------------
# AC5: Plan Phase 3.2a conditional Journey Segment
# ---------------------------------------------------------------------------
class TestAC5PlanJourneySegment:
    def test_plan_has_journey_segment_generation(self):
        cmd = _prompts()
        plan = cmd.COMMANDS_CONTENT["project-plan.md"]
        assert "Journey Segment" in plan, (
            "Plan must reference Journey Segment generation"
        )

    def test_plan_journey_segment_is_conditional(self):
        """Must be conditional on journey.md existence."""
        cmd = _prompts()
        plan = cmd.COMMANDS_CONTENT["project-plan.md"]
        lower = plan.lower()
        assert "journey.md" in lower and ("if" in lower or "conditional" in lower), (
            "Plan Journey Segment must be conditional on journey.md existence"
        )

    def test_plan_journey_segment_format(self):
        """Must define the annotation format with Journey/Steps/Impact fields."""
        cmd = _prompts()
        plan = cmd.COMMANDS_CONTENT["project-plan.md"]
        assert "Journey:" in plan and "Steps:" in plan and "Impact:" in plan, (
            "Plan must define Journey Segment format with Journey/Steps/Impact fields"
        )
