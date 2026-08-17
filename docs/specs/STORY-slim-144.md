# STORY-slim-144: Sprint Wave Mode: conflict-aware parallel orchestration

| Field | Value |
|-------|-------|
| ID | STORY-slim-144 |
| Status | Done |
| Priority | P1 |
| Release | 2.19.0 |

## Background

`/project-sprint` (v1.5.0) orchestrates exactly ONE story per invocation: Plan → Act → Check → Close, strictly sequential in worktrees. STORY-slim-143 delivered the missing data layer — every Spec now declares a Dependency Surface, and `pactkit spec-graph` computes execution waves (topological layers) and a file-overlap conflict matrix. What remains is the **consumer**: a wave mode in sprint that runs multiple backlog stories concurrently when the data proves it safe.

Design constraints from the existing architecture:
- Backward compatible: `$ARGUMENTS` present → current single-story mode, unchanged.
- LLM ≠ Calculator: wave membership, parallel/serialize decisions, and conflict checks come from `spec-graph` output, never from orchestrator judgment.
- Safe by default: stories without a declared `Touches` (legacy/placeholder) MUST NOT be parallelized — unknown conflict surface means serialize.

## Requirements

### R1: `spec-graph --json` Machine-Readable Output (MUST)

`pactkit spec-graph` MUST accept a `--json` flag emitting `{waves: [[ids]], conflicts: [{story_a, story_b, shared, same_wave}]}` with sorted, deterministic ordering. The sprint orchestrator consumes this instead of parsing human output. Cycle errors MUST still exit non-zero (JSON or not).

### R2: Wave Mode Entry (MUST)

`commands/project-sprint.md` (source: `src/pactkit/prompts/workflows.py` SPRINT_PROMPT) MUST gain a wave mode with this entry rule:

- `$ARGUMENTS` non-empty → existing single-story mode, byte-for-byte behavior preserved.
- `$ARGUMENTS` empty → wave mode:
  1. `board.py list_stories` → BACKLOG story IDs.
  2. `pactkit spec-graph --json` → waves + conflicts, filtered to backlog IDs with existing Specs.
  3. If no parallelizable stories exist (all serialized), log and fall back to single-story suggestion.

### R3: Conflict-Aware Scheduling Policy (MUST)

Within each wave, the orchestrator MUST partition stories into:

- **Parallel batch**: stories whose Touches are all declared (no placeholder/missing) AND pairwise non-conflicting per the matrix. Batch size MUST NOT exceed `sprint.max_parallel` from pactkit.yaml (default 3, named constant — no magic value); excess stories spill to a following sub-batch.
- **Serialized tail**: stories flagged same-wave-conflict, or with undeclared Touches, run one-at-a-time after the parallel batch.

Each story (parallel or serialized) runs the EXISTING per-story PDCA chain (Plan→Act→Check→Close) in its own worktree, reusing current Stage A/B/C dispatch logic — no duplicated stage definitions (DRY).

### R4: Wave Gate & Failure Policy (MUST)

