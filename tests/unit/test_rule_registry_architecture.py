"""Contract tests for STORY-slim-20260825b1c83a046b4b.

These tests intentionally assert the user-visible rule-loading and ownership
semantics, rather than preserving the former merged-constitution layout.
"""

from pathlib import Path
import hashlib
import json


def test_runtime_kernel_is_small_and_has_no_phase_gate_content():
    from pactkit.prompts.rules import RULES_MODULES

    runtime = RULES_MODULES["runtime"]
    assert len(runtime.strip().splitlines()) <= 70
    for forbidden in ("Strict TDD", "Visual First", "Command Reference", "File Atlas"):
        assert forbidden not in runtime
    for workflow_term in ("WorkUnit", "Board", "journal", "receipt"):
        assert workflow_term not in runtime
    assert "current session" in runtime.lower()
    assert "Historical" in runtime


def test_portable_methods_do_not_expose_internal_or_host_specific_orchestration():
    from pactkit.portable_methods import get_portable_methods

    content = "\n".join(method["skill_md"] for method in get_portable_methods())
    for forbidden in (
        "WorkUnit", "EvidenceReceipt", "codex runner",
        "--owner codex", "Codex thread",
    ):
        assert forbidden not in content
    assert "current request" in content
    assert "current conversation" in content


def test_registry_only_allows_hard_rules_to_block_exact_risks():
    from pactkit.prompts.rules import RULE_DEFINITIONS

    valid_failures = {"block_action", "incomplete_continue", "record_deviation", "warn_continue"}
    for definition in RULE_DEFINITIONS.values():
        assert definition.trigger
        assert definition.evidence
        assert definition.override
        assert isinstance(definition.skip_when, tuple)
        assert definition.failure in valid_failures
        if definition.level == "hard":
            assert definition.failure == "block_action"
        else:
            assert definition.failure != "block_action"

    preflight = RULE_DEFINITIONS["spec-preflight"]
    assert "first source write" in preflight.trigger
    assert "project-hotfix is active" in preflight.skip_when
    assert "Spec hash" in preflight.evidence[0]


def test_act_loads_its_contract_not_other_phase_contracts():
    from pactkit.prompts.rules import COMMAND_RULES_MAP

    rules = set(COMMAND_RULES_MAP["project-act"])
    assert {"runtime", "pdca-lifecycle", "phase-act", "shared-execution", "spec-preflight"} <= rules
    assert "phase-plan" not in rules
    assert "phase-release" not in rules


def test_every_project_skill_has_common_lifecycle_without_global_leakage():
    from pactkit.prompts.rules import COMMAND_RULES_MAP, RULE_DEFINITIONS

    for command, rules in COMMAND_RULES_MAP.items():
        assert "pdca-lifecycle" in rules, command
    lifecycle = RULE_DEFINITIONS["pdca-lifecycle"]
    assert lifecycle.load_policy == "command"
    for section in ("## Entry", "## Execution", "## Transition", "## Completion", "## Interruption and Change", "## Exit"):
        assert section in lifecycle.content
    assert "new session is optional" in lifecycle.content.lower()
    assert "not a lock" in lifecycle.content.lower()


def test_phase_policies_cover_every_command_and_keep_side_effects_explicit():
    from pactkit.prompts.rules import COMMAND_RULES_MAP, PHASE_POLICIES

    assert set(PHASE_POLICIES) == set(COMMAND_RULES_MAP)
    for command, policy in PHASE_POLICIES.items():
        assert policy.entry, command
        assert policy.outputs, command
        assert policy.completion_evidence, command
        assert set(policy.next_commands) <= set(PHASE_POLICIES), command
    assert PHASE_POLICIES["project-pr"].external_effects == ("push", "pull request")
    assert PHASE_POLICIES["project-release"].external_effects == (
        "tag", "publish", "release"
    )
    assert PHASE_POLICIES["project-act"].external_effects == ()


def test_maintainer_overlay_is_added_only_for_the_pactkit_source_root(tmp_path):
    from pactkit.config import activate_pactkit_maintainer_overlay
    from pactkit.generators.deployer import _get_command_rules

    business = tmp_path / "business"
    business.mkdir()
    business_config = activate_pactkit_maintainer_overlay({}, business)
    assert "pactkit-maintainer" not in _get_command_rules("project-act", business_config)

    pactkit_root = tmp_path / "pactkit"
    (pactkit_root / "src" / "pactkit").mkdir(parents=True)
    (pactkit_root / "pyproject.toml").write_text(
        "[project]\nname = \"pactkit\"\n", encoding="utf-8"
    )
    maintainer_config = activate_pactkit_maintainer_overlay({}, pactkit_root)
    assert maintainer_config["_pactkit_self_development"] is True
    assert "pactkit-maintainer" in maintainer_config["rules"]
    assert "pactkit-maintainer" in _get_command_rules("project-act", maintainer_config)


