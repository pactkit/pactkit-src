"""STORY-slim-099: Act Phase reference in Shared Protocols Context.md section."""

from pactkit.prompts.rules import RULES_MODULES


class TestAC1SharedProtocolsReference:
    """AC1: Shared Protocols Context.md Canonical Format includes Act Phase 4."""

    def test_context_canonical_format_references_act_phase4(self):
        shared = RULES_MODULES["shared"]
        assert "Act Phase 4" in shared

    def test_context_canonical_format_referenced_by_line(self):
        shared = RULES_MODULES["shared"]
        for line in shared.splitlines():
            if "Local Context Projection Format" in line:
                break
        else:
            raise AssertionError("Local Context Projection Format section not found")
        # The next non-empty line should be the "Referenced by" line
        lines = shared.splitlines()
        idx = lines.index(line)
        ref_line = lines[idx + 1]
        assert "Act Phase 4" in ref_line
        assert "Init Phase 6" in ref_line
        assert "Plan Phase 3" in ref_line
        assert "Done Phase 4.5" in ref_line


class TestAC2AC3SourceTemplateConsistency:
    """AC2/AC3: Source template Act Phase 4 has context continuation step."""

    def test_act_template_has_continuation_step(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        act_template = COMMANDS_CONTENT["project-act.md"]
        assert "pactkit context --continuation" in act_template

    def test_act_template_continuation_in_phase4(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        act_template = COMMANDS_CONTENT["project-act.md"]
        phase4_start = act_template.index("Phase 4")
        remainder = act_template[phase4_start:]
        assert "pactkit context --continuation" in remainder
