"""Tests for STORY-slim-111: Check Phase 4 Playwright Assertion Strategy Guide.

Verifies:
- R1: Element locator priority is documented (role > data-testid > CSS)
- R2: AI content assertion boundaries (structure yes, specific text no)
- R3: Wait strategy for async AI responses (state signal, not fixed timeout)
- R4: Positioned after Journey-Based Coverage subsection (compatible)
"""
import pytest

from pactkit.prompts.commands import COMMANDS_CONTENT


@pytest.fixture()
def check_prompt():
    return COMMANDS_CONTENT["project-check.md"]


# ---------------------------------------------------------------------------
# R1: Element Locator Priority
# ---------------------------------------------------------------------------
class TestR1LocatorPriority:
    """Phase 4 must document element locator priority order."""

    def test_mentions_accessibility_role(self, check_prompt):
        """R1: MUST mention accessibility role as highest priority locator."""
        assert "role" in check_prompt.lower()

    def test_mentions_data_testid(self, check_prompt):
        """R1: MUST mention data-testid as fallback locator."""
        assert "data-testid" in check_prompt

    def test_mentions_css_selector_last_resort(self, check_prompt):
        """R1: MUST mention CSS selector as last resort."""
        prompt_lower = check_prompt.lower()
        assert "css" in prompt_lower

    def test_priority_order_role_before_testid(self, check_prompt):
        """R1: role must appear before data-testid in the priority list."""
        role_pos = check_prompt.lower().find("role")
        testid_pos = check_prompt.find("data-testid")
        assert role_pos < testid_pos, "role should be listed before data-testid"

    def test_priority_order_testid_before_css(self, check_prompt):
        """R1: data-testid must appear before CSS selector in the priority list."""
        # Find within the assertion strategy section
        section_start = check_prompt.find("Playwright Assertion Strategy")
        assert section_start != -1, "Section header must exist"
        section = check_prompt[section_start:]
        testid_pos = section.find("data-testid")
        css_pos = section.lower().find("css")
        assert testid_pos < css_pos, "data-testid should be listed before CSS"


# ---------------------------------------------------------------------------
# R2: AI Content Assertion Boundaries
# ---------------------------------------------------------------------------
class TestR2AIContentAssertions:
    """Phase 4 must document what to assert and what NOT to assert for AI content."""

    def test_assert_structure_exists(self, check_prompt):
        """R2: MUST instruct asserting structure exists."""
        prompt_lower = check_prompt.lower()
        assert "structure" in prompt_lower

    def test_assert_content_non_empty(self, check_prompt):
        """R2: MUST instruct asserting content is non-empty."""
        prompt_lower = check_prompt.lower()
        assert "non-empty" in prompt_lower or "not empty" in prompt_lower

    def test_assert_no_error_state(self, check_prompt):
        """R2: MUST instruct asserting no error/exception state."""
        prompt_lower = check_prompt.lower()
        assert "error" in prompt_lower or "exception" in prompt_lower

    def test_must_not_assert_specific_text(self, check_prompt):
        """R2: MUST NOT assert specific text content for AI output."""
        # The section should contain guidance about not asserting specific text
        section_start = check_prompt.find("Playwright Assertion Strategy")
        assert section_start != -1
        section = check_prompt[section_start:]
        section_lower = section.lower()
        assert "specific text" in section_lower or "exact text" in section_lower

    def test_must_not_assert_specific_values(self, check_prompt):
        """R2: MUST NOT assert specific numeric values for AI output."""
        section_start = check_prompt.find("Playwright Assertion Strategy")
        assert section_start != -1
        section = check_prompt[section_start:]
        section_lower = section.lower()
        assert "numeric" in section_lower or "specific value" in section_lower


# ---------------------------------------------------------------------------
# R3: Wait Strategy
# ---------------------------------------------------------------------------
class TestR3WaitStrategy:
    """Phase 4 must document wait strategy for async AI responses."""

    def test_loading_state_signal(self, check_prompt):
        """R3: SHOULD mention using loading state disappearance as signal."""
        prompt_lower = check_prompt.lower()
        assert "loading" in prompt_lower

    def test_streaming_completion_marker(self, check_prompt):
        """R3: SHOULD mention streaming completion marker."""
        assert "data-streaming" in check_prompt

    def test_not_fixed_timeout(self, check_prompt):
        """R3: SHOULD advise against fixed timeout/sleep."""
        section_start = check_prompt.find("Playwright Assertion Strategy")
        assert section_start != -1
        section = check_prompt[section_start:]
        section_lower = section.lower()
        assert "fixed" in section_lower or "sleep" in section_lower


# ---------------------------------------------------------------------------
# R4: Compatibility with Journey-Based Coverage
# ---------------------------------------------------------------------------
class TestR4JourneyCompatibility:
    """Assertion strategy section must be positioned after Journey-Based Coverage."""

    def test_section_exists(self, check_prompt):
        """R4: 'Playwright Assertion Strategy' section MUST exist."""
        assert "Playwright Assertion Strategy" in check_prompt

    def test_positioned_after_journey_section(self, check_prompt):
        """R4: Assertion strategy MUST appear after Journey-Based Coverage."""
        journey_pos = check_prompt.find("Journey-Based Coverage")
        assertion_pos = check_prompt.find("Playwright Assertion Strategy")
        assert journey_pos != -1, "Journey-Based Coverage must exist"
        assert assertion_pos != -1, "Playwright Assertion Strategy must exist"
        assert assertion_pos > journey_pos, (
            "Playwright Assertion Strategy should come after Journey-Based Coverage"
        )

    def test_positioned_before_phase_4_5(self, check_prompt):
        """R4: Assertion strategy should be within Phase 4, before Phase 4.5."""
        assertion_pos = check_prompt.find("Playwright Assertion Strategy")
        phase45_pos = check_prompt.find("Phase 4.5")
        assert assertion_pos < phase45_pos, (
            "Playwright Assertion Strategy should be before Phase 4.5"
        )
