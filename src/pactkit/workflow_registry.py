"""Execution reliability registry for every deployed PactKit entry point."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol

from pactkit.workflow_validators import (
    act_validator,
    plan_validator,
    project_command_validator,
)


class WorkflowValidator(Protocol):
    def validate(self, state: dict, step: str, evidence: dict, status: str) -> None: ...
    def fingerprints(self, state: dict) -> dict[str, str]: ...

ValidatorFactory = Callable[[Path], WorkflowValidator]


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    steps: tuple[str, ...]
    validator_factory: ValidatorFactory
    managed_operations: Mapping[str, tuple[str, ...]]
    start_evidence_requirements: tuple[str, ...] = ()
    completion_evidence_requirements: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReliabilityContract:
    name: str
    entry_type: str
    category: str
    recovery: str
    persistence: str = "not_persisted"
    completion: str = "declared"
    manual_operations: tuple[str, ...] = ()


ACT_STEPS = ("preflight", "red", "green", "regression_lint", "sync_coverage")
PLAN_STEPS = (
    "preflight", "intent_clarified", "archaeology", "story_identified",
    "spec_scaffolded", "requirements_written", "acceptance_written",
    "security_scoped", "spec_linted", "board_synced",
)
COMMAND_STEPS = {
    "project-check": ("started", "security_scanned", "quality_scanned", "completed"),
    "project-done": ("started", "audited", "governance_synced", "completed"),
    "project-init": ("started", "configured", "governance_created", "completed"),
    "project-sprint": ("started", "planned", "executed", "completed"),
    "project-hotfix": ("started", "registered", "verified", "completed"),
    "project-design": ("started", "prd_written", "stories_created", "completed"),
    "project-clarify": ("started", "questions_asked", "requirements_confirmed", "completed"),
    "project-release": ("started", "validated", "authorized", "completed"),
    "project-pr": ("started", "validated", "authorized", "completed"),
    "project-debug": ("started", "hypotheses_tested", "root_cause_found", "completed"),
}
COMMAND_COMPLETION_REQUIREMENTS = {
    "project-check": (
        "security_scan=pass", "quality_scan=pass", "spec_alignment=pass",
        "tests.exit_code=0",
    ),
    "project-done": (
        "audit=pass", "governance=pass", "deployment=pass",
        "git.commit=<HEAD sha>|git.mode=no_git",
    ),
    "project-init": (
        "guard=pass", "configuration_created=true", "governance_created=true",
    ),
    "project-sprint": (
        "planned=true", "executed=true", "cleanup=pass", "stories=<non-empty list>",
    ),
    "project-hotfix": (
        "traceability=true", "tests.exit_code=0", "lint=pass",
    ),
    "project-design": (
        "prd_created=true", "stories_created>0", "board_synced=true",
    ),
    "project-clarify": ("requirements_confirmed=true", "decision_count>0"),
    "project-release": (
        "version=<value>", "tag=<value>", "release=<url|local_only>",
    ),
    "project-pr": ("branch=<value>", "pull_request=<url|not_required>"),
    "project-debug": (
        "root_cause=<value>", "evidence=<non-empty list>", "next_action=<value>",
    ),
}

WORKFLOW_REGISTRY = {
    "project-act": WorkflowDefinition(
        "project-act", ACT_STEPS, act_validator,
        {
            "red": ("create_test",),
            "green": ("write_source",),
            "regression_lint": ("write_source",),
            "sync_coverage": ("update_story", "update_board"),
        },
        ("spec_lint=pass", "graph_provider=<pactkit query decision>"),
    ),
    "project-plan": WorkflowDefinition(
        "project-plan", PLAN_STEPS, plan_validator,
        {
            "story_identified": ("create_spec", "create_story"),
            "spec_scaffolded": ("write_spec",),
            "requirements_written": ("write_spec",),
            "acceptance_written": ("write_spec",),
            "security_scoped": ("write_spec",),
            "spec_linted": ("create_story", "update_story", "update_board"),
        },
        ("guard=pass", "input_fingerprint=<sha256>"),
    ),
    **{
        name: WorkflowDefinition(
            name, steps, project_command_validator, {}, ("started=true",),
            COMMAND_COMPLETION_REQUIREMENTS[name],
        )
        for name, steps in COMMAND_STEPS.items()
    },
}

_COMMAND_CONTRACTS = {
    "project-plan": ("long_local_write", "verified_resume", "full", ()),
    "project-act": ("long_local_write", "verified_resume", "full", ()),
    "project-check": ("long_verification", "replay", "full", ()),
    "project-done": ("git_archive_write", "manual_confirmation", "full", ("commit", "archive")),
    "project-init": ("create_only", "idempotent_local_write", "full", ()),
    "project-sprint": ("orchestrator", "manual_confirmation", "full", ()),
    "project-hotfix": ("short_local_write", "idempotent_local_write", "full", ()),
    "project-design": ("multi_spec_write", "manual_confirmation", "full", ()),
    "project-clarify": ("interactive_analysis", "replay", "full", ()),
    "project-release": ("high_side_effect", "manual_confirmation", "full", ("tag", "publish", "release")),
    "project-pr": ("external_write", "manual_confirmation", "full", ("push", "pull_request")),
    "project-debug": ("hypothesis_analysis", "replay", "full", ()),
}

_SKILL_CONTRACTS = {
    "pactkit-visualize": ("derived_replayable", "replay"),
    "pactkit-board": ("local_write", "idempotent_local_write"),
    "pactkit-scaffold": ("create_only", "manual_confirmation"),
    "pactkit-report": ("derived_replayable", "replay"),
    "pactkit-trace": ("read_only", "replay"),
    "pactkit-draw": ("user_owned_write", "manual_confirmation"),
    "pactkit-status": ("read_only", "replay"),
    "pactkit-doctor": ("read_only", "replay"),
    "pactkit-garden": ("read_only", "replay"),
    "pactkit-review": ("external_read", "replay"),
    "pactkit-release": ("high_side_effect", "manual_confirmation"),
    "pactkit-analyze": ("read_only", "replay"),
    "pactkit-audit": ("derived_replayable", "replay"),
}

EXECUTION_RELIABILITY_REGISTRY = {
    **{
        name: ReliabilityContract(
            name, "command", category, recovery, persistence,
            completion="validated", manual_operations=manual,
        )
        for name, (category, recovery, persistence, manual) in _COMMAND_CONTRACTS.items()
    },
    **{
        name: ReliabilityContract(name, "skill", category, recovery)
        for name, (category, recovery) in _SKILL_CONTRACTS.items()
    },
}


def get_workflow(name: str) -> WorkflowDefinition:
    try:
        return WORKFLOW_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unknown workflow: {name}") from exc


def validate_registry() -> list[str]:
    from pactkit.config import VALID_COMMANDS
    from pactkit.prompts.commands import COMMANDS_CONTENT
    from pactkit.prompts.skills import SKILL_MANIFEST

    command_templates = {name.removesuffix(".md") for name in COMMANDS_CONTENT}
    skills = {entry["name"] for entry in SKILL_MANIFEST}
    expected = set(VALID_COMMANDS) | skills
    errors = []
    if command_templates != set(VALID_COMMANDS):
        errors.append("command template registry differs from VALID_COMMANDS")
    missing = expected - set(EXECUTION_RELIABILITY_REGISTRY)
    extra = set(EXECUTION_RELIABILITY_REGISTRY) - expected
    if missing:
        errors.append("missing reliability contracts: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("unknown reliability contracts: " + ", ".join(sorted(extra)))
    return errors
