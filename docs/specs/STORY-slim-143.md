# STORY-slim-143: Spec Dependency Surface & Story DAG (spec-graph)

| Field | Value |
|-------|-------|
| ID | STORY-slim-143 |
| Status | Done |
| Priority | P1 |
| Release | 2.19.0 |

## Background

/project-plan currently writes each Spec in isolation — there is no structured record of *what a story depends on*, *what public surface it provides*, or *which files it will touch*. Plan Phase 3.3 only suggests "record story dependencies if applicable" via Memory MCP (optional, unstructured). Consequences:

1. When multiple stories are implemented in parallel (multiple agents / worktrees), file-level conflicts are only discovered at merge time.
2. Story execution order （先后顺序） is implicit in the architect's head, not computable — nothing can topologically sort the board.
3. `/project-sprint` today runs strictly one story at a time; safe parallel scheduling requires machine-readable dependency data.

This story adds a **Dependency Surface** section to the Spec schema, lints it, and introduces `pactkit spec-graph` — a deterministic CLI that parses all Specs and emits a story dependency DAG, topological execution waves, and a file-overlap conflict matrix. Downstream stories (sprint wave orchestration, interface-first contract staging, merge-preflight) consume this data but are out of scope here.

## Requirements

### R1: Dependency Surface Schema (MUST)

`schemas.py` MUST define a new optional Spec section `## Dependency Surface` (added to `SPEC_TEMPLATE` and `SPEC_OPTIONAL_SECTIONS`, registered in `SCHEMA_REGISTRY`) with exactly four pipe-table fields:

| Field | Value |
|-------|-------|
| Depends on | comma-separated story IDs this story consumes, each with a `needs:` note (e.g. `STORY-143 (needs: spec-graph CLI)`), or `None` |
| Provides | public surface this story adds (CLI commands, exported functions, schema constants), or `None` |
| Touches | glob-level file paths this story expects to modify (e.g. `src/pactkit/cli.py`, `src/pactkit/skills/*.py`) |
| Conflict risk | `LOW` / `MEDIUM` / `HIGH` + free-text reason |

Schema constants (section name, field names, risk levels) MUST live in `schemas.py` as named constants — no magic strings in parser/linter/CLI.

### R2: Linter Rules for Dependency Surface (MUST)

`spec_linter.py` MUST add checks, invoked from `validate_spec()` following the existing `_check_*` call-sequence pattern:

- **New ERROR rule**: a `Depends on` entry references a story ID that has no corresponding file in the specs dir (dangling dependency) — typo protection, since ordering decisions rely on these edges.
- **New WARNING rule**: `## Dependency Surface` section is missing or its table lacks any of the four required fields.

Both rules MUST reuse the existing `_find_section` / `_section_text` parsing helpers — no fourth copy of section-parsing regexes.

### R3: `pactkit spec-graph` CLI (MUST)

New module `src/pactkit/spec_graph.py` + `spec-graph` subcommand in `cli.py` (argparse subparser + dispatch chain, same pattern as `spec-lint`). Given `--specs-dir docs/specs` (default), it MUST:

1. Parse every Spec's Dependency Surface table (reusing spec_linter parsing helpers).
2. Build the story DAG from `Depends on` edges (excluding edges to stories already `Status | Done`, which are satisfied).
3. Topologically sort into **execution waves**: wave N contains all stories whose remaining dependencies are all in waves < N. Stories in the same wave are parallelizable.
4. Compute a **conflict matrix**: pairs of stories whose `Touches` globs overlap (same literal path or glob intersection) are flagged; pairs in the same wave with overlap MUST be highlighted as unsafe-parallel.
5. Detect dependency cycles and MUST report them as an error (non-zero exit) with the cycle path — a cycle means the Specs themselves are contradictory.
6. Emit a Mermaid graph to `docs/architecture/graphs/story_graph.mmd` (`--write-graph` flag) and print the wave list + conflict matrix to stdout.

### R4: Deterministic Scheduling Semantics (MUST)

Wave assignment, overlap detection, and cycle detection MUST be computed entirely in code (LLM ≠ Calculator). The CLI output MUST be stable for identical Spec inputs — same input, same waves, same matrix ordering (sorted output, no dict-iteration nondeterminism).

### R5: Plan Playbook Integration (SHOULD)

`pactkit-plugin/commands/project-plan.md` Phase 3.2 SHOULD gain a step instructing the architect to fill the Dependency Surface from Phase 1 trace findings (touches = traced files; depends-on = stories whose Provides it consumes). Sprint parallel orchestration itself is explicitly NOT changed by this story.

## Technical Design

### Lateral Scan Results

- Operation: parse Spec metadata/section structure
- Existing implementations: 3 (`spec_linter.py` `_find_section`/`_section_text`, `done_verify.py` requirement parsing, `audit.py` status check)
- Assessment: **Reuse existing** — `spec_graph.py` and the new lint rules import spec_linter's helpers; no new regex parser is written.

### Capability Assessment

| Need | Source | Decision |
|------|--------|----------|
| Spec section/metadata parsing | `pactkit.skills.spec_linter` (project) | Reuse |
| Topological sort / cycle detection | stdlib (`graphlib.TopologicalSorter`, Python ≥ 3.9) | Enable — no new dependency |
| Glob overlap check | stdlib `fnmatch` + path normalization | Enable |
| CLI registration | `cli.py` subparser chain (project) | Reuse |

### New Implementation Required

- `pactkit/spec_graph.py`: Dependency Surface parsing → DAG → waves → conflict matrix → Mermaid emit. Single responsibility, pure functions over parsed data (testable without filesystem fixtures beyond temp specs).

### Concurrency Decision (Engineering Concern: concurrency)

