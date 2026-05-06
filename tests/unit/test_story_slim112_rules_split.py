"""Tests for STORY-slim-112: Rules Architecture Refactor — Global vs On-Demand.

Verifies the split of PactKit rules into:
- Global rules (~/.claude/rules/) — always loaded, 6 files
- On-demand rules (~/.claude/skills/_rules/) — loaded via @import in skill commands, 6 files

Acceptance Criteria:
- AC1: Global rules contain only the 6 designated files
- AC2: On-demand rules contain only the 6 designated files
- AC3: No overlap between global and on-demand sets
- AC4: 05-principles.md content contains required principles
- AC5: Deployer writes global to rules/ and on-demand to skills/_rules/
- AC6: COMMAND_RULES_MAP values only reference valid keys
- AC7: Backward compat — user files (10-*, 13-*, slim-01-*) not affected
"""

import pytest
from pathlib import Path


def _rules():
    import importlib
    import pactkit.prompts.rules as rules_mod
    importlib.reload(rules_mod)
    return rules_mod


# ---------------------------------------------------------------------------
# AC1: RULES_CORE_FILES structure
# ---------------------------------------------------------------------------
class TestRulesCoreFiles:
    def test_core_files_has_6_entries(self):
        rules = _rules()
        assert len(rules.RULES_CORE_FILES) == 6, (
            f"RULES_CORE_FILES should have 6 entries, got {len(rules.RULES_CORE_FILES)}: "
            f"{list(rules.RULES_CORE_FILES.keys())}"
        )

    def test_core_files_contains_required_keys(self):
        rules = _rules()
        required = {"core", "hierarchy", "atlas", "routing", "principles", "nudge"}
        assert required == set(rules.RULES_CORE_FILES.keys()), (
            f"RULES_CORE_FILES keys mismatch. Expected {required}, got {set(rules.RULES_CORE_FILES.keys())}"
        )

    def test_core_files_filenames(self):
        rules = _rules()
        expected = {
            "core": "01-core-protocol.md",
            "hierarchy": "02-hierarchy-of-truth.md",
            "atlas": "03-file-atlas.md",
            "routing": "04-routing-table.md",
            "principles": "05-principles.md",
            "nudge": "11-pdca-nudge.md",
        }
        assert rules.RULES_CORE_FILES == expected, (
            f"RULES_CORE_FILES filenames mismatch: {rules.RULES_CORE_FILES}"
        )

    def test_core_files_keys_subset_of_rules_modules(self):
        rules = _rules()
        for key in rules.RULES_CORE_FILES:
            assert key in rules.RULES_MODULES, (
                f"RULES_CORE_FILES key '{key}' not found in RULES_MODULES"
            )


# ---------------------------------------------------------------------------
# AC2: RULES_ONDEMAND_FILES structure
# ---------------------------------------------------------------------------
class TestRulesOndemandFiles:
    def test_ondemand_files_has_6_entries(self):
        rules = _rules()
        assert len(rules.RULES_ONDEMAND_FILES) == 6, (
            f"RULES_ONDEMAND_FILES should have 6 entries, got {len(rules.RULES_ONDEMAND_FILES)}: "
            f"{list(rules.RULES_ONDEMAND_FILES.keys())}"
        )

    def test_ondemand_files_contains_required_keys(self):
        rules = _rules()
        required = {"workflow", "mcp", "shared", "architecture", "sectional", "solution"}
        assert required == set(rules.RULES_ONDEMAND_FILES.keys()), (
            f"RULES_ONDEMAND_FILES keys mismatch. Expected {required}, "
            f"got {set(rules.RULES_ONDEMAND_FILES.keys())}"
        )

    def test_ondemand_files_filenames(self):
        rules = _rules()
        expected = {
            "workflow": "05-workflow-conventions.md",
            "mcp": "06-mcp-integration.md",
            "shared": "07-shared-protocols.md",
            "architecture": "08-architecture-principles.md",
            "sectional": "09-sectional-write.md",
            "solution": "12-solution-design.md",
        }
        assert rules.RULES_ONDEMAND_FILES == expected, (
            f"RULES_ONDEMAND_FILES filenames mismatch: {rules.RULES_ONDEMAND_FILES}"
        )

    def test_ondemand_files_keys_subset_of_rules_modules(self):
        rules = _rules()
        for key in rules.RULES_ONDEMAND_FILES:
            assert key in rules.RULES_MODULES, (
                f"RULES_ONDEMAND_FILES key '{key}' not found in RULES_MODULES"
            )