def test_legacy_rule_identifiers_resolve_to_current_registry_ids():
    from pactkit.prompts.rules import normalize_rule_id

    assert normalize_rule_id("pactkit") == "runtime"
    assert normalize_rule_id("02-mcp-integration") == "external-tools"
    assert normalize_rule_id("03-shared-protocols") == "shared-execution"
    assert normalize_rule_id("01-core-protocol") == "runtime"
    assert normalize_rule_id("02-hierarchy-of-truth") == "shared-execution"
    assert normalize_rule_id("03-file-atlas") == "engineering-index"
    assert normalize_rule_id("04-routing-table") == "pdca-lifecycle"
    assert normalize_rule_id("05-workflow-conventions") == "git-workflow"
    assert normalize_rule_id("06-mcp-integration") == "external-tools"
    assert normalize_rule_id("07-shared-protocols") == "shared-execution"
    assert normalize_rule_id("08-architecture-principles") == "capability-design"
    assert normalize_rule_id("09-sectional-write") == "sectional-heuristics"


def test_every_guide_is_risk_driven_and_problematic_absolutes_are_removed():
    from pactkit.prompts.guides import GUIDE_DEFINITIONS, GUIDES_FILES

    assert set(GUIDE_DEFINITIONS) == set(GUIDES_FILES)
    for filename, definition in GUIDE_DEFINITIONS.items():
        assert definition.trigger
        assert definition.defaults
        assert definition.hard_safety
        assert definition.evidence
        assert "## Trigger" in GUIDES_FILES[filename]
        body_after_safety = GUIDES_FILES[filename].split("## Evidence", 1)[-1]
        assert "## MUST" not in body_after_safety
        assert "## NEVER" not in body_after_safety
        assert " MUST " not in body_after_safety
        assert "- NEVER " not in body_after_safety

    all_content = "\n".join(GUIDES_FILES.values())
    for obsolete_absolute in (
        "All caches MUST have TTL",
        "Every awaitable MUST have timeout",
        "NEVER hold transactions > 1 second",
        "All write APIs MUST accept and enforce idempotency key",
        "System MUST have health check endpoint",
    ):
        assert obsolete_absolute not in all_content


def test_unmodified_legacy_rule_is_migrated_but_user_modified_file_is_preserved(tmp_path, capsys):
    from pactkit.generators.deployer import _deploy_rules
    from pactkit.prompts.rules import LEGACY_RULE_CONTENTS, RULES_FILES

    root = Path(tmp_path)
    rules = root / "rules"
    rules.mkdir()
    (rules / "pactkit.md").write_text(LEGACY_RULE_CONTENTS["pactkit.md"], encoding="utf-8")

    _deploy_rules(root, list(RULES_FILES))
    assert not (rules / "pactkit.md").exists()
    assert (rules / "pactkit-runtime.md").exists()

    (rules / "pactkit.md").write_text("# user custom rule\n", encoding="utf-8")
    _deploy_rules(root, list(RULES_FILES))
    assert (rules / "pactkit.md").read_text(encoding="utf-8") == "# user custom rule\n"
    assert "preserved user-modified" in capsys.readouterr().out


def test_user_modified_current_managed_rule_gets_side_by_side_candidate(tmp_path, capsys):
    from pactkit.generators.deployer import _deploy_rules
    from pactkit.prompts.rules import RULE_DEFINITIONS

    root = Path(tmp_path)
    destination = root / "rules" / "pactkit-runtime.md"
    destination.parent.mkdir(parents=True)
    original = "# local runtime adjustment\n"
    destination.write_text(original, encoding="utf-8")
    expected = hashlib.sha256(b"# prior managed runtime\n").hexdigest()
    (root / ".pactkit-deployed.json").write_text(json.dumps({
        "files": {"rules/pactkit-runtime.md": expected},
    }), encoding="utf-8")

    _deploy_rules(root, ["runtime"])

    assert destination.read_text(encoding="utf-8") == original
    candidate = destination.with_suffix(".md.pactkit-new")
    assert candidate.read_text(encoding="utf-8") == RULE_DEFINITIONS["runtime"].content
    from pactkit.deploy_manifest import pactkit_owned_files
    assert "rules/pactkit-runtime.md" not in pactkit_owned_files(
        root, {"skills": [], "portable_methods": [], "commands": [], "agents": []},
    )
    assert "preserved user-modified PactKit rule" in capsys.readouterr().out


