"""Tests for STORY-slim-011: Rule-Command Mapping — Context-Aware Rule Loading.

Covers:
- AC1:  COMMAND_RULES_MAP matches Spec R1 table
- AC2:  Classic @import injection for project-clarify
- AC3:  Classic @import injection for project-act (full validation)
- AC4:  OpenCode inline embedding for project-clarify
- AC5:  OpenCode inline embedding for project-act (full validation)
- AC6:  Credential safety forced inclusion (even when user omits)
- AC7:  User custom override via command_rules config
- AC8:  Anti-regression: every rule mapped to at least one command
- AC9:  Anti-regression: every command has a rule mapping
- AC10: Anti-regression: credential safety in all commands
- AC11: Classic CLAUDE.md no longer has global rule @imports
- AC12: OpenCode instructions only keeps 09-credential-safety
"""

import json

import pytest

try:
    import pactkit_opencode  # noqa: F401
    _has_opencode = True
except ImportError:
    _has_opencode = False

_skip_no_opencode = pytest.mark.skipif(not _has_opencode, reason="pactkit-opencode not installed")

from pactkit.prompts import COMMANDS_CONTENT
from pactkit.prompts.rules import (
    COMMAND_RULES_MAP,
    RULES_FILES,
)

# ---------------------------------------------------------------------------
# AC1: COMMAND_RULES_MAP matches Spec R1 table
# ---------------------------------------------------------------------------

# Spec R1 table (rule numbers → keys mapping):
# 01=core, 02=hierarchy, 03=atlas, 04=routing, 05=workflow,
# 06=mcp, 07=shared, 08=architecture, 09=credential
SPEC_TABLE = {
    # architecture/solution/engineering removed from @inject — loaded on-demand via Read in playbooks
    "project-init": ["core", "sectional", "atlas", "shared", "credential"],
    "project-plan": ["core", "sectional", "hierarchy", "atlas", "mcp", "shared", "credential"],
    "project-clarify": ["core", "credential"],
    "project-act": ["core", "hierarchy", "atlas", "mcp", "shared", "credential"],
    "project-check": ["core", "hierarchy", "atlas", "mcp", "shared", "credential"],
    "project-done": ["core", "hierarchy", "atlas", "workflow", "shared", "credential"],
    "project-release": ["core", "workflow", "credential"],
    "project-pr": ["core", "workflow", "credential"],
    "project-hotfix": ["core", "hierarchy", "atlas", "workflow", "shared", "credential"],
    "project-design": ["core", "sectional", "atlas", "mcp", "credential"],
    "project-sprint": [
        "core", "sectional", "hierarchy", "atlas", "routing", "workflow",
        "mcp", "shared", "credential",
    ],
}


class TestAC1MappingTable:
    """AC1: COMMAND_RULES_MAP matches Spec R1 table."""

    @pytest.mark.parametrize("cmd", sorted(SPEC_TABLE.keys()))
    def test_command_rules_match_spec(self, cmd):
        assert cmd in COMMAND_RULES_MAP, f"Command {cmd} missing from COMMAND_RULES_MAP"
        assert sorted(COMMAND_RULES_MAP[cmd]) == sorted(SPEC_TABLE[cmd]), (
            f"Command {cmd}: expected {sorted(SPEC_TABLE[cmd])}, got {sorted(COMMAND_RULES_MAP[cmd])}"
        )


# ---------------------------------------------------------------------------
# AC8: Anti-regression — every rule must be mapped to at least one command
# ---------------------------------------------------------------------------

class TestAC8AllRulesMapped:
    """AC8: Every rule in RULES_FILES must appear in at least one command's rule list."""

    def test_all_rules_mapped_to_at_least_one_command(self):
        all_rule_keys = set(RULES_FILES.keys())
        mapped_keys = set()
        for rules_list in COMMAND_RULES_MAP.values():
            mapped_keys.update(rules_list)

        # credential is special (not in RULES_FILES) — exclude from check
        mapped_keys.discard("credential")

        # nudge is conversation-scoped (suppressed inside PDCA context) — not command-mapped
        all_rule_keys.discard("nudge")

        # STORY-slim-112: principles is a global rule (auto-loaded by harness) — not command-mapped
        # Global rules are always in context, so no @import needed in commands
        all_rule_keys.discard("principles")

        # Post-merge refactor: pactkit is the merged global file (auto-loaded) — not command-mapped
        all_rule_keys.discard("pactkit")

        # Slimmed from @inject to on-demand Read (referenced in playbook text, not COMMAND_RULES_MAP)
        all_rule_keys.discard("architecture")
        all_rule_keys.discard("solution")
        all_rule_keys.discard("engineering")

        unmapped = all_rule_keys - mapped_keys
        assert not unmapped, f"Rules not mapped to any command: {unmapped}"


