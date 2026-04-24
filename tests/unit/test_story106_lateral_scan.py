"""Tests for STORY-slim-106: Plan Lateral Scan + hooks removal + spec_linter W010.

AC1: Plan playbook contains Lateral Scan step
AC2: Solution Design Protocol contains Internal Patterns step
AC3: Architecture Principles uses generic examples
AC4: hooks code completely removed
AC5: spec_linter W010 for missing Lateral Scan Results
"""
import sys
import warnings
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestAC1PlanLateralScan:

    def test_plan_playbook_contains_lateral_scan_phase(self):
        """Plan playbook must contain Lateral Scan step after Logic Trace."""
        from pactkit.prompts.commands import COMMANDS_CONTENT
        plan = COMMANDS_CONTENT["project-plan.md"]
        assert "Lateral Scan" in plan

    def test_plan_playbook_lists_lsp_visualize_grep_strategy(self):
        """Lateral Scan must list the tiered strategy: LSP > visualize > grep."""
        from pactkit.prompts.commands import COMMANDS_CONTENT
        plan = COMMANDS_CONTENT["project-plan.md"]
        assert "LSP" in plan
        assert "visualize" in plan
        assert "grep" in plan

    def test_plan_playbook_lateral_scan_after_logic_trace(self):
        """Lateral Scan must appear after Logic Trace in the playbook."""
        from pactkit.prompts.commands import COMMANDS_CONTENT
        plan = COMMANDS_CONTENT["project-plan.md"]
        trace_pos = plan.find("Logic Trace")
        lateral_pos = plan.find("Lateral Scan")
        solution_pos = plan.find("Solution Design Protocol")
        assert trace_pos < lateral_pos < solution_pos


class TestAC2SolutionDesignInternalPatterns:

    def test_solution_design_contains_internal_patterns_step(self):
        """Solution Design Protocol must contain Step 3.5 Internal Patterns."""
        from pactkit.prompts.rules import RULES_MODULES
        solution = RULES_MODULES["solution"]
        assert "Internal Patterns" in solution or "Project Internal" in solution

    def test_solution_design_delta_table_has_multiple_row(self):
        """Delta Assessment table must include a row for ≥ 3 independent implementations."""
        from pactkit.prompts.rules import RULES_MODULES
        solution = RULES_MODULES["solution"]
        assert "3 independent" in solution or "≥ 3" in solution

    def test_solution_design_mentions_lsp_and_visualize(self):
        """Step 3.5 must reference LSP and visualize as scan methods."""
        from pactkit.prompts.rules import RULES_MODULES
        solution = RULES_MODULES["solution"]
        assert "LSP" in solution or "incomingCalls" in solution
        assert "visualize" in solution or "fan-in" in solution or "reverse" in solution


class TestAC3ArchitecturePrinciplesGeneric:

    def test_dry_has_generic_example(self):
        """DRY section must include a generic anti-pattern example."""
        from pactkit.prompts.rules import RULES_MODULES
        arch = RULES_MODULES["architecture"]
        dry_start = arch.find("Single Source of Truth")
        ocp_start = arch.find("Open-Closed Principle")
        dry_section = arch[dry_start:ocp_start]
        assert "Anti-pattern" in dry_section or "anti-pattern" in dry_section or "example" in dry_section.lower()

    def test_ocp_has_if_elif_antipattern(self):
        """OCP section must mention if/elif chain as anti-pattern."""
        from pactkit.prompts.rules import RULES_MODULES
        arch = RULES_MODULES["architecture"]
        ocp_start = arch.find("Open-Closed Principle")
        dip_start = arch.find("Dependency Inversion")
        ocp_section = arch[ocp_start:dip_start]
        assert "if/elif" in ocp_section or "strategy" in ocp_section.lower() or "registry" in ocp_section.lower()


