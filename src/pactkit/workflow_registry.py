"""Execution reliability registry for every deployed PactKit entry point."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from pactkit.workflow_validators import act_validator, plan_validator


class WorkflowValidator(Protocol):
    def validate(self, state: dict, step: str, evidence: dict, status: str) -> None: ...
    def fingerprints(self, state: dict) -> dict[str, str]: ...

ValidatorFactory = Callable[[Path], WorkflowValidator]


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    steps: tuple[str, ...]
    validator_factory: ValidatorFactory


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

WORKFLOW_REGISTRY = {
    "project-act": WorkflowDefinition("project-act", ACT_STEPS, act_validator),
    "project-plan": WorkflowDefinition("project-plan", PLAN_STEPS, plan_validator),
}

_COMMAND_CONTRACTS = {
    "project-plan": ("long_local_write", "verified_resume", "full", ()),
    "project-act": ("long_local_write", "verified_resume", "full", ()),
    "project-check": ("long_verification", "replay", "not_persisted", ()),
    "project-done": ("git_archive_write", "manual_confirmation", "not_persisted", ("commit", "archive")),
    "project-init": ("create_only", "idempotent_local_write", "not_persisted", ()),
    "project-sprint": ("orchestrator", "manual_confirmation", "not_persisted", ()),
    "project-hotfix": ("short_local_write", "idempotent_local_write", "not_persisted", ()),
    "project-design": ("multi_spec_write", "manual_confirmation", "not_persisted", ()),
    "project-clarify": ("interactive_analysis", "replay", "not_persisted", ()),
    "project-release": ("high_side_effect", "manual_confirmation", "not_persisted", ("tag", "publish", "release")),
    "project-pr": ("external_write", "manual_confirmation", "not_persisted", ("push", "pull_request")),
    "project-debug": ("hypothesis_analysis", "replay", "not_persisted", ()),
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
        name: ReliabilityContract(name, "command", category, recovery, persistence, manual_operations=manual)
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