# ---------------------------------------------------------------------------
# AC9: Anti-regression — every command must have a rule mapping
# ---------------------------------------------------------------------------

class TestAC9AllCommandsMapped:
    """AC9: Every command in COMMANDS_CONTENT must have a COMMAND_RULES_MAP entry."""

    def test_all_commands_have_rule_mapping(self):
        all_commands = {f.removesuffix(".md") for f in COMMANDS_CONTENT.keys()}
        mapped_commands = set(COMMAND_RULES_MAP.keys())

        unmapped = all_commands - mapped_commands
        assert not unmapped, f"Commands without rule mapping: {unmapped}"


# ---------------------------------------------------------------------------
# AC10: Anti-regression — credential safety in every command
# ---------------------------------------------------------------------------

class TestAC10CredentialSafetyEnforced:
    """AC10: Every command must include 'credential' in its rule list."""

    @pytest.mark.parametrize("cmd", sorted(COMMAND_RULES_MAP.keys()) if hasattr(COMMAND_RULES_MAP, 'keys') else [])
    def test_credential_safety_in_all_commands(self, cmd):
        assert "credential" in COMMAND_RULES_MAP[cmd], (
            f"Command '{cmd}' missing credential safety rule"
        )


# ---------------------------------------------------------------------------
# AC2/AC3: Classic @import injection
# ---------------------------------------------------------------------------

class TestAC2AC3ClassicImport:
    """AC2/AC3: Classic command files get @import headers for their rules."""

    def test_classic_clarify_imports(self, tmp_path):
        """AC2: project-clarify gets only credential @import.
        Global rules (pactkit.md) are auto-loaded by harness, no @import needed.
        Only user-managed credential file gets an @import.
        """
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        profile = get_profile("classic")
        _deploy_commands(skills_dir, ["project-clarify"], profile=profile)

        # STORY-slim-063: deployed as skills_dir/{name}/SKILL.md
        content = (skills_dir / "project-clarify" / "SKILL.md").read_text()
        # Only credential (user-managed) should be @imported
        assert "@~/.claude/rules/09-credential-safety.md" in content
        # Global rules are auto-loaded by harness — no @import needed
        assert "@~/.claude/rules/pactkit.md" not in content
        assert "@~/.claude/rules/01-core-protocol.md" not in content
        # On-demand rules not in clarify's map should not appear
        assert "@~/.claude/skills/_rules/04-architecture-principles.md" not in content

    def test_classic_act_imports(self, tmp_path):
        """AC3: project-act gets on-demand rule @imports from skills/_rules/ + credential.
        Global rules (pactkit.md) are auto-loaded, not @imported.
        On-demand rules (02-mcp, 03-shared, 04-architecture, 05-sectional, 06-solution)
        are @imported from skills/_rules/.
        """
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        profile = get_profile("classic")
        _deploy_commands(skills_dir, ["project-act"], profile=profile)

        # STORY-slim-063: deployed as skills_dir/{name}/SKILL.md
        content = (skills_dir / "project-act" / "SKILL.md").read_text()
        # On-demand rules should be @imported from skills/_rules/ with new filenames
        # (architecture/solution/engineering slimmed to on-demand Read, not @inject)
        for rule_file in [
            "02-mcp-integration.md",
            "03-shared-protocols.md",
        ]:
            assert f"@~/.claude/skills/_rules/{rule_file}" in content, (
                f"Missing @import for on-demand rule {rule_file}"
            )
        # Credential (user-managed) from rules/
        assert "@~/.claude/rules/09-credential-safety.md" in content
        # Global merged file should NOT be @imported (auto-loaded by harness)
        assert "@~/.claude/rules/pactkit.md" not in content
        assert "@~/.claude/rules/01-core-protocol.md" not in content
        assert "@~/.claude/rules/02-hierarchy-of-truth.md" not in content
        # On-demand rules should NOT appear under the old rules/ path
        assert "@~/.claude/rules/02-mcp-integration.md" not in content
        assert "@~/.claude/rules/04-architecture-principles.md" not in content


# ---------------------------------------------------------------------------
# AC4/AC5: OpenCode inline embedding
# ---------------------------------------------------------------------------

