"""Tests for STORY-slim-009: Lazy Rule Loading.

Covers:
- AC1: instructions only contains core rules (not glob)
- AC2: AGENTS.md contains @reference index for on-demand rules
- AC3: All rules files still deployed to rules/ directory
- AC4: CLAUDE_MD_TEMPLATE still contains ALL rules (classic unchanged)
- AC5: User-existing instructions are preserved (merge, not overwrite)
- AC6: Token overhead < 10KB for core instructions + AGENTS.md
"""

import json
import pytest

try:
    import pactkit_opencode  # noqa: F401
    _has_opencode = True
except ImportError:
    _has_opencode = False

_skip_no_opencode = pytest.mark.skipif(not _has_opencode, reason="pactkit-opencode not installed")

# ---------------------------------------------------------------------------
# R1: RULES_CORE_FILES + RULES_ONDEMAND_FILES constants exist
# ---------------------------------------------------------------------------


class TestRulesFilesSplit:
    def test_rules_core_files_exists(self):
        from pactkit.prompts.rules import RULES_CORE_FILES

        assert isinstance(RULES_CORE_FILES, dict)
        assert len(RULES_CORE_FILES) >= 2

    def test_rules_ondemand_files_exists(self):
        from pactkit.prompts.rules import RULES_ONDEMAND_FILES

        assert isinstance(RULES_ONDEMAND_FILES, dict)
        assert len(RULES_ONDEMAND_FILES) >= 4

    def test_core_contains_required_rules(self):
        """Security-critical rules must be in core (always-load)."""
        from pactkit.prompts.rules import RULES_CORE_FILES

        filenames = list(RULES_CORE_FILES.values())
        assert "01-core-protocol.md" in filenames
        assert "02-hierarchy-of-truth.md" in filenames

    def test_credential_safety_in_core(self):
        """Credential safety rule must be always-loaded (SEC-1).
        It lives in RULES_INSTRUCTIONS_CORE (not RULES_CORE_FILES since it's user-managed).
        """
        from pactkit.prompts.rules import RULES_INSTRUCTIONS_CORE

        assert any("09-credential-safety" in p or "credential" in p for p in RULES_INSTRUCTIONS_CORE), (
            "09-credential-safety.md must be in RULES_INSTRUCTIONS_CORE"
        )

    def test_architecture_not_in_core(self):
        """Large/low-frequency rules must be on-demand."""
        from pactkit.prompts.rules import RULES_CORE_FILES

        filenames = list(RULES_CORE_FILES.values())
        assert "08-architecture-principles.md" not in filenames

    def test_rules_files_is_union(self):
        """RULES_FILES must be the full union of core + ondemand."""
        from pactkit.prompts.rules import RULES_CORE_FILES, RULES_FILES, RULES_ONDEMAND_FILES

        expected = {**RULES_CORE_FILES, **RULES_ONDEMAND_FILES}
        for key, val in expected.items():
            assert key in RULES_FILES
            assert RULES_FILES[key] == val

    def test_no_overlap_between_core_and_ondemand(self):
        from pactkit.prompts.rules import RULES_CORE_FILES, RULES_ONDEMAND_FILES

        core_keys = set(RULES_CORE_FILES.keys())
        ondemand_keys = set(RULES_ONDEMAND_FILES.keys())
        assert core_keys.isdisjoint(ondemand_keys), f"Overlap: {core_keys & ondemand_keys}"


# ---------------------------------------------------------------------------
# AC1: instructions only contains core rules (not glob)
# ---------------------------------------------------------------------------