def test_conflicted_rule_is_excluded_from_both_manifest_ownership_views(tmp_path):
    from pactkit.deploy_manifest import pactkit_rule_ownership, pactkit_owned_files

    destination = tmp_path / "rules" / "pactkit-runtime.md"
    destination.parent.mkdir(parents=True)
    destination.write_text("# user runtime\n", encoding="utf-8")
    destination.with_suffix(".md.pactkit-new").write_text(
        "# proposed runtime\n", encoding="utf-8"
    )
    components = {"skills": [], "portable_methods": [], "commands": [], "agents": []}

    assert "rules/pactkit-runtime.md" not in pactkit_owned_files(
        tmp_path, components, enabled_rules=["runtime"]
    )
    assert pactkit_rule_ownership(tmp_path, enabled_rules=["runtime"]) == []


def test_manifest_rule_records_include_executable_semantics(tmp_path):
    from pactkit.deploy_manifest import pactkit_rule_ownership
    from pactkit.generators.deployer import _deploy_rules

    _deploy_rules(tmp_path, ["runtime", "spec-preflight"])
    records = {
        record["id"]: record
        for record in pactkit_rule_ownership(
            tmp_path, enabled_rules=["runtime", "spec-preflight"]
        )
    }
    assert records["runtime"]["level"] == "required"
    assert records["runtime"]["failure"] == "incomplete_continue"
    assert records["spec-preflight"]["trigger"] == (
        "before the first source write in a Spec-bound Act"
    )
    assert "project-hotfix is active" in records["spec-preflight"]["skip_when"]
    assert records["runtime"]["legacy_ids"]


def test_manifest_v2_records_normalized_pdca_semantics(tmp_path):
    import json

    from pactkit.deploy_manifest import write_deploy_manifest
    from pactkit.generators.deployer import _deploy_rules

    _deploy_rules(tmp_path, ["runtime"])
    manifest = write_deploy_manifest(
        tmp_path,
        "classic",
        {"skills": [], "commands": [], "agents": [], "rules": ["runtime"]},
    )
    payload = json.loads(manifest.read_text())
    assert payload["rule_schema_version"] == 2
    assert payload["rule_loading"]["primary_hosts"] == [
        "classic", "codex", "opencode",
    ]
    assert payload["rule_loading"]["compatibility_hosts"] == ["copilot"]
    assert payload["rule_clauses"]["safety.authorization"]["failure"] == (
        "block_exact_action"
    )
    assert payload["phase_contracts"]["project-act"]["failure_semantics"] == (
        "incomplete_continue"
    )
    assert len(payload["guides"]) == 23
    assert payload["sprint_capsules"]["single_active_phase"] is True


def test_rule_ownership_doctor_is_read_only_and_flags_only_high_signal_conflicts(tmp_path):
    from pactkit.deploy_manifest import write_deploy_manifest
    from pactkit.doctor import check_rule_ownership
    from pactkit.generators.deployer import _deploy_rules

    home = tmp_path / "home"
    project = tmp_path / "project"
    deploy_root = home / ".claude"
    project_rules = project / ".claude" / "rules"
    user_rules = deploy_root / "rules"
    project_rules.mkdir(parents=True)
    user_rules.mkdir(parents=True)
    _deploy_rules(deploy_root, ["runtime"])
    write_deploy_manifest(
        deploy_root, "classic",
        {"skills": [], "commands": [], "agents": [], "rules": ["runtime"]},
    )
    personal = user_rules / "10-safety.md"
    personal.write_text("STOP and require a new session\n", encoding="utf-8")
    optional = user_rules / "11-session-choice.md"
    optional.write_text(
        "A new session is optional.\n"
        "Do not create a permanent workflow lock or require a new session.\n",
        encoding="utf-8",
    )
    local = project_rules / "architecture.md"
    local.write_text("# Project architecture\n", encoding="utf-8")
    before = {path: path.read_bytes() for path in (personal, optional, local)}

    result = check_rule_ownership(project, home=home)

    assert any(item["path"] == "rules/pactkit-runtime.md" for item in result["pactkit_owned"])
    assert any(item["path"] == "rules/10-safety.md" for item in result["user_owned"])
    assert any(item["path"] == "rules/architecture.md" for item in result["project_owned"])
    assert {item["signal"] for item in result["potential_conflicts"]} == {
        "unscoped STOP", "forced session split",
    }
    assert not any(
        item["path"] == "rules/11-session-choice.md"
        for item in result["potential_conflicts"]
    )
    assert {path: path.read_bytes() for path in before} == before


