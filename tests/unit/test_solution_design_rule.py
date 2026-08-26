"""Tests for STORY-slim-101: Solution Design Protocol Rule."""


def _prompts():
    import importlib

    import pactkit.prompts as p
    importlib.reload(p)
    return p


def _config():
    import importlib

    import pactkit.config as c
    importlib.reload(c)
    return c


class TestSolutionDesignRuleRegistered:
    """AC1: Rule File Exists — verify rule is registered in all required places."""

    def test_rules_modules_has_solution(self):
        """Solution design module is registered in RULES_MODULES."""
        p = _prompts()
        assert "solution" in p.RULES_MODULES

    def test_rules_files_has_solution(self):
        """Solution design file mapping exists."""
        p = _prompts()
        assert "capability-design" in p.RULES_FILES
        assert p.RULES_FILES["capability-design"] == "design/capability-design.md"

    def test_legacy_solution_identifier_normalizes_to_capability_design(self):
        p = _prompts()
        from pactkit.prompts.rules import normalize_rule_id

        assert normalize_rule_id("solution") == "capability-design"
        assert normalize_rule_id("06-solution-design") == "capability-design"

    def test_valid_rules_has_solution(self):
        """The current logical ID is accepted by config validation."""
        c = _config()
        assert "capability-design" in c.VALID_RULES

    def test_claude_md_template_imports_solution(self):
        """Capability design is command scoped, not globally loaded."""
        p = _prompts()
        assert "design/capability-design.md" in p.RULES_ONDEMAND_FILES.values()


class TestSolutionDesignContent:
    """AC2-AC5: Protocol content requirements."""

    def test_has_framework_query_section(self):
        """R2: Framework capability query path defined."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        assert "Context7" in solution
        assert "WebFetch" in solution or "training data" in solution.lower()

    def test_has_project_discovery_section(self):
        """R3: Project capability discovery methods defined."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        text = solution.lower()
        assert "import" in text or "usage" in text
        assert "get_" in solution or "build_" in solution or "create_" in solution
        assert "abstraction" in text or "wrapper" in text or "factory" in text

    def test_has_delta_assessment(self):
        """R4: Delta assessment matrix defined."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        text = solution.lower()
        assert "delta" in text or "assessment" in text or "matrix" in text

    def test_has_decision_constraints(self):
        """R5: Decision constraints defined."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        assert "MUST NOT" in solution or "bypass" in solution.lower()

    def test_has_output_format(self):
        """R6: Output format defined."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        assert "Technical Design" in solution or "output" in solution.lower()

    def test_has_implementation_constraints(self):
        """Implementation constraints for new code defined."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        assert "Implementation Constraints" in solution
        assert "Magic Values" in solution or "hardcode" in solution.lower()
        assert "Open-Closed" in solution
        assert "Single Responsibility" in solution


class TestSolutionDesignStackAgnostic:
    """AC7: Multi-stack support."""

    def test_supports_python_deps(self):
        """R7: Python dependency files mentioned."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        assert "pyproject.toml" in solution or "requirements.txt" in solution

    def test_supports_node_deps(self):
        """R7: Node dependency files mentioned."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        assert "package.json" in solution

    def test_supports_go_deps(self):
        """R7: Go dependency files mentioned."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        assert "go.mod" in solution

    def test_supports_java_deps(self):
        """R7: Java dependency files mentioned."""
        p = _prompts()
        solution = p.RULES_MODULES["solution"]
        assert "pom.xml" in solution or "build.gradle" in solution


class TestPlaybookIntegration:
    """AC8: Playbook references protocol via on-demand Read."""

    def test_plan_command_references_solution_design(self):
        """R8: project-plan references solution design rule for on-demand Read."""
        p = _prompts()
        plan_content = p.COMMANDS_CONTENT["project-plan.md"]
        assert "design/capability-design.md" in plan_content

    def test_act_command_references_solution_design(self):
        """R8: project-act references solution design rule for on-demand Read."""
        p = _prompts()
        act_content = p.COMMANDS_CONTENT["project-act.md"]
        assert "design/capability-design.md" in act_content
