# STORY-slim-20260824dd23a0ed3b4c: Unified WorkUnit Write/Read Scope Derivation for Non-Standard Directory Layouts

| Field | Value |
|-------|-------|
| ID | STORY-slim-20260824dd23a0ed3b4c |
| Status | Draft |
| Priority | P1 |
| Release | 2.22.0 |

## Background

PactKit's `WorkflowEngine` hardcodes WorkUnit write/read scope to `src/**`, `tests/**`, `docs/**`, `.pactkit/**` in the frozen `WorkUnitTemplate` tuples (`PLAN_WORK_UNITS`, `ACT_WORK_UNITS`, `CHECK_WORK_UNITS`, `DONE_WORK_UNITS`, and the `OTHER_WORKFLOW_UNITS` hotfix `fix` unit). When a target project uses a non-standard directory layout (`frontend/src/`, `backend/migrations/`, `directus-extensions/`, `scripts/`), the implementing agent's writes to those paths fail the `fnmatch` scope gate at `_validate_receipt` (`workflow_engine.py:1807-1808`) and the WorkUnit returns `write_scope_violation`, blocking `project-act` (and `project-hotfix`).

The fix must NOT enumerate directory names in PactKit source (that becomes a fragile rule library). Instead, WorkUnit scope MUST be derived per-Story from the Spec's `Touches` declaration plus project-declared roots, using a **union** model (not intersection): the Spec is Tier-1 law and must not be clipped by mutable config.

## Requirements

### R1: Union scope model (MUST)

WorkUnit `allowed_writes`/`allowed_reads` MUST be derived at record-materialization time in `WorkflowEngine.acquire` (and `lease_current` for consistency) as a union layered ON TOP of the unit's own template scope:

```
record.scope = template.{allowed_reads, allowed_writes}  ∪  applicable config.write_scope roots  ∪  story.touches
```

- `template.{allowed_reads, allowed_writes}` — the EXISTING frozen per-Unit scope (UNCHANGED). This is the unit-specific floor (e.g. `red` = `tests/**`, `implementation` = `src/**,tests/**`). Preserving it guarantees zero behavior change (R7) by construction, since today's records already equal the templates. No separate `DEFAULT_ROOTS` constant is introduced (DRY: it would duplicate what the templates already encode).
- `applicable config.write_scope roots` — the subset of `source_roots`/`test_roots`/`docs_roots` that applies to THIS step (see R2 per-step category mapping). For `red` (tests-first), only `test_roots` apply — `source_roots` MUST NOT be granted, preserving TDD red isolation.
- `story.touches` — the Spec's `Touches` paths, parsed via the EXISTING `spec_graph._parse_touches()` (reuse, no new parser).

The union MUST be order-stable and deduped. Rationale for union over intersection: `Touches` is Tier-1 Spec law produced under governance + spec-lint; clipping it with mutable `pactkit.yaml` inverts the Hierarchy of Truth. Path-escape safety is enforced at the correct layer (R6), not at the scope gate.

### R2: Single `resolve_scope` SSoT, suite-wide (MUST)

A single function `resolve_scope(workflow_id, step_id, story_id, state, config, root) -> (allowed_reads, allowed_writes)` MUST be the canonical source of runtime scope, called by `acquire()` (and `lease_current()`) for ALL workflows — `project-act`, `project-hotfix`, `project-check`, `project-done` (Plan is excluded: it produces `Touches`, does not consume it). The frozen `WorkUnitTemplate.allowed_writes` tuples become the floor that `resolve_scope` unions onto; templates MUST NOT be edited per-layout (Open-Closed). No if/elif per workflow or per directory name.

Per-WorkUnit layer selection (which root sets + touches apply):
- `act` `implementation` writes = source_roots ∪ test_roots ∪ touches
- `act` `red` writes = test_roots ∪ touches (TDD: tests first)
- `act` `story_tests` writes = none (run-only)
- `act` `sync_coverage` writes = docs_roots
- `act` `finalize_act` writes = docs_roots ∪ .pactkit
- `check_*` / `done_preflight` / `governance_sync` reads = source_roots ∪ test_roots ∪ docs_roots ∪ touches
- `hotfix` `fix` writes = source_roots ∪ test_roots (no `touches` — hotfix has no Spec)