No runtime concurrency in this story. The *scheduling* semantics are deterministic data: waves are computed by `graphlib`, and any future parallel executor (sprint story) consumes the wave list rather than re-deriving it. This keeps the "can these two stories run in parallel?" judgment in code, not in an LLM prompt.

## Acceptance Criteria

### AC1: Scaffolded Spec carries Dependency Surface (R1)

- **Given** a project with pactkit initialized and the new schema deployed
- **When** `scaffold.py create_spec "STORY-x-999" "demo"` is run
- **Then** the generated Spec contains `## Dependency Surface` with all four fields (Depends on / Provides / Touches / Conflict risk) and `pactkit spec-lint` on it reports 0 errors and 0 warnings for the new rules.

### AC2: Dangling dependency is rejected (R2)

- **Given** a Spec whose `Depends on` includes `STORY-slim-999` and no such file exists in the specs dir
- **When** `pactkit spec-lint` runs on that Spec
- **Then** it reports the new ERROR rule naming the dangling ID, and exits non-zero.

### AC3: Missing section is a warning (R2)

- **Given** an otherwise-valid Spec with no `## Dependency Surface` section (e.g. all pre-2.19 Specs)
- **When** `pactkit spec-lint` runs on it
- **Then** the new WARNING fires but existing rules are unaffected.

### AC4: Waves and conflict matrix from real Specs (R3, R4)

- **Given** three Specs: A (Depends on: None, Touches: `a.py`), B (Depends on: A, Touches: `b.py`), C (Depends on: None, Touches: `a.py`)
- **When** `pactkit spec-graph` runs
- **Then** output shows wave 1 = {A, C}, wave 2 = {B}, and flags A↔C as a same-wave file conflict on `a.py` (unsafe-parallel).

### AC5: Cycle detection (R3, R4)

- **Given** two Specs that depend on each other
- **When** `pactkit spec-graph` runs
- **Then** it exits non-zero and prints the cycle path (e.g. `A -> B -> A`).

### AC6: Deterministic output (R4)

- **Given** any fixed set of Specs
- **When** `pactkit spec-graph` runs twice
- **Then** wave lists and conflict matrix are byte-identical (sorted, stable ordering).

### AC7: Plan playbook documents the step (R5)

- **Given** the updated `project-plan.md` playbook
- **When** reading Phase 3.2
- **Then** it contains a step instructing the architect to fill the Dependency Surface (touches from Phase 1 trace, depends-on from consumed Provides), with a pointer to the field semantics in R1.

## Target Call Chain

- CLI: `pactkit spec-graph` → `cli.py` (subparser + dispatch) → `pactkit.spec_graph.main(argv)`
- Core: `spec_graph.main` → `parse_dependency_surfaces(specs_dir)` (reuses `spec_linter._find_section` / `_section_text`) → `build_dag()` → `graphlib.TopologicalSorter` (waves) → `conflict_matrix()` (fnmatch overlap) → stdout / `story_graph.mmd`
- Lint: `pactkit spec-lint` → `spec_linter.validate_spec()` → new `_check_dependency_surface()` (dangling-ref ERROR, missing-section WARNING)
- Scaffold: `scaffold.py create_spec` → `schemas.SPEC_TEMPLATE` (now includes Dependency Surface)

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | `pactkit spec-graph` CLI; `pactkit.spec_graph` module; `DEP_SURFACE_*` schema constants; 2 new spec-lint rules |
| Touches | `src/pactkit/schemas.py`, `src/pactkit/skills/spec_linter.py`, `src/pactkit/spec_graph.py` (new), `src/pactkit/cli.py`, `pactkit-plugin/commands/project-plan.md`, `tests/unit/test_story_slim143_spec_graph.py` (new), `tests/unit/test_story042_spec_linter.py` |
| Conflict risk | LOW — schemas.py and cli.py are frequently touched, but changes are append-only (new section constant, new subparser), minimal overlap with typical feature stories |

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/schemas.py` | Add `DEP_SURFACE_*` constants + section in SPEC_TEMPLATE + SCHEMA_REGISTRY | None | Low |
| 2 | `src/pactkit/skills/spec_linter.py` | Add `_check_dependency_surface` (dangling-ref ERROR, missing-section WARNING) | Step 1 | Low |
| 3 | `src/pactkit/spec_graph.py` | New module: parse → DAG → waves (graphlib) → conflict matrix → Mermaid | Step 1 | Medium (glob-overlap edge cases) |
| 4 | `src/pactkit/cli.py` | Register `spec-graph` subparser + dispatch | Step 3 | Low |
| 5 | `tests/unit/` | TDD tests for AC1–AC6 | Steps 1–4 | Low |
| 6 | `pactkit-plugin/commands/project-plan.md` | Phase 3.2 step: fill Dependency Surface from trace findings | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | new source module spec_graph.py — code quality standards apply |
| SEC-2 | Yes | parses user-authored Spec markdown + glob paths — must tolerate malformed tables/globs without crashing |
| SEC-3 | N/A | no database/ORM (auto-detect false positive: no SQL involved) |
| SEC-4 | N/A | no frontend files |
| SEC-5 | N/A | no auth patterns |
| SEC-6 | N/A | no API/route files |
| SEC-7 | Yes | cycle detection and dangling refs must fail with clear errors, non-zero exit, no stack traces |
| SEC-8 | N/A | no new dependencies — stdlib only (graphlib, fnmatch) |

## Out of Scope

- `/project-sprint` wave-based parallel orchestration (depends on this story's Provides; separate story)
- Interface-first contract staging for depended-upon stories
- Merge-preflight conflict check (`--check-conflicts`) at agent completion time
- Auto-fixing file conflicts (spec-graph only *reports* them)
- Board format changes (board.py untouched)
