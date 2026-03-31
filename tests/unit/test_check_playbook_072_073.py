"""
STORY-slim-072 + 073: Verify Check playbook contains Phase 4.5 and 4.7.
"""


class TestCheckPlaybookPhases:
    """R1 (072) + R2 (073): Check playbook has new config-gated phases."""

    def test_check_playbook_has_pactguard_phase(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT
        check = COMMANDS_CONTENT["project-check.md"]
        assert "Phase 4.5" in check
        assert "PactGuard" in check

    def test_check_playbook_has_observe_phase(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT
        check = COMMANDS_CONTENT["project-check.md"]
        assert "Phase 4.7" in check
        assert "Observability" in check

    def test_pactguard_phase_is_config_gated(self):
        """Phase 4.5 must mention config gate."""
        from pactkit.prompts.commands import COMMANDS_CONTENT
        check = COMMANDS_CONTENT["project-check.md"]
        assert "check.pactguard.enabled" in check

    def test_observe_phase_is_config_gated(self):
        """Phase 4.7 must mention config gate."""
        from pactkit.prompts.commands import COMMANDS_CONTENT
        check = COMMANDS_CONTENT["project-check.md"]
        assert "check.observe.enabled" in check

    def test_pactguard_phase_silent_skip(self):
        """Disabled → silently skip, no Verdict row."""
        from pactkit.prompts.commands import COMMANDS_CONTENT
        check = COMMANDS_CONTENT["project-check.md"]
        assert "silently skip" in check.lower()

    def test_act_playbook_unchanged(self):
        """072: Act playbook must NOT mention PactGuard."""
        from pactkit.prompts.commands import COMMANDS_CONTENT
        act = COMMANDS_CONTENT["project-act.md"]
        assert "PactGuard" not in act
        assert "Phase 0.3" not in act or "pactguard" not in act.lower()

    def test_done_playbook_unchanged(self):
        """072/073: Done playbook must NOT mention PactGuard or Observe."""
        from pactkit.prompts.commands import COMMANDS_CONTENT
        done = COMMANDS_CONTENT["project-done.md"]
        assert "PactGuard" not in done
        assert "Observability Scan" not in done