### R3: `write_scope` config section (MUST)

`PactKitConfig` (`config.py:144`) MUST accept a new optional top-level `write_scope` section:

```yaml
write_scope:
  source_roots: [frontend/src, backend, scripts, directus-extensions]
  test_roots: [frontend/tests, frontend/e2e, tests]
  docs_roots: [docs]
```

All three keys optional; absent `write_scope` ⇒ only `template floor ∪ touches` apply (zero-regression, see R7). The section MUST be schema-validated (reject non-list values) and round-tripped by the existing config writer.

### R4: Reuse `_parse_touches` (MUST)

Tier-1 path parsing MUST reuse `spec_graph._parse_touches()` (`spec_graph.py:80`). `resolve_scope` calls `parse_story(spec_path).touches` (or the lower-level `_parse_touches` on the Dependency Surface table) to obtain Story paths. The returned list is already fnmatch-compatible and deduped. No new parser, no duplicate parsing of `Implementation Steps` (DRY: `Touches` is the canonical "files this story modifies" field per `schemas.py:129`).

### R5: spec-lint rejects pathological `Touches` (MUST)

`spec_linter` MUST extend its `Touches` validation to reject entries that are: the bare glob `**` (repo-wide), absolute paths (leading `/`), or contain `..` (traversal). This is a deterministic Code-enforced check at Plan time (spec-lint), not a runtime scope gate. Reuse `_parse_touches` to iterate entries; apply the pathological regex.

### R6: Runtime path-escape stays in `_safe_repo_path` (MUST — no change)

Runtime path-escape prevention MUST remain the responsibility of the EXISTING `_safe_repo_path` (`workflow_engine.py:1810`), called per-fingerprint in `_validate_receipt`. R6 requires NO code change — it documents that the union model's safety does not depend on the scope gate, because `_safe_repo_path` blocks actual traversal/symlink/absolute escapes regardless of what `allowed_writes` contains. This keeps the security control deterministic and Code-enforced at the file-access layer.

### R7: Zero regression (MUST)