class TestAC4HooksRemoved:

    def test_no_valid_hook_templates_constant(self):
        """VALID_HOOK_TEMPLATES must no longer exist in config."""
        from pactkit import config
        assert not hasattr(config, "VALID_HOOK_TEMPLATES")

    def test_default_config_has_no_hooks(self):
        """get_default_config must not include a hooks section."""
        from pactkit.config import get_default_config
        cfg = get_default_config()
        assert "hooks" not in cfg

    def test_deploy_no_hooks_dir(self, tmp_path):
        """deploy() must not create a hooks directory."""
        from pactkit.generators.deployer import deploy
        deploy(target=str(tmp_path / ".claude"))
        hooks_dir = tmp_path / ".claude" / "hooks"
        if hooks_dir.exists():
            scripts = list(hooks_dir.glob("*"))
            assert len(scripts) == 0

    def test_deploy_with_legacy_hooks_yaml_no_error(self, tmp_path):
        """deploy() must not crash when config contains a legacy hooks section."""
        from pactkit.generators.deployer import deploy
        from pactkit.config import get_default_config
        cfg = get_default_config()
        cfg["hooks"] = {"pre_commit_lint": True}
        deploy(config=cfg, target=str(tmp_path / ".claude"))

    def test_generate_default_yaml_no_hooks(self):
        """generate_default_yaml must not contain a hooks section."""
        from pactkit.config import generate_default_yaml
        yaml_text = generate_default_yaml()
        assert "hooks:" not in yaml_text
        assert "pre_commit_lint" not in yaml_text

    def test_validate_config_ignores_hooks(self):
        """validate_config must not warn about hooks (section is simply ignored)."""
        from pactkit.config import get_default_config, validate_config
        cfg = get_default_config()
        cfg["hooks"] = {"unknown_hook": True}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            validate_config(cfg)
        hook_warnings = [x for x in w if "hook" in str(x.message).lower()]
        assert len(hook_warnings) == 0


class TestAC5SpecLinterW010:

    def _make_spec(self, has_tech_design=False, has_lateral_scan=False):
        """Build a minimal spec string for testing."""
        lines = [
            "# STORY-TEST-001: Test",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| ID | STORY-TEST-001 |",
            "| Status | Draft |",
            "| Priority | P1 |",
            "| Release | 1.0.0 |",
            "",
            "## Background",
            "",
            "Some background.",
            "",
            "## Requirements",
            "",
            "### R1: Test Requirement (MUST)",
            "",
            "Description.",
            "",
            "## Acceptance Criteria",
            "",
            "### AC1: Test (R1)",
            "",
            "- **Given** precondition",
            "- **When** action",
            "- **Then** result",
            "",
            "## Target Call Chain",
            "",
            "```",
            "foo() -> bar()",
            "```",
            "",
            "## Implementation Steps",
            "",
            "| Step | File | Action | Dependencies | Risk |",
            "|------|------|--------|-------------|------|",
            "| 1 | `src/foo.py` | Update | None | Low |",
            "",
            "## Security Scope",
            "",
            "| Check | Applicable | Reason |",
            "|-------|------------|--------|",
            "| SEC-1 | N/A | test |",
            "",
            "## Out of Scope",
            "",
            "- Nothing",
        ]
        if has_tech_design:
            lines.extend([
                "",
                "## Technical Design",
                "",
                "Some design notes.",
            ])
            if has_lateral_scan:
                lines.extend([
                    "",
                    "### Lateral Scan Results",
                    "",
                    "No duplicates found.",
                ])
        return "\n".join(lines)

    def test_w010_fires_when_tech_design_lacks_lateral_scan(self, tmp_path):
        """W010 should fire when Technical Design exists but Lateral Scan Results is missing."""
        spec_file = tmp_path / "STORY-TEST-001.md"
        spec_file.write_text(self._make_spec(has_tech_design=True, has_lateral_scan=False))
        from pactkit.skills.spec_linter import validate_spec
        result = validate_spec(str(spec_file))
        w010_warnings = [w for w in result.warnings if w.rule_id == "W010"]
        assert len(w010_warnings) == 1

    def test_w010_not_fired_when_lateral_scan_present(self, tmp_path):
        """W010 should not fire when Lateral Scan Results exists."""
        spec_file = tmp_path / "STORY-TEST-001.md"
        spec_file.write_text(self._make_spec(has_tech_design=True, has_lateral_scan=True))
        from pactkit.skills.spec_linter import validate_spec
        result = validate_spec(str(spec_file))
        w010_warnings = [w for w in result.warnings if w.rule_id == "W010"]
        assert len(w010_warnings) == 0

    def test_w010_not_fired_when_no_tech_design(self, tmp_path):
        """W010 should not fire when there is no Technical Design section at all."""
        spec_file = tmp_path / "STORY-TEST-001.md"
        spec_file.write_text(self._make_spec(has_tech_design=False))
        from pactkit.skills.spec_linter import validate_spec
        result = validate_spec(str(spec_file))
        w010_warnings = [w for w in result.warnings if w.rule_id == "W010"]
        assert len(w010_warnings) == 0

    def test_w010_is_warning_not_error(self, tmp_path):
        """W010 must be a WARNING, not an ERROR (non-blocking)."""
        spec_file = tmp_path / "STORY-TEST-001.md"
        spec_file.write_text(self._make_spec(has_tech_design=True, has_lateral_scan=False))
        from pactkit.skills.spec_linter import validate_spec
        result = validate_spec(str(spec_file))
        assert result.passed, "W010 should not cause spec lint to fail"
