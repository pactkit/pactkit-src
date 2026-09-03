"""Tests for STORY-slim-2026090301691dea72e8: 规则遵循率实证修复.

Covers:
- R1: W012 capability-assessment lint gate (trigger / no false positive /
  non-blocking)
- R2: plan playbook domain-material declaration step
- R3: check contract setup-alignment + environment-provenance semantics,
  done contract evidence, check playbook anti-pattern + provenance step
- R4: check contract defect-class sweep invariant + playbook step
- R5: adapter parity via _render_prompt across FORMAT_PROFILES

Evidence base (2026-09-03 transcript analysis): Capability Assessment
produced 1 time in 56 /project-plan runs; highest-frequency user
correction class was "didn't read project domain material"; three
verification-setup falsifications (admin-tested business permissions,
claimed-test-without-artifacts, stale-process test runs).
"""

from pathlib import Path

from pactkit.skills.spec_linter import validate_spec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def write_spec(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "TEST-001.md"
    p.write_text(content, encoding="utf-8")
    return p


_TD_SPEC_TEMPLATE = """\
# STORY-001: Some Title

| Field     | Value |
|-----------|-------|
| ID        | STORY-001 |
| Status    | Draft |
| Priority  | High |
| Release   | 1.4.0 |

## Background

Some background text.

## Technical Design

{tech_design}

### Lateral Scan Results

- Reuse existing.

## Target Call Chain

Some call chain.

## Requirements

### R1: First Requirement (MUST)

This requirement MUST be satisfied.

## Acceptance Criteria

### AC1: Happy Path (R1)
**Given** a valid input
**When** R1 action is taken
**Then** the result is correct

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Test only |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | None |
| Touches | `tests/` |
| Conflict risk | LOW |

## Out of Scope

- Not in scope.
"""


def _spec_with_tech_design(tech_design: str) -> str:
    return _TD_SPEC_TEMPLATE.format(tech_design=tech_design)


def _rule_ids(result, level: str) -> set[str]:
    return {issue.rule_id for issue in getattr(result, level)}


# ---------------------------------------------------------------------------
# R1: W012 capability-assessment gate
# ---------------------------------------------------------------------------

class TestW012CapabilityAssessment:
    def test_w012_fires_on_dependency_signal_without_subsection(self, tmp_path):
        """Technical Design mentions pyproject.toml but has no Capability
        Assessment subsection → W012 warning, non-blocking."""
        spec = write_spec(
            tmp_path,
            _spec_with_tech_design("Uses pyproject.toml to declare dependencies."),
        )
        result = validate_spec(str(spec))
        assert "W012" in _rule_ids(result, "warnings")
        assert result.passed is True  # W-level never blocks

    def test_w012_case_insensitive_framework_signal(self, tmp_path):
        spec = write_spec(
            tmp_path,
            _spec_with_tech_design("Built on the FastAPI Framework."),
        )
        result = validate_spec(str(spec))
        assert "W012" in _rule_ids(result, "warnings")

    def test_w012_silent_without_dependency_signal(self, tmp_path):
        # NOTE: negation sentences ("no frameworks involved") still contain
        # the keyword and intentionally fire — keyword gates cannot parse
        # negation, which is exactly why this is a W rule, not an E rule.
        spec = write_spec(
            tmp_path,
            _spec_with_tech_design("Pure internal logic, stdlib only."),
        )
        result = validate_spec(str(spec))
        assert "W012" not in _rule_ids(result, "warnings")

    def test_w012_silent_when_subsection_present(self, tmp_path):
        spec = write_spec(
            tmp_path,
            _spec_with_tech_design(
                "Uses go.mod.\n\n### Capability Assessment\n\n| Need | Source | Decision |\n"
            ),
        )
        result = validate_spec(str(spec))
        assert "W012" not in _rule_ids(result, "warnings")

    def test_w012_silent_without_technical_design_section(self, tmp_path):
        spec = write_spec(tmp_path, _TD_SPEC_TEMPLATE.replace(
            "## Technical Design\n\n{tech_design}\n\n### Lateral Scan Results\n\n- Reuse existing.\n\n",
            "",
        ))
        result = validate_spec(str(spec))
        assert "W012" not in _rule_ids(result, "warnings")


# ---------------------------------------------------------------------------
# R3/R4: check + done contract verification semantics
# ---------------------------------------------------------------------------

class TestCheckContractVerificationSemantics:
    def test_check_invariants_carry_three_semantics(self):
        from pactkit.prompts.rules import PHASE_CONTRACTS

        invariants = PHASE_CONTRACTS["project-check"].invariants
        joined = " ".join(invariants).lower()
        assert "actor" in joined, "setup-alignment semantics missing"
        assert "provenance" in joined or "running code" in joined, (
            "environment-provenance semantics missing"
        )
        assert "sweeps its class" in joined, "defect-class sweep missing"

    def test_check_completion_evidence_requires_provenance(self):
        from pactkit.prompts.rules import PHASE_CONTRACTS

        evidence = PHASE_CONTRACTS["project-check"].completion_evidence
        joined = " ".join(evidence).lower()
        assert "provenance" in joined

    def test_done_evidence_adequate_covers_actor_and_environment(self):
        from pactkit.prompts.rules import PHASE_CONTRACTS

        evidence = PHASE_CONTRACTS["project-done"].completion_evidence
        joined = " ".join(evidence).lower()
        assert "actor" in joined
        assert "environment" in joined or "provenance" in joined

    def test_rendered_phase_check_contract_contains_semantics(self):
        from pactkit.prompts.rules import PHASE_RULE_CONTENTS

        rendered = PHASE_RULE_CONTENTS["phase-check"]
        assert "actor" in rendered.lower()
        assert "provenance" in rendered.lower() or "running code" in rendered.lower()
        assert "sweeps its class" in rendered.lower()


# ---------------------------------------------------------------------------
# R2/R3/R4: playbook steps
# ---------------------------------------------------------------------------

class TestPlaybookSteps:
    def test_plan_playbook_requires_domain_material_declaration(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        plan = COMMANDS_CONTENT["project-plan.md"]
        text = plan.lower()
        assert "implementation inputs" in text
        assert "domain material" in text

    def test_check_playbook_phase2_has_defect_class_sweep(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        check = COMMANDS_CONTENT["project-check.md"].lower()
        assert "sweep" in check

    def test_check_playbook_phase35_has_setup_actor_mismatch(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        check = COMMANDS_CONTENT["project-check.md"].lower()
        assert "actor" in check
        assert "mismatch" in check

    def test_check_playbook_phase4_has_environment_provenance(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        check = COMMANDS_CONTENT["project-check.md"].lower()
        assert "provenance" in check


# ---------------------------------------------------------------------------
# R5: adapter parity — the new semantics survive rendering per format
# ---------------------------------------------------------------------------

class TestAdapterParity:
    def test_check_semantics_render_identically_across_formats(self):
        from pactkit.generators.deployer import _render_prompt
        from pactkit.profiles import FORMAT_PROFILES
        from pactkit.prompts.commands import COMMANDS_CONTENT

        template = COMMANDS_CONTENT["project-check.md"]
        for name, profile in FORMAT_PROFILES.items():
            rendered = _render_prompt(template, profile)
            lowered = rendered.lower()
            assert "sweep" in lowered, f"sweep missing in {name}"
            assert "mismatch" in lowered, f"mismatch missing in {name}"
            assert "provenance" in lowered, f"provenance missing in {name}"

    def test_plan_domain_step_renders_across_formats(self):
        from pactkit.generators.deployer import _render_prompt
        from pactkit.profiles import FORMAT_PROFILES
        from pactkit.prompts.commands import COMMANDS_CONTENT

        template = COMMANDS_CONTENT["project-plan.md"]
        for name, profile in FORMAT_PROFILES.items():
            rendered = _render_prompt(template, profile)
            assert "domain material" in rendered.lower(), (
                f"domain-material step missing in {name}"
            )