class TestAC4AC5OpenCodeInline:
    """AC4/AC5: OpenCode command files embed rule content inline."""

    def test_opencode_clarify_inline(self, tmp_path):
        """AC4: project-clarify embeds 01 and 09 rule content (09 as @import since user-managed)."""
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        profile = get_profile("opencode")
        _deploy_commands(commands_dir, ["project-clarify"], profile=profile)

        content = (commands_dir / "project-clarify.md").read_text()
        # Should have 01 content inlined
        assert "# Core Protocol" in content
        # Should NOT have other rule content
        assert "# The Hierarchy of Truth" not in content
        assert "# File Atlas" not in content
        assert "# Architecture Principles" not in content

    def test_opencode_act_inline(self, tmp_path):
        """AC5: project-act embeds 01, 02, 03, 06, 07, 08 rule content inline."""
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        profile = get_profile("opencode")
        _deploy_commands(commands_dir, ["project-act"], profile=profile)

        content = (commands_dir / "project-act.md").read_text()
        # Should have managed rule content (architecture/solution/engineering now on-demand)
        for heading in [
            "# Core Protocol",
            "# The Hierarchy of Truth",
            "# File Atlas",
            "# MCP Integration",
            "# Shared Protocols",
        ]:
            assert heading in content, f"Missing inline content: {heading}"
        # Should NOT have 04-routing-table or 05-workflow content
        assert "# Command Reference (Routing Table)" not in content
        assert "# Workflow Conventions" not in content


# ---------------------------------------------------------------------------
# AC6: Credential safety forced inclusion
# ---------------------------------------------------------------------------

class TestAC6CredentialSafetyForced:
    """AC6: Even if user omits credential from command_rules, deployer adds it."""

    def test_credential_forced_when_user_omits(self, tmp_path):
        from pactkit.generators.deployer import _get_command_rules

        # User config omits credential
        config = {"command_rules": {"project-act": ["core", "hierarchy"]}}
        rules = _get_command_rules("project-act", config)
        assert "credential" in rules, "Credential safety must be forced even when user omits it"

    def test_credential_not_duplicated_when_user_includes(self, tmp_path):
        from pactkit.generators.deployer import _get_command_rules

        config = {"command_rules": {"project-act": ["core", "credential"]}}
        rules = _get_command_rules("project-act", config)
        assert rules.count("credential") == 1, "Credential should not be duplicated"


# ---------------------------------------------------------------------------
# AC7: User custom override
# ---------------------------------------------------------------------------

class TestAC7UserOverride:
    """AC7: command_rules in config overrides default mapping."""

    def test_user_override_respected(self):
        from pactkit.generators.deployer import _get_command_rules

        config = {"command_rules": {"project-act": ["core", "hierarchy", "credential"]}}
        rules = _get_command_rules("project-act", config)
        assert sorted(rules) == sorted(["core", "hierarchy", "credential"])

    def test_default_used_when_no_override(self):
        from pactkit.generators.deployer import _get_command_rules

        config = {}
        rules = _get_command_rules("project-act", config)
        assert sorted(rules) == sorted(COMMAND_RULES_MAP["project-act"])


# ---------------------------------------------------------------------------
# AC11: Classic CLAUDE.md — no global rule @imports
# ---------------------------------------------------------------------------

class TestAC11ClassicClaudeMd:
    """AC11: CLAUDE.md should not have global rule @imports (rules are now per-command)."""

    def test_claude_md_no_global_rule_imports(self, tmp_path):
        from pactkit.generators.deployer import _deploy_claude_md

        _deploy_claude_md(tmp_path, sorted(RULES_FILES.keys()))

        content = (tmp_path / "CLAUDE.md").read_text()
        # Should have version header
        assert "# PactKit Global Constitution" in content
        # Should NOT have rule @imports
        for filename in RULES_FILES.values():
            assert f"@~/.claude/rules/{filename}" not in content, (
                f"CLAUDE.md should not have global @import for {filename}"
            )


# ---------------------------------------------------------------------------
# AC12: OpenCode instructions — only 09 in instructions
# ---------------------------------------------------------------------------

@_skip_no_opencode
class TestAC12OpenCodeInstructions:
    """AC12: opencode.json instructions should only keep 09-credential-safety."""

    def test_opencode_json_instructions_only_09(self, tmp_path):
        from pactkit_opencode.deployer import OpenCodeDeployer

        # Pre-existing opencode.json with old instructions
        old_config = {
            "$schema": "https://opencode.ai/config.json",
            "instructions": [
                "rules/01-core-protocol.md",
                "rules/02-hierarchy-of-truth.md",
                "rules/09-credential-safety.md",
            ],
        }
        json_path = tmp_path / "opencode.json"
        json_path.write_text(json.dumps(old_config))

        OpenCodeDeployer._update_global_opencode_json(tmp_path)

        result = json.loads(json_path.read_text())
        instructions = result["instructions"]

        # Should keep 09
        assert "rules/09-credential-safety.md" in instructions
        # Should NOT have 01 or 02 (now loaded per-command)
        assert "rules/01-core-protocol.md" not in instructions
        assert "rules/02-hierarchy-of-truth.md" not in instructions
