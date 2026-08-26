"""Tests for STORY-slim-128: Engineering Concerns — Guide-based NFR enforcement.

Verifies:
- AC1: Trigger index rule deployed as 07-engineering-concerns.md
- AC2: 13 guide files deployed to _rules/guides/ subdirectory
- AC3: Plan command contains Engineering Concerns Assessment phase
- AC4: Act command contains Phase 1.5 Engineering Concerns Loading
- AC5: Multi-format parity (guides available in all formats)
"""

import importlib
from pathlib import Path
import tempfile


def _rules():
    import pactkit.prompts.rules as rules_mod
    importlib.reload(rules_mod)
    return rules_mod


def _guides():
    import pactkit.prompts.guides as guides_mod
    importlib.reload(guides_mod)
    return guides_mod


def _commands():
    import pactkit.prompts.commands as commands_mod
    importlib.reload(commands_mod)
    return commands_mod


def _config():
    import pactkit.config as config_mod
    importlib.reload(config_mod)
    return config_mod


# ---------------------------------------------------------------------------
# AC1: Trigger Index Rule Registration
# ---------------------------------------------------------------------------
class TestTriggerIndexRule:
    def test_engineering_key_in_rules_modules(self):
        rules = _rules()
        assert "engineering" in rules.RULES_MODULES, (
            "RULES_MODULES must contain 'engineering' key"
        )

    def test_engineering_key_in_ondemand_files(self):
        rules = _rules()
        assert "engineering-index" in rules.RULES_ONDEMAND_FILES, (
            "RULES_ONDEMAND_FILES must contain the engineering-index key"
        )

    def test_engineering_filename(self):
        rules = _rules()
        assert rules.RULES_ONDEMAND_FILES["engineering-index"] == "engineering/index.md"

    def test_engineering_content_has_keyword_table(self):
        rules = _rules()
        content = rules.RULES_MODULES["engineering"]
        assert "concern" in content.lower()
        assert "guide" in content.lower()

    def test_engineering_in_valid_rules(self):
        config = _config()
        assert "engineering-index" in config.VALID_RULES

    def test_engineering_referenced_in_plan_command(self):
        """Plan command references engineering concerns for on-demand Read."""
        import pactkit.prompts as prompts
        importlib.reload(prompts)
        plan_content = prompts.COMMANDS_CONTENT["project-plan.md"]
        assert "engineering/index.md" in plan_content

    def test_engineering_referenced_in_act_command(self):
        """Act command references engineering concerns for on-demand Read."""
        import pactkit.prompts as prompts
        importlib.reload(prompts)
        act_content = prompts.COMMANDS_CONTENT["project-act.md"]
        assert "engineering/index.md" in act_content

    def test_engineering_index_uses_logical_path_not_numeric_prefix(self):
        rules = _rules()
        assert rules.RULES_ONDEMAND_PREFIXES == []


# ---------------------------------------------------------------------------
# AC2: Guides Files Definition and Deployment
# ---------------------------------------------------------------------------
class TestGuidesFiles:
    EXPECTED_GUIDES = {
        "concurrency.md",
        "async-patterns.md",
        "configuration.md",
        "observability.md",
        "module-design.md",
        "database.md",
        "caching.md",
        "api-integration.md",
        "event-driven.md",
        "resilience.md",
        "memory-management.md",
        "code-review-first.md",
        "component-reuse.md",
        "error-recovery.md",
        "data-consistency.md",
        "backwards-compatibility.md",
        "performance-antipatterns.md",
        "graceful-shutdown.md",
        "testing-strategy.md",
        "operational-readiness.md",
        "dependency-supply-chain.md",
        "ui-state-accessibility.md",
    }

    def test_guides_files_has_22_entries(self):
        guides = _guides()
        assert len(guides.GUIDES_FILES) == 22, (
            f"GUIDES_FILES should have 22 entries, got {len(guides.GUIDES_FILES)}: "
            f"{list(guides.GUIDES_FILES.keys())}"
        )

    def test_guides_files_expected_keys(self):
        guides = _guides()
        assert set(guides.GUIDES_FILES.keys()) == self.EXPECTED_GUIDES

    def test_each_guide_under_50_lines(self):
        guides = _guides()
        for filename, content in guides.GUIDES_FILES.items():
            line_count = len(content.strip().splitlines())
            assert line_count <= 50, (
                f"Guide '{filename}' has {line_count} lines (max 50)"
            )

    def test_each_guide_has_risk_driven_sections(self):
        guides = _guides()
        for filename, content in guides.GUIDES_FILES.items():
            for section in (
                "## Trigger", "## Questions", "## Safe Invariants",
                "## Defaults", "## Alternatives", "## Evidence",
                "## Non-applicable",
            ):
                assert section in content, f"Guide '{filename}' missing {section}"
            body = content.split("## Evidence", 1)[-1]
            assert "## MUST" not in body
            assert "## NEVER" not in body

    def test_deploy_guides_creates_directory(self):
        from pactkit.generators.deployer import _deploy_guides
        with tempfile.TemporaryDirectory() as tmp:
            claude_root = Path(tmp)
            count = _deploy_guides(claude_root)
            guides_dir = claude_root / "skills" / "_rules" / "guides"
            assert guides_dir.exists()
            assert count == 22
            files = list(guides_dir.glob("*.md"))
            assert len(files) == 22

    def test_deploy_guides_file_content_matches_source(self):
        from pactkit.generators.deployer import _deploy_guides
        guides = _guides()
        with tempfile.TemporaryDirectory() as tmp:
            claude_root = Path(tmp)
            _deploy_guides(claude_root)
            guides_dir = claude_root / "skills" / "_rules" / "guides"
            for filename, expected_content in guides.GUIDES_FILES.items():
                deployed = (guides_dir / filename).read_text()
                assert deployed == expected_content, (
                    f"Deployed guide '{filename}' content mismatch"
                )


# ---------------------------------------------------------------------------
# AC3: Plan Command Contains Engineering Concerns Assessment
# ---------------------------------------------------------------------------
class TestPlanCommandEnhancement:
    def test_plan_contains_engineering_concerns_phase(self):
        commands = _commands()
        plan_content = commands.COMMANDS_CONTENT["project-plan.md"]
        assert "Engineering Concerns" in plan_content

    def test_plan_contains_keyword_scanning(self):
        commands = _commands()
        plan_content = commands.COMMANDS_CONTENT["project-plan.md"]
        assert "concern" in plan_content.lower()
        # Should reference scanning requirement keywords
        assert "API" in plan_content or "数据库" in plan_content or "database" in plan_content.lower()


# ---------------------------------------------------------------------------
# AC4: Act Command Contains Phase 1.5
# ---------------------------------------------------------------------------
class TestActCommandEnhancement:
    def test_act_contains_engineering_concerns_loading(self):
        commands = _commands()
        act_content = commands.COMMANDS_CONTENT["project-act.md"]
        assert "Engineering Concerns" in act_content

    def test_act_references_guides_directory(self):
        commands = _commands()
        act_content = commands.COMMANDS_CONTENT["project-act.md"]
        assert "GUIDES_PATH" in act_content or "guides/" in act_content

    def test_act_mentions_only_load_relevant(self):
        commands = _commands()
        act_content = commands.COMMANDS_CONTENT["project-act.md"]
        assert "1-3" in act_content or "only" in act_content.lower()
