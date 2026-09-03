"""Acceptance tests for STORY-slim-202608268fc379dbe6ef."""

def test_runtime_uses_atomic_clauses_and_is_not_a_monolithic_hard_gate():
    from pactkit.prompts.rules import RULE_CLAUSES, RULE_DEFINITIONS

    runtime = RULE_DEFINITIONS["runtime"]
    assert runtime.level != "hard"
    assert runtime.failure != "block_action"
    hard = [clause for clause in RULE_CLAUSES.values() if clause.level == "hard"]
    assert hard
    assert all(clause.failure == "block_exact_action" for clause in hard)
    assert {clause.id for clause in hard} == {
        "safety.credentials",
        "safety.authorization",
        "safety.irreversible-damage",
    }
    for clause in RULE_CLAUSES.values():
        assert clause.trigger and clause.evidence and clause.override
        assert "active instruction artifact" not in " ".join(clause.evidence)


def test_all_workflow_commands_have_complete_phase_contracts():
    from pactkit.prompts.rules import COMMAND_RULES_MAP, PHASE_CONTRACTS

    assert set(PHASE_CONTRACTS) == set(COMMAND_RULES_MAP)
    for command, contract in PHASE_CONTRACTS.items():
        assert contract.entry, command
        assert contract.inputs, command
        assert contract.outputs, command
        assert contract.invariants, command
        assert contract.completion_evidence, command
        assert contract.failure_semantics == "incomplete_continue", command
        assert set(contract.allowed_next) <= set(PHASE_CONTRACTS), command
        rendered = contract.render()
        assert len(rendered.splitlines()) <= 40
        for forbidden in ("pactkit ", "pytest", "model:", "TeamCreate"):
            assert forbidden not in rendered


def test_sprint_static_rules_only_load_orchestration_dependencies():
    from pactkit.prompts.rules import COMMAND_RULES_MAP, SPRINT_PHASE_SEQUENCE

    rules = COMMAND_RULES_MAP["project-sprint"]
    assert "sprint-orchestrator" in rules
    assert not set(SPRINT_PHASE_SEQUENCE) & set(rules)
    assert SPRINT_PHASE_SEQUENCE == (
        "phase-plan", "phase-act", "phase-check", "phase-done"
    )


def test_risk_router_uses_structured_evidence_and_caps_guides():
    from pactkit.risk_profile import build_change_risk_profile

    migration = build_change_risk_profile(
        "Move the deployment manifest schema and preserve old config",
        changed_paths=("src/pactkit/deploy_manifest.py",),
    )
    assert migration.decisions["public-api-schema"].level in {"medium", "high"}
    assert migration.decisions["data-migration"].reason
    assert 0 < len(migration.selected_guides) <= 3
    assert "backwards-compatibility.md" in migration.selected_guides

    docs = build_change_risk_profile(
        "Document the word database without changing behavior",
        changed_paths=("docs/guide.md",),
    )
    assert docs.selected_guides == ()


def test_scope_integrity_and_evidence_freshness_are_non_blocking():
    from pactkit.delivery_evidence import assess_evidence_freshness, assess_scope_integrity

    scope = assess_scope_integrity(
        expected=("src/pactkit/prompts/",),
        changed=("src/pactkit/prompts/rules.py", "pyproject.toml"),
    )
    assert scope.completion_ready is False
    assert scope.can_continue is True
    assert scope.unexpected == ("pyproject.toml",)

    fresh = assess_evidence_freshness(
        evidence_inputs={"src/a.py": "abc"},
        current_inputs={"src/a.py": "abc"},
    )
    stale = assess_evidence_freshness(
        evidence_inputs={"src/a.py": "abc"},
        current_inputs={"src/a.py": "changed"},
    )
    assert fresh.reusable is True
    assert stale.reusable is False
    assert stale.changed_inputs == ("src/a.py",)


def test_test_adequacy_requires_behavior_without_blocking_safe_repair():
    from pactkit.delivery_evidence import assess_test_adequacy

    weak = assess_test_adequacy(
        behavior_assertions=False,
        defect_reproduced=False,
        boundary_or_failure_paths=False,
        mocks_cross_core_boundary=True,
        negative_control_fails=False,
    )
    assert weak.completion_ready is False
    assert weak.can_continue is True
    assert len(weak.gaps) == 5

    adequate = assess_test_adequacy(
        behavior_assertions=True,
        defect_reproduced=True,
        boundary_or_failure_paths=True,
        negative_control_fails=True,
    )
    assert adequate.completion_ready is True
    assert adequate.gaps == ()


def test_guides_are_native_seven_section_documents():
    import inspect
    from pactkit.prompts import guides

    assert len(guides.GUIDE_DEFINITIONS) == 23
    required = (
        "## Trigger", "## Questions", "## Safe Invariants",
        "## Defaults", "## Alternatives", "## Evidence",
        "## Non-applicable",
    )
    for filename, content in guides.GUIDES_FILES.items():
        assert all(section in content for section in required), filename
    source = inspect.getsource(guides)
    assert "def _risk_driven_content" not in source
    assert "content.replace(\"## MUST\"" not in source
    assert {
        "operational-readiness.md",
        "dependency-supply-chain.md",
        "ui-state-accessibility.md",
    } <= set(guides.GUIDE_DEFINITIONS)


def test_preflight_ignores_nested_host_worktrees(tmp_path):
    from pactkit.spec_preflight import run_spec_preflight

    root = tmp_path
    (root / "src").mkdir()
    (root / "src" / "target.py").write_text("VALUE = 1\n")
    shadow = root / ".claude" / "worktrees" / "old" / "src"
    shadow.mkdir(parents=True)
    (shadow / "target.py").write_text("VALUE = 0\n")
    spec = root / "docs" / "specs" / "STORY-x-1.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("# Spec\n\nUse `target.py`.\n")

    result = run_spec_preflight(root, spec)

    assert result.receipt["inputs"][0]["path"] == "src/target.py"


def test_rule_resolution_is_explainable_non_mutating_and_phase_bounded():
    from pactkit.doctor import resolve_rule_context

    result = resolve_rule_context(
        "project-sprint",
        active_phase="act",
        selected_guides=("testing-strategy.md",),
        host_format="codex",
    )
    assert result["active_phase"] == "act"
    assert {item["id"] for item in result["loaded"]} >= {
        "runtime", "sprint-orchestrator",
    }
    assert not {
        "phase-plan", "phase-act", "phase-check", "phase-done",
    } & {item["id"] for item in result["loaded"]}
    assert result["guides"][0]["id"] == "testing-strategy.md"
    assert "latest user instruction" in result["precedence"]
    assert not any("Sprint statically" in warning for warning in result["warnings"])