The frozen `WorkUnitTemplate` tuples MUST remain byte-identical to today (no per-layout edits). For projects with no `write_scope` config and `Touches` within the standard roots (including PactKit's own repo), `resolve_scope` adds nothing ⇒ `record.scope == template.scope`, identical to today's behavior. No existing test may regress.

## Acceptance Criteria

### AC1: Non-standard directory project does not block (R1, R2)

- **Given** a project whose `pactkit.yaml` declares `write_scope.source_roots: [frontend/src]` and a Spec with `Touches: frontend/src/components/Foo.vue`
- **When** `project-act` runs the `implementation` WorkUnit and the agent writes `frontend/src/components/Foo.vue`
- **Then** `_validate_receipt` returns no `write_scope_violation` and the WorkUnit completes

### AC2: Union, not intersection (R1)

- **Given** a Spec `Touches: backend/migrations/012.sql` and a project `write_scope` that does NOT list `backend`
- **When** `resolve_scope` computes the `implementation` scope
- **Then** `backend/migrations/012.sql` IS included in `allowed_writes` (union honors Tier-1 Touches; config does not clip it)

### AC3: `resolve_scope` is the single caller path (R2)

- **Given** `resolve_scope` defined and `acquire()`/`lease_current()` both routing through it
- **When** any WorkUnit is materialized for any PDCA workflow
- **Then** `allowed_writes`/`allowed_reads` on the record equals `resolve_scope(...)` output; no template tuple was edited per-layout (grep confirms `ACT_WORK_UNITS` etc. unchanged)

### AC4: `write_scope` config round-trips (R3)

- **Given** a `pactkit.yaml` with the `write_scope` section
- **When** `PactKitConfig` loads and the writer re-emits it
- **Then** the three root lists parse to lists and round-trip identically; absent section ⇒ empty roots (not an error)

### AC5: Pathological `Touches` rejected at Plan time (R5)

- **Given** a Spec whose `Touches` contains `**`, or `/abs/path`, or `../escape`
- **When** `pactkit spec-lint` runs
- **Then** lint reports an error (non-zero) naming the offending entry; the Spec cannot reach `spec_lint pass`

### AC6: Runtime escape still blocked independent of scope (R6)

- **Given** a Spec whose `Touches` is `Touches: legit/file.py` and a malicious agent that attempts to write `../outside.py`
- **When** the agent submits a receipt fingerprinting `../outside.py`
- **Then** `_validate_receipt` rejects it (via `_safe_repo_path`), regardless of `allowed_writes` containing the union

### AC7: PactKit repo regression-free (R7)

- **Given** PactKit's own repo (no `write_scope` config)
- **When** the full `tests/unit/` suite runs after the change
- **Then** all pre-existing tests pass; `resolve_scope` adds nothing and `record.scope == template.scope` (identical to today)

### AC8: `_parse_touches` reused, not re-implemented (R4)

- **Given** the implementation diff
- **When** `grep` checks for new Touches-parsing code in `resolve_scope`'s call site
- **Then** `resolve_scope` obtains Story paths by calling `spec_graph.parse_story`/`_parse_touches`; no second parser is introduced (DRY)

## Target Call Chain

`pactkit work-unit acquire` → `WorkflowEngine.acquire` (`workflow_engine.py:1539`) → record materialization at `:1587-1605`, specifically `:1596 allowed_writes = render(template.allowed_writes)` (current `{story_id}`-only) → replaced by `resolve_scope(...)` call. `lease_current` (`:1617`) routes through the same. Enforcement unchanged at `_validate_receipt` (`:1793`) → `fnmatch` gate (`:1807-1808`) → `_safe_repo_path` (`:1810`). Story paths sourced from `spec_graph.parse_story` → `_parse_touches` (`spec_graph.py:80/113`). Config roots from `PactKitConfig` (`config.py:144`).

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_resolve_scope.py` | RED: write resolve_scope tests (union, per-WorkUnit mapping, default fallback, dedup) | None | Low |
| 2 | `src/pactkit/workflow_engine.py` | Add `resolve_scope()` SSoT; call it in `acquire()` and `lease_current()` to union extra scope onto each unit's template `allowed_{reads,writes}` floor. Templates UNCHANGED | R4, R3 | Medium |
| 3 | `src/pactkit/config.py` | Add `write_scope` section to `PactKitConfig` (source/test/docs_roots lists) + schema validation + writer round-trip | None | Low |
| 4 | `src/pactkit/skills/spec_linter.py` | Extend `Touches` validation to reject `**`, absolute, `..` entries | R4 | Low |
| 5 | `tests/unit/test_resolve_scope.py` | GREEN: confirm all RED tests pass; add non-standard-dir fixture (frontend/backend) end-to-end | 2,3 | Low |
| 6 | `tests/unit/test_story_slim_work_units.py` | Add regression: pactkit repo (no write_scope) scope == today's hardcoded tuples | 2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code files modified (workflow_engine.py, config.py, spec_linter.py) |
| SEC-6 | Yes | Scope-gate logic is an access-control boundary (write_scope_violation); must not be bypassable via crafted Spec Touches |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | `resolve_scope` SSoT for WorkUnit runtime scope; `write_scope` config section; non-standard-directory project support |
| Touches | `src/pactkit/workflow_engine.py`, `src/pactkit/config.py`, `src/pactkit/skills/spec_linter.py`, `tests/unit/test_resolve_scope.py`, `tests/unit/test_story_slim_work_units.py` |
| Conflict risk | LOW |

## Out of Scope

- A `write_scope.replace_defaults` strict-minimal-privilege mode (the template floor is always unioned for now; revisit if friction shows over-permissive scope).
- Automatic build-entry inference (package.json/pyproject.toml) granting runtime scope — Tier-3 inference may only PRE-FILL config suggestions in the future, never grant at runtime.
- Per-Story `Touches` parsing from `Implementation Steps` (only `Dependency Surface.Touches` is the scope source; `Implementation Steps` is procedural guidance).
