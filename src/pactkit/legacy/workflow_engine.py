"""
FROZEN legacy module (STORY-slim-20260826cb37edfdd4da): no new
features, bugfix-only. Deletion candidate gated on one release
cycle of zero explicit invocations. Moved verbatim; public import
path preserved via the compatibility alias shim.

Core-owned, host-neutral WorkUnit execution protocol."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import math
import re
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from pactkit.protocols import CORE_PROTOCOL_VERSION  # noqa: E402
from pactkit.utils import atomic_write

RUN_SCHEMA_VERSION = 3
RECEIPT_SCHEMA_VERSION = 1
DEFAULT_LEASE_SECONDS = 300
ATTEMPT_TERMINALS = frozenset({
    "succeeded", "rejected", "interrupted", "host_error",
    "malformed_result", "awaiting_approval",
})
_MALFORMED_RECEIPT_DIGEST = "malformed:malformed_receipt"
_UNSET = object()
_RUN_ID_PATTERN = re.compile(r"run-[0-9a-f]{32}")
_UNIT_ID_PATTERN = re.compile(r"unit-[0-9a-f]{32}")
_STORY_ID_PATTERN = re.compile(r"STORY-[A-Za-z0-9-]+")


class WorkUnitError(ValueError):
    """A WorkUnit transition is invalid or unsafe."""


class ProtocolError(ValueError):
    """Core and adapter cannot negotiate a compatible protocol."""


class ExecutionMode(str, Enum):
    PORTABLE = "portable"
    GUIDED = "guided"
    RESUMABLE = "resumable"
    MANAGED = "managed"


@dataclass(frozen=True)
class HostCapabilities:
    host: str
    protocol_version: int = CORE_PROTOCOL_VERSION
    discovery_source: str = "adapter_manifest"
    instructions_discovery: bool = True
    skills_discovery: bool = True
    native_commands: bool = False
    structured_results: bool = False
    tool_execution: bool = False
    approval: bool = False
    lifecycle_events: bool = False
    thread_resume: bool = False
    turn_steer: bool = False
    background_execution: bool = False
    cancellation: bool = False
    e2e_validated: bool = False


def select_execution_mode(capabilities: HostCapabilities) -> ExecutionMode:
    """Return the strongest proven mode; incompatible versions fail closed."""
    if (
        isinstance(capabilities.protocol_version, bool)
        or not isinstance(capabilities.protocol_version, int)
        or capabilities.protocol_version != CORE_PROTOCOL_VERSION
    ):
        raise ProtocolError("protocol_version_mismatch")
    managed = (
        capabilities.structured_results
        and capabilities.tool_execution
        and capabilities.lifecycle_events
        and capabilities.thread_resume
        and capabilities.turn_steer
        and capabilities.background_execution
        and capabilities.cancellation
        and capabilities.e2e_validated
    )
    if managed:
        return ExecutionMode.MANAGED
    # A declared resume API is not evidence that it works against this Core
    # version.  Reporting resumable before an end-to-end probe would turn a
    # capability claim into a false delivery guarantee.
    if capabilities.tool_execution and capabilities.thread_resume and capabilities.e2e_validated:
        return ExecutionMode.RESUMABLE
    if capabilities.tool_execution:
        return ExecutionMode.GUIDED
    return ExecutionMode.PORTABLE


@dataclass(frozen=True)
class WorkUnitTemplate:
    step_id: str
    objective: str
    allowed_reads: tuple[str, ...]
    allowed_writes: tuple[str, ...]
    forbidden_operations: tuple[str, ...]
    acceptance_commands: tuple[str, ...]
    manual_authorization: tuple[str, ...] = ()
    required_claims: tuple[str, ...] = ()


PLAN_WORK_UNITS = (
    WorkUnitTemplate("preflight", "Verify project governance", (".pactkit/**",), (),
                     ("external_write",), ("pactkit guard",), (),
                     ('guard must equal "pass" after pactkit guard exits 0',)),
    WorkUnitTemplate("clarification", "Resolve material ambiguity", ("docs/product/**",), (),
                     ("write_source", "external_write"), ("receipt:clarification",), (),
                     ("clarification_resolved must equal true",)),
    WorkUnitTemplate("archaeology", "Trace the affected architecture", ("src/**", "docs/**"), (),
                     ("write_source", "external_write"), ("pactkit query --explore",), (),
                     ("trace must be a non-empty array of non-empty strings",)),
    WorkUnitTemplate("story_identity", "Allocate and bind one Story identity", ("docs/specs/**",), (),
                     ("write_source", "external_write"), ("pactkit generate-id",), (),
                     ("story_id must equal the newly allocated Story ID",)),
    WorkUnitTemplate("spec_scaffold", "Create the Story Spec scaffold", ("docs/specs/**",),
                     ("docs/specs/{story_id}.md",), ("update_board", "external_write"),
                     ("test -f docs/specs/{story_id}.md",)),
    WorkUnitTemplate("spec_content", "Write requirements and acceptance criteria", ("docs/**", "src/**"),
                     ("docs/specs/{story_id}.md", "docs/architecture/graphs/system_design.mmd"),
                     ("update_board", "external_write"), ("receipt:requirements", "receipt:acceptance"), (),
                     ("evidence_files must exactly equal allowed_writes",
                      "system_design.mmd must contain a valid Mermaid graph or flowchart")),
    WorkUnitTemplate("spec_security", "Complete security and dependency scope", ("docs/**",),
                     ("docs/specs/{story_id}.md",), ("update_board", "external_write"),
                     ("receipt:security_scope",), (),
                     ("security_scoped must equal true",)),
    WorkUnitTemplate("spec_lint", "Validate the completed Spec", ("docs/specs/**",),
                     ("docs/specs/{story_id}.md",), ("update_board", "external_write"),
                     ("pactkit spec-lint docs/specs/{story_id}.md",), (),
                     ("remove every scaffold placeholder and make spec-lint pass",
                      "evidence_files must contain the completed Spec path")),
    WorkUnitTemplate("finalize_plan", "Atomically publish Plan governance facts", ("docs/**", ".pactkit/**"),
                     ("docs/product/stories/{story_id}.yaml", "docs/product/sprint_board.md",
                      ".pactkit/context.md"), ("external_write",), ("receipt:finalize_plan",), (),
                     ("return non-empty story_id, title, and tasks for Core finalization",
                      "do not invoke finalize-plan or write final governance projections")),
)

ACT_WORK_UNITS = (
    WorkUnitTemplate("act_preflight", "Validate the bound Spec and locate the change",
                     ("docs/specs/{story_id}.md", "src/**", "tests/**"), (),
                     ("write_source", "external_write"), ("pactkit spec-lint docs/specs/{story_id}.md",), (),
                     ("spec_lint must equal pass", "trace must be non-empty")),
    WorkUnitTemplate("red", "Create focused tests and prove they fail",
                     ("docs/specs/{story_id}.md", "src/**", "tests/**"), ("tests/**",),
                     ("write_source", "external_write"), ("receipt:red_test",), (),
                     ("story_tests.exit_code must equal 1",)),
    WorkUnitTemplate("implementation", "Implement only the Spec-scoped change",
                     ("docs/specs/{story_id}.md", "src/**", "tests/**"), ("src/**", "tests/**"),
                     ("external_write",), ("receipt:implementation",), (),
                     ("changed_files must be a non-empty list",)),
    WorkUnitTemplate("story_tests", "Run focused Story tests to GREEN",
                     ("src/**", "tests/**"), (), ("write_source", "external_write"),
                     ("receipt:story_tests",), (), ("story_tests.exit_code must equal 0",)),
    WorkUnitTemplate("regression_lint", "Run regression and lint gates",
                     ("src/**", "tests/**", "docs/**"), (), ("write_source", "external_write"),
                     ("pactkit regression", "pactkit lint"), (),
                     ("regression must equal pass", "lint must equal pass")),
    WorkUnitTemplate("sync_coverage", "Synchronize derived artifacts and requirement coverage",
                     ("docs/**", "src/**", "tests/**"),
                     ("docs/architecture/graphs/**", "docs/e2e/journey.md"),
                     ("external_write",), ("receipt:coverage",), (),
                     ("coverage and acceptance_coverage must be complete",
                      "board_tasks must exactly match the canonical Story task titles")),
    WorkUnitTemplate("finalize_act", "Atomically record verified Act completion",
                     ("docs/**", "src/**", "tests/**", ".pactkit/**"), (),
                     ("external_write",), ("receipt:finalize_act",), (),
                     ("completed must equal true",)),
)

CHECK_WORK_UNITS = (
    WorkUnitTemplate("check_preflight", "Load the bound Spec and implementation",
                     ("docs/**", "src/**", "tests/**"), (), ("write_source", "external_write"),
                     ("pactkit spec-lint docs/specs/{story_id}.md",), (), ("spec_lint must equal pass",)),
    WorkUnitTemplate("security_scan", "Run the security review", ("docs/**", "src/**", "tests/**"), (),
                     ("write_source", "external_write"), ("receipt:security_scan",), (),
                     ("security_scan must equal pass",)),
    WorkUnitTemplate("quality_scan", "Run quality and lint review", ("docs/**", "src/**", "tests/**"), (),
                     ("write_source", "external_write"), ("receipt:quality_scan",), (),
                     ("quality_scan must equal pass",)),
    WorkUnitTemplate("spec_alignment", "Verify requirements and acceptance alignment",
                     ("docs/**", "src/**", "tests/**"), (), ("write_source", "external_write"),
                     ("receipt:spec_alignment",), (), ("spec_alignment must equal pass",)),
    WorkUnitTemplate("check_tests", "Run deterministic verification tests", ("src/**", "tests/**"), (),
                     ("write_source", "external_write"), ("receipt:tests",), (), ("tests.exit_code must equal 0",)),
    WorkUnitTemplate("finalize_check", "Record verified Check completion", ("docs/**", ".pactkit/**"), (),
                     ("external_write",), ("receipt:finalize_check",), (), ("completed must equal true",)),
)

DONE_WORK_UNITS = (
    WorkUnitTemplate("done_preflight", "Verify Check completion and repository state",
                     ("docs/**", "src/**", "tests/**", ".pactkit/**"), (),
                     ("write_source", "external_write"), ("receipt:done_preflight",), (),
                     ("check_complete must equal true",)),
    WorkUnitTemplate("governance_sync", "Synchronize Story, Board, context, and derived docs",
                     ("docs/**", ".pactkit/**"), ("docs/**", ".pactkit/context.md"),
                     ("write_source", "external_write"), ("receipt:governance",), (), ("governance must equal pass",)),
    WorkUnitTemplate("done_verify", "Verify audit and deployment health",
                     ("docs/**", "src/**", "tests/**", ".pactkit/**"), (),
                     ("write_source", "external_write"), ("receipt:done_verify",), (),
                     ("audit and deployment must equal pass",)),
    WorkUnitTemplate("commit", "Create the explicitly authorized local commit", ("**",), (),
                     ("push", "tag", "release"), ("git commit",), ("commit",),
                     ("git.commit must identify HEAD, or git.mode must equal no_git",)),
    WorkUnitTemplate("finalize_done", "Record verified Done completion", ("docs/**", ".pactkit/**"), (),
                     ("external_write",), ("receipt:finalize_done",), (), ("completed must equal true",)),
)

def _unit(
    step: str, objective: str, *, writes: tuple[str, ...] = (),
    manual: tuple[str, ...] = (), claims: tuple[str, ...] = (),
) -> WorkUnitTemplate:
    forbidden = () if writes else ("write_source", "external_write")
    return WorkUnitTemplate(
        step, objective, ("**",), writes, forbidden, (f"receipt:{step}",),
        manual, claims,
    )


def _terminal(workflow_id: str) -> WorkUnitTemplate:
    return _unit(
        "finalize_workflow", f"Record verified {workflow_id} completion",
        claims=("completed must equal true",),
    )


# ---------------------------------------------------------------------------
# Unified WorkUnit scope derivation (STORY-slim-20260824dd23a0ed3b4c)
#
# WorkUnit read/write scope is NOT a hardcoded directory whitelist. It is the
# union of the unit's frozen template floor + applicable project-declared
# write_scope roots + the Story's Touches (Tier-1 Spec law). Union — never
# intersection — so mutable config never clips Spec-declared surface. Runtime
# path-escape is still blocked by _safe_repo_path; pathological Touches are
# rejected at Plan time by spec_linter (R5).
# ---------------------------------------------------------------------------

# category -> pactkit.yaml write_scope key
_WRITE_SCOPE_CONFIG_KEYS = {
    "source": "source_roots",
    "test": "test_roots",
    "docs": "docs_roots",
}
_WRITE_SCOPE_ROOT_KEYS = tuple(_WRITE_SCOPE_CONFIG_KEYS)

# Per (workflow, step) config-root category selection for WRITES (Open-Closed:
# extend to add steps). absence ⇒ the step writes nothing extra (run-only /
# governance). Keyed by (workflow_id, step_id) so step_ids never collide across
# workflows.
_STEP_WRITE_CATEGORIES: dict[tuple[str, str], tuple[str, ...]] = {
    ("project-act", "red"): ("test",),                 # TDD: tests first, no source
    ("project-act", "implementation"): ("source", "test"),
    ("project-hotfix", "fix"): ("source", "test"),     # hotfix implementation
    ("project-act", "sync_coverage"): ("docs",),
    ("project-act", "finalize_act"): ("docs",),
}
# (workflow, step) pairs whose writes also include story.touches.
_STEP_TOUCHES_WRITES = frozenset({
    ("project-act", "implementation"),
    ("project-act", "red"),
    ("project-act", "sync_coverage"),
})


def _dedupe_scope(items):
    """Order-stable dedupe of an iterable into a tuple."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return tuple(out)


def _normalize_write_scope(ws) -> dict[str, list[str]]:
    """Normalize a write_scope mapping into {source, test, docs} root lists.

    Tolerates malformed input (non-list / non-string entries are filtered),
    matching validate_config's warn-never-raise contract. Accepts the
    pactkit.yaml shape (source_roots/test_roots/docs_roots).
    """
    out = {cat: [] for cat in _WRITE_SCOPE_ROOT_KEYS}
    if not isinstance(ws, dict):
        return out
    for cat, config_key in _WRITE_SCOPE_CONFIG_KEYS.items():
        roots = ws.get(config_key)
        if isinstance(roots, list):
            out[cat] = [r for r in roots if isinstance(r, str) and r]
    return out


def _load_write_scope(root: Path) -> dict[str, list[str]]:
    """Load the write_scope section from pactkit.yaml relative to *root*."""
    from pactkit.config import find_pactkit_yaml, load_config

    found = find_pactkit_yaml(root)
    raw = load_config(found) if found is not None else {}
    ws = raw.get("write_scope") if isinstance(raw, dict) else None
    return _normalize_write_scope(ws)


