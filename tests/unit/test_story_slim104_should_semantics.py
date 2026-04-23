"""
STORY-slim-104: Fix L3 SHOULD semantics in Signal Strength Convention
STORY-slim-105: Upgrade L3 SHOULD to require DEFERRED comment when skipped

Verifies that L3 Recommended uses RFC 2119 SHOULD semantics,
not the misleading "warning, non-blocking" phrasing.
"""

from pactkit.prompts.rules import RULES_MODULES


class TestL3ShouldSemantics:
    """AC1 + AC2: L3 row and clarification note in source."""

    def test_l3_semantics_is_rfc2119(self):
        """R1: L3 must require DEFERRED comment when skipped (STORY-slim-105 upgrade)."""
        core = RULES_MODULES["core"]
        assert "Default required" in core
        assert "DEFERRED" in core  # STORY-slim-105: upgraded from "stated reason" to DEFERRED comment

    def test_old_semantics_removed(self):
        """R1: Old misleading phrasing must not appear."""
        core = RULES_MODULES["core"]
        assert "warning, non-blocking" not in core

    def test_should_clarification_note(self):
        """R2: Clarification bullet that SHOULD is not optional."""
        core = RULES_MODULES["core"]
        assert "SHOULD" in core
        assert "not optional" in core or "DEFERRED" in core