@_skip_no_opencode
class TestInstructionsCoreOnly:
    def test_opencode_json_has_credential_only_instructions(self, tmp_path):
        """STORY-slim-011: _update_global_opencode_json writes only credential safety, not core rules."""
        from pactkit_opencode.deployer import OpenCodeDeployer

        json_path = tmp_path / "opencode.json"
        OpenCodeDeployer._update_global_opencode_json(tmp_path)

        config = json.loads(json_path.read_text())
        instructions = config.get("instructions", [])

        # Must NOT contain glob
        assert "rules/*.md" not in instructions, "instructions must not contain glob 'rules/*.md'"

        # STORY-slim-011: Only credential safety in instructions (core rules moved to per-command)
        assert "rules/09-credential-safety.md" in instructions
        assert "rules/01-core-protocol.md" not in instructions
        assert "rules/02-hierarchy-of-truth.md" not in instructions

    def test_non_core_rules_not_in_instructions(self, tmp_path):
        """On-demand rules must not appear in instructions."""
        from pactkit_opencode.deployer import OpenCodeDeployer
        from pactkit.prompts.rules import RULES_ONDEMAND_FILES

        OpenCodeDeployer._update_global_opencode_json(tmp_path)

        config = json.loads((tmp_path / "opencode.json").read_text())
        instructions = config.get("instructions", [])

        for filename in RULES_ONDEMAND_FILES.values():
            assert f"rules/{filename}" not in instructions, f"On-demand rule {filename} must NOT be in instructions"

    def test_existing_user_instructions_preserved(self, tmp_path):
        """AC5: User's own instructions are not removed during update."""
        from pactkit_opencode.deployer import OpenCodeDeployer

        # Pre-existing user config
        existing = {"$schema": "https://opencode.ai/config.json", "instructions": ["CONTRIBUTING.md", "rules/*.md"]}
        json_path = tmp_path / "opencode.json"
        json_path.write_text(json.dumps(existing))

        OpenCodeDeployer._update_global_opencode_json(tmp_path)

        config = json.loads(json_path.read_text())
        instructions = config.get("instructions", [])

        # User file preserved
        assert "CONTRIBUTING.md" in instructions
        # Old glob removed
        assert "rules/*.md" not in instructions
        # STORY-slim-011: Only credential safety added (core rules now per-command)
        assert "rules/09-credential-safety.md" in instructions

    def test_no_duplicate_instructions(self, tmp_path):
        """Running update twice must not add duplicates."""
        from pactkit_opencode.deployer import OpenCodeDeployer

        OpenCodeDeployer._update_global_opencode_json(tmp_path)
        OpenCodeDeployer._update_global_opencode_json(tmp_path)  # second run

        config = json.loads((tmp_path / "opencode.json").read_text())
        instructions = config.get("instructions", [])
        assert len(instructions) == len(set(instructions)), "Duplicate entries in instructions"


# ---------------------------------------------------------------------------
# AC2: AGENTS.md contains @reference index
# ---------------------------------------------------------------------------


@_skip_no_opencode
class TestAgentsMdOnDemandRefs:
    def _get_agents_md(self, tmp_path):
        from pactkit_opencode.deployer import OpenCodeDeployer

        OpenCodeDeployer._deploy_agents_md_inline(tmp_path)
        return (tmp_path / "AGENTS.md").read_text()

    def test_agents_md_contains_ondemand_refs(self, tmp_path):
        content = self._get_agents_md(tmp_path)
        from pactkit.prompts.rules import RULES_ONDEMAND_FILES

        for filename in RULES_ONDEMAND_FILES.values():
            assert f"@rules/{filename}" in content, f"AGENTS.md missing @reference for {filename}"

    def test_agents_md_contains_lazy_load_instruction(self, tmp_path):
        """Must instruct AI to use Read tool, not preemptively load."""
        content = self._get_agents_md(tmp_path)
        assert "Read tool" in content or "need-to-know" in content, "AGENTS.md must instruct AI to use lazy loading"

    def test_agents_md_core_rules_not_referenced(self, tmp_path):
        """Core rules are in instructions, not in @refs (no duplication)."""
        content = self._get_agents_md(tmp_path)
        from pactkit.prompts.rules import RULES_CORE_FILES

        for filename in RULES_CORE_FILES.values():
            assert f"@rules/{filename}" not in content, (
                f"Core rule {filename} should not have @ref (it's in instructions)"
            )


# ---------------------------------------------------------------------------
# AC3: All rules files still deployed
# ---------------------------------------------------------------------------


