"""Tests for BUG-slim-004: Cross-Flow Integrity Gaps.

R1: Hotfix lint step
R2: Done document validators
R3: upgrade --agent flag
R4: upgrade handler forwards agent
R5: Check uses spec-lint
R6: Design calls pactkit context
"""

import inspect
from pathlib import Path


def _get_done_prompt():
    from pactkit.prompts.commands import COMMANDS_CONTENT
    return COMMANDS_CONTENT["project-done.md"]


def _get_check_prompt():
    from pactkit.prompts.commands import COMMANDS_CONTENT
    return COMMANDS_CONTENT["project-check.md"]


# ---------------------------------------------------------------------------
# R1: HOTFIX_PROMPT must contain `pactkit lint` reference
# ---------------------------------------------------------------------------
class TestR1HotfixLint:
    def test_hotfix_prompt_contains_pactkit_lint(self):
        from pactkit.prompts.workflows import HOTFIX_PROMPT

        assert "pactkit lint" in HOTFIX_PROMPT, (
            "HOTFIX_PROMPT must reference 'pactkit lint' in Phase 2"
        )

    def test_hotfix_lint_after_test_step(self):
        from pactkit.prompts.workflows import HOTFIX_PROMPT

        lint_pos = HOTFIX_PROMPT.index("pactkit lint")
        test_pos = HOTFIX_PROMPT.index("Phase 2: Verify")
        assert lint_pos > test_pos, (
            "pactkit lint must appear after Phase 2 (Verify)"
        )


# ---------------------------------------------------------------------------
# R2: DONE_PROMPT must validate generated governance views
# ---------------------------------------------------------------------------
class TestR2DoneDocValidators:
    def test_done_prompt_contains_context_stdout(self):
        done = _get_done_prompt()
        assert "pactkit context --stdout" in done, (
            "Done prompt must validate local Context generation"
        )

    def test_done_prompt_contains_board_projection_check(self):
        done = _get_done_prompt()
        assert "pactkit board render --check" in done, (
            "Done prompt must validate the optional Board projection"
        )

    def test_done_lint_validators_in_phase3(self):
        done = _get_done_prompt()
        phase3_start = done.index("Phase 3: Hygiene")
        phase35_start = done.index("Phase 3.5:")
        phase3_text = done[phase3_start:phase35_start]
        assert "pactkit context --stdout" in phase3_text
        assert "pactkit board render --check" in phase3_text


# ---------------------------------------------------------------------------
# R3: upgrade subparser must have --agent flag
# ---------------------------------------------------------------------------
class TestR3UpgradeAgentFlag:
    def test_upgrade_parser_has_agent_flag(self):
        """upgrade must expose --agent (golden-pinned help surface).

        STORY-slim-2026082672b57c78fd67 moved the parser definitions into
        the shared _add_deploy_args builder, so source-string introspection
        of main() no longer sees them — the golden help snapshot is the
        behavior-level assertion."""
        golden = (
            Path(__file__).resolve().parent.parent
            / "fixtures" / "cli_help_golden" / "upgrade.txt"
        ).read_text(encoding="utf-8")
        assert "--agent" in golden

    def test_upgrade_agent_choices_match_init(self):
        """Verify upgrade --agent has same choices as init."""
        fixtures = Path(__file__).resolve().parent.parent / "fixtures" / "cli_help_golden"
        upgrade = (fixtures / "upgrade.txt").read_text(encoding="utf-8")
        init = (fixtures / "init.txt").read_text(encoding="utf-8")
        for choice in ("claude", "cursor", "copilot", "generic", "all"):
            assert choice in upgrade, f"upgrade --agent must include choice '{choice}'"
        # Both parsers come from the same _add_deploy_args builder; the
        # usage line wraps differently per command, so equality is asserted
        # on the option help text, not the wrapped usage line.
        up_help = next(l for l in upgrade.splitlines() if "Target agent format" in l)
        init_help = next(l for l in init.splitlines() if "Target agent format" in l)
        assert up_help == init_help


# ---------------------------------------------------------------------------
# R4: upgrade handler forwards agent to deploy()
# ---------------------------------------------------------------------------
class TestR4UpgradeForwardsAgent:
    def test_deploy_receives_agent_from_upgrade(self):
        """The deploy() call must include agent= (now in the extracted handler)."""
        from pactkit import cli as cli_module

        source = inspect.getsource(cli_module._run_deploy_command)
        assert "agent=" in source, (
            "deploy() call must pass agent= parameter"
        )


# ---------------------------------------------------------------------------
# R5: CHECK_PROMPT Phase 3 must reference pactkit spec-lint
# ---------------------------------------------------------------------------
class TestR5CheckSpecLint:
    def test_check_prompt_contains_spec_lint(self):
        check = _get_check_prompt()
        assert "pactkit spec-lint" in check, (
            "Check prompt must reference 'pactkit spec-lint'"
        )

    def test_check_spec_lint_in_phase3(self):
        check = _get_check_prompt()
        phase3_start = check.index("Phase 3:")
        phase35_idx = check.index("Phase 3.5:")
        phase3_text = check[phase3_start:phase35_idx]
        assert "pactkit spec-lint" in phase3_text


# ---------------------------------------------------------------------------
# R6: DESIGN_PROMPT must call pactkit context
# ---------------------------------------------------------------------------
class TestR6DesignContext:
    def test_design_prompt_contains_pactkit_context(self):
        from pactkit.prompts.workflows import DESIGN_PROMPT

        assert "pactkit context" in DESIGN_PROMPT, (
            "DESIGN_PROMPT must reference 'pactkit context'"
        )

    def test_design_context_after_phase4(self):
        from pactkit.prompts.workflows import DESIGN_PROMPT

        context_pos = DESIGN_PROMPT.index("pactkit context")
        phase4_pos = DESIGN_PROMPT.index("Phase 4: Board Setup")
        assert context_pos > phase4_pos, (
            "pactkit context must appear after Phase 4 (Board Setup)"
        )
