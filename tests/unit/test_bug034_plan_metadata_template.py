"""
BUG-034: Plan Command Missing Spec Metadata Table Template
Tests that the Plan command playbook contains an explicit metadata table template.
"""


class TestR1MetadataTableTemplate:
    """R1: Plan command playbook MUST include explicit metadata table template."""

    def test_plan_command_contains_metadata_header(self):
        """Plan command contains '| Field | Value |' header."""
        from pactkit.prompts.commands import COMMANDS_CONTENT

        plan_content = COMMANDS_CONTENT["project-plan.md"]
        assert "| Field | Value |" in plan_content

    def test_plan_command_contains_metadata_separator(self):
        """Plan command contains '|-------|-------|' separator."""
        from pactkit.prompts.commands import COMMANDS_CONTENT

        plan_content = COMMANDS_CONTENT["project-plan.md"]
        assert "|-------|-------|" in plan_content

    def test_plan_command_contains_id_field(self):
        """Plan command contains '| ID |' field row."""
        from pactkit.prompts.commands import COMMANDS_CONTENT

        plan_content = COMMANDS_CONTENT["project-plan.md"]
        assert "| ID |" in plan_content

    def test_plan_command_contains_status_field(self):
        """Plan command contains '| Status |' field row."""
        from pactkit.prompts.commands import COMMANDS_CONTENT

        plan_content = COMMANDS_CONTENT["project-plan.md"]
        assert "| Status |" in plan_content

    def test_plan_command_contains_priority_field(self):
        """Plan command contains '| Priority |' field row."""
        from pactkit.prompts.commands import COMMANDS_CONTENT

        plan_content = COMMANDS_CONTENT["project-plan.md"]
        assert "| Priority |" in plan_content

    def test_plan_command_contains_release_field(self):
        """Plan command contains '| Release |' field row."""
        from pactkit.prompts.commands import COMMANDS_CONTENT

        plan_content = COMMANDS_CONTENT["project-plan.md"]
        assert "| Release |" in plan_content


class TestR2CanonicalFormatConsistency:
    """R2: Template SHOULD match scaffold.py:create_spec() format."""

    def test_metadata_table_uses_exact_field_names(self):
        """Metadata table uses exact field names (ID, Status, Priority, Release)."""
        from pactkit.prompts.commands import COMMANDS_CONTENT

        plan_content = COMMANDS_CONTENT["project-plan.md"]
        # Field names must be exact case (not bold, not different names)
        assert "| ID |" in plan_content
        assert "| Status |" in plan_content
        assert "| Priority |" in plan_content
        assert "| Release |" in plan_content
        # Should NOT contain bold field names
        assert "| **ID** |" not in plan_content
        assert "| **Status** |" not in plan_content