- Wave N+1 MUST NOT start until every wave-N story is merged green (worktree merged, tests passing per each story's Close stage).
- Any story failure → STOP the wave immediately (fail-fast, consistent with current single-story semantics), report which stories completed/merged vs pending, and leave remaining stories on the board. NEVER auto-retry a failed story in the same run.
- Merge conflict on worktree merge → STOP + suggest `git merge --abort` (existing error contract preserved).

### R5: Observability (SHOULD)

The orchestrator SHOULD print a wave plan before dispatching (wave N: parallel=[...], serialized=[...], skipped=[...] with reasons) so the user can abort before any subagent spawns.

## Technical Design

### Lateral Scan Results

- Operation: subagent orchestration with dependency ordering
- Existing implementations: 1 (`SPRINT_PROMPT` single-story chain) — no existing parallel scheduler
- Assessment: **New is justified** — wave mode extends the single existing orchestrator; per-story chain is reused verbatim, not copied.

### Capability Assessment

| Need | Source | Decision |
|------|--------|----------|
| Waves + conflict matrix | `pactkit spec-graph` (STORY-slim-143) | Reuse — add `--json` consumer interface |
| Backlog enumeration | `board.py list_stories` | Reuse |
| Worktree isolation | existing sprint Stage A/B/C pattern | Reuse |
| Parallel cap config | pactkit.yaml `sprint.max_parallel` (new optional key, default 3) | New config key |

### New Implementation Required

- `spec_graph.py`: `--json` flag + `to_json()` serializer (~30 lines).
- `SPRINT_PROMPT`: Wave Mode section (Phase 0.5: Mode Detection; Phase 1W: Wave loop). Deployed copy `pactkit-plugin/commands/project-sprint.md` regenerated via `pactkit update`.

### Concurrency Decision (Engineering Concern: concurrency)

Parallelism is at the **subagent/team level** (Claude Code Task agents with worktree isolation), not threads/processes in pactkit code — pactkit itself stays single-threaded. The cap (`sprint.max_parallel`, default 3) bounds concurrent worktrees. Merging is always sequential (one worktree at a time), which is the serialization point that keeps git state sane. Conflict avoidance is precomputed by `spec-graph`, not detected at merge time.

### Error-Recovery Decision (Engineering Concern: error-recovery)

Fail-fast per wave; no auto-retry; partial progress is always safe because every completed story merged through its own green PDCA chain. Resume = re-run `/project-sprint` — remaining backlog stories re-enter wave computation (idempotent, since completed stories are Done and excluded by spec-graph).

### Backwards-Compatibility Decision (Engineering Concern: backwards-compatibility)

Single-story mode is the default when args are present — zero behavior change for existing users. Wave mode is opt-in via empty args. `sprint.max_parallel` absent from pactkit.yaml → default 3, no config migration needed.

## Acceptance Criteria

### AC1: JSON output shape (R1)

- **Given** specs forming 2 waves with one same-wave conflict
- **When** `pactkit spec-graph --json` runs
- **Then** stdout parses as JSON with `waves` (list of sorted ID lists) and `conflicts` (list of objects with story_a/story_b/shared/same_wave), and two runs are byte-identical.

### AC2: Cycle still errors under --json (R1)

- **Given** two mutually dependent specs
- **When** `pactkit spec-graph --json` runs
- **Then** exit code is non-zero and stderr names the cycle.

### AC3: Mode detection (R2)

- **Given** the updated SPRINT_PROMPT / project-sprint.md
- **When** reading the entry phase
- **Then** it specifies: non-empty `$ARGUMENTS` → single-story mode (unchanged path); empty → wave mode with board scan + `spec-graph --json` + fallback when nothing is parallelizable.

### AC4: Scheduling policy documented and deterministic (R3)

- **Given** the updated playbook
- **When** reading the wave-mode section
- **Then** it encodes all of: parallel batch requires declared Touches AND pairwise non-conflict; `sprint.max_parallel` cap with default 3; serialized tail for conflicted/undeclared stories; per-story worktree PDCA chain reuse (reference, not copy).

### AC5: Wave gate & failure policy (R4, R5)

- **Given** the updated playbook
- **When** reading the wave-mode section
- **Then** it states: wave N+1 blocked until wave N fully merged; fail-fast STOP with completed/pending report; no auto-retry; merge-conflict → STOP + `git merge --abort` suggestion; wave plan printed before dispatch.

### AC6: Prompt hygiene (R2-R5)

- **Given** the implemented changes
- **When** running `pytest tests/unit/test_prompt_cli_refs.py tests/unit/test_story063_prompt_slimming.py` and full suite
- **Then** all pass (prompt baselines bumped per project convention if needed, with justification comments).

## Target Call Chain

- Wave mode: `/project-sprint` (empty args) → SPRINT_PROMPT Mode Detection → `board.py list_stories` + `pactkit spec-graph --json` → wave plan → per-story existing Stage A/B/C dispatch (worktree) → sequential merges → wave gate → next wave
- JSON: `cli.py spec-graph` → `spec_graph.main(["--json"])` → `to_json(graph)` (waves via `compute_waves`, conflicts via `compute_conflicts`)

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | STORY-slim-143 (needs: `pactkit spec-graph` waves + conflict matrix, `spec_graph.compute_waves`/`compute_conflicts`) |
| Provides | `pactkit spec-graph --json`; sprint wave mode; `sprint.max_parallel` config key |
| Touches | `src/pactkit/spec_graph.py`, `src/pactkit/prompts/workflows.py`, `pactkit-plugin/commands/project-sprint.md`, `tests/unit/test_story_slim144_wave_mode.py` (new) |
| Conflict risk | LOW — workflows.py SPRINT_PROMPT and spec_graph.py append-only changes; no overlap with typical feature stories |

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/spec_graph.py` | Add `--json` + `to_json()` | None | Low |
| 2 | `tests/unit/test_story_slim144_wave_mode.py` | TDD tests for AC1/AC2 | Step 1 | Low |
| 3 | `src/pactkit/prompts/workflows.py` | SPRINT_PROMPT wave mode section (R2-R5) | Step 1 | Medium (prompt size budget) |
| 4 | `pactkit-plugin/commands/project-sprint.md` | Regenerate via `pactkit update` | Step 3 | Low |
| 5 | `tests/unit/` | Prompt content assertions for AC3-AC5 | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | spec_graph.py source change — code quality standards apply |
| SEC-2 | Yes | --json serializer consumes spec-derived data — output must be valid JSON for any malformed surface input |
| SEC-3 | N/A | no database |
| SEC-4 | N/A | no frontend |
| SEC-5 | N/A | auto-detect false positive: no auth/session code touched (prompt text only) |
| SEC-6 | N/A | no API endpoints |
| SEC-7 | Yes | cycle error under --json must stay a clean single-line stderr + non-zero exit |
| SEC-8 | N/A | no new dependencies (stdlib json) |

## Out of Scope

- Interface-first contract staging (separate downstream story)
- Merge-preflight conflict check at agent completion time
- Auto-retry / self-healing of failed stories
- Parallelism inside pactkit code itself (threads/async) — orchestration-level only
- Changing single-story mode behavior in any way