def test_selective_redeploy_removes_only_unchanged_disabled_rules(tmp_path):
    from pactkit.deploy_manifest import write_deploy_manifest
    from pactkit.generators.deployer import _deploy_rules

    config = {"skills": [], "commands": [], "agents": [], "rules": ["runtime", "phase-act"]}
    _deploy_rules(tmp_path, config["rules"])
    write_deploy_manifest(tmp_path, "classic", config)

    disabled = tmp_path / "skills" / "_rules" / "phases" / "act-contract.md"
    assert disabled.is_file()
    _deploy_rules(tmp_path, ["runtime"])
    assert not disabled.exists()


def test_selective_redeploy_preserves_modified_disabled_rule(tmp_path):
    from pactkit.deploy_manifest import write_deploy_manifest
    from pactkit.generators.deployer import _deploy_rules

    config = {"skills": [], "commands": [], "agents": [], "rules": ["runtime", "phase-act"]}
    _deploy_rules(tmp_path, config["rules"])
    write_deploy_manifest(tmp_path, "classic", config)
    disabled = tmp_path / "skills" / "_rules" / "phases" / "act-contract.md"
    disabled.write_text("# locally retained contract\n", encoding="utf-8")

    _deploy_rules(tmp_path, ["runtime"])
    assert disabled.read_text(encoding="utf-8") == "# locally retained contract\n"


def test_user_modified_guide_is_preserved_and_not_reclaimed_by_manifest(tmp_path, capsys):
    """Guide upgrades use the same ownership proof as registry rules."""
    from pactkit.deploy_manifest import pactkit_owned_files
    from pactkit.generators.deployer import _deploy_guides
    from pactkit.prompts.guides import GUIDES_DIR

    destination = tmp_path / "skills" / "_rules" / GUIDES_DIR / "caching.md"
    destination.parent.mkdir(parents=True)
    original = "# local caching policy\n"
    destination.write_text(original, encoding="utf-8")
    expected = hashlib.sha256(b"# prior managed caching guide\n").hexdigest()
    relative = destination.relative_to(tmp_path).as_posix()
    (tmp_path / ".pactkit-deployed.json").write_text(json.dumps({
        "files": {relative: expected},
    }), encoding="utf-8")

    _deploy_guides(tmp_path)

    assert destination.read_text(encoding="utf-8") == original
    assert destination.with_suffix(".md.pactkit-new").is_file()
    assert relative not in pactkit_owned_files(
        tmp_path, {"skills": [], "portable_methods": [], "commands": [], "agents": []},
    )
    assert "preserved user-modified PactKit guide" in capsys.readouterr().out


def test_untracked_same_named_guide_is_not_overwritten(tmp_path):
    """A pre-existing guide path is user-owned until a manifest proves otherwise."""
    from pactkit.generators.deployer import _deploy_guides
    from pactkit.prompts.guides import GUIDES_DIR

    destination = tmp_path / "skills" / "_rules" / GUIDES_DIR / "resilience.md"
    destination.parent.mkdir(parents=True)
    original = "# user resilience guide\n"
    destination.write_text(original, encoding="utf-8")

    _deploy_guides(tmp_path)

    assert destination.read_text(encoding="utf-8") == original
    assert destination.with_suffix(".md.pactkit-new").is_file()


class TestCapsuleComplianceCriteria:
    """Capsule-only rules must carry verifiable completion criteria.

    A capsule whose legacy_ids claim absorption of an older rule must contain
    that rule's decision semantics. Regression: shared-execution claimed
    legacy 02-hierarchy-of-truth but carried none of its content, and
    capability-design collapsed the legacy solution protocol's assessment
    matrix and output format into a single uncheckable sentence.
    """

    def test_shared_execution_defines_hierarchy_of_truth(self):
        from pactkit.prompts.rules import SHARED_RULES

        capsule = SHARED_RULES["shared-execution"]
        text = capsule.lower()
        assert "tier 1" in text
        assert "tier 2" in text
        assert "tier 3" in text
        # Conflict resolution is actionable, not just naming the tiers.
        assert "takes precedence" in text or "higher tier wins" in text
        # The Spec-is-wrong path is stated.
        assert "fix the spec first" in text

    def test_capability_design_names_procedure_artifact_and_skip(self):
        from pactkit.prompts.rules import SHARED_RULES

        capsule = SHARED_RULES["capability-design"]
        text = capsule.lower()
        # Procedure: dependency scan with per-capability source decision.
        assert "dependency" in text
        assert "framework native" in text
        assert "project wrapper" in text
        # Verifiable output artifact with a shape and a destination.
        assert "need" in text and "source" in text and "decision" in text
        assert "technical design" in text
        # Skip condition and the no-bypass constraint survive from legacy.
        assert "skip" in text
        assert "bypass" in text
