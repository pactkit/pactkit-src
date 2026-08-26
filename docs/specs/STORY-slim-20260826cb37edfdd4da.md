# STORY-slim-20260826cb37edfdd4da: Freeze and isolate the legacy workflow engine with a data-driven deletion track

| Field | Value |
|-------|-------|
| ID | STORY-slim-20260826cb37edfdd4da |
| Status | Done |
| Priority | P1 |
| Release | 2.23.0 |

## Background

The WorkUnit engine (workflow_engine.py, 3154 lines) plus
host_continuation.py (208 lines) exist to simulate completion-guarantee
semantics on hosts without hooks — historically driven by Codex
adaptation. The HLD already classifies their entry points as
"Legacy / Explicit Compatibility APIs (Non-default)": the default PDCA
execution path (native sessions + prompt-driven commands) does not
traverse them. Yet they remain in the core package at full maintenance
cost — the 2026-08-26 review found ~20 defects there, and one full
Sprint story (STORY-slim-202608267c3989223b4d) plus QA iterations were
spent hardening a non-default path.

Verified dependency surface (2026-08-26):

- deploy_manifest.py imports only CORE_PROTOCOL_VERSION (a constant).
- doctor.py imports WorkflowEngine, WorkUnitError, and
  _validate_workflow_state for corrupt-run diagnostics.
- cli.py imports both engines only for the explicit `workflow`,
  `work-unit`, and `continuation` subcommands.
- continuation.py does NOT import workflow_engine (independent), and it
  has ACTIVE consumers (governance.py and skills/scaffold.py call
  ContinuationEngine.validate_managed_operation as a live validation
  gate; context_gen.py and garden.py use ContinuationStore read APIs) —
  so continuation.py stays in the core.
- No adapter package (pactkit-codex / pactkit-copilot /
  pactkit-opencode, grep-verified) imports the engine directly.

Lateral scan: the extract-and-reexport pattern already exists in-repo
(generators/claude_md.py extraction with a compatibility re-export,
2026-08-26) — this Spec reuses it.

## Requirements

### R1: Frozen legacy package (MUST)

workflow_engine.py and host_continuation.py MUST move to a frozen
subpackage (src/pactkit/legacy/) whose modules carry a FROZEN marker
docstring: no new features, bugfix-only, deletion candidate. The public
import paths (pactkit.workflow_engine, pactkit.host_continuation) MUST
keep working via compatibility re-export shims for the entire
deprecation window. continuation.py MUST remain in the core package
(active validation-gate and read consumers).

### R2: Active-dependency relocation (MUST)

CORE_PROTOCOL_VERSION MUST move to a neutral module (single source of
truth) consumed by deploy_manifest and the legacy package. doctor's
run-file diagnostics MUST keep working unchanged (importing from the
legacy package is acceptable for diagnostics; behavior MUST be
byte-identical). Zero behavior change for every CLI subcommand.

### R3: Usage instrumentation (MUST)

Each explicit legacy entry point (`pactkit workflow`, `pactkit
work-unit`, `pactkit continuation`) MUST increment a machine-local
usage counter (~/.pactkit/legacy-engine-usage.json: count + first/last
seen dates) on invocation. Machine-local, not project-local: per-machine
usage is the deletion signal, and STORY-slim-146 pins the project
.pactkit tree write-free for read-only continuation commands
(amendment 2026-08-26). The counter MUST NOT record command arguments or
any content beyond the command name. doctor MUST surface the counter
("legacy engine invocations: N since DATE"). Test invocations MUST NOT
count: a PACTKIT_DISABLE_USAGE_COUNTING kill-switch is honored by the
recorder and set by the e2e test harness (amendment 2026-08-26). validate_managed_operation
calls from active gates MUST NOT be counted — only user-initiated
explicit invocations.

### R4: Deletion decision gate (MUST)

The Spec MUST define the deletion criterion: after one minor release
cycle, if the usage counters on the maintainer's and internal team's
machines show zero explicit invocations, the legacy package is deleted
in the next release (deprecation notice in CHANGELOG + doctor warning
in the release prior). The decision is recorded in the Story notes, not
automated — no telemetry, no remote collection.

### R5: Test migration (MUST)

All engine tests MUST continue to pass unmodified in behavior (import
paths may be updated). The frozen modules MUST remain covered by the
existing suite; coverage MUST NOT drop.

## Acceptance Criteria

### AC1: public import paths survive (R1)

- **Given** external code importing pactkit.workflow_engine and pactkit.host_continuation
- **When** the refactor lands
- **Then** both imports resolve to the legacy package modules