# ---------------------------------------------------------------------------
# AC3: No overlap between global and on-demand
# ---------------------------------------------------------------------------
class TestNoOverlap:
    def test_no_key_overlap(self):
        rules = _rules()
        core_keys = set(rules.RULES_CORE_FILES.keys())
        ondemand_keys = set(rules.RULES_ONDEMAND_FILES.keys())
        overlap = core_keys & ondemand_keys
        assert not overlap, (
            f"Keys appear in both RULES_CORE_FILES and RULES_ONDEMAND_FILES: {overlap}"
        )

    def test_no_filename_overlap(self):
        rules = _rules()
        core_files = set(rules.RULES_CORE_FILES.values())
        ondemand_files = set(rules.RULES_ONDEMAND_FILES.values())
        overlap = core_files & ondemand_files
        assert not overlap, (
            f"Filenames appear in both RULES_CORE_FILES and RULES_ONDEMAND_FILES: {overlap}"
        )

    def test_rules_files_is_union(self):
        """RULES_FILES should be the union of core + ondemand."""
        rules = _rules()
        combined = {**rules.RULES_CORE_FILES, **rules.RULES_ONDEMAND_FILES}
        assert rules.RULES_FILES == combined, (
            f"RULES_FILES should equal RULES_CORE_FILES | RULES_ONDEMAND_FILES"
        )


# ---------------------------------------------------------------------------
# AC4: 05-principles.md content validation
# ---------------------------------------------------------------------------
class TestPrinciplesContent:
    def test_principles_key_in_rules_modules(self):
        rules = _rules()
        assert "principles" in rules.RULES_MODULES, (
            "RULES_MODULES must contain 'principles' key"
        )

    def test_principles_contains_no_magic_values(self):
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        assert "No Magic Values" in content or "magic value" in content.lower(), (
            "05-principles.md must contain 'No Magic Values' principle"
        )

    def test_principles_contains_dry_or_single_source(self):
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        assert "DRY" in content or "Single Source of Truth" in content, (
            "05-principles.md must contain DRY / Single Source of Truth principle"
        )

    def test_principles_contains_code_enforces(self):
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        assert "Code Enforces" in content or "LLM" in content, (
            "05-principles.md must contain 'Code Enforces, Prompt Instructs' principle"
        )

    def test_principles_contains_dependency_direction(self):
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        assert "Dependency Direction" in content or "import" in content.lower(), (
            "05-principles.md must contain Dependency Direction principle"
        )

    def test_principles_reasonable_length(self):
        """05-principles.md should be condensed (~60 lines), not a full copy of 08/12."""
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        line_count = content.count("\n")
        assert line_count <= 100, (
            f"05-principles.md should be condensed (<=100 lines), got {line_count} lines"
        )
        assert line_count >= 20, (
            f"05-principles.md seems too short ({line_count} lines) — likely incomplete"
        )


# ---------------------------------------------------------------------------
# AC5: Deployer writes to two directories
# ---------------------------------------------------------------------------
class TestDeployerTwoDirectories:
    def test_deploy_rules_writes_global_to_rules_dir(self, tmp_path):
        """Global rules (01-, 02-, 03-, 04-, 05-principles, 11-) go to rules/."""
        from pactkit.generators.deployer import _deploy_rules
        from pactkit.config import VALID_RULES
        from pactkit.profiles import get_profile

        claude_root = tmp_path / "claude"
        claude_root.mkdir()
        profile = get_profile("classic")

        _deploy_rules(claude_root, list(VALID_RULES), profile=profile)

        rules_dir = claude_root / "rules"
        deployed_files = {f.name for f in rules_dir.glob("*.md")}

        # Global files should be in rules/
        from pactkit.prompts.rules import RULES_CORE_FILES
        for filename in RULES_CORE_FILES.values():
            assert filename in deployed_files, (
                f"Global rule '{filename}' not found in rules/ dir. Found: {deployed_files}"
            )

    def test_deploy_rules_writes_ondemand_to_skills_rules_dir(self, tmp_path):
        """On-demand rules go to skills/_rules/."""
        from pactkit.generators.deployer import _deploy_rules
        from pactkit.config import VALID_RULES
        from pactkit.profiles import get_profile

        claude_root = tmp_path / "claude"
        claude_root.mkdir()
        profile = get_profile("classic")

        _deploy_rules(claude_root, list(VALID_RULES), profile=profile)

        ondemand_dir = claude_root / "skills" / "_rules"
        assert ondemand_dir.exists(), (
            f"On-demand rules directory skills/_rules/ should be created"
        )

        deployed_files = {f.name for f in ondemand_dir.glob("*.md")}

        # On-demand files should be in skills/_rules/
        from pactkit.prompts.rules import RULES_ONDEMAND_FILES
        for filename in RULES_ONDEMAND_FILES.values():
            assert filename in deployed_files, (
                f"On-demand rule '{filename}' not found in skills/_rules/. Found: {deployed_files}"
            )

    def test_deploy_rules_global_dir_has_only_global_files(self, tmp_path):
        """rules/ should NOT contain on-demand rule files."""
        from pactkit.generators.deployer import _deploy_rules
        from pactkit.config import VALID_RULES
        from pactkit.profiles import get_profile
        from pactkit.prompts.rules import RULES_ONDEMAND_FILES

        claude_root = tmp_path / "claude"
        claude_root.mkdir()
        profile = get_profile("classic")

        _deploy_rules(claude_root, list(VALID_RULES), profile=profile)

        rules_dir = claude_root / "rules"
        deployed_files = {f.name for f in rules_dir.glob("*.md")}
        ondemand_filenames = set(RULES_ONDEMAND_FILES.values())

        contamination = deployed_files & ondemand_filenames
        assert not contamination, (
            f"On-demand rule files found in rules/ dir (should be in skills/_rules/): "
            f"{contamination}"
        )

    def test_deploy_rules_returns_total_count(self, tmp_path):
        """_deploy_rules should return the count of all deployed rules (global + ondemand)."""
        from pactkit.generators.deployer import _deploy_rules
        from pactkit.config import VALID_RULES
        from pactkit.profiles import get_profile

        claude_root = tmp_path / "claude"
        claude_root.mkdir()
        profile = get_profile("classic")

        count = _deploy_rules(claude_root, list(VALID_RULES), profile=profile)
        assert count == len(VALID_RULES), (
            f"_deploy_rules should return count of all deployed rules. "
            f"Expected {len(VALID_RULES)}, got {count}"
        )


