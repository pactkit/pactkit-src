# STORY-slim-071: Context Handoff — Structured Agent Continuation

| Field | Value |
|-------|-------|
| ID | STORY-slim-071 |
| Status | Done |
| Priority | P1 |
| Release | 3.0.0 |

## Background

Inspired by Anthropic's "Context Reset > Context Compaction" finding: when a long-running agent loses coherence, clearing context and restarting with a structured handoff outperforms trying to compress the existing context.

PactKit's `context.md` currently captures a static snapshot: sprint status, active stories, recent completions, active branches, key decisions, and next recommended action. This is good for cold-start orientation but lacks **continuation state** — where the agent stopped, what it was trying to do, what blocked it, and what the acceptance criteria are for the current work.

When a user starts a new session mid-story (common: laptop restart, context window limit, switching between projects), the new agent must re-derive all of this from git log, board state, and spec reading. This wastes 2-5 minutes of agent time per session restart.

This story enriches `context.md` with a new `## Agent Continuation` section that captures the last active command, its current phase, blockers, and the sprint contract (acceptance criteria for in-progress work). The Done and Act commands auto-update this section.

## Requirements

### R1: Agent Continuation Section in context.md (MUST)

`context.md` MUST include a new `## Agent Continuation` section after `## Next Recommended Action`, containing:
- `Last Command`: the PDCA command that last ran (e.g., `/project-act STORY-slim-070`)
- `Phase Reached`: the phase number/name where work stopped (e.g., `Phase 3: Implementation — step 2/5 complete`)
- `Blockers`: any blockers or open questions (e.g., `RFC: R3 implementation unclear — awaiting user input`)
- `Sprint Contract`: the acceptance criteria for the current in-progress story (extracted from Spec AC section)

If no story is in progress, this section MUST show `No active work session.`

### R2: Auto-Update on Act Exit (MUST)

The Act command playbook MUST include a final step that calls `pactkit context --continuation` to update the Agent Continuation section. This runs regardless of whether Act completed successfully or was interrupted.

Parameters passed: `--last-command`, `--phase`, `--blockers` (optional).

### R3: Auto-Clear on Done (MUST)

The Done command MUST clear the Agent Continuation section (reset to `No active work session.`) after successfully completing a story. This prevents stale continuation state from misleading the next session.

### R4: Sprint Contract Extraction (SHOULD)

When `--continuation` is called with an active story ID, `context_gen.py` SHOULD read the story's Spec and extract AC section titles as a checklist:
```
### Sprint Contract (STORY-slim-070)
- [ ] AC1: Dead Import Detected
- [ ] AC2: Stale Spec Reference
- [x] AC3: Stale Context Detected (verified in Phase 2)
```

Checked items are determined by which ACs have corresponding passing tests (via test-map).

### R5: Schema Update (MUST)

`schemas.py` MUST add `CONTEXT_SECTION_CONTINUATION = "## Agent Continuation"` to `CONTEXT_SECTIONS`. The `context_gen.py` function MUST handle the new section.

## Acceptance Criteria

### AC1: New Section Present (R1)

- **Given** an in-progress story STORY-slim-070 on the board
- **When** `pactkit context --continuation --last-command "/project-act STORY-slim-070" --phase "Phase 3: step 2/5"` runs
- **Then** `context.md` contains `## Agent Continuation` with Last Command, Phase Reached, and Sprint Contract fields

### AC2: Cold Start Reads Continuation (R1)

- **Given** `context.md` has an Agent Continuation section with phase info
- **When** a new agent session starts and reads `context.md`
- **Then** the agent can determine the exact resumption point without re-reading git log or board

### AC3: Act Exit Updates Continuation (R2)

- **Given** `/project-act STORY-slim-070` reaches Phase 3 step 2 and the session ends
- **When** the Act exit step runs `pactkit context --continuation`
- **Then** `context.md` Agent Continuation shows `Last Command: /project-act STORY-slim-070` and `Phase Reached: Phase 3: step 2/5`

### AC5: Done Clears Continuation (R3)

- **Given** `context.md` has an active Agent Continuation section
- **When** `/project-done STORY-slim-070` completes successfully
- **Then** the Agent Continuation section shows `No active work session.`

### AC6: Sprint Contract Checklist (R4)

- **Given** STORY-slim-070 has 7 ACs in its Spec, and AC1/AC2/AC3 have passing tests
- **When** `pactkit context --continuation` runs
- **Then** the Sprint Contract shows `[x]` for AC1-AC3 and `[ ]` for AC4-AC7

### AC7: No In-Progress Story (R1)

- **Given** sprint board has no In Progress stories
- **When** `pactkit context` runs
- **Then** Agent Continuation section shows `No active work session.`

### AC8: Backward Compatible (R5)

- **Given** an existing `context.md` without the Agent Continuation section
- **When** `pactkit context` runs (without `--continuation`)
- **Then** the new section is appended with default `No active work session.` — no existing sections are modified

## Target Call Chain

```
pactkit context [--continuation --last-command CMD --phase PHASE --blockers TEXT]
  → cli.py: context command dispatch (existing, extended)
  → context_gen.py: generate_context(root, command, continuation_args=None)
    → _parse_board() [existing]
    → _parse_active_stories() [existing]
    → _parse_recent_completions() [existing]
    → _get_git_branches() [existing]
    → _parse_last_lessons() [existing]
    → _generate_continuation(root, continuation_args) [NEW]
      → if continuation_args: format Last Command + Phase + Blockers
      → if story_id in continuation: _extract_sprint_contract(spec_path)
      → else: "No active work session."
    → assemble all sections → return string

Act playbook (exit step):
  → pactkit context --continuation --last-command "/project-act {ID}" --phase "{phase}"

Done playbook (Phase 4.5):
  → pactkit context  (no --continuation → clears to default)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_context_gen.py` | TDD: tests for `_generate_continuation()`, `_extract_sprint_contract()`, backward compat | None | Low |
| 2 | `src/pactkit/schemas.py` | Add `CONTEXT_SECTION_CONTINUATION`, update `CONTEXT_SECTIONS` tuple | None | Low |
| 3 | `src/pactkit/context_gen.py` | Add `_generate_continuation()`, `_extract_sprint_contract()`, extend `generate_context()` | Step 2 | Medium |
| 4 | `src/pactkit/cli.py` | Add `--continuation`, `--last-command`, `--phase`, `--blockers` args to context subcommand | Step 3 | Low |
| 5 | `src/pactkit/prompts/commands.py` | Add exit step in Act template + clear step in Done template | Step 4 | Low |
| 6 | `tests/e2e/cli/test_cli_e2e.py` | E2E test: `pactkit context --continuation` round-trip | Step 4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Input Validation) | MUST | `--last-command`, `--phase`, `--blockers` are free-text CLI args — sanitize before writing to context.md |
| SEC-2 (Auth) | N/A | No auth changes |
| SEC-3 (Injection) | N/A | No command construction |
| SEC-4 (Secrets) | N/A | No credential handling |
| SEC-5 (CORS) | N/A | CLI-only |
| SEC-6 (Path Traversal) | N/A | Writes only to `docs/product/context.md` |
| SEC-7 (DoS) | N/A | Bounded by spec count |
| SEC-8 (Dependencies) | N/A | No new dependencies |

## Out of Scope

- Automatic phase detection (agent must explicitly pass `--phase`; inferring phase from git diff is fragile)
- Multi-story continuation (only one active story tracked; sprint with parallel stories is future work)
- Continuation state for non-PDCA commands (e.g., `/project-hotfix` does not update continuation)
- Persistent continuation across branches (continuation is per-project, not per-branch)
