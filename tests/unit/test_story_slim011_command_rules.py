"""Rule-to-command loading contracts for the scenario-driven registry."""

import json

import pytest

from pactkit.prompts import COMMANDS_CONTENT
from pactkit.prompts.rules import (
    COMMAND_CONDITIONAL_RULES_MAP,
    COMMAND_RULES_MAP,
    RULES_FILES,
)


SPEC_TABLE = {
    "project-init": ["runtime", "phase-plan", "shared-execution"],
    "project-plan": ["runtime", "phase-plan", "shared-execution"],
    "project-clarify": ["runtime", "phase-plan"],
    "project-act": ["runtime", "phase-act", "shared-execution", "spec-preflight"],
    "project-check": ["runtime", "phase-check", "shared-execution"],
    "project-done": ["runtime", "phase-done", "shared-execution", "git-workflow"],
    "project-release": ["runtime", "phase-release", "git-workflow"],
    "project-pr": ["runtime", "phase-pr", "git-workflow"],
    "project-hotfix": ["runtime", "phase-hotfix", "shared-execution"],
    "project-design": ["runtime", "phase-plan"],
    "project-sprint": ["runtime", "sprint-orchestrator", "shared-execution"],
    "project-debug": ["runtime", "shared-execution"],
}

for _rules in SPEC_TABLE.values():
    _rules.insert(1, "pdca-lifecycle")


@pytest.mark.parametrize("command", sorted(SPEC_TABLE))
def test_command_rules_match_scenario_contract(command):
    assert COMMAND_RULES_MAP[command] == SPEC_TABLE[command]


def test_every_command_has_a_mapping_and_runtime_safety():
    commands = {name.removesuffix(".md") for name in COMMANDS_CONTENT}
    assert commands == set(COMMAND_RULES_MAP)
    assert all("runtime" in rules for rules in COMMAND_RULES_MAP.values())


def test_every_non_maintainer_registry_rule_is_reachable():
    mapped = {rule for rules in COMMAND_RULES_MAP.values() for rule in rules}
    mapped.update(
        rule for rules in COMMAND_CONDITIONAL_RULES_MAP.values() for rule in rules
    )
    assert set(RULES_FILES) - {"pactkit-maintainer"} <= mapped


def test_classic_act_imports_only_its_nonruntime_modules(tmp_path):
    from pactkit.generators.deployer import _deploy_commands
    from pactkit.profiles import get_profile

    _deploy_commands(tmp_path / "skills", ["project-act"], profile=get_profile("classic"))
    content = (tmp_path / "skills" / "project-act" / "SKILL.md").read_text()
    expected = {
        "phases/act-contract.md", "execution/shared-execution.md",
        "execution/spec-preflight.md",
    }
    for filename in expected:
        assert f"@~/.claude/skills/_rules/{filename}" in content
    assert "@~/.claude/rules/pactkit-runtime.md" not in content
    for conditional in ("external-tools.md", "capability-design.md", "engineering/index.md"):
        assert f"@~/.claude/skills/_rules/{conditional}" not in content


def test_opencode_act_inlines_only_its_nonruntime_modules(tmp_path):
    from pactkit.generators.deployer import _deploy_commands
    from pactkit.profiles import get_profile

    _deploy_commands(tmp_path / "commands", ["project-act"], profile=get_profile("opencode"))
    content = (tmp_path / "commands" / "project-act.md").read_text()
    for heading in ("# Act Contract", "# Shared Execution", "# Spec Preflight"):
        assert heading in content
    assert "# External Tools" not in content
    assert "# Capability Design" not in content
    assert "# PactKit Runtime Contract" not in content
    assert "# Plan Contract" not in content


def test_legacy_command_override_normalizes_credential_to_runtime():
    from pactkit.generators.deployer import _get_command_rules

    rules = _get_command_rules("project-act", {"command_rules": {"project-act": ["pactkit", "03-shared-protocols"]}})
    assert rules == ["runtime", "shared-execution"]


def test_classic_claude_md_loads_only_runtime(tmp_path):
    from pactkit.generators.deployer import _deploy_claude_md

    _deploy_claude_md(tmp_path, sorted(RULES_FILES))
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "@~/.claude/rules/pactkit-runtime.md" in content
    assert "skills/_rules" not in content


def test_opencode_global_instructions_keep_only_self_contained_runtime(tmp_path):
    pytest.importorskip("pactkit_opencode")
    from pactkit_opencode.deployer import OpenCodeDeployer

    (tmp_path / "opencode.json").write_text(json.dumps({"instructions": ["rules/01-core-protocol.md"]}))
    OpenCodeDeployer._update_global_opencode_json(tmp_path)
    instructions = json.loads((tmp_path / "opencode.json").read_text())["instructions"]
    assert "rules/pactkit-runtime.md" in instructions
    assert "rules/09-credential-safety.md" not in instructions
    assert "rules/01-core-protocol.md" not in instructions
