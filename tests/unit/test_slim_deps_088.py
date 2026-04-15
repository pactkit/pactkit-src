"""STORY-slim-088: Slim dependencies and robust CLI fallback.

Tests for:
- R1/R2: pyproject.toml dependency structure (core vs optional)
- R3: spec-lint fallback in playbooks
- R4: add_story call signature in Plan playbook
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"


# ---------------------------------------------------------------------------
# R1/R2: Dependency structure
# ---------------------------------------------------------------------------

class TestDependencyStructure:
    """AC1/AC2/AC3: Core deps are slim; adapters and tree-sitter are optional."""

    @pytest.fixture(autouse=True)
    def _load_pyproject(self):
        self.text = PYPROJECT.read_text()

    def _core_deps_block(self) -> str:
        """Extract the [project].dependencies list text."""
        m = re.search(
            r'^\[project\]\s*$.*?^dependencies\s*=\s*\[(.*?)\]',
            self.text,
            re.MULTILINE | re.DOTALL,
        )
        assert m, "Could not find [project].dependencies in pyproject.toml"
        return m.group(1)

    def _optional_deps_block(self) -> str:
        """Extract the [project.optional-dependencies] section text."""
        m = re.search(
            r'^\[project\.optional-dependencies\]\s*$(.+?)(?=^\[|\Z)',
            self.text,
            re.MULTILINE | re.DOTALL,
        )
        assert m, "Could not find [project.optional-dependencies] in pyproject.toml"
        return m.group(1)

    # AC1: no adapter packages in core
    def test_no_adapter_in_core_deps(self):
        core = self._core_deps_block()
        assert "pactkit-opencode" not in core, "pactkit-opencode must not be in core dependencies"
        assert "pactkit-codex" not in core, "pactkit-codex must not be in core dependencies"

    # AC2: no tree-sitter in core
    def test_no_tree_sitter_in_core_deps(self):
        core = self._core_deps_block()
        assert "tree-sitter" not in core, "tree-sitter must not be in core dependencies"

    # AC1/AC2: core only has pyyaml
    def test_core_deps_only_pyyaml(self):
        core = self._core_deps_block()
        deps = [line.strip().strip('"').strip("'").strip(",") for line in core.splitlines() if line.strip() and not line.strip().startswith("#")]
        dep_names = [re.split(r'[><=!]', d)[0].strip() for d in deps]
        assert dep_names == ["pyyaml"], f"Core dependencies should only be ['pyyaml'], got {dep_names}"

    # AC3: optional-dependencies has the right extras
    def test_optional_extras_exist(self):
        opt = self._optional_deps_block()
        assert "opencode" in opt, "Missing 'opencode' extra"
        assert "codex" in opt, "Missing 'codex' extra"
        assert "visualize" in opt, "Missing 'visualize' extra"
        assert "all" in opt, "Missing 'all' extra"

    def test_opencode_extra_has_adapter(self):
        opt = self._optional_deps_block()
        assert "pactkit-opencode" in opt

    def test_codex_extra_has_adapter(self):
        opt = self._optional_deps_block()
        assert "pactkit-codex" in opt

    def test_visualize_extra_has_tree_sitter(self):
        opt = self._optional_deps_block()
        assert "tree-sitter" in opt


# ---------------------------------------------------------------------------
# R3: Spec-lint fallback
# ---------------------------------------------------------------------------

class TestSpecLintFallback:
    """AC4: Playbooks must have python3 -m pactkit fallback for spec-lint."""

    @pytest.fixture(autouse=True)
    def _load_prompts(self):
        from pactkit.prompts import COMMANDS_CONTENT
        from pactkit.prompts.workflows import DESIGN_PROMPT
        self.plan_prompt = COMMANDS_CONTENT["project-plan.md"]
        self.act_prompt = COMMANDS_CONTENT["project-act.md"]
        self.check_prompt = COMMANDS_CONTENT["project-check.md"]
        self.design_prompt = DESIGN_PROMPT

    def test_plan_spec_lint_has_fallback(self):
        assert "python3 -m pactkit spec-lint" in self.plan_prompt, \
            "Plan playbook must have python3 -m pactkit spec-lint fallback"

    def test_act_spec_lint_has_fallback(self):
        assert "python3 -m pactkit spec-lint" in self.act_prompt, \
            "Act playbook must have python3 -m pactkit spec-lint fallback"

    def test_check_spec_lint_has_fallback(self):
        assert "python3 -m pactkit spec-lint" in self.check_prompt, \
            "Check playbook must have python3 -m pactkit spec-lint fallback"

    def test_design_spec_lint_has_fallback(self):
        assert "python3 -m pactkit spec-lint" in self.design_prompt, \
            "Design playbook must have python3 -m pactkit spec-lint fallback"


# ---------------------------------------------------------------------------
# R4: add_story call signature
# ---------------------------------------------------------------------------

class TestAddStorySignature:
    """AC5: Plan playbook Phase 3.3 must show full add_story signature."""

    def test_plan_add_story_has_tasks_arg(self):
        from pactkit.prompts import COMMANDS_CONTENT
        plan = COMMANDS_CONTENT["project-plan.md"]
        # The playbook should show the 3-argument form: ID, title, tasks
        # Match pattern like: add_story "{STORY_ID}" "{title}" "{tasks}"
        # or: add_story "STORY-{NNN}" "{title}" "{task list}"
        assert re.search(r'add_story\s+.*".*".*".*".*"', plan), \
            "Plan playbook Phase 3.3 must show add_story with ID, title, AND tasks arguments"
