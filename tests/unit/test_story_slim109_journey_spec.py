"""Tests for STORY-slim-109: E2E journey.md format specification.

Verifies:
- R1: journey.md format spec exists and contains required sections
- R2: File Atlas registers docs/e2e/journey.md
- R3: Check Phase 4 references journey.md
- R4: AI content assertion strategy is documented
"""
import os

import pytest


class TestFileAtlasRegistration:
    """R2: File Atlas includes journey.md entry."""

    def test_atlas_contains_journey_md_path(self):
        """The File Atlas in rules.py MUST contain docs/e2e/journey.md."""
        from pactkit.prompts.rules import RULES_MODULES

        atlas = RULES_MODULES["atlas"]
        assert "docs/e2e/journey.md" in atlas

    def test_atlas_journey_purpose_description(self):
        """The journey.md entry MUST have a purpose mentioning User Journey."""
        from pactkit.prompts.rules import RULES_MODULES

        atlas = RULES_MODULES["atlas"]
        # The purpose column should mention journey definitions
        assert "User Journey" in atlas or "user journey" in atlas


class TestCheckPhase4JourneyReference:
    """R3: Check Phase 4 references journey.md for E2E guidance."""

    def test_check_command_references_journey_md(self):
        """project-check Phase 4 MUST reference journey.md."""
        from pactkit.prompts.commands import COMMANDS_CONTENT

        check_content = COMMANDS_CONTENT["project-check.md"]
        assert "journey.md" in check_content

    def test_check_phase4_journey_guidance(self):
        """Phase 4 MUST provide guidance on using journey.md for E2E coverage."""
        from pactkit.prompts.commands import COMMANDS_CONTENT

        check_content = COMMANDS_CONTENT["project-check.md"]
        # Should mention consulting journey.md when it exists
        assert "docs/e2e/journey.md" in check_content


class TestJourneySpecDocument:
    """R1 + R4: journey.md format specification document exists with required content."""

    @pytest.fixture
    def journey_path(self):
        """Path to the journey.md spec document."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        return os.path.join(project_root, "docs", "e2e", "journey.md")

    def test_journey_md_exists(self, journey_path):
        """R1: docs/e2e/journey.md MUST exist."""
        assert os.path.isfile(journey_path), (
            f"docs/e2e/journey.md not found at {journey_path}"
        )

    def test_journey_md_has_format_header(self, journey_path):
        """R1: journey.md MUST have a format specification header."""
        content = open(journey_path).read()
        assert "# " in content  # Has a title
        # Should explain it is a format specification
        assert "format" in content.lower() or "specification" in content.lower()

    def test_journey_md_has_step_sequence(self, journey_path):
        """R1: Format MUST define step sequence structure."""
        content = open(journey_path).read()
        assert "step" in content.lower()

    def test_journey_md_has_execution_layer_annotation(self, journey_path):
        """R1: Steps MUST annotate execution layer."""
        content = open(journey_path).read()
        assert "[client]" in content
        assert "[server]" in content

    def test_journey_md_has_assertions_section(self, journey_path):
        """R1: Format MUST define assertions per step."""
        content = open(journey_path).read()
        assert "assert" in content.lower()

    def test_journey_md_has_fixture_section(self, journey_path):
        """R1: Format MUST define pre-condition fixtures."""
        content = open(journey_path).read()
        assert "fixture" in content.lower() or "pre-condition" in content.lower()

    def test_journey_md_has_structure_vs_content_assertions(self, journey_path):
        """R1: Assertions MUST be split into structure and content types."""
        content = open(journey_path).read()
        assert "structure" in content.lower()
        # Content assertions should be marked as MUST NOT for AI content
        assert "content" in content.lower()

    def test_journey_md_has_ai_assertion_guide(self, journey_path):
        """R4: MUST include AI content assertion strategy guide."""
        content = open(journey_path).read()
        # Should have a section about AI-generated content assertions
        assert "AI" in content
        # Should advise asserting structure exists
        assert "non-empty" in content.lower() or "not empty" in content.lower()
        # Should advise NOT asserting specific text
        assert "MUST NOT" in content or "must not" in content.lower()
