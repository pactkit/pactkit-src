"""Deployment layout contracts for the scenario-driven rules registry."""


def test_runtime_is_the_only_always_loaded_rule():
    from pactkit.prompts.rules import RULE_DEFINITIONS, RULES_CORE_FILES, RULES_ONDEMAND_FILES

    assert RULES_CORE_FILES == {"runtime": "pactkit-runtime.md"}
    assert set(RULES_ONDEMAND_FILES) == set(RULE_DEFINITIONS) - {"runtime"}
    assert all(
        definition.load_policy != "global"
        for key, definition in RULE_DEFINITIONS.items()
        if key != "runtime"
    )


def test_registry_uses_stable_logical_nested_paths_not_numeric_prefixes():
    from pactkit.prompts.rules import RULES_ONDEMAND_FILES

    assert "phases/act-contract.md" in RULES_ONDEMAND_FILES.values()
    assert "execution/shared-execution.md" in RULES_ONDEMAND_FILES.values()
    assert all(not filename[:1].isdigit() for filename in RULES_ONDEMAND_FILES.values())


def test_classic_deploy_routes_runtime_and_command_modules_separately(tmp_path):
    from pactkit.generators.deployer import _deploy_rules
    from pactkit.prompts.rules import RULE_DEFINITIONS

    _deploy_rules(tmp_path, list(RULE_DEFINITIONS))
    assert (tmp_path / "rules" / "pactkit-runtime.md").is_file()
    assert not (tmp_path / "skills" / "_rules" / "pactkit-runtime.md").exists()
    for definition in RULE_DEFINITIONS.values():
        if definition.id != "runtime":
            assert (tmp_path / "skills" / "_rules" / definition.filename).is_file()


def test_registry_references_are_valid_and_credential_is_virtual():
    from pactkit.prompts.rules import COMMAND_RULES_MAP, RULE_DEFINITIONS

    for rule_ids in COMMAND_RULES_MAP.values():
        assert all(rule_id == "credential" or rule_id in RULE_DEFINITIONS for rule_id in rule_ids)


def test_legacy_ids_remain_accepted_but_default_config_uses_current_ids():
    from pactkit.config import DEFAULT_RULE_IDS, VALID_RULES, get_default_config

    assert {"pactkit", "02-mcp-integration", "03-shared-protocols"} <= VALID_RULES
    assert set(get_default_config()["rules"]) == set(DEFAULT_RULE_IDS)
