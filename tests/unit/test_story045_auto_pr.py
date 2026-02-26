"""
STORY-045: Auto-PR Enhancement

Tests for:
- Phase 4.2 Auto-PR Generation inserted into project-done.md
  (between Phase 4 Git Commit and Phase 4.5 Session Context Update)
"""


def _commands():
    from pactkit.prompts import COMMANDS_CONTENT
    return COMMANDS_CONTENT


# ===========================================================================
# Phase 4.2: Auto-PR Generation in project-done.md
# ===========================================================================

class TestDonePhase42AutoPR:
    """Phase 4.2 must be present in project-done.md between Phase 4 and Phase 4.5."""

    def test_phase_42_exists_in_done(self):
        """Phase 4.2 header exists in project-done.md."""
        content = _commands()["project-done.md"]
        assert "Phase 4.2" in content

    def test_phase_42_mentions_auto_pr(self):
        """Phase 4.2 is an Auto-PR phase."""
        content = _commands()["project-done.md"]
        assert "Auto-PR" in content

    def test_phase_42_mentions_main_master_skip(self):
        """Phase 4.2 skips when on main/master branch."""
        content = _commands()["project-done.md"]
        has_main_skip = (
            "main" in content and "master" in content
            and ("skip" in content.lower() or "Skip" in content)
        )
        assert has_main_skip

    def test_phase_42_mentions_existing_pr_check(self):
        """Phase 4.2 checks for an existing open PR."""
        content = _commands()["project-done.md"]
        assert "gh pr list" in content

    def test_phase_42_mentions_user_confirmation(self):
        """Phase 4.2 asks user for confirmation before creating PR."""
        content = _commands()["project-done.md"]
        has_confirmation = (
            "yes/no" in content
            or "yes/no/edit" in content
            or "confirmation" in content.lower()
            or ("yes" in content and "no" in content and "edit" in content)
        )
        assert has_confirmation

    def test_phase_42_mentions_gh_cli_fallback(self):
        """Phase 4.2 handles gh CLI being unavailable."""
        content = _commands()["project-done.md"]
        has_fallback = (
            "gh CLI" in content
            or "gh` CLI" in content
            or "gh cli" in content.lower()
        ) and (
            "unavailable" in content
            or "not available" in content
            or "skip" in content.lower()
        )
        assert has_fallback

    def test_phase_42_mentions_pr_body_structure(self):
        """Phase 4.2 defines a PR body with Summary, Changes, and Acceptance Criteria."""
        content = _commands()["project-done.md"]
        has_summary = "Summary" in content
        has_changes = "Changes" in content
        has_ac = "Acceptance Criteria" in content
        assert has_summary and has_changes and has_ac

    def test_phase_42_is_between_phase_4_and_phase_45(self):
        """Phase 4.2 appears between Phase 4 and Phase 4.5 in document order."""
        content = _commands()["project-done.md"]
        # Find Phase 4 (Git Commit) — use the section header
        pos_4 = content.find("Phase 4: Git Commit")
        pos_42 = content.find("Phase 4.2")
        pos_45 = content.find("Phase 4.5")
        assert pos_4 != -1, "Phase 4 (Git Commit) must exist"
        assert pos_42 != -1, "Phase 4.2 must exist"
        assert pos_45 != -1, "Phase 4.5 must exist"
        assert pos_4 < pos_42 < pos_45, (
            f"Expected order Phase 4 ({pos_4}) < Phase 4.2 ({pos_42}) < Phase 4.5 ({pos_45})"
        )
