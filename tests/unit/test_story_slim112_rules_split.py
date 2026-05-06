"""Tests for STORY-slim-112 (updated): Rules Architecture Refactor — Global vs On-Demand.

Verifies the merged split of PactKit rules into:
- Global rules (~/.claude/rules/) — single pactkit.md containing all 6 core modules
- On-demand rules (~/.claude/skills/_rules/) — 6 operational files numbered 01-06

Acceptance Criteria:
- AC1: Global rules contain only the 1 merged pactkit.md file
- AC2: On-demand rules contain only the 6 designated files (01-06)
- AC3: No overlap between global and on-demand sets
- AC4: pactkit.md content contains all required principles from merged modules
- AC5: Deployer writes global to rules/ and on-demand to skills/_rules/
- AC6: COMMAND_RULES_MAP values only reference valid keys
- AC7: Backward compat — user files (10-*, 13-*, slim-01-*) not affected
"""



def _rules():
    import importlib
    import pactkit.prompts.rules as rules_mod
    importlib.reload(rules_mod)
    return rules_mod


# ---------------------------------------------------------------------------
# AC1: RULES_CORE_FILES structure — merged single file
# ---------------------------------------------------------------------------
class TestRulesCoreFiles:
    def test_core_files_has_1_entry(self):
        rules = _rules()
        assert len(rules.RULES_CORE_FILES) == 1, (
            f"RULES_CORE_FILES should have 1 entry (merged pactkit.md), got "
            f"{len(rules.RULES_CORE_FILES)}: {list(rules.RULES_CORE_FILES.keys())}"
        )

    def test_core_files_contains_pactkit_key(self):
        rules = _rules()
        assert "pactkit" in rules.RULES_CORE_FILES, (
            f"RULES_CORE_FILES must have 'pactkit' key, got {set(rules.RULES_CORE_FILES.keys())}"
        )

    def test_core_files_filename_is_pactkit_md(self):
        rules = _rules()
        expected = {"pactkit": "pactkit.md"}
        assert rules.RULES_CORE_FILES == expected, (
            f"RULES_CORE_FILES filenames mismatch: {rules.RULES_CORE_FILES}"
        )

    def test_core_files_keys_subset_of_rules_modules(self):
        rules = _rules()
        for key in rules.RULES_CORE_FILES:
            assert key in rules.RULES_MODULES, (
                f"RULES_CORE_FILES key '{key}' not found in RULES_MODULES"
            )

    def test_pactkit_module_contains_all_core_content(self):
        """pactkit key in RULES_MODULES must be concatenation of all 6 core modules."""
        rules = _rules()
        pactkit_content = rules.RULES_MODULES["pactkit"]
        for key in ("core", "hierarchy", "atlas", "routing", "principles", "nudge"):
            module_content = rules.RULES_MODULES[key]
            # Check first significant line of each module appears in pactkit
            first_header = next(
                (line for line in module_content.splitlines() if line.startswith("#")),
                None
            )
            if first_header:
                assert first_header in pactkit_content, (
                    f"Module '{key}' header '{first_header}' not found in pactkit merged content"
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
            "workflow": "01-workflow-conventions.md",
            "mcp": "02-mcp-integration.md",
            "shared": "03-shared-protocols.md",
            "architecture": "04-architecture-principles.md",
            "sectional": "05-sectional-write.md",
            "solution": "06-solution-design.md",
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
            "RULES_FILES should equal RULES_CORE_FILES | RULES_ONDEMAND_FILES"
        )