### AC2: zero behavior change (R2)

- **Given** the CLI before and after
- **When** `pactkit workflow list`, `pactkit continuation resume X`, and `pactkit doctor` run against a fixture state
- **Then** outputs are byte-identical (doctor may gain the usage line only)

### AC3: usage counter increments (R3)

- **Given** no counter file
- **Given** HOME redirected to a temp directory
- **When** `pactkit workflow list` runs
- **Then** ~/.pactkit/legacy-engine-usage.json exists with count 1 and a last-seen date of today

### AC4: active gates are not counted (R3)

- **Given** governance/scaffold invoking validate_managed_operation
- **When** those code paths run
- **Then** the usage counter does not change

### AC5: doctor surfaces usage (R3)

- **Given** a counter file with N invocations
- **When** pactkit doctor runs
- **Then** the report includes the legacy engine invocation count

### AC6: frozen marker present (R1)

- **Given** the legacy package modules
- **When** read
- **Then** each module docstring declares the FROZEN policy and the deletion criterion

### AC7: deprecation notice published (R4)

- **Given** the release containing this story
- **When** CHANGELOG.md is read
- **Then** the legacy engine is declared a deletion candidate with the one-release-cycle usage criterion stated

### AC8: engine tests survive the move (R5)

- **Given** the engine test files after import-path updates
- **When** the full suite runs
- **Then** all previously passing engine tests pass and no test file is deleted

## Target Call Chain

```
cli.py (workflow / work-unit / continuation subcommands)
  → [instrumentation: usage counter]                [R3]
  → src/pactkit/legacy/workflow_engine.py           [R1 — moved, frozen]
  → src/pactkit/legacy/host_continuation.py         [R1 — moved, frozen]
  → src/pactkit/workflow_engine (shim re-export)    [R1 — compatibility]
pactkit/protocols.py (CORE_PROTOCOL_VERSION)        [R2 — neutral home]
  → deploy_manifest.py, legacy package
doctor.py → legacy validators + usage surfacing     [R2/R3]
continuation.py — UNCHANGED (active gates/readers)  [R1]
```

## Implementation Inputs

| Path | Mode | Range | Required |
|------|------|-------|----------|
| src/pactkit/workflow_engine.py | interface | all | MUST |
| src/pactkit/cli.py | interface | all | MUST |

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | tests/unit/ | RED: AC1-AC6 (import shims, counter, doctor line, frozen markers) | None | Low |
| 2 | src/pactkit/protocols.py | New neutral constants module (CORE_PROTOCOL_VERSION) | None | Low |
| 3 | src/pactkit/legacy/ | Move workflow_engine.py + host_continuation.py; FROZEN docstrings; shims at old paths | Step 2 | Medium |
| 4 | src/pactkit/cli.py + deploy_manifest.py + doctor.py | Re-point imports; usage instrumentation in the three legacy handlers; doctor usage line | Steps 2-3 | Medium |
| 5 | tests/ | Update import paths where needed; full regression | Steps 2-4 | Low |
| 6 | CHANGELOG.md | Deprecation notice for the legacy engine (deletion candidate, criterion) | Steps 2-5 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-2 | Yes | Usage counter writes a local JSON file — MUST validate shape on read and never execute recorded content |
| SEC-7 | No | Doctor line prints counts only, no paths beyond project root |
| Others | N/A | Pure relocation + local counter, no new network/auth/DB surface |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None (Story 5 subtraction pass touches workflow_engine too — coordinate ordering: this story lands FIRST, Story 5's engine-scope items re-target the legacy package or drop) |
| Provides | Frozen legacy package; usage counter; neutral protocols module |
| Touches | src/pactkit/legacy/ (new), src/pactkit/workflow_engine.py (shim), src/pactkit/host_continuation.py (shim), src/pactkit/protocols.py (new), src/pactkit/cli.py, src/pactkit/doctor.py, src/pactkit/deploy_manifest.py, tests/, CHANGELOG.md |
| Conflict risk | MEDIUM — overlaps STORY-slim-2026082672b57c78fd67 (subtraction pass) on workflow_engine.py; ordering constraint documented |

## Out of Scope

- Deleting the legacy package (gated by R4 usage data after one release cycle)
- Moving continuation.py (active consumers depend on it)
- Any engine behavior change (bugfix-only freeze; today's robustness fixes remain)
- Separate PyPI package split (in-repo frozen subpackage chosen: zero release-pipeline cost, fully reversible)