def _load_touches(root: Path, story_id: str | None) -> list[str]:
    """Return the Spec's Touches paths for *story_id* (empty if unbound/no spec)."""
    if not story_id:
        return []
    try:
        from pactkit.spec_graph import parse_story

        node = parse_story(root / "docs/specs" / f"{story_id}.md")
    except (OSError, ImportError, ValueError):
        return []
    return list(node.touches) if node is not None else []


def resolve_scope(
    workflow_id: str,
    step_id: str,
    story_id: str | None,
    root: Path,
    *,
    write_scope=None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (extra_reads, extra_writes) to union onto the unit template floor.

    Pure SSoT — called by WorkflowEngine.acquire for every workflow. Templates
    stay frozen; this layers project write_scope roots + Story touches on top.

    Args:
        workflow_id: workflow (project-act / project-hotfix / ...). Plan is
            excluded by the caller (it produces Touches, does not consume).
        step_id: the WorkUnit step (drives per-step category selection).
        story_id: bound Story ID (None ⇒ no touches).
        root: project root (for loading pactkit.yaml + the Spec).
        write_scope: inject the raw write_scope mapping (config shape) to
            bypass disk in tests; None ⇒ load from pactkit.yaml.

    Returns:
        (extra_reads, extra_writes) — deduped, order-stable. Reads always
        include all categories + touches; writes follow per-step selection.
    """
    ws = (
        _normalize_write_scope(write_scope)
        if write_scope is not None
        else _load_write_scope(root)
    )
    touches = _load_touches(root, story_id)

    write_cats = _STEP_WRITE_CATEGORIES.get((workflow_id, step_id), ())
    extra_writes: list[str] = []
    for cat in write_cats:
        extra_writes.extend(ws[cat])
    if (workflow_id, step_id) in _STEP_TOUCHES_WRITES:
        extra_writes.extend(touches)

    extra_reads: list[str] = []
    for cat in _WRITE_SCOPE_ROOT_KEYS:
        extra_reads.extend(ws[cat])
    extra_reads.extend(touches)

    return _dedupe_scope(extra_reads), _dedupe_scope(extra_writes)


OTHER_WORKFLOW_UNITS = {
    "project-init": (
        _unit("preflight", "Inspect an uninitialized project", claims=("ready must equal true",)),
        _unit("configure", "Create PactKit configuration", writes=(".codex/**", ".claude/**"),
              claims=("configuration_created must equal true",)),
        _unit("governance", "Create governance files", writes=("docs/**",),
              claims=("governance_created must equal true", "guard must equal pass")),
        _terminal("project-init"),
    ),
    "project-sprint": (
        _unit("preflight", "Select Sprint Stories", claims=("stories must be non-empty",)),
        _unit("plan_phase", "Complete or verify Plan for every Sprint Story",
              writes=("docs/**", ".pactkit/**"), manual=("orchestrate",),
              claims=("planned must equal true",)),
        _unit("act_phase", "Complete Act for every Sprint Story",
              writes=("src/**", "tests/**", "docs/**", ".pactkit/**"),
              manual=("orchestrate",), claims=("executed must equal true",)),
        _unit("check_phase", "Complete Check for every Sprint Story",
              manual=("orchestrate",), claims=("checked must equal true",)),
        _unit("done_phase", "Complete authorized Done operations",
              writes=("docs/**", ".pactkit/**"), manual=("orchestrate",), claims=("cleanup must equal pass",)),
        _terminal("project-sprint"),
    ),
    "project-hotfix": (
        _unit("preflight", "Register and trace the hotfix", writes=("docs/**",),
              claims=("traceability must equal true",)),
        _unit("fix", "Implement the bounded hotfix", writes=("src/**", "tests/**"),
              claims=("executed must equal true",)),
        _unit("verify", "Run hotfix tests and lint", claims=("tests.exit_code=0", "lint must equal pass")),
        _terminal("project-hotfix"),
    ),
    "project-design": (
        _unit("preflight", "Clarify product vision", claims=("ready must equal true",)),
        _unit("prd", "Create the product requirements document", writes=("docs/product/**",),
              claims=("prd_created must equal true",)),
        _unit("stories", "Create Specs and Story facts", writes=("docs/**",),
              claims=("stories_created must be positive", "board_synced must equal true")),
        _terminal("project-design"),
    ),
    "project-clarify": (
        _unit("preflight", "Identify material ambiguities", claims=("ready must equal true",)),
        _unit("decisions", "Resolve requirements with the user",
              claims=("requirements_confirmed must equal true", "decision_count must be positive")),
        _terminal("project-clarify"),
    ),
    "project-release": (
        _unit("preflight", "Validate release readiness", claims=("ready must equal true",)),
        _unit("prepare", "Prepare version and release artifacts", writes=("docs/**",),
              claims=("version and tag must be non-empty",)),
        _unit("publish", "Publish the explicitly authorized release", manual=("tag", "publish", "release"),
              claims=("release URL or local_only mode is required",)),
        _terminal("project-release"),
    ),
    "project-pr": (
        _unit("preflight", "Validate branch and PR readiness", claims=("ready must equal true",)),
        _unit("publish", "Push and open the explicitly authorized pull request",
              manual=("push", "pull_request"), claims=("branch and pull_request are required",)),
        _terminal("project-pr"),
    ),
    "project-debug": (
        _unit("preflight", "Capture symptoms and constraints", claims=("ready must equal true",)),
        _unit("hypotheses", "Test bounded root-cause hypotheses", claims=("evidence must be non-empty",)),
        _unit("diagnosis", "Establish root cause and next action",
              claims=("root_cause and next_action must be non-empty",)),
        _terminal("project-debug"),
    ),
}

WORKFLOW_UNITS = {
    "project-plan": PLAN_WORK_UNITS, "project-act": ACT_WORK_UNITS,
    "project-check": CHECK_WORK_UNITS, "project-done": DONE_WORK_UNITS,
    **OTHER_WORKFLOW_UNITS,
}


@dataclass(frozen=True)
class WorkflowRun:
    run_id: str
    workflow_id: str
    goal_digest: str
    story_id: str | None
    status: str
    current_index: int
    source_schema_version: int = RUN_SCHEMA_VERSION


@dataclass(frozen=True)
class WorkUnit:
    run_id: str
    unit_id: str
    workflow_id: str
    step_id: str
    version: int
    objective: str
    input_refs: tuple[str, ...]
    allowed_reads: tuple[str, ...]
    allowed_writes: tuple[str, ...]
    forbidden_operations: tuple[str, ...]
    acceptance_commands: tuple[str, ...]
    manual_authorization: tuple[str, ...]
    lease_owner: str
    lease_expires_at: float
    receipt_schema_version: int = RECEIPT_SCHEMA_VERSION
    required_claims: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceReceipt:
    schema_version: int
    unit_id: str
    unit_version: int
    owner: str
    claims: dict[str, Any] = field(default_factory=dict)
    file_fingerprints: dict[str, str] = field(default_factory=dict)
    result_refs: tuple[str, ...] = ()
    host: str | None = None
    capabilities: dict[str, Any] = field(default_factory=dict)
    session_ref: str | None = None
    thread_ref: str | None = None
    turn_ref: str | None = None
    adapter_version: str | None = None
    started_at: float | None = None

    @classmethod
    def for_files(
        cls, unit: WorkUnit, *, owner: str, root: Path, files: Iterable[str],
        claims: dict[str, Any] | None = None,
    ) -> EvidenceReceipt:
        fingerprints = {
            name: _fingerprint(_safe_repo_path(root, name)) for name in files
        }
        return cls(RECEIPT_SCHEMA_VERSION, unit.unit_id, unit.version, owner,
                   claims or {}, fingerprints)


@dataclass(frozen=True)
class SubmissionResult:
    attempt_id: str
    attempt_status: str
    workflow_status: str
    decision: str
    reason_code: str
    next_unit_id: str | None = None


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def _persisted_fingerprints(receipt_fingerprints: dict) -> dict[str, str]:
    """State fingerprints taken from the just-validated receipt.

    The receipt's digests were verified against disk by _validate_receipt
    under the same engine lock, so persisting them directly closes both the
    vanish window AND the modify window (a file rewritten between validation
    and persistence must not become the trusted baseline). The literal
    "missing" or any non-hex digest fails the submit explicitly instead of
    bricking the run — the state validator rejects it forever
    (STORY-slim-202608267c3989223b4d R1).
    """
    out: dict[str, str] = {}
    for name, digest in receipt_fingerprints.items():
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise WorkUnitError(
                f"artifact_vanished: evidence unavailable at validation: {name}"
            )
        out[name] = digest
    return out


def _safe_repo_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise WorkUnitError("invalid_evidence_path")
    resolved = (root.resolve() / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise WorkUnitError("invalid_evidence_path") from exc
    return resolved


def _opaque_ref(value: str | None) -> str | None:
    if value is None:
        return None
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def _receipt_digest(receipt: EvidenceReceipt) -> str:
    """Bind an idempotency key to exactly one immutable submit request."""
    payload = asdict(receipt)
    payload["result_refs"] = list(receipt.result_refs)
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _generic_finalize_request_digest(
    *, run_id: str, workflow_id: str, story_id: str | None,
    claims: dict[str, Any], fingerprints: dict[str, str],
) -> str:
    if not isinstance(claims, dict) or not _is_json_value(claims):
        raise WorkUnitError("invalid_finalize_request")
    _validate_fingerprint_map(fingerprints)
    return hashlib.sha256(json.dumps({
        "run_id": run_id, "workflow_id": workflow_id, "story_id": story_id,
        "claims": claims, "fingerprints": fingerprints,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _is_json_value(value: Any) -> bool:
    """Return whether a candidate value is safe to persist as JSON evidence."""
    if value is None or isinstance(value, (bool, int, str)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def _validate_identity(
    *, owner: Any = _UNSET, idempotency_key: Any = _UNSET,
) -> None:
    """Reject invalid actor and idempotency identities before state changes.

    Both values participate in durable Core state.  Validating them before a
    lock-protected transition prevents native string/JSON errors from leaving a
    Unit mutation without a matching durable idempotency record.
    """
    if owner is not _UNSET and (not isinstance(owner, str) or not owner):
        raise WorkUnitError("invalid_idempotency_identity")
    if idempotency_key is not _UNSET and (
        not isinstance(idempotency_key, str) or not idempotency_key
    ):
        raise WorkUnitError("invalid_idempotency_identity")


def _timestamp(value: Any | None) -> float:
    """Return a finite timestamp suitable for durable workflow state.

    JSON permits non-standard NaN and Infinity spellings by default, but they
    are not portable governance facts and make lease comparisons unreliable.
    """
    if value is None:
        return time.time()
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise WorkUnitError("invalid_timestamp")
    return float(value)


def _validate_workflow_start(
    *, workflow_id: Any, goal: Any, story_id: Any,
) -> None:
    if not isinstance(workflow_id, str) or not workflow_id:
        raise WorkUnitError("unknown_workflow")
    if not isinstance(goal, str) or not goal:
        raise WorkUnitError("invalid_workflow_goal")
    if story_id is not None:
        _validate_story_id(story_id)


def _validate_run_id(run_id: Any) -> None:
    if not isinstance(run_id, str) or _RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise WorkUnitError("invalid_run_id")


def _validate_unit_id(unit_id: Any) -> None:
    if not isinstance(unit_id, str) or _UNIT_ID_PATTERN.fullmatch(unit_id) is None:
        raise WorkUnitError("invalid_unit_id")


def _validate_story_id(story_id: Any) -> None:
    if not isinstance(story_id, str) or _STORY_ID_PATTERN.fullmatch(story_id) is None:
        raise WorkUnitError("invalid_story_id")


def _receipt_shape_reason(receipt: Any) -> str | None:
    """Validate untrusted Receipt shape before hashing or persisting it.

    Core must never let malformed adapter data escape as a Python exception:
    that would make the attempted execution neither auditable nor retryable.
    """
    if not isinstance(receipt, EvidenceReceipt):
        return "malformed_receipt"
    if isinstance(receipt.schema_version, bool) or not isinstance(receipt.schema_version, int):
        return "malformed_receipt"
    if not all(isinstance(value, str) and value for value in (receipt.unit_id, receipt.owner)):
        return "malformed_receipt"
    if isinstance(receipt.unit_version, bool) or not isinstance(receipt.unit_version, int):
        return "malformed_receipt"
    if not isinstance(receipt.claims, dict) or not _is_json_value(receipt.claims):
        return "malformed_receipt"
    if not isinstance(receipt.file_fingerprints, dict) or not all(
        isinstance(path, str) and path
        and isinstance(fingerprint, str)
        and re.fullmatch(r"[0-9a-f]{64}|missing", fingerprint)
        for path, fingerprint in receipt.file_fingerprints.items()
    ):
        return "malformed_receipt"
    if not isinstance(receipt.result_refs, tuple) or not all(
        isinstance(reference, str) and reference for reference in receipt.result_refs
    ):
        return "malformed_receipt"
    if not isinstance(receipt.capabilities, dict) or not _is_json_value(receipt.capabilities):
        return "malformed_receipt"
    if any(
        value is not None and (not isinstance(value, str) or not value)
        for value in (receipt.host, receipt.session_ref, receipt.thread_ref, receipt.turn_ref, receipt.adapter_version)
    ):
        return "malformed_receipt"
    if receipt.started_at is not None and (
        isinstance(receipt.started_at, bool)
        or not isinstance(receipt.started_at, (int, float))
        or not math.isfinite(receipt.started_at)
    ):
        return "malformed_receipt"
    return None


def _receipt_execution_mode(receipt: EvidenceReceipt) -> str | None:
    """Derive an auditable mode from a Receipt without trusting unknown keys."""
    if not receipt.capabilities:
        return None
    fields = HostCapabilities.__dataclass_fields__
    values = {
        name: value for name, value in receipt.capabilities.items()
        if name in fields and name != "host"
    }
    host = receipt.host or receipt.capabilities.get("host")
    if not isinstance(host, str) or not host:
        return None
    try:
        return select_execution_mode(HostCapabilities(host=host, **values)).value
    except (ProtocolError, TypeError, ValueError):
        return None


def _finalize_request_digest(
    *, run_id: str, story_id: str, title: str, tasks: list[str],
) -> str:
    """Return the stable identity of one finalize request.

    A finalize key is an at-most-once key, not an authorization to reuse the
    completed transaction with a different Story payload.
    """
    if not isinstance(title, str) or not title or (
        not isinstance(tasks, list)
        or not tasks
        or not all(isinstance(task, str) and task for task in tasks)
    ):
        raise WorkUnitError("invalid_finalize_request")
    payload = {
        "run_id": run_id,
        "story_id": story_id,
        "title": title,
        "tasks": tasks,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _attempt_metadata(
    *, host: str, session: str | None, thread: str | None, turn: str | None,
    result_refs: Iterable[str], failure_reason: str | None,
    started_at: float | None, adapter_version: str | None, now: float | None,
    capabilities: HostCapabilities | None,
) -> tuple[tuple[str, ...], float | None, float | None]:
    """Validate host-terminal audit values before changing Unit state.

    Attempt records are part of Core's durable governance evidence.  Invalid
    host metadata must fail closed before a failure terminal releases a lease,
    otherwise a serialization error can leave a state transition without its
    required audit fact.
    """
    if not isinstance(host, str) or not host:
        raise WorkUnitError("invalid_attempt_metadata")
    if any(
        value is not None and (not isinstance(value, str) or not value)
        for value in (session, thread, turn, failure_reason, adapter_version)
    ):
        raise WorkUnitError("invalid_attempt_metadata")
    if started_at is not None and (
        not isinstance(started_at, (int, float))
        or not float("-inf") < started_at < float("inf")
    ):
        raise WorkUnitError("invalid_attempt_metadata")
    if now is not None and (
        not isinstance(now, (int, float)) or not float("-inf") < now < float("inf")
    ):
        raise WorkUnitError("invalid_attempt_metadata")
    try:
        references = tuple(result_refs)
    except TypeError as exc:
        raise WorkUnitError("invalid_attempt_metadata") from exc
    if not all(isinstance(reference, str) and reference for reference in references):
        raise WorkUnitError("invalid_attempt_metadata")
    if capabilities is not None:
        if not isinstance(capabilities, HostCapabilities):
            raise WorkUnitError("invalid_attempt_metadata")
        values = asdict(capabilities)
        if (
            not isinstance(values["host"], str)
            or not values["host"]
            or not isinstance(values["protocol_version"], int)
            or not isinstance(values["discovery_source"], str)
            or not values["discovery_source"]
            or any(
                not isinstance(values[name], bool)
                for name in (
                    "instructions_discovery", "skills_discovery",
                    "native_commands", "structured_results", "tool_execution",
                    "approval", "lifecycle_events", "thread_resume",
                    "turn_steer", "background_execution", "cancellation",
                    "e2e_validated",
                )
            )
        ):
            raise WorkUnitError("invalid_attempt_metadata")
    return references, started_at, now


def _record_story_id(record: dict[str, Any]) -> str | None:
    """Extract the bound Story identity without trusting adapter claims."""
    for value in record.get("input_refs", ()):
        if isinstance(value, str) and value.startswith("STORY-"):
            return value
    return None


def _validate_work_unit_record(
    record: Any, *, unit_id: str, run_id: str, workflow_id: str,
) -> None:
    """Validate one durable Unit before scheduling or lease operations."""
    if not isinstance(record, dict):
        raise WorkUnitError("invalid_workflow_state")
    try:
        _validate_unit_id(unit_id)
        if (
            record.get("unit_id") != unit_id
            or record.get("run_id") != run_id
            or record.get("workflow_id") != workflow_id
            or record.get("step_id") not in {
                template.step_id for template in WORKFLOW_UNITS[workflow_id]
            }
            or not isinstance(record.get("objective"), str)
            or not record["objective"]
            or isinstance(record.get("version"), bool)
            or not isinstance(record.get("version"), int)
            or record["version"] <= 0
            or record.get("state") not in {"leased", "succeeded", "retry", "expired"}
            or not isinstance(record.get("lease_owner"), str)
            or not record["lease_owner"]
            or isinstance(record.get("lease_expires_at"), bool)
            or not isinstance(record.get("lease_expires_at"), (int, float))
            or not math.isfinite(record["lease_expires_at"])
            or isinstance(record.get("receipt_schema_version"), bool)
            or record.get("receipt_schema_version") != RECEIPT_SCHEMA_VERSION
        ):
            raise WorkUnitError("invalid_workflow_state")
        for name in (
            "input_refs", "allowed_reads", "allowed_writes",
            "forbidden_operations", "acceptance_commands", "manual_authorization",
        ):
            values = record[name]
            if not isinstance(values, (list, tuple)) or not all(
                isinstance(value, str) and value for value in values
            ):
                raise WorkUnitError("invalid_workflow_state")
        required_claims = record.get("required_claims", ())
        if not isinstance(required_claims, (list, tuple)) or not all(
            isinstance(value, str) and value for value in required_claims
        ):
            raise WorkUnitError("invalid_workflow_state")
        accepted_claims = record.get("accepted_claims")
        if accepted_claims is not None and (
            not isinstance(accepted_claims, dict) or not _is_json_value(accepted_claims)
        ):
            raise WorkUnitError("invalid_workflow_state")
    except (KeyError, TypeError) as exc:
        raise WorkUnitError("invalid_workflow_state") from exc


def _validate_attempt_record(attempt: Any, *, units: dict[str, Any]) -> None:
    """Validate durable host/receipt audit facts before replaying a run."""
    if not isinstance(attempt, dict):
        raise WorkUnitError("invalid_workflow_state")
    try:
        attempt_id = attempt["attempt_id"]
        unit_id = attempt["unit_id"]
        if (
            not isinstance(attempt_id, str)
            or re.fullmatch(r"attempt-[0-9a-f]{32}", attempt_id) is None
            or unit_id not in units
            or isinstance(attempt["unit_version"], bool)
            or not isinstance(attempt["unit_version"], int)
            or attempt["unit_version"] <= 0
            or attempt["status"] not in ATTEMPT_TERMINALS
            or attempt["decision"] not in {
                "execute_unit", "retry", "ignored", "done",
                "await_receipt", "await_approval",
            }
            or attempt.get("host") is not None
            and (not isinstance(attempt["host"], str) or not attempt["host"])
            or attempt.get("reason_code") is not None
            and (not isinstance(attempt["reason_code"], str) or not attempt["reason_code"])
            or attempt.get("adapter_version") is not None
            and (not isinstance(attempt["adapter_version"], str) or not attempt["adapter_version"])
            or attempt.get("execution_mode") not in {None, *(mode.value for mode in ExecutionMode)}
            or not isinstance(attempt["capabilities"], dict)
            or not _is_json_value(attempt["capabilities"])
            or not isinstance(attempt["result_refs"], list)
            or not all(isinstance(reference, str) and reference for reference in attempt["result_refs"])
        ):
            raise WorkUnitError("invalid_workflow_state")
        for name in ("session_ref", "thread_ref", "turn_ref"):
            value = attempt.get(name)
            if value is not None and (
                not isinstance(value, str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None
            ):
                raise WorkUnitError("invalid_workflow_state")
        evidence = attempt.get("file_fingerprints")
        if evidence is not None and (
            not isinstance(evidence, dict)
            or not all(
                isinstance(path, str)
                and path
                and not Path(path).is_absolute()
                and ".." not in Path(path).parts
                and isinstance(digest, str)
                and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
                for path, digest in evidence.items()
            )
        ):
            raise WorkUnitError("invalid_workflow_state")
        for name in ("started_at", "finished_at"):
            value = attempt[name]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise WorkUnitError("invalid_workflow_state")
        latency = attempt["latency_ms"]
        if isinstance(latency, bool) or not isinstance(latency, int) or latency < 0:
            raise WorkUnitError("invalid_workflow_state")
    except (KeyError, TypeError) as exc:
        raise WorkUnitError("invalid_workflow_state") from exc


def _validate_work_unit_snapshot(
    snapshot: Any, *, unit_id: str, run_id: str, workflow_id: str,
) -> None:
    """Validate an immutable acquire/retry response kept for replay."""
    if not isinstance(snapshot, dict):
        raise WorkUnitError("invalid_workflow_state")
    record = dict(snapshot)
    record["state"] = "leased"
    _validate_work_unit_record(
        record, unit_id=unit_id, run_id=run_id, workflow_id=workflow_id,
    )


def _validate_idempotency_record(
    key: Any, record: Any, *, run_id: str, workflow_id: str, goal_digest: str,
    units: dict[str, Any], attempts: list[Any],
) -> None:
    """Validate every durable replay record, including inactive keys.

    Idempotency entries influence future transition responses.  Validating only
    the key currently requested lets an unrelated corrupt entry survive a
    successful write, so recovery must inspect the whole map before use.
    """
    if not isinstance(key, str) or not key or not isinstance(record, dict):
        raise WorkUnitError("invalid_workflow_state")
    try:
        if key.startswith(("acquire:", "retry:")):
            suffix = key.split(":", 1)[1]
            if not suffix or set(record) != {"unit_id", "unit_version", "owner", "result"}:
                raise WorkUnitError("invalid_workflow_state")
            unit_id = record["unit_id"]
            _validate_unit_id(unit_id)
            if unit_id not in units:
                raise WorkUnitError("invalid_workflow_state")
            if (
                isinstance(record["unit_version"], bool)
                or not isinstance(record["unit_version"], int)
                or record["unit_version"] <= 0
            ):
                raise WorkUnitError("invalid_workflow_state")
            _validate_identity(owner=record["owner"])
            _validate_work_unit_snapshot(
                record["result"], unit_id=unit_id, run_id=run_id, workflow_id=workflow_id,
            )
            if (
                record["result"]["version"] != record["unit_version"]
                or record["result"]["lease_owner"] != record["owner"]
            ):
                raise WorkUnitError("invalid_workflow_state")
            return
        if key.startswith("bind-story:"):
            suffix = key.split(":", 1)[1]
            if not suffix or set(record) != {"story_id", "owner", "result"}:
                raise WorkUnitError("invalid_workflow_state")
            _validate_story_id(record["story_id"])
            _validate_identity(owner=record["owner"])
            result = record["result"]
            if not isinstance(result, dict) or set(result) != {
                "run_id", "workflow_id", "goal_digest", "story_id",
                "status", "current_index", "source_schema_version",
            }:
                raise WorkUnitError("invalid_workflow_state")
            if (
                result["run_id"] != run_id
                or result["workflow_id"] != workflow_id
                or result["goal_digest"] != goal_digest
                or result["story_id"] != record["story_id"]
                or not isinstance(result["goal_digest"], str)
                or re.fullmatch(r"[0-9a-f]{64}", result["goal_digest"]) is None
                or result["status"] not in {"running", "completed", "blocked"}
                or isinstance(result["current_index"], bool)
                or not isinstance(result["current_index"], int)
                or not 0 <= result["current_index"] < len(WORKFLOW_UNITS[workflow_id])
                or isinstance(result["source_schema_version"], bool)
                or result["source_schema_version"] not in {1, 2, RUN_SCHEMA_VERSION}
            ):
                raise WorkUnitError("invalid_workflow_state")
            return
        if key.startswith("submit:"):
            suffix = key.split(":", 1)[1]
            if not suffix or set(record) != {
                "unit_id", "request_unit_version", "owner", "receipt_digest", "result",
            }:
                raise WorkUnitError("invalid_workflow_state")
            _validate_unit_id(record["unit_id"])
            if record["unit_id"] not in units:
                raise WorkUnitError("invalid_workflow_state")
            version = record["request_unit_version"]
            if version is not None and (
                isinstance(version, bool) or not isinstance(version, int) or version <= 0
            ):
                raise WorkUnitError("invalid_workflow_state")
            _validate_identity(owner=record["owner"])
            digest = record["receipt_digest"]
            if not isinstance(digest, str) or (
                digest != _MALFORMED_RECEIPT_DIGEST
                and re.fullmatch(r"[0-9a-f]{64}", digest) is None
            ):
                raise WorkUnitError("invalid_workflow_state")
            result = record["result"]
            if not isinstance(result, dict) or set(result) != {
                "attempt_id", "attempt_status", "workflow_status",
                "decision", "reason_code", "next_unit_id",
            }:
                raise WorkUnitError("invalid_workflow_state")
            if (
                not isinstance(result["attempt_id"], str)
                or re.fullmatch(r"attempt-[0-9a-f]{32}", result["attempt_id"]) is None
                or result["attempt_status"] not in {"succeeded", "rejected"}
                or result["workflow_status"] not in {"running", "completed", "blocked"}
                or result["decision"] not in {"execute_unit", "retry", "ignored"}
                or not isinstance(result["reason_code"], str)
                or not result["reason_code"]
                or result["next_unit_id"] is not None
            ):
                raise WorkUnitError("invalid_workflow_state")
            attempt = next(
                (item for item in attempts if item["attempt_id"] == result["attempt_id"]),
                None,
            )
            if (
                attempt is None
                or attempt["unit_id"] != record["unit_id"]
                or attempt["status"] != result["attempt_status"]
                or attempt["decision"] != result["decision"]
                or attempt["reason_code"] != result["reason_code"]
            ):
                raise WorkUnitError("invalid_workflow_state")
            return
    except (KeyError, TypeError):
        raise WorkUnitError("invalid_workflow_state") from None
    raise WorkUnitError("invalid_workflow_state")


def _validate_fingerprint_map(fingerprints: dict[Any, Any]) -> None:
    """Validate evidence fingerprints without resolving paths on recovery."""
    logical_keys = {"spec", "hld", "story", "board", "context"}
    for name, fingerprint in fingerprints.items():
        path = Path(name) if isinstance(name, str) and name else None
        if (
            not isinstance(name, str)
            or not name
            or (name not in logical_keys and (
                path is None or path.is_absolute() or ".." in path.parts
            ))
            or not isinstance(fingerprint, str)
            or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None
        ):
            raise WorkUnitError("invalid_workflow_state")


def _validate_finalize_projection_fingerprints(
    root: Path, story_id: str, fingerprints: dict[str, Any], *,
    story_contract: dict[str, Any], error_code: str,
) -> None:
    """Bind a completed finalize checkpoint to the files it projects.

    A fingerprint map stored in both a Run and its journal is an immutable
    audit snapshot, not a perpetual freeze on repository evolution. Story
    facts and derived projections may evolve; a changed global HLD is accepted
    only when another completed Core journal has recorded that exact revision.
    """
    required = {"spec", "hld", "story", "board", "context"}
    try:
        _validate_story_id(story_id)
    except WorkUnitError as exc:
        raise WorkUnitError(error_code) from exc
    if (
        not isinstance(fingerprints, dict)
        or set(fingerprints) != required
        or not all(
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
            for value in fingerprints.values()
        )
    ):
        raise WorkUnitError(error_code)
    if (
        not isinstance(story_contract, dict)
        or set(story_contract) != {"title", "spec_path", "tasks"}
        or not isinstance(story_contract["title"], str)
        or not story_contract["title"].strip()
        or story_contract["spec_path"] != f"docs/specs/{story_id}.md"
        or not isinstance(story_contract["tasks"], list)
        or not all(
            isinstance(task, dict)
            and set(task) == {"id", "title"}
            and isinstance(task["id"], str) and task["id"]
            and isinstance(task["title"], str) and task["title"].strip()
            for task in story_contract["tasks"]
        )
    ):
        raise WorkUnitError(error_code)
    try:
        from pactkit.context_gen import context_output_path, generate_context
        from pactkit.governance import BoardRenderer, StoryRepository
        from pactkit.skills.spec_linter import validate_spec

        repository = StoryRepository(root)
        story = repository.load(story_id)
        current_contract = {
            "title": story.get("title"),
            "spec_path": story.get("spec_path"),
            "tasks": [
                {"id": task.get("id"), "title": task.get("title")}
                for task in story.get("tasks", [])
            ],
        }
        if current_contract != story_contract:
            raise WorkUnitError(error_code)
        spec = root / story["spec_path"]
        hld = root / "docs/architecture/graphs/system_design.mmd"
        if (
            not spec.is_file()
            or _fingerprint(spec) != fingerprints["spec"]
            or not validate_spec(str(spec)).passed
            or not hld.is_file()
            or re.search(r"^\s*(?:graph|flowchart)\b", hld.read_text(encoding="utf-8"), re.MULTILINE) is None
        ):
            raise WorkUnitError(error_code)
        current_hld = _fingerprint(hld)
        if current_hld != fingerprints["hld"]:
            known_hld = {fingerprints["hld"]}
            runs = root / ".pactkit/workflow-runs"
            journals = root / ".pactkit/finalize"
            for state_path in runs.glob("run-*.json") if runs.is_dir() else ():
                try:
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                    _validate_workflow_state(state)
                    if state.get("run_id") != state_path.stem:
                        continue
                    for attempt in state.get("attempts", []):
                        unit = state.get("units", {}).get(attempt.get("unit_id"))
                        evidence = attempt.get("file_fingerprints", {})
                        hld_evidence = evidence.get("docs/architecture/graphs/system_design.mmd")
                        if (
                            attempt.get("status") == "succeeded"
                            and attempt.get("decision") == "execute_unit"
                            and unit is not None
                            and unit.get("version") == attempt.get("unit_version")
                            and "docs/architecture/graphs/system_design.mmd"
                            in unit.get("allowed_writes", [])
                            and isinstance(hld_evidence, str)
                            and re.fullmatch(r"[0-9a-f]{64}", hld_evidence)
                        ):
                            known_hld.add(hld_evidence)
                    journal = json.loads((journals / f"{state_path.stem}.json").read_text(encoding="utf-8"))
                    candidate = journal.get("fingerprints", {})
                    if (
                        state.get("status") == "completed"
                        and journal.get("stage") == "completed"
                        and journal.get("run_id") == state.get("run_id") == state_path.stem
                        and isinstance(candidate, dict)
                        and state.get("fingerprints", {}).get("hld") == candidate.get("hld")
                        and isinstance(candidate.get("hld"), str)
                        and re.fullmatch(r"[0-9a-f]{64}", candidate["hld"])
                    ):
                        known_hld.add(candidate["hld"])
                # Historical run files are untrusted recovery inputs.  A
                # malformed unrelated run must never contribute an HLD
                # authorization, but it also must not make a different
                # completed run unreadable.  Direct reads of that malformed
                # run still fail closed through ``_read``.
                except (OSError, json.JSONDecodeError, TypeError, WorkUnitError):
                    continue
            if current_hld not in known_hld:
                raise WorkUnitError(error_code)
        board = root / "docs/product/sprint_board.md"
        if not board.is_file() or board.read_text(encoding="utf-8") != BoardRenderer(repository).render():
            raise WorkUnitError(error_code)
        context = context_output_path(root)
        if not context.is_file():
            raise WorkUnitError(error_code)
        def normalize_timestamp(value: str) -> str:
            return re.sub(
                r"^> Last updated: .+$", "> Last updated: <dynamic>",
                value, count=1, flags=re.MULTILINE,
            )

        if normalize_timestamp(context.read_text(encoding="utf-8")) != normalize_timestamp(
            generate_context(root, command="pactkit finalize-plan")
        ):
            raise WorkUnitError(error_code)
    except WorkUnitError:
        raise
    except Exception as exc:
        raise WorkUnitError(error_code) from exc


def _validate_native_workflow_topology(
    *, workflow_id: str, status: str, current_index: int,
    story_id: str | None, units: dict[str, Any], attempts: list[Any],
    fingerprints: dict[str, Any],
) -> None:
    """Verify native Run progress was produced by Core's state machine.

    Field-level schema checks alone cannot distinguish a genuine accepted Unit
    from a file edited to mark a step succeeded and advance ``current_index``.
    Native runs therefore require one durable Unit per reached step and an
    accepted submission Attempt for every succeeded Unit.  Imported legacy
    states intentionally do not satisfy this newer audit shape.
    """
    templates = WORKFLOW_UNITS[workflow_id]
    # Native WorkUnit runs have no blocked transition.  A host failure becomes
    # a retryable Attempt; accepting a persisted blocked flag would let an
    # external writer change Core authority without an audited transition.
    if status == "blocked":
        raise WorkUnitError("invalid_workflow_state")
    step_indexes = {template.step_id: index for index, template in enumerate(templates)}
    identity_index = step_indexes.get("story_identity")
    if identity_index is not None and current_index > identity_index and story_id is None:
        raise WorkUnitError("invalid_workflow_state")
    records_by_step: dict[str, list[dict[str, Any]]] = {}
    for record in units.values():
        step_id = record["step_id"]
        records_by_step.setdefault(step_id, []).append(record)
        if step_indexes[step_id] > current_index:
            raise WorkUnitError("invalid_workflow_state")
    if any(len(records) != 1 for records in records_by_step.values()):
        raise WorkUnitError("invalid_workflow_state")

    # All steps before the scheduler cursor must be accepted exactly once.
    for template in templates[:current_index]:
        records = records_by_step.get(template.step_id)
        if records is None or records[0]["state"] != "succeeded":
            raise WorkUnitError("invalid_workflow_state")

    # A running cursor cannot already have accepted its ordinary current Unit;
    # the only exception is the terminal finalize Unit, whose acceptance does
    # not advance the cursor and whose actual completion remains journaled.
    current_step = templates[current_index].step_id
    current_records = records_by_step.get(current_step, [])
    if (
        status == "running"
        and not current_step.startswith("finalize_")
        and current_step != "finalize_workflow"
        and any(record["state"] == "succeeded" for record in current_records)
    ):
        raise WorkUnitError("invalid_workflow_state")
    if status == "completed" and current_index != len(templates) - 1:
        raise WorkUnitError("invalid_workflow_state")
    if (
        status == "completed" and workflow_id == "project-plan"
        and not {"spec", "hld", "story", "board", "context"} <= set(fingerprints)
    ):
        raise WorkUnitError("invalid_workflow_state")

    for record in units.values():
        if record["state"] != "succeeded":
            continue
        if not any(
            attempt["unit_id"] == record["unit_id"]
            and attempt["unit_version"] == record["version"]
            and attempt["status"] == "succeeded"
            and attempt["decision"] == "execute_unit"
            for attempt in attempts
        ):
            raise WorkUnitError("invalid_workflow_state")


def _validate_workflow_state(state: Any) -> None:
    """Validate the durable run envelope before executing any transition.

    Run files are recovery inputs as well as Core outputs.  A syntactically
    valid JSON document is not necessarily a valid scheduler state; reject a
    damaged envelope before it can produce an implicit state mutation.
    """
    if not isinstance(state, dict):
        raise WorkUnitError("invalid_workflow_state")
    if (
        isinstance(state.get("schema_version"), bool)
        or state.get("schema_version") != RUN_SCHEMA_VERSION
        or isinstance(state.get("protocol_version"), bool)
        or state.get("protocol_version") != CORE_PROTOCOL_VERSION
    ):
        raise WorkUnitError("unsupported_run_schema")
    try:
        _validate_run_id(state.get("run_id"))
        workflow_id = state["workflow_id"]
        if not isinstance(workflow_id, str) or workflow_id not in WORKFLOW_UNITS:
            raise WorkUnitError("invalid_workflow_state")
        goal_digest = state["goal_digest"]
        if not isinstance(goal_digest, str) or re.fullmatch(r"[0-9a-f]{64}", goal_digest) is None:
            raise WorkUnitError("invalid_workflow_state")
        story_id = state.get("story_id")
        if story_id is not None:
            _validate_story_id(story_id)
        if state["status"] not in {"running", "completed", "blocked"}:
            raise WorkUnitError("invalid_workflow_state")
        current_index = state["current_index"]
        if (
            isinstance(current_index, bool)
            or not isinstance(current_index, int)
            or not 0 <= current_index < len(WORKFLOW_UNITS[workflow_id])
        ):
            raise WorkUnitError("invalid_workflow_state")
        for name in ("units", "idempotency", "fingerprints"):
            if not isinstance(state[name], dict):
                raise WorkUnitError("invalid_workflow_state")
        if not isinstance(state["attempts"], list):
            raise WorkUnitError("invalid_workflow_state")
        for unit_id, record in state["units"].items():
            _validate_work_unit_record(
                record, unit_id=unit_id, run_id=state["run_id"], workflow_id=workflow_id,
            )
        for attempt in state["attempts"]:
            _validate_attempt_record(attempt, units=state["units"])
        for key, record in state["idempotency"].items():
            _validate_idempotency_record(
                key, record, run_id=state["run_id"], workflow_id=workflow_id,
                goal_digest=goal_digest, units=state["units"], attempts=state["attempts"],
            )
        _validate_fingerprint_map(state["fingerprints"])
        if (
            isinstance(state.get("source_schema_version"), bool)
            or state.get("source_schema_version") not in {1, 2, RUN_SCHEMA_VERSION}
            or isinstance(state.get("updated_at"), bool)
            or not isinstance(state.get("updated_at"), (int, float))
            or not math.isfinite(state["updated_at"])
        ):
            raise WorkUnitError("invalid_workflow_state")
        if state["source_schema_version"] == RUN_SCHEMA_VERSION:
            _validate_native_workflow_topology(
                workflow_id=workflow_id, status=state["status"], current_index=current_index,
                story_id=story_id, units=state["units"], attempts=state["attempts"],
                fingerprints=state["fingerprints"],
            )
    except (KeyError, TypeError) as exc:
        raise WorkUnitError("invalid_workflow_state") from exc


class WorkflowEngine:
    """Single-writer JSON workflow engine with leases and receipt validation."""

    def __init__(self, root: Path, *, lease_seconds: int = DEFAULT_LEASE_SECONDS):
        if (
            isinstance(lease_seconds, bool)
            or not isinstance(lease_seconds, int)
            or lease_seconds <= 0
        ):
            raise WorkUnitError("invalid_lease_duration")
        self.root = root.resolve()
        self.directory = self.root / ".pactkit/workflow-runs"
        self.lease_seconds = lease_seconds

    def path_for(self, run_id: str) -> Path:
        _validate_run_id(run_id)
        return self.directory / f"{run_id}.json"

    @contextmanager
    def _lock(self, run_id: str):
        import fcntl

        path = self.path_for(run_id).with_suffix(".lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def _story_lock(self, story_id: str):
        """Serialize Story-bound run creation across Core processes."""
        import fcntl

        _validate_story_id(story_id)
        path = self.directory / "stories" / f"{story_id}.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _validate_completed_finalize_journal(self, state: dict[str, Any]) -> None:
        """Bind a completed native Run to its durable finalize commit.

        The run file is not sufficient completion authority: its final
        projections live in a separately durable journal.  Normal readers must
        therefore reject a completed state whose commit record was deleted, is
        unfinished, or disagrees with the stored projection fingerprints.
        """
        if state["status"] != "completed" or state["source_schema_version"] != RUN_SCHEMA_VERSION:
            return
        path = self.root / ".pactkit/finalize" / f"{state['run_id']}.json"
        try:
            journal = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkUnitError("invalid_workflow_state") from exc
        if not isinstance(journal, dict):
            raise WorkUnitError("invalid_workflow_state")
        if state["workflow_id"] != "project-plan":
            if (
                set(journal) != {
                    "run_id", "workflow_id", "story_id", "idempotency_key",
                    "request_digest", "stage", "claims", "fingerprints",
                }
                or journal.get("stage") != "completed"
                or journal.get("run_id") != state["run_id"]
                or journal.get("workflow_id") != state["workflow_id"]
                or journal.get("story_id") != state.get("story_id")
                or not isinstance(journal.get("idempotency_key"), str)
                or not isinstance(journal.get("claims"), dict)
                or not isinstance(journal.get("fingerprints"), dict)
                or journal["fingerprints"] != state["fingerprints"]
            ):
                raise WorkUnitError("invalid_workflow_state")
            if state["workflow_id"] == "project-act":
                story_id = state.get("story_id")
                board_tasks = journal["claims"].get("board_tasks")
                if not isinstance(story_id, str) or not isinstance(board_tasks, list):
                    raise WorkUnitError("invalid_workflow_state")
                try:
                    from pactkit.governance import BoardRenderer, StoryRepository

                    repository = StoryRepository(self.root)
                    story = repository.load(story_id)
                    if (
                        [task["title"] for task in story["tasks"]] != board_tasks
                        or not story["tasks"]
                        or not all(task["completed"] for task in story["tasks"])
                        or story["status"] != "done"
                        or not BoardRenderer(repository).check(
                            self.root / "docs/product/sprint_board.md",
                        )
                    ):
                        raise WorkUnitError("invalid_workflow_state")
                except WorkUnitError:
                    raise
                except Exception as exc:
                    raise WorkUnitError("invalid_workflow_state") from exc
            return
        fingerprints = journal.get("fingerprints")
        if (
            set(journal) != {
                "run_id", "story_id", "idempotency_key", "request_digest",
                "stage", "story_contract", "fingerprints",
            }
            or journal.get("stage") != "completed"
            or journal.get("run_id") != state["run_id"]
            or journal.get("story_id") != state.get("story_id")
            or not isinstance(journal.get("idempotency_key"), str)
            or not journal["idempotency_key"]
            or not isinstance(journal.get("request_digest"), str)
            or re.fullmatch(r"[0-9a-f]{64}", journal["request_digest"]) is None
            or not isinstance(fingerprints, dict)
            or set(fingerprints) != {"spec", "hld", "story", "board", "context"}
            or any(state["fingerprints"].get(name) != value for name, value in fingerprints.items())
        ):
            raise WorkUnitError("invalid_workflow_state")
        _validate_finalize_projection_fingerprints(
            self.root, state["story_id"], fingerprints,
            story_contract=journal.get("story_contract"),
            error_code="invalid_workflow_state",
        )

    def _read(
        self, run_id: str, *, allow_finalize_recovery: bool = False,
    ) -> dict[str, Any]:
        try:
            state = json.loads(self.path_for(run_id).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkUnitError("workflow_state_unavailable") from exc
        _validate_workflow_state(state)
        if state["run_id"] != run_id:
            raise WorkUnitError("invalid_workflow_state")
        if not allow_finalize_recovery:
            self._validate_completed_finalize_journal(state)
        return state

    def _read_scanned_state(
        self, path: Path, *, validate_completed: bool = True,
    ) -> dict[str, Any]:
        """Read a discovered run only after binding it to its filename.

        Directory scans support Unit lookup and Story resume, so they are also
        recovery inputs.  Treating their JSON as an unvalidated index allows a
        swapped or malformed run file to select a different authoritative run.
        """
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkUnitError("workflow_state_unavailable") from exc
        _validate_workflow_state(state)
        if state["run_id"] != path.stem:
            raise WorkUnitError("invalid_workflow_state")
        if validate_completed:
            self._validate_completed_finalize_journal(state)
        return state

    def _write(self, state: dict[str, Any]) -> None:
        atomic_write(
            self.path_for(state["run_id"]),
            json.dumps(state, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        )

    @staticmethod
    def _run(state: dict[str, Any]) -> WorkflowRun:
        return WorkflowRun(
            state["run_id"], state["workflow_id"], state["goal_digest"],
            state.get("story_id"), state["status"], state["current_index"],
            state.get("source_schema_version", RUN_SCHEMA_VERSION),
        )

    def start(
        self, workflow_id: str, *, goal: str, story_id: str | None = None,
    ) -> WorkflowRun:
        _validate_workflow_start(
            workflow_id=workflow_id, goal=goal, story_id=story_id,
        )
        templates = WORKFLOW_UNITS.get(workflow_id)
        if not templates:
            raise WorkUnitError("unknown_workflow")
        if story_id is not None:
            with self._story_lock(story_id):
                if self._active_runs_for_story(story_id):
                    raise WorkUnitError("story_already_has_active_workflow_run")
                predecessor = {
                    "project-check": "project-act",
                    "project-done": "project-check",
                }.get(workflow_id)
                if predecessor and not self._completed_run_for_story(story_id, predecessor):
                    raise WorkUnitError(f"{predecessor}_completion_required")
                return self._start(workflow_id, goal=goal, story_id=story_id)
        return self._start(workflow_id, goal=goal, story_id=None)

    def _start(
        self, workflow_id: str, *, goal: str, story_id: str | None,
    ) -> WorkflowRun:
        run_id = "run-" + uuid.uuid4().hex
        state = {
            "schema_version": RUN_SCHEMA_VERSION,
            "protocol_version": CORE_PROTOCOL_VERSION,
            "run_id": run_id,
            "workflow_id": workflow_id,
            "goal_digest": hashlib.sha256(goal.encode()).hexdigest(),
            "story_id": story_id,
            "status": "running",
            "current_index": 0,
            "units": {},
            "attempts": [],
            "idempotency": {},
            "fingerprints": {},
            "source_schema_version": RUN_SCHEMA_VERSION,
            "updated_at": time.time(),
        }
        with self._lock(run_id):
            self._write(state)
        return self._run(state)

    @staticmethod
    def _template(state: dict[str, Any]) -> WorkUnitTemplate:
        return WORKFLOW_UNITS[state["workflow_id"]][state["current_index"]]

    @staticmethod
    def _unit(record: dict[str, Any]) -> WorkUnit:
        data = {key: value for key, value in record.items() if key != "state"}
        data.setdefault("required_claims", ())
        for key in (
            "input_refs", "allowed_reads", "allowed_writes", "forbidden_operations",
            "acceptance_commands", "manual_authorization", "required_claims",
        ):
            data[key] = tuple(data[key])
        return WorkUnit(**data)

    @classmethod
    def _idempotent_unit_result(
        cls, cached: Any, *, unit_id: str, owner: str,
    ) -> WorkUnit:
        """Rehydrate one immutable acquire/retry response snapshot.

        WorkUnits are versioned in place while retrying.  Reconstructing an
        old idempotent response from the mutable Unit record would therefore
        silently change its version and lease.  Cache records must carry the
        exact WorkUnit returned by their original request.
        """
        if not isinstance(cached, dict) or {
            "unit_id", "unit_version", "owner", "result",
        } - cached.keys():
            raise WorkUnitError("invalid_idempotency_record")
        if cached["unit_id"] != unit_id or cached["owner"] != owner:
            raise WorkUnitError("idempotency_key_conflict")
        result = cached["result"]
        if not isinstance(result, dict):
            raise WorkUnitError("invalid_idempotency_record")
        try:
            snapshot = cls._unit(result)
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkUnitError("invalid_idempotency_record") from exc
        if (
            snapshot.unit_id != unit_id
            or snapshot.version != cached["unit_version"]
            or snapshot.lease_owner != owner
        ):
            raise WorkUnitError("invalid_idempotency_record")
        return snapshot

    @staticmethod
    def _idempotent_run_result(
        cached: Any, *, run_id: str, story_id: str, owner: str,
    ) -> WorkflowRun:
        """Rehydrate one immutable bind-story response snapshot.

        A bound run keeps advancing after its identity Unit succeeds.  An old
        idempotency key must therefore return the run as it was when binding
        completed, rather than projecting the current mutable scheduler state.
        """
        if not isinstance(cached, dict) or {
            "story_id", "owner", "result",
        } - cached.keys():
            raise WorkUnitError("invalid_idempotency_record")
        if cached["story_id"] != story_id or cached["owner"] != owner:
            raise WorkUnitError("idempotency_key_conflict")
        result = cached["result"]
        if not isinstance(result, dict):
            raise WorkUnitError("invalid_idempotency_record")
        try:
            snapshot = WorkflowRun(**result)
        except (TypeError, ValueError) as exc:
            raise WorkUnitError("invalid_idempotency_record") from exc
        if (
            snapshot.run_id != run_id
            or snapshot.story_id != story_id
            or asdict(snapshot) != result
        ):
            raise WorkUnitError("invalid_idempotency_record")
        return snapshot

    @staticmethod
    def _idempotent_submission_result(
        cached: Any, *, unit_id: str, owner: str, receipt_digest: str,
        request_unit_version: int | None,
    ) -> SubmissionResult:
        """Rehydrate one immutable submit response for the same request.

        The WorkUnit record is versioned in place by retry.  Validation must
        compare the receipt's original version, never the record's current
        version, or a legitimate replay after retry would become a conflict.
        """
        if not isinstance(cached, dict) or {
            "unit_id", "request_unit_version", "owner",
            "receipt_digest", "result",
        } - cached.keys():
            raise WorkUnitError("invalid_idempotency_record")
        if (
            cached["unit_id"] != unit_id
            or cached["request_unit_version"] != request_unit_version
            or cached["owner"] != owner
            or cached["receipt_digest"] != receipt_digest
        ):
            raise WorkUnitError("idempotency_key_conflict")
        result = cached["result"]
        if not isinstance(result, dict):
            raise WorkUnitError("invalid_idempotency_record")
        try:
            snapshot = SubmissionResult(**result)
        except (TypeError, ValueError) as exc:
            raise WorkUnitError("invalid_idempotency_record") from exc
        if asdict(snapshot) != result:
            raise WorkUnitError("invalid_idempotency_record")
        return snapshot

    def acquire(
        self, run_id: str, *, owner: str, idempotency_key: str,
        now: float | None = None,
    ) -> WorkUnit:
        _validate_identity(owner=owner, idempotency_key=idempotency_key)
        now = _timestamp(now)
        with self._lock(run_id):
            state = self._read(run_id)
            if state["status"] == "completed":
                raise WorkUnitError("workflow_completed")
            if state["status"] == "blocked":
                raise WorkUnitError("workflow_blocked")
            cached = state["idempotency"].get("acquire:" + idempotency_key)
            if cached:
                cached_unit_id = cached.get("unit_id") if isinstance(cached, dict) else None
                if not isinstance(cached_unit_id, str):
                    raise WorkUnitError("invalid_idempotency_record")
                return self._idempotent_unit_result(
                    cached, unit_id=cached_unit_id, owner=owner,
                )
            template = self._template(state)
            retryable = next(
                (item for item in state["units"].values()
                 if item["step_id"] == template.step_id
                 and item.get("state") in {"retry", "expired"}),
                None,
            )
            if retryable:
                raise WorkUnitError("retry_required")
            active = next(
                (item for item in state["units"].values()
                 if item["step_id"] == template.step_id and item.get("state") == "leased"),
                None,
            )
            if active and active["lease_expires_at"] > now:
                if active["lease_owner"] != owner:
                    raise WorkUnitError("lease_contended")
                raise WorkUnitError("idempotency_key_required")
            if active and active["lease_expires_at"] <= now:
                active["state"] = "expired"
                self._write(state)
                raise WorkUnitError("lease_expired")
            unit_id = "unit-" + uuid.uuid4().hex
            story_id = state.get("story_id") or "{story_id}"

            def render(values: tuple[str, ...]) -> tuple[str, ...]:
                return tuple(value.replace("{story_id}", story_id) for value in values)

            # STORY-slim-20260824dd23a0ed3b4c — union project write_scope roots +
            # Story Touches onto the frozen template floor (resolve_scope SSoT).
            extra_reads, extra_writes = resolve_scope(
                state["workflow_id"], template.step_id,
                state.get("story_id"), self.root,
            )

            record = {
                "run_id": run_id,
                "unit_id": unit_id,
                "workflow_id": state["workflow_id"],
                "step_id": template.step_id,
                "version": 1,
                "objective": template.objective,
                "input_refs": tuple(filter(None, (state.get("story_id"), state["goal_digest"]))),
                "allowed_reads": _dedupe_scope((*render(template.allowed_reads), *extra_reads)),
                "allowed_writes": _dedupe_scope((*render(template.allowed_writes), *extra_writes)),
                "forbidden_operations": template.forbidden_operations,
                "acceptance_commands": render(template.acceptance_commands),
                "manual_authorization": template.manual_authorization,
                "lease_owner": owner,
                "lease_expires_at": now + self.lease_seconds,
                "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
                "required_claims": template.required_claims,
                "state": "leased",
            }
            state["units"][unit_id] = record
            state["idempotency"]["acquire:" + idempotency_key] = {
                "unit_id": unit_id,
                "unit_version": record["version"],
                "owner": owner,
                "result": asdict(self._unit(record)),
            }
            state["updated_at"] = now
            self._write(state)
            return self._unit(record)

    def lease_current(
        self, run_id: str, *, owner: str, idempotency_key: str,
        now: float | None = None,
    ) -> WorkUnit:
        """Lease the Core-selected current unit, including a required retry.

        Host adapters must not inspect durable unit records to decide whether
        to call ``acquire`` or ``retry``. Core exposes that scheduling choice
        here; the selected transition still performs its own locked validation
        so a concurrent state change fails closed.
        """
        _validate_identity(owner=owner, idempotency_key=idempotency_key)
        state = self._read(run_id)
        if state["status"] == "completed":
            raise WorkUnitError("workflow_completed")
        if state["status"] == "blocked":
            raise WorkUnitError("workflow_blocked")
        template = self._template(state)
        retryable = [
            item for item in state["units"].values()
            if item.get("step_id") == template.step_id
            and item.get("state") in {"retry", "expired"}
        ]
        if len(retryable) > 1:
            raise WorkUnitError("invalid_workflow_state")
        if retryable:
            return self.retry(
                retryable[0]["unit_id"], owner=owner,
                idempotency_key=idempotency_key, now=now,
            )
        try:
            return self.acquire(
                run_id, owner=owner, idempotency_key=idempotency_key, now=now,
            )
        except WorkUnitError as exc:
            if str(exc) != "lease_expired":
                raise
            # acquire atomically marks the stale active lease expired. Finish
            # the same scheduling request by versioning that existing Unit.
            refreshed = self._read(run_id)
            current = self._template(refreshed)
            expired = [
                item for item in refreshed["units"].values()
                if item.get("step_id") == current.step_id
                and item.get("state") == "expired"
            ]
            if len(expired) != 1:
                raise WorkUnitError("invalid_workflow_state") from exc
            return self.retry(
                expired[0]["unit_id"], owner=owner,
                idempotency_key=idempotency_key, now=now,
            )

    def _find_run_for_unit(self, unit_id: str) -> str:
        _validate_unit_id(unit_id)
        paths = self.directory.glob("run-*.json") if self.directory.is_dir() else ()
        for path in paths:
            state = self._scan_or_skip(
                path, relevance=lambda s: unit_id in s.get("units", {})
            )
            if state is not None and unit_id in state.get("units", {}):
                return state["run_id"]
        raise WorkUnitError("unknown_unit")

    def _scan_or_skip(
        self, path: Path, *, relevance=None,
    ) -> dict[str, Any] | None:
        """Scan-read a run, skipping corrupt files with a warning — unless
        the corrupted file is RELEVANT to the query.

        A single malformed unrelated run file must not block every lookup
        (STORY-slim-202608267c3989223b4d R2). But a parseable run whose
        (unvalidated) content matches the query — the unit being looked up,
        or the Story being resumed — is the TARGET: it fails closed, because
        silently skipping it could mask tampering or resurrect duplicate
        active runs. `relevance` receives the raw parsed dict.
        """
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  ⚠️  skipping unparseable run file {path.stem}: {exc}", file=sys.stderr)
            return None
        try:
            return self._read_scanned_state(path, validate_completed=False)
        except WorkUnitError as exc:
            if relevance is not None and isinstance(raw, dict) and relevance(raw):
                raise
            print(
                f"  ⚠️  skipping corrupt run file {path.stem}: {exc}",
                file=sys.stderr,
            )
            return None

    def _active_runs_for_story(self, story_id: str) -> list[dict[str, Any]]:
        """Return valid, non-terminal runs bound to exactly one Story."""
        _validate_story_id(story_id)
        paths = self.directory.glob("run-*.json") if self.directory.is_dir() else ()
        active: list[dict[str, Any]] = []
        for path in paths:
            # Completed runs cannot be active.  Their projection validity is
            # checked by direct status/replay reads, not while discovering a
            # different Story's runnable work.
            state = self._scan_or_skip(
                path, relevance=lambda s: s.get("story_id") == story_id
            )
            if state is None:
                continue
            if (
                state["story_id"] == story_id
                and state.get("status") == "running"
            ):
                active.append(state)
        return active

    def _completed_run_for_story(self, story_id: str, workflow_id: str) -> dict[str, Any] | None:
        """Return a completed predecessor for one Story, if present.

        STORY-slim-2026082466c8670d9655 R2: an EXISTENCE lookup must not
        re-validate sibling journals' projection fingerprints — that strict
        validation belongs on EXECUTION reads (_read), where tamper-detection
        matters. A stale sibling journal (e.g. a plan run whose projections a
        later workflow legitimately overwrote) must not poison a predecessor
        lookup and block project-check/project-done start.
        """
        for path in self.directory.glob("run-*.json") if self.directory.is_dir() else ():
            state = self._scan_or_skip(
                path, relevance=lambda s: s.get("story_id") == story_id
            )
            if state is None:
                continue
            if (
                state.get("story_id") == story_id
                and state.get("workflow_id") == workflow_id
                and state.get("status") == "completed"
            ):
                return state
        return None

    def resume(self, story_id: str) -> dict[str, Any]:
        """Find the one resumable Plan run for a Story without changing state."""
        active = self._active_runs_for_story(story_id)
        if not active:
            raise WorkUnitError("no_active_workflow_run")
        if len(active) != 1:
            raise WorkUnitError("multiple_active_workflow_runs")
        state = active[0]
        run_id = state["run_id"]
        return {
            "decision": "resume_at",
            "run_id": run_id,
            "workflow_id": state["workflow_id"],
            "workflow_status": state["status"],
            "step_id": self._template(state).step_id,
            "manual_resume_command": (
                f"pactkit work-unit acquire {run_id} "
                "--owner <owner> --idempotency-key <key>"
            ),
        }

    def bind_story(
        self, run_id: str, *, story_id: str, owner: str, idempotency_key: str,
        now: float | None = None,
    ) -> WorkflowRun:
        """Atomically bind the Story allocated by the leased identity Unit.

        A Plan run may start before a Story ID exists.  Binding is deliberately
        limited to the identity Unit so an adapter cannot retarget a later
        write Unit or create two active authoritative runs for one Story.
        """
        _validate_identity(owner=owner, idempotency_key=idempotency_key)
        now = _timestamp(now)
        with self._story_lock(story_id):
            with self._lock(run_id):
                state = self._read(run_id)
                cached = state["idempotency"].get("bind-story:" + idempotency_key)
                if cached:
                    return self._idempotent_run_result(
                        cached, run_id=run_id, story_id=story_id, owner=owner,
                    )
                if state.get("story_id") is not None:
                    if state["story_id"] == story_id:
                        raise WorkUnitError("story_bind_not_allowed")
                    raise WorkUnitError("story_identity_mismatch")
                if self._template(state).step_id != "story_identity":
                    raise WorkUnitError("story_bind_not_allowed")
                identity_units = [
                    record for record in state["units"].values()
                    if record.get("step_id") == "story_identity"
                    and record.get("state") == "leased"
                    and record.get("lease_owner") == owner
                    and record.get("lease_expires_at", 0) > now
                ]
                if len(identity_units) != 1:
                    raise WorkUnitError("story_bind_requires_identity_lease")
                if self._active_runs_for_story(story_id):
                    raise WorkUnitError("story_already_has_active_workflow_run")
                state["story_id"] = story_id
                identity_units[0]["input_refs"] = (story_id, state["goal_digest"])
                result = self._run(state)
                state["idempotency"]["bind-story:" + idempotency_key] = {
                    "story_id": story_id,
                    "owner": owner,
                    "result": asdict(result),
                }
                state["updated_at"] = now
                self._write(state)
                return result

    def renew(self, unit_id: str, *, owner: str, now: float | None = None) -> WorkUnit:
        _validate_identity(owner=owner)
        now = _timestamp(now)
        run_id = self._find_run_for_unit(unit_id)
        with self._lock(run_id):
            state = self._read(run_id)
            record = state["units"][unit_id]
            if record["lease_owner"] != owner:
                raise WorkUnitError("lease_owner_mismatch")
            if record["state"] != "leased" or record["lease_expires_at"] <= now:
                raise WorkUnitError("lease_expired")
            record["lease_expires_at"] = now + self.lease_seconds
            self._write(state)
            return self._unit(record)

    def _validate_receipt(
        self, state: dict[str, Any], record: dict[str, Any],
        receipt: EvidenceReceipt, owner: str, now: float,
    ) -> str:
        if receipt.schema_version != RECEIPT_SCHEMA_VERSION:
            return "receipt_schema_mismatch"
        if receipt.unit_id != record["unit_id"] or receipt.unit_version != record["version"]:
            return "unit_version_mismatch"
        if owner != record["lease_owner"] or receipt.owner != owner:
            return "lease_owner_mismatch"
        if record["state"] != "leased" or record["lease_expires_at"] <= now:
            return "lease_expired"
        for name, claimed in receipt.file_fingerprints.items():
            allowed = record["allowed_writes"]
            if not any(fnmatch.fnmatch(name, pattern) for pattern in allowed):
                return "write_scope_violation"
            try:
                path = _safe_repo_path(self.root, name)
            except WorkUnitError as exc:
                return str(exc)
            # A receipt proves a completed write only when Core can reread an
            # actual regular file.  The sentinel "missing" is useful for
            # diagnostics but must never satisfy a WorkUnit validator.
            if not path.is_file() or _fingerprint(path) != claimed:
                return "fingerprint_mismatch"
        step = record["step_id"]
        claims = receipt.claims
        story_id = _record_story_id(record)
        if record["workflow_id"] == "project-plan" and step == "preflight":
            from pactkit.guards import check_init_markers

            guard_passed, _missing = check_init_markers(self.root)
            if claims.get("guard") != "pass" or not guard_passed:
                return "validator_failed"
        if step == "clarification" and claims.get("clarification_resolved") is not True:
            return "validator_failed"
        if step == "archaeology":
            trace = claims.get("trace")
            if not isinstance(trace, list) or not trace or not all(isinstance(item, str) and item for item in trace):
                return "validator_failed"
        if step == "story_identity" and (
            story_id is None or claims.get("story_id") != story_id
        ):
            return "validator_failed"
        if step == "spec_scaffold" and not receipt.file_fingerprints:
            return "validator_failed"
        if step == "spec_content":
            if set(receipt.file_fingerprints) != set(record["allowed_writes"]):
                return "validator_failed"
            hld = _safe_repo_path(
                self.root, "docs/architecture/graphs/system_design.mmd",
            )
            try:
                hld_text = hld.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                return "validator_failed"
            if re.search(
                r"^\s*(?:graph|flowchart)\b", hld_text, re.MULTILINE,
            ) is None:
                return "validator_failed"
        if step == "spec_security" and (
            claims.get("security_scoped") is not True or not receipt.file_fingerprints
        ):
            return "validator_failed"
        if step == "spec_lint":
            from pactkit.skills.spec_linter import validate_spec

            spec_paths = [
                _safe_repo_path(self.root, name)
                for name in receipt.file_fingerprints
                if name.startswith("docs/specs/") and name.endswith(".md")
            ]
            if len(spec_paths) != 1 or not validate_spec(str(spec_paths[0])).passed:
                return "validator_failed"
        workflow = record["workflow_id"]
        if (
            workflow != "project-plan"
            and (step.startswith("finalize_") or step == "finalize_workflow")
            and claims.get("completed") is not True
        ):
            return "validator_failed"
        if workflow == "project-act":
            if step == "act_preflight":
                trace = claims.get("trace")
                if claims.get("spec_lint") != "pass" or not isinstance(trace, list) or not trace:
                    return "validator_failed"
                if story_id is None:
                    return "validator_failed"
                from pactkit.skills.spec_linter import validate_spec
                spec = self.root / "docs/specs" / f"{story_id}.md"
                if not spec.is_file() or not validate_spec(str(spec)).passed:
                    return "validator_failed"
            elif step == "red":
                tests = claims.get("story_tests")
                if not isinstance(tests, dict) or tests.get("exit_code") != 1 or not receipt.file_fingerprints:
                    return "validator_failed"
            elif step == "implementation":
                changed = claims.get("changed_files")
                if (
                    not isinstance(changed, list) or not changed
                    or not all(isinstance(path, str) and path for path in changed)
                    or set(changed) != set(receipt.file_fingerprints)
                ):
                    return "validator_failed"
            elif step == "story_tests":
                tests = claims.get("story_tests")
                if not isinstance(tests, dict) or tests.get("exit_code") != 0:
                    return "validator_failed"
            elif step == "regression_lint" and (
                claims.get("regression") != "pass" or claims.get("lint") != "pass"
            ):
                return "validator_failed"
            elif step == "sync_coverage":
                coverage = claims.get("coverage")
                acceptance = claims.get("acceptance_coverage")
                board_tasks = claims.get("board_tasks")
                if not isinstance(coverage, dict) or not coverage or not all(coverage.values()):
                    return "validator_failed"
                if not isinstance(acceptance, dict) or not acceptance or not all(acceptance.values()):
                    return "validator_failed"
                if (
                    not isinstance(board_tasks, list) or not board_tasks
                    or not all(isinstance(task, str) and task.strip() for task in board_tasks)
                    or len(set(board_tasks)) != len(board_tasks)
                ):
                    return "validator_failed"
        elif workflow == "project-check":
            expected = {
                "check_preflight": ("spec_lint", "pass"),
                "security_scan": ("security_scan", "pass"),
                "quality_scan": ("quality_scan", "pass"),
                "spec_alignment": ("spec_alignment", "pass"),
            }.get(step)
            if expected and claims.get(expected[0]) != expected[1]:
                return "validator_failed"
            if step == "check_tests":
                tests = claims.get("tests")
                if not isinstance(tests, dict) or tests.get("exit_code") != 0:
                    return "validator_failed"
        elif workflow == "project-done":
            if step == "done_preflight" and claims.get("check_complete") is not True:
                return "validator_failed"
            if step == "governance_sync" and claims.get("governance") != "pass":
                return "validator_failed"
            if step == "done_verify" and (
                claims.get("audit") != "pass" or claims.get("deployment") != "pass"
            ):
                return "validator_failed"
            if step == "commit":
                git = claims.get("git")
                if not isinstance(git, dict):
                    return "validator_failed"
                if git.get("mode") != "no_git":
                    commit = git.get("commit")
                    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{7,64}", commit) is None:
                        return "validator_failed"
        elif workflow == "project-init":
            if step == "preflight" and claims.get("ready") is not True:
                return "validator_failed"
            if step == "configure" and claims.get("configuration_created") is not True:
                return "validator_failed"
            if step == "governance":
                from pactkit.guards import check_init_markers

                guard_passed, _missing = check_init_markers(self.root)
                if (
                    claims.get("governance_created") is not True
                    or claims.get("guard") != "pass" or not guard_passed
                ):
                    return "validator_failed"
        elif workflow == "project-sprint":
            if step == "preflight":
                stories = claims.get("stories")
                if (
                    not isinstance(stories, list) or not stories
                    or not all(
                        isinstance(item, str) and _STORY_ID_PATTERN.fullmatch(item)
                        for item in stories
                    )
                ):
                    return "validator_failed"
            expected = {
                "plan_phase": ("planned", True),
                "act_phase": ("executed", True),
                "check_phase": ("checked", True),
                "done_phase": ("cleanup", "pass"),
            }.get(step)
            if expected and claims.get(expected[0]) != expected[1]:
                return "validator_failed"
            predecessor = {
                "plan_phase": "project-plan",
                "act_phase": "project-act",
                "check_phase": "project-check",
                "done_phase": "project-done",
            }.get(step)
            if predecessor:
                selected = next((
                    item.get("accepted_claims", {}).get("stories")
                    for item in state["units"].values()
                    if item.get("step_id") == "preflight"
                    and item.get("state") == "succeeded"
                ), None)
                if not isinstance(selected, list) or not all(
                    self._completed_run_for_story(story, predecessor)
                    for story in selected
                ):
                    return "validator_failed"
        elif workflow == "project-hotfix":
            if step == "preflight" and claims.get("traceability") is not True:
                return "validator_failed"
            if step == "fix" and claims.get("executed") is not True:
                return "validator_failed"
            if step == "verify":
                tests = claims.get("tests")
                if (
                    not isinstance(tests, dict) or tests.get("exit_code") != 0
                    or claims.get("lint") != "pass"
                ):
                    return "validator_failed"
        elif workflow == "project-design":
            if step == "preflight" and claims.get("ready") is not True:
                return "validator_failed"
            if step == "prd" and claims.get("prd_created") is not True:
                return "validator_failed"
            count = claims.get("stories_created")
            if step == "stories" and (
                not isinstance(count, int) or isinstance(count, bool) or count <= 0
                or claims.get("board_synced") is not True
            ):
                return "validator_failed"
        elif workflow == "project-clarify":
            if step == "preflight" and claims.get("ready") is not True:
                return "validator_failed"
            count = claims.get("decision_count")
            if step == "decisions" and (
                claims.get("requirements_confirmed") is not True
                or not isinstance(count, int) or isinstance(count, bool) or count <= 0
            ):
                return "validator_failed"
        elif workflow == "project-release":
            if step == "preflight" and claims.get("ready") is not True:
                return "validator_failed"
            if step == "prepare" and not all(
                isinstance(claims.get(key), str) and claims[key].strip()
                for key in ("version", "tag")
            ):
                return "validator_failed"
            release = claims.get("release")
            if step == "publish" and (
                not isinstance(release, dict)
                or not (
                    isinstance(release.get("url"), str) and release["url"].strip()
                    or release.get("mode") == "local_only"
                )
            ):
                return "validator_failed"
        elif workflow == "project-pr":
            if step == "preflight" and claims.get("ready") is not True:
                return "validator_failed"
            pull_request = claims.get("pull_request")
            if step == "publish" and (
                not isinstance(claims.get("branch"), str) or not claims["branch"].strip()
                or not isinstance(pull_request, dict)
                or not (
                    isinstance(pull_request.get("url"), str) and pull_request["url"].strip()
                    or pull_request.get("mode") == "not_required"
                )
            ):
                return "validator_failed"
        elif workflow == "project-debug":
            if step == "preflight" and claims.get("ready") is not True:
                return "validator_failed"
            evidence = claims.get("evidence")
            if step == "hypotheses" and (
                not isinstance(evidence, list) or not evidence
                or not all(isinstance(item, str) and item for item in evidence)
            ):
                return "validator_failed"
            if step == "diagnosis" and not all(
                isinstance(claims.get(key), str) and claims[key].strip()
                for key in ("root_cause", "next_action")
            ):
                return "validator_failed"
        return "accepted"

    def reject(
        self, unit_id: str, *, owner: str, reason_code: str,
        now: float | None = None,
    ) -> SubmissionResult:
        _validate_identity(owner=owner)
        if not isinstance(reason_code, str) or not reason_code:
            raise WorkUnitError("invalid_attempt_reason")
        now = _timestamp(now)
        run_id = self._find_run_for_unit(unit_id)
        with self._lock(run_id):
            state = self._read(run_id)
            record = state["units"][unit_id]
            if record["lease_owner"] != owner:
                raise WorkUnitError("lease_owner_mismatch")
            if record["state"] != "leased":
                raise WorkUnitError("unit_not_rejectable")
            if record["lease_expires_at"] <= now:
                raise WorkUnitError("lease_expired")
            record["state"] = "retry"
            attempt_id = "attempt-" + uuid.uuid4().hex
            state["attempts"].append({
                "attempt_id": attempt_id, "unit_id": unit_id,
                "unit_version": record["version"], "host": None,
                "session_ref": None, "thread_ref": None, "turn_ref": None,
                "capabilities": {}, "execution_mode": None,
                "adapter_version": None, "status": "rejected",
                "result_refs": [], "decision": "retry",
                "reason_code": reason_code, "started_at": now,
                "finished_at": now, "latency_ms": 0,
            })
            self._write(state)
            return SubmissionResult(
                attempt_id, "rejected", state["status"], "retry", reason_code,
            )

    def retry(
        self, unit_id: str, *, owner: str, idempotency_key: str,
        now: float | None = None,
    ) -> WorkUnit:
        _validate_identity(owner=owner, idempotency_key=idempotency_key)
        now = _timestamp(now)
        run_id = self._find_run_for_unit(unit_id)
        with self._lock(run_id):
            state = self._read(run_id)
            cached = state["idempotency"].get("retry:" + idempotency_key)
            if cached:
                cached_unit_id = cached.get("unit_id") if isinstance(cached, dict) else None
                if not isinstance(cached_unit_id, str):
                    raise WorkUnitError("invalid_idempotency_record")
                return self._idempotent_unit_result(
                    cached, unit_id=unit_id, owner=owner,
                )
            record = state["units"][unit_id]
            if record["lease_owner"] != owner:
                raise WorkUnitError("lease_owner_mismatch")
            if record["state"] not in {"retry", "expired"}:
                raise WorkUnitError("unit_not_retryable")
            # Instruction-only acceptance guidance may become more explicit
            # across Core upgrades. Refresh it for the new Unit version while
            # preserving the original read/write and authorization boundary;
            # retry must never retroactively broaden a persisted lease.
            template = self._template(state)
            if template.step_id != record["step_id"]:
                raise WorkUnitError("unit_not_current")
            record["required_claims"] = template.required_claims
            record["version"] += 1
            record["state"] = "leased"
            record["lease_expires_at"] = now + self.lease_seconds
            state["idempotency"]["retry:" + idempotency_key] = {
                "unit_id": unit_id,
                "unit_version": record["version"],
                "owner": owner,
                "result": asdict(self._unit(record)),
            }
            self._write(state)
            return self._unit(record)

    def expire(
        self, unit_id: str, *, owner: str, now: float | None = None,
    ) -> dict[str, Any]:
        _validate_identity(owner=owner)
        now = _timestamp(now)
        run_id = self._find_run_for_unit(unit_id)
        with self._lock(run_id):
            state = self._read(run_id)
            record = state["units"][unit_id]
            if record["lease_owner"] != owner:
                raise WorkUnitError("lease_owner_mismatch")
            if record["state"] != "leased":
                raise WorkUnitError("unit_not_expirable")
            if record["lease_expires_at"] > now:
                raise WorkUnitError("lease_not_expired")
            record["state"] = "expired"
            self._write(state)
            return dict(record)

    def submit(
        self, unit_id: str, receipt: EvidenceReceipt, *, owner: str,
        idempotency_key: str, now: float | None = None,
    ) -> SubmissionResult:
        _validate_identity(owner=owner, idempotency_key=idempotency_key)
        now = _timestamp(now)
        run_id = self._find_run_for_unit(unit_id)
        with self._lock(run_id):
            state = self._read(run_id)
            record = state["units"].get(unit_id)
            if record is None:
                raise WorkUnitError("unknown_unit")
            shape_reason = _receipt_shape_reason(receipt)
            # A structurally invalid receipt cannot be canonically serialized.
            # Bind an idempotency key to its stable reason instead, then record
            # the rejection through the same authoritative attempt path.
            request_digest = (
                _receipt_digest(receipt) if shape_reason is None else _MALFORMED_RECEIPT_DIGEST
            )
            request_unit_version = receipt.unit_version if shape_reason is None else None
            cached = state["idempotency"].get("submit:" + idempotency_key)
            if cached:
                return self._idempotent_submission_result(
                    cached, unit_id=unit_id, owner=owner,
                    receipt_digest=request_digest,
                    request_unit_version=request_unit_version,
                )
            reason = shape_reason or self._validate_receipt(state, record, receipt, owner, now)
            # Only the owner of the currently leased WorkUnit may change
            # authoritative state.  Late, cross-owner, expired, or prior-step
            # Receipts are still audited below, but are not allowed to reopen a
            # succeeded Unit or advance the scheduler a second time.
            receipt_identity_matches = (
                shape_reason is not None
                or (
                    receipt.unit_id == unit_id
                    and receipt.unit_version == record.get("version")
                    and receipt.owner == owner
                )
            )
            transition_allowed = (
                record.get("state") == "leased"
                and record.get("lease_owner") == owner
                and record.get("lease_expires_at", 0) > now
                and record.get("step_id") == self._template(state).step_id
                and receipt_identity_matches
            )
            accepted = reason == "accepted" and transition_allowed
            if reason == "accepted" and not transition_allowed:
                reason = "unit_not_current"
            attempt_id = "attempt-" + uuid.uuid4().hex
            attempt_status = "succeeded" if accepted else "rejected"
            decision = "ignored"
            if accepted:
                record["state"] = "succeeded"
                record["accepted_claims"] = dict(receipt.claims)
                state["fingerprints"].update(
                    _persisted_fingerprints(receipt.file_fingerprints)
                )
                if state["current_index"] + 1 < len(WORKFLOW_UNITS[state["workflow_id"]]):
                    state["current_index"] += 1
                decision = "execute_unit"
            elif transition_allowed:
                # A candidate submitted by the current lease holder did not
                # pass Core validation, so this exact Unit is retried through
                # the versioned retry path.
                record["state"] = "retry"
                decision = "retry"
            # Never project fields from a structurally invalid candidate into
            # the persisted audit record. A reason code is enough to preserve
            # the fact of rejection without persisting arbitrary objects.
            if shape_reason is None:
                receipt_host = receipt.host
                session_ref = _opaque_ref(receipt.session_ref)
                thread_ref = _opaque_ref(receipt.thread_ref)
                turn_ref = _opaque_ref(receipt.turn_ref)
                capabilities = dict(receipt.capabilities)
                adapter_version = receipt.adapter_version
                result_refs = list(receipt.result_refs)
                started_at = receipt.started_at if receipt.started_at is not None else now
            else:
                receipt_host = None
                session_ref = None
                thread_ref = None
                turn_ref = None
                capabilities = {}
                adapter_version = None
                result_refs = []
                started_at = now
            attempt = {
                "attempt_id": attempt_id,
                "unit_id": unit_id,
                "unit_version": record["version"],
                "host": receipt_host,
                "session_ref": session_ref,
                "thread_ref": thread_ref,
                "turn_ref": turn_ref,
                "capabilities": capabilities,
                "execution_mode": _receipt_execution_mode(receipt) if shape_reason is None else None,
                "adapter_version": adapter_version,
                "status": attempt_status,
                "result_refs": result_refs,
                "decision": decision,
                "reason_code": reason,
                "started_at": started_at,
                "finished_at": now,
                "latency_ms": max(0, round((now - started_at) * 1000)),
            }
            if accepted:
                attempt["file_fingerprints"] = dict(receipt.file_fingerprints)
            state["attempts"].append(attempt)
            result = SubmissionResult(
                attempt_id, attempt_status, state["status"], decision, reason,
            )
            state["idempotency"]["submit:" + idempotency_key] = {
                "unit_id": unit_id,
                "request_unit_version": request_unit_version,
                "owner": owner,
                "receipt_digest": request_digest,
                "result": asdict(result),
            }
            state["updated_at"] = now
            self._write(state)
            return result

    def record_turn_terminal(
        self, run_id: str, *, unit_id: str, unit_version: int,
        owner: str, host: str, status: str,
        session: str | None = None, thread: str | None = None,
        turn: str | None = None,
        capabilities: HostCapabilities | None = None,
        result_refs: Iterable[str] = (),
        failure_reason: str | None = None,
        started_at: float | None = None,
        adapter_version: str | None = None, now: float | None = None,
    ) -> dict[str, Any]:
        if not isinstance(status, str) or not status or status not in ATTEMPT_TERMINALS:
            raise WorkUnitError("invalid_attempt_terminal")
        if isinstance(unit_version, bool) or not isinstance(unit_version, int):
            raise WorkUnitError("invalid_attempt_unit_version")
        _validate_identity(owner=owner)
        result_refs, started_at, now = _attempt_metadata(
            host=host, session=session, thread=thread, turn=turn,
            result_refs=result_refs, failure_reason=failure_reason,
            started_at=started_at, adapter_version=adapter_version, now=now,
            capabilities=capabilities,
        )
        execution_mode: ExecutionMode | None = None
        if capabilities is not None:
            if capabilities.host != host:
                raise WorkUnitError("attempt_host_mismatch")
            execution_mode = select_execution_mode(capabilities)
        with self._lock(run_id):
            state = self._read(run_id)
            record = state["units"].get(unit_id)
            if record is None or record.get("run_id") != run_id:
                raise WorkUnitError("attempt_unit_mismatch")
            if record.get("version") != unit_version:
                raise WorkUnitError("attempt_unit_version_mismatch")
            if record.get("lease_owner") != owner:
                raise WorkUnitError("lease_owner_mismatch")
            finished_at = _timestamp(now)
            if record.get("state") != "leased" or record.get("lease_expires_at", 0) <= finished_at:
                raise WorkUnitError("lease_expired")
            if any(
                attempt.get("unit_id") == unit_id
                and attempt.get("unit_version") == unit_version
                and attempt.get("host") == host
                and attempt.get("turn_ref") == _opaque_ref(turn)
                for attempt in state["attempts"]
            ):
                raise WorkUnitError("duplicate_attempt_terminal")
            # A successful host terminal only means that a candidate Receipt
            # may still arrive.  Failure terminals release the lease for a
            # versioned retry immediately, instead of forcing the user to
            # wait for expiry after a disconnected host.
            if status in {
                "rejected", "interrupted", "host_error", "malformed_result",
                "awaiting_approval",
            }:
                record["state"] = "retry"
            attempt_started_at = started_at if started_at is not None else finished_at
            if state["status"] == "completed":
                decision = "done"
            elif status == "succeeded":
                # A host terminal is not Receipt acceptance. Keep the lease
                # available to its owner while Core waits for explicit proof.
                decision = "await_receipt"
            elif status == "awaiting_approval":
                decision = "await_approval"
            else:
                decision = "retry"
            state["attempts"].append({
                "attempt_id": "attempt-" + uuid.uuid4().hex,
                "unit_id": unit_id,
                "unit_version": unit_version,
                "host": host,
                "session_ref": _opaque_ref(session),
                "thread_ref": _opaque_ref(thread),
                "turn_ref": _opaque_ref(turn),
                "capabilities": asdict(capabilities) if capabilities else {},
                "execution_mode": execution_mode.value if execution_mode else None,
                "adapter_version": adapter_version,
                "result_refs": list(result_refs),
                "decision": decision,
                "reason_code": failure_reason,
                "status": status,
                "started_at": attempt_started_at,
                "finished_at": finished_at,
                "latency_ms": max(0, round((finished_at - attempt_started_at) * 1000)),
            })
            self._write(state)
        return {
            "workflow_status": state["status"],
            "decision": decision,
        }

    def status(self, run_id: str) -> dict[str, Any]:
        state = self._read(run_id)
        return {
            "run_id": run_id,
            "workflow_id": state["workflow_id"],
            "status": state["status"],
            "step_id": self._template(state).step_id,
            "guarantee_level": "guided",
            "stop_hook_required": False,
            "single_writer": "core",
        }

    def import_legacy(self, path: Path) -> WorkflowRun:
        """Import v1/v2 state without modifying or replacing the source file."""
        try:
            source = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkUnitError("invalid_legacy_state") from exc
        version = source.get("schema_version")
        if version not in {1, 2}:
            raise WorkUnitError("unsupported_legacy_schema")
        run = self.start(
            "project-plan",
            goal="legacy:" + str(source.get("story_id", "")),
            story_id=source.get("story_id"),
        )
        with self._lock(run.run_id):
            state = self._read(run.run_id)
            state["source_schema_version"] = version
            state["legacy_source_fingerprint"] = _fingerprint(path)
            state["legacy_status"] = source.get("status")
            # Terminal legacy runs are immutable historical facts.  A blocked
            # handoff is also not executable until a deliberate recovery path
            # is added, otherwise importing it silently loses the blocker.
            if source.get("status") in {"completed", "blocked"}:
                state["status"] = "completed"
                if source.get("status") == "blocked":
                    state["status"] = "blocked"
                    state["legacy_blocker"] = source.get("blocker")
            self._write(state)
        return self._run(state)

    def complete(self, run_id: str, *, fingerprints: dict[str, str]) -> dict[str, Any]:
        """Reject the legacy direct-completion API for journaled Plan runs.

        A Plan completion is also a governance transaction.  Marking the run
        completed before Story, Board, context, and journal projections are
        committed would create an authoritative false completion.
        """
        del run_id, fingerprints
        raise WorkUnitError("finalize_must_use_plan_finalizer")

    def _complete_locked(
        self, state: dict[str, Any], fingerprints: dict[str, str],
    ) -> dict[str, Any]:
        if self._template(state).step_id != "finalize_plan":
            raise WorkUnitError("finalize_not_ready")
        state["fingerprints"].update(fingerprints)
        state["status"] = "completed"
        state["updated_at"] = time.time()
        self._write(state)
        return state

    def plan_ready_to_finalize(self, state: dict[str, Any]) -> bool:
        """Return whether Core accepted every Plan unit before finalize."""
        if state["workflow_id"] != "project-plan":
            return False
        if self._template(state).step_id != "finalize_plan":
            return False
        required = {item.step_id for item in PLAN_WORK_UNITS[:-1]}
        succeeded = {
            record["step_id"] for record in state["units"].values()
            if record.get("state") == "succeeded"
        }
        return required <= succeeded

    def workflow_ready_to_finalize(self, state: dict[str, Any]) -> bool:
        """Return whether every non-terminal unit was accepted by Core."""
        templates = WORKFLOW_UNITS[state["workflow_id"]]
        terminal = templates[-1].step_id
        if state["workflow_id"] == "project-plan" or self._template(state).step_id != terminal:
            return False
        succeeded = {
            record["step_id"] for record in state["units"].values()
            if record.get("state") == "succeeded"
        }
        return {item.step_id for item in templates[:-1]} <= succeeded


class PlanFinalizer:
    """Idempotent, journaled transaction for Plan governance projections."""

    def __init__(self, root: Path, engine: WorkflowEngine):
        self.root = root.resolve()
        self.engine = engine

    def _journal_path(self, run_id: str) -> Path:
        return self.root / ".pactkit/finalize" / f"{run_id}.json"

    @contextmanager
    def _projection_lock(self):
        """Serialize the shared Board/context projection transaction."""
        import fcntl

        path = self.root / ".pactkit/finalize" / "projections.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def _story_lock(self, story_id: str):
        import fcntl

        _validate_story_id(story_id)
        path = self.root / ".pactkit/finalize" / f"{story_id}.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _write_board(self) -> None:
        from pactkit.governance import BoardRenderer, StoryRepository

        renderer = BoardRenderer(StoryRepository(self.root))
        atomic_write(self.root / "docs/product/sprint_board.md", renderer.render())

    def _write_context(self) -> None:
        from pactkit.context_gen import context_output_path, generate_context

        atomic_write(
            context_output_path(self.root),
            generate_context(self.root, command="pactkit finalize-plan"),
        )

    @staticmethod
    def _save_journal(path: Path, journal: dict[str, Any]) -> None:
        atomic_write(
            path, json.dumps(journal, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        )

    def _validate_journal(
        self, journal: Any, *, run_id: str, story_id: str, idempotency_key: str,
        request_digest: str, state: dict[str, Any],
    ) -> None:
        """Reject a malformed or forged durable finalize checkpoint.

        A completed journal is recovery evidence, not an authority to mark a
        running workflow complete.  It must agree with the Core run state and
        its persisted projection fingerprints.
        """
        if not isinstance(journal, dict) or journal.get("stage") not in {
            "validated", "story", "board", "context", "completed",
        }:
            raise WorkUnitError("corrupt_finalize_journal")
        if (
            journal.get("run_id") != run_id
            or journal.get("story_id") != story_id
            or journal.get("idempotency_key") != idempotency_key
            or journal.get("request_digest") != request_digest
        ):
            raise WorkUnitError("finalize_idempotency_conflict")
        if journal["stage"] == "completed":
            fingerprints = journal.get("fingerprints")
            if (
                state.get("status") != "completed"
                or not isinstance(fingerprints, dict)
                or set(fingerprints) != {"spec", "hld", "story", "board", "context"}
                or not all(
                    isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                    for value in fingerprints.values()
                )
                or not isinstance(state.get("fingerprints"), dict)
                or any(
                    state["fingerprints"].get(name) != value
                    for name, value in fingerprints.items()
                )
            ):
                raise WorkUnitError("corrupt_finalize_journal")
            _validate_finalize_projection_fingerprints(
                self.root, story_id, fingerprints,
                story_contract=journal.get("story_contract"),
                error_code="corrupt_finalize_journal",
            )

    def finalize(
        self, run_id: str, *, story_id: str, title: str, tasks: list[str],
        idempotency_key: str,
    ) -> dict[str, Any]:
        _validate_identity(idempotency_key=idempotency_key)
        request_digest = _finalize_request_digest(
            run_id=run_id, story_id=story_id, title=title, tasks=tasks,
        )
        # All multi-resource workflow operations acquire Story before Run.
        # bind_story() uses the same order; reversing it here would deadlock
        # a concurrent bind and finalize on the same Story.
        with self._projection_lock(), self._story_lock(story_id), self.engine._lock(run_id):
                state = self.engine._read(run_id, allow_finalize_recovery=True)
                if state.get("story_id") != story_id:
                    raise WorkUnitError("story_identity_mismatch")
                if state["status"] == "completed":
                    journal_path = self._journal_path(run_id)
                    try:
                        completed_journal = json.loads(journal_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        raise WorkUnitError("corrupt_finalize_journal") from exc
                    self._validate_journal(
                        completed_journal, run_id=run_id, story_id=story_id,
                        idempotency_key=idempotency_key, request_digest=request_digest,
                        state=state,
                    )
                    if completed_journal.get("stage") == "completed":
                        return state
                    if completed_journal.get("stage") != "context":
                        raise WorkUnitError("corrupt_finalize_journal")
                    _validate_finalize_projection_fingerprints(
                        self.root, story_id, {
                            name: state["fingerprints"].get(name)
                            for name in ("spec", "hld", "story", "board", "context")
                        },
                        story_contract=completed_journal.get("story_contract"),
                        error_code="corrupt_finalize_journal",
                    )
                    completed_journal["stage"] = "completed"
                    completed_journal["fingerprints"] = {
                        name: state["fingerprints"][name]
                        for name in ("spec", "hld", "story", "board", "context")
                    }
                    self._save_journal(journal_path, completed_journal)
                    return state
                if not self.engine.plan_ready_to_finalize(state):
                    raise WorkUnitError("finalize_not_ready")

                journal_path = self._journal_path(run_id)
                journal: dict[str, Any] = {
                    "run_id": run_id,
                    "idempotency_key": idempotency_key,
                    "request_digest": request_digest,
                    "stage": "new",
                }
                if journal_path.is_file():
                    try:
                        journal = json.loads(journal_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        raise WorkUnitError("corrupt_finalize_journal") from exc
                    self._validate_journal(
                        journal, run_id=run_id, story_id=story_id,
                        idempotency_key=idempotency_key, request_digest=request_digest,
                        state=state,
                    )
                    if journal.get("stage") == "completed":
                        return state

                spec = self.root / "docs/specs" / f"{story_id}.md"
                hld = self.root / "docs/architecture/graphs/system_design.mmd"
                from pactkit.skills.spec_linter import validate_spec

                if (
                    not spec.is_file() or not hld.is_file()
                    or not validate_spec(str(spec)).passed
                ):
                    raise WorkUnitError("plan_artifact_validation_failed")
                journal.update({"stage": "validated", "story_id": story_id})
                self._save_journal(journal_path, journal)

                from pactkit.governance import StoryRepository

                repository = StoryRepository(self.root)
                story_path = repository.path_for(story_id)
                if story_path.is_file():
                    record = repository.load(story_id)
                    if (
                        record["title"] != title
                        or [item["title"] for item in record["tasks"]] != tasks
                    ):
                        raise WorkUnitError("existing_story_mismatch")
                else:
                    repository.add(story_id, title, tasks)
                record = repository.load(story_id)
                journal["story_contract"] = {
                    "title": record["title"],
                    "spec_path": record["spec_path"],
                    "tasks": [
                        {"id": task["id"], "title": task["title"]}
                        for task in record["tasks"]
                    ],
                }
                journal["stage"] = "story"
                self._save_journal(journal_path, journal)

                self._write_board()
                journal["stage"] = "board"
                self._save_journal(journal_path, journal)
                self._write_context()
                journal["stage"] = "context"
                self._save_journal(journal_path, journal)

                fingerprints = {
                    "spec": _fingerprint(spec), "hld": _fingerprint(hld),
                    "story": _fingerprint(story_path),
                    "board": _fingerprint(self.root / "docs/product/sprint_board.md"),
                    "context": _fingerprint(self.root / ".pactkit/context.md"),
                }
                result = self.engine._complete_locked(state, fingerprints)
                journal["stage"] = "completed"
                journal["fingerprints"] = fingerprints
                self._save_journal(journal_path, journal)
                return result


class WorkflowFinalizer:
    """Journaled completion for every native workflow except Plan."""

    def __init__(self, root: Path, engine: WorkflowEngine):
        self.root = root.resolve()
        self.engine = engine

    def _journal_path(self, run_id: str) -> Path:
        return self.root / ".pactkit/finalize" / f"{run_id}.json"

    @staticmethod
    def _save(path: Path, journal: dict[str, Any]) -> None:
        atomic_write(
            path, json.dumps(journal, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        )

    def finalize(
        self, run_id: str, receipt: EvidenceReceipt, *, owner: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        _validate_identity(owner=owner, idempotency_key=idempotency_key)
        shape_reason = _receipt_shape_reason(receipt)
        if shape_reason is not None:
            raise WorkUnitError(shape_reason)
        initial = self.engine._read(run_id, allow_finalize_recovery=True)
        if initial["workflow_id"] == "project-plan":
            raise WorkUnitError("plan_requires_plan_finalizer")
        if initial["status"] != "completed":
            if not self.engine.workflow_ready_to_finalize(initial):
                raise WorkUnitError("finalize_not_ready")
            completion_evidence = self._completion_evidence(initial, receipt)
            self._validate_completion(initial, completion_evidence)
            for name, digest in initial["fingerprints"].items():
                if _fingerprint(_safe_repo_path(self.root, name)) != digest:
                    raise WorkUnitError("artifact_drift")
            submission = self.engine.submit(
                receipt.unit_id, receipt, owner=owner,
                idempotency_key=idempotency_key + ":receipt",
            )
            if submission.attempt_status != "succeeded":
                raise WorkUnitError("workflow_completion_validation_failed")
        with self.engine._lock(run_id):
            state = self.engine._read(run_id, allow_finalize_recovery=True)
            if state["workflow_id"] == "project-plan":
                raise WorkUnitError("plan_requires_plan_finalizer")
            record = state["units"].get(receipt.unit_id)
            if record is None or record.get("step_id") != self.engine._template(state).step_id:
                raise WorkUnitError("finalize_not_ready")
            request_digest = _generic_finalize_request_digest(
                run_id=run_id, workflow_id=state["workflow_id"],
                story_id=state.get("story_id"), claims=receipt.claims,
                fingerprints=state["fingerprints"],
            )
            journal_path = self._journal_path(run_id)
            journal = None
            if journal_path.is_file():
                try:
                    journal = json.loads(journal_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise WorkUnitError("corrupt_finalize_journal") from exc
                if (
                    not isinstance(journal, dict)
                    or journal.get("run_id") != run_id
                    or journal.get("workflow_id") != state["workflow_id"]
                    or journal.get("story_id") != state.get("story_id")
                    or journal.get("idempotency_key") != idempotency_key
                    or journal.get("request_digest") != request_digest
                    or journal.get("stage") not in {"validated", "governance", "completed"}
                ):
                    raise WorkUnitError("finalize_idempotency_conflict")
            if state["status"] == "completed":
                if journal is None or journal.get("stage") not in {
                    "validated", "governance", "completed",
                }:
                    raise WorkUnitError("corrupt_finalize_journal")
                if state["workflow_id"] == "project-act":
                    self._complete_act_story_tasks(state, journal["claims"])
                if journal["stage"] != "completed":
                    journal["stage"] = "completed"
                    self._save(journal_path, journal)
                return state
            if not self.engine.workflow_ready_to_finalize(state):
                raise WorkUnitError("finalize_not_ready")
            completion_evidence = self._completion_evidence(state, receipt)
            self._validate_completion(state, completion_evidence)
            for name, digest in state["fingerprints"].items():
                if _fingerprint(_safe_repo_path(self.root, name)) != digest:
                    raise WorkUnitError("artifact_drift")
            if journal is None:
                journal = {
                    "run_id": run_id, "workflow_id": state["workflow_id"],
                    "story_id": state.get("story_id"), "idempotency_key": idempotency_key,
                    "request_digest": request_digest, "stage": "validated",
                    "claims": completion_evidence,
                    "fingerprints": dict(state["fingerprints"]),
                }
                self._save(journal_path, journal)
            if state["workflow_id"] == "project-act":
                self._complete_act_story_tasks(state, journal["claims"])
                journal["stage"] = "governance"
                self._save(journal_path, journal)
            state["status"] = "completed"
            state["updated_at"] = time.time()
            self.engine._write(state)
            journal["stage"] = "completed"
            self._save(journal_path, journal)
            return state

    @staticmethod
    def _completion_evidence(
        state: dict[str, Any], receipt: EvidenceReceipt,
    ) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        for unit_record in state["units"].values():
            if unit_record.get("state") == "succeeded":
                evidence.update(unit_record.get("accepted_claims", {}))
        evidence.update(receipt.claims)
        return evidence

    def _validate_completion(
        self, state: dict[str, Any], evidence: dict[str, Any],
    ) -> None:
        if state["workflow_id"] == "project-act":
            if not self._validate_pdca_completion(state["workflow_id"], evidence):
                raise WorkUnitError("workflow_completion_validation_failed")
            return
        from pactkit.workflow_validators import project_command_validator

        try:
            project_command_validator(self.root).validate(
                state, "completed", evidence, "completed",
            )
        except ValueError as exc:
            raise WorkUnitError("workflow_completion_validation_failed") from exc

    def _complete_act_story_tasks(
        self, state: dict[str, Any], evidence: dict[str, Any],
    ) -> None:
        """Apply verified Act task completion as a recoverable Core projection."""
        story_id = state.get("story_id")
        board_tasks = evidence.get("board_tasks")
        if not isinstance(story_id, str) or not isinstance(board_tasks, list):
            raise WorkUnitError("workflow_completion_validation_failed")
        try:
            from pactkit.governance import BoardRenderer, StoryRepository

            repository = StoryRepository(self.root)
            record = repository.load(story_id)
            canonical = [task["title"] for task in record["tasks"]]
            if canonical != board_tasks:
                raise WorkUnitError("workflow_completion_validation_failed")
            completed = {task["title"] for task in record["tasks"] if task["completed"]}
            for task in canonical:
                if task not in completed:
                    repository.complete_task(story_id, task)
            atomic_write(
                self.root / "docs/product/sprint_board.md",
                BoardRenderer(repository).render(),
            )
            # STORY-slim-2026082466c8670d9655 R1: regenerate context.md to the
            # post-completion canonical AFTER complete_task flipped the story to
            # done, so a later workflow's finalize does not leave context.md
            # reflecting pre-completion counts (which would make earlier plan
            # runs' context projection re-validation fail).
            from pactkit.context_gen import context_output_path, generate_context

            atomic_write(
                context_output_path(self.root),
                generate_context(self.root, command="pactkit finalize-workflow"),
            )
            self._validate_act_story_projection(story_id, board_tasks)
        except WorkUnitError:
            raise
        except Exception as exc:
            raise WorkUnitError("workflow_completion_validation_failed") from exc

    def _validate_act_story_projection(
        self, story_id: str, board_tasks: list[str],
    ) -> None:
        """Fail closed unless Story task state and its Board projection agree."""
        try:
            from pactkit.governance import BoardRenderer, StoryRepository

            repository = StoryRepository(self.root)
            record = repository.load(story_id)
            if (
                [task["title"] for task in record["tasks"]] != board_tasks
                or not record["tasks"]
                or not all(task["completed"] for task in record["tasks"])
                or record["status"] != "done"
                or not BoardRenderer(repository).check(
                    self.root / "docs/product/sprint_board.md",
                )
            ):
                raise WorkUnitError("workflow_completion_validation_failed")
        except WorkUnitError:
            raise
        except Exception as exc:
            raise WorkUnitError("workflow_completion_validation_failed") from exc

    @staticmethod
    def _validate_pdca_completion(workflow_id: str, evidence: dict[str, Any]) -> bool:
        if workflow_id == "project-act":
            tests = evidence.get("story_tests")
            board_tasks = evidence.get("board_tasks")
            return (
                isinstance(tests, dict) and tests.get("exit_code") == 0
                and evidence.get("regression") == "pass"
                and evidence.get("lint") == "pass"
                and isinstance(evidence.get("coverage"), dict)
                and bool(evidence["coverage"]) and all(evidence["coverage"].values())
                and isinstance(evidence.get("acceptance_coverage"), dict)
                and bool(evidence["acceptance_coverage"])
                and all(evidence["acceptance_coverage"].values())
                and isinstance(board_tasks, list) and bool(board_tasks)
                and all(isinstance(task, str) and task.strip() for task in board_tasks)
            )
        if workflow_id == "project-check":
            tests = evidence.get("tests")
            return (
                evidence.get("security_scan") == "pass"
                and evidence.get("quality_scan") == "pass"
                and evidence.get("spec_alignment") == "pass"
                and isinstance(tests, dict) and tests.get("exit_code") == 0
            )
        if workflow_id == "project-done":
            git = evidence.get("git")
            return (
                evidence.get("audit") == "pass"
                and evidence.get("governance") == "pass"
                and evidence.get("deployment") == "pass"
                and isinstance(git, dict)
                and (git.get("mode") == "no_git" or bool(git.get("commit")))
            )
        return False