# ---------------------------------------------------------------------------
# AC4: pactkit merged module content validation
# ---------------------------------------------------------------------------
class TestPrinciplesContent:
    def test_principles_key_in_rules_modules(self):
        """Individual 'principles' module key still exists in RULES_MODULES."""
        rules = _rules()
        assert "principles" in rules.RULES_MODULES, (
            "RULES_MODULES must still contain 'principles' key (used for inline embedding)"
        )

    def test_pactkit_key_in_rules_modules(self):
        rules = _rules()
        assert "pactkit" in rules.RULES_MODULES, (
            "RULES_MODULES must contain 'pactkit' merged key"
        )

    def test_principles_contains_no_magic_values(self):
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        assert "No Magic Values" in content or "magic value" in content.lower(), (
            "principles module must contain 'No Magic Values' principle"
        )

    def test_principles_contains_dry_or_single_source(self):
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        assert "DRY" in content or "Single Source of Truth" in content, (
            "principles module must contain DRY / Single Source of Truth principle"
        )

    def test_principles_contains_code_enforces(self):
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        assert "Code Enforces" in content or "LLM" in content, (
            "principles module must contain 'Code Enforces, Prompt Instructs' principle"
        )

    def test_principles_contains_dependency_direction(self):
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        assert "Dependency Direction" in content or "import" in content.lower(), (
            "principles module must contain Dependency Direction principle"
        )

    def test_principles_reasonable_length(self):
        """principles module should be condensed (~60 lines), not a full copy of 08/12."""
        rules = _rules()
        content = rules.RULES_MODULES["principles"]
        line_count = content.count("\n")
        assert line_count <= 100, (
            f"principles module should be condensed (<=100 lines), got {line_count} lines"
        )
        assert line_count >= 20, (
            f"principles module seems too short ({line_count} lines) — likely incomplete"
        )

    def test_pactkit_merged_is_substantially_longer(self):
        """pactkit merged content must be longer than any single module."""
        rules = _rules()
        pactkit_len = len(rules.RULES_MODULES["pactkit"])
        for key in ("core", "hierarchy", "atlas", "routing", "principles", "nudge"):
            module_len = len(rules.RULES_MODULES[key])
            assert pactkit_len > module_len, (
                f"pactkit merged content ({pactkit_len} chars) must be longer than "
                f"module '{key}' ({module_len} chars)"
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
            "On-demand rules directory skills/_rules/ should be created"
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
        """Each global rule file stem (or name) should be in RULES_GLOBAL_PREFIXES."""
        rules = _rules()
        for filename in rules.RULES_CORE_FILES.values():
            # pactkit.md -> stem "pactkit"; numeric files -> prefix "01-" etc.
            stem = filename.removesuffix(".md")
            prefix = filename[:3] if filename[0].isdigit() else stem
            assert prefix in rules.RULES_GLOBAL_PREFIXES, (
                f"Core file '{filename}' identifier '{prefix}' not in RULES_GLOBAL_PREFIXES: "
                f"{rules.RULES_GLOBAL_PREFIXES}"
            )

    def test_ondemand_prefixes_match_ondemand_files(self):
        """Each on-demand rule file should have its numeric prefix in RULES_ONDEMAND_PREFIXES."""
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
    def test_valid_rules_contains_pactkit(self):
        from pactkit.config import VALID_RULES
        assert "pactkit" in VALID_RULES, (
            "VALID_RULES must contain 'pactkit' (merged global rules)"
        )

    def test_valid_rules_total_count(self):
        """VALID_RULES should have 7 entries (1 global + 6 on-demand)."""
        from pactkit.config import VALID_RULES
        assert len(VALID_RULES) == 7, (
            f"VALID_RULES should have 7 entries, got {len(VALID_RULES)}: {sorted(VALID_RULES)}"
        )

    def test_valid_rules_contains_all_keys(self):
        """VALID_RULES stems should match RULES_FILES keys mapped to filenames."""
        from pactkit.config import VALID_RULES
        rules = _rules()
        expected_stems = {filename.removesuffix(".md") for filename in rules.RULES_FILES.values()}
        assert VALID_RULES == frozenset(expected_stems), (
            f"VALID_RULES mismatch. Expected {sorted(expected_stems)}, got {sorted(VALID_RULES)}"
        )