# ---------------------------------------------------------------------------
# AC6: COMMAND_RULES_MAP values reference valid keys
# ---------------------------------------------------------------------------
class TestCommandRulesMap:
    def test_all_command_rules_map_values_are_valid_keys(self):
        rules = _rules()
        all_valid_keys = set(rules.RULES_MODULES.keys()) | {"credential"}
        for cmd, rule_keys in rules.COMMAND_RULES_MAP.items():
            for key in rule_keys:
                assert key in all_valid_keys, (
                    f"COMMAND_RULES_MAP['{cmd}'] references unknown key '{key}'. "
                    f"Valid keys: {sorted(all_valid_keys)}"
                )


# ---------------------------------------------------------------------------
# Constants validation
# ---------------------------------------------------------------------------
class TestRulesPrefixConstants:
    def test_rules_global_prefixes_defined(self):
        rules = _rules()
        assert hasattr(rules, "RULES_GLOBAL_PREFIXES"), (
            "rules.py must define RULES_GLOBAL_PREFIXES"
        )
        assert isinstance(rules.RULES_GLOBAL_PREFIXES, list)

    def test_rules_ondemand_prefixes_defined(self):
        rules = _rules()
        assert hasattr(rules, "RULES_ONDEMAND_PREFIXES"), (
            "rules.py must define RULES_ONDEMAND_PREFIXES"
        )
        assert isinstance(rules.RULES_ONDEMAND_PREFIXES, list)

    def test_rules_ondemand_dir_defined(self):
        rules = _rules()
        assert hasattr(rules, "RULES_ONDEMAND_DIR"), (
            "rules.py must define RULES_ONDEMAND_DIR"
        )
        assert rules.RULES_ONDEMAND_DIR == "_rules"

    def test_global_prefixes_match_core_files(self):
        """Each global rule file should have its prefix in RULES_GLOBAL_PREFIXES."""
        rules = _rules()
        for filename in rules.RULES_CORE_FILES.values():
            # e.g. "01-core-protocol.md" -> prefix "01-"
            prefix = filename[:3]
            assert prefix in rules.RULES_GLOBAL_PREFIXES, (
                f"Core file '{filename}' prefix '{prefix}' not in RULES_GLOBAL_PREFIXES: "
                f"{rules.RULES_GLOBAL_PREFIXES}"
            )

    def test_ondemand_prefixes_match_ondemand_files(self):
        """Each on-demand rule file should have its prefix in RULES_ONDEMAND_PREFIXES.
        Note: '05-' appears in both sets since 05-principles is global and
        05-workflow-conventions is on-demand.
        """
        rules = _rules()
        for filename in rules.RULES_ONDEMAND_FILES.values():
            prefix = filename[:3]
            assert prefix in rules.RULES_ONDEMAND_PREFIXES, (
                f"On-demand file '{filename}' prefix '{prefix}' not in RULES_ONDEMAND_PREFIXES: "
                f"{rules.RULES_ONDEMAND_PREFIXES}"
            )


# ---------------------------------------------------------------------------
# AC7: config.py VALID_RULES updated
# ---------------------------------------------------------------------------
class TestValidRulesUpdated:
    def test_valid_rules_contains_principles(self):
        from pactkit.config import VALID_RULES
        assert "05-principles" in VALID_RULES, (
            "VALID_RULES must contain '05-principles'"
        )

    def test_valid_rules_total_count(self):
        """VALID_RULES should have 12 entries (6 global + 6 on-demand)."""
        from pactkit.config import VALID_RULES
        assert len(VALID_RULES) == 12, (
            f"VALID_RULES should have 12 entries, got {len(VALID_RULES)}: {sorted(VALID_RULES)}"
        )

    def test_valid_rules_contains_all_keys(self):
        """VALID_RULES stems should match RULES_FILES keys mapped to filenames."""
        from pactkit.config import VALID_RULES
        rules = _rules()
        expected_stems = {filename.removesuffix(".md") for filename in rules.RULES_FILES.values()}
        assert VALID_RULES == frozenset(expected_stems), (
            f"VALID_RULES mismatch. Expected {sorted(expected_stems)}, got {sorted(VALID_RULES)}"
        )