class TestAllRulesDeployed:
    def test_deploy_rules_writes_all_files(self, tmp_path):
        """_deploy_rules writes all PactKit-managed rules to correct directories.
        STORY-slim-112: Global rules → rules/, On-demand rules → skills/_rules/
        _deploy_rules expects rule_ids as filename-stems (e.g. '01-core-protocol').
        User-managed files (09-credential-safety, 10-retrieval-routing) have no
        RULES_MODULES entry and are not deployed by PactKit.
        """
        from pactkit.generators.deployer import _deploy_rules
        from pactkit.prompts.rules import (
            RULES_FILES, RULES_MODULES, RULES_CORE_FILES, RULES_ONDEMAND_FILES, RULES_ONDEMAND_DIR
        )

        # Pass rule IDs as filename stems (how deploy callers use them)
        rule_ids = [v.removesuffix(".md") for k, v in RULES_FILES.items() if k in RULES_MODULES]
        _deploy_rules(tmp_path, rule_ids)

        rules_dir = tmp_path / "rules"
        ondemand_dir = tmp_path / "skills" / RULES_ONDEMAND_DIR

        # Global rules must be in rules/
        for filename in RULES_CORE_FILES.values():
            assert (rules_dir / filename).exists(), f"Global rule file {filename} not in rules/"
        # On-demand rules must be in skills/_rules/
        for filename in RULES_ONDEMAND_FILES.values():
            assert (ondemand_dir / filename).exists(), f"On-demand rule file {filename} not in skills/_rules/"


# ---------------------------------------------------------------------------
# AC4: Classic CLAUDE_MD_TEMPLATE unchanged
# ---------------------------------------------------------------------------


class TestClassicUnchanged:
    def test_claude_md_template_contains_global_rules(self):
        """STORY-slim-112: CLAUDE_MD_TEMPLATE references only global rules (in rules/).
        On-demand rules are in skills/_rules/ and loaded via @import in commands.
        """
        from pactkit.prompts.rules import CLAUDE_MD_TEMPLATE, RULES_CORE_FILES, RULES_ONDEMAND_FILES

        # Global rules must be referenced in CLAUDE_MD_TEMPLATE
        for filename in RULES_CORE_FILES.values():
            assert filename in CLAUDE_MD_TEMPLATE, f"CLAUDE_MD_TEMPLATE missing global rule {filename}"
        # On-demand rules should NOT be in CLAUDE_MD_TEMPLATE
        for filename in RULES_ONDEMAND_FILES.values():
            assert filename not in CLAUDE_MD_TEMPLATE, (
                f"CLAUDE_MD_TEMPLATE should not reference on-demand rule {filename}"
            )

    def test_claude_md_template_uses_at_import(self):
        """Classic uses @import syntax (not OpenCode @reference)."""
        from pactkit.prompts.rules import CLAUDE_MD_TEMPLATE

        assert "@~/.claude/rules/" in CLAUDE_MD_TEMPLATE


# ---------------------------------------------------------------------------
# AC6: Token overhead < 10KB
# ---------------------------------------------------------------------------


@_skip_no_opencode
class TestTokenOverhead:
    def test_core_instructions_under_10kb(self, tmp_path):
        """Core rules + AGENTS.md must be under 10KB total."""
        from pactkit.generators.deployer import _deploy_rules
        from pactkit_opencode.deployer import OpenCodeDeployer
        from pactkit.prompts.rules import RULES_CORE_FILES, RULES_FILES

        _deploy_rules(tmp_path, list(RULES_FILES.keys()))
        OpenCodeDeployer._update_global_opencode_json(tmp_path)
        OpenCodeDeployer._deploy_agents_md_inline(tmp_path)

        # Sum core rule files
        rules_dir = tmp_path / "rules"
        core_size = sum(
            (rules_dir / filename).stat().st_size
            for filename in RULES_CORE_FILES.values()
            if (rules_dir / filename).exists()
        )
        agents_size = (tmp_path / "AGENTS.md").stat().st_size
        total = core_size + agents_size

        assert total < 10_000, f"Core instructions + AGENTS.md = {total} bytes, must be < 10KB"
