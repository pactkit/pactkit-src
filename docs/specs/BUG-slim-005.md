# BUG-slim-005: Cross-Flow Residual Gaps — Hotfix Context, Board Refs, Dead Code

| Field | Value |
|-------|-------|
| ID | BUG-slim-005 |
| Status | Draft |
| Priority | P2 |
| Release | 2.2.0 |

## Background

Post-CLI-migration audit (BUG-slim-004 follow-up) revealed 5 residual gaps across Hotfix, Act, Check, and LANG_PROFILES. These are consistency issues that escaped the first two audit rounds.

## Requirements

### R1: Hotfix MUST call `pactkit context` after completion
- **Current**: Hotfix Phase 3 ends at git commit + board update. No context regeneration.
- **Fix**: Add Phase 3.5 (Session Context Update) to HOTFIX_PROMPT referencing `pactkit context`.
- **Rationale**: Plan, Act (via Done), Done, Init, and Design all call `pactkit context`. Hotfix is the only flow that skips it, causing stale `context.md` after hotfixes.

### R2: Hotfix Phase 3.4 board update MUST reference `{BOARD_CMD} update_task`
- **Current**: "Mark the hotfix task as done on the Board" — underspecified.
- **Fix**: Replace with explicit `{BOARD_CMD} update_task HOTFIX-{NNN} "Task Name"` instruction.

### R3: Act Phase 4.2 board update MUST reference `{BOARD_CMD} update_task`
- **Current**: "Mark the tasks in `docs/product/sprint_board.md` as `[x]`" — manual edit instruction.
- **Fix**: Replace with `{BOARD_CMD} update_task {STORY_ID} "Task Name"` instruction.

### R4: `lint-testcase` CLI subcommand MUST be referenced in Check prompt
- **Current**: `pactkit lint-testcase` exists in cli.py but no prompt references it. Siblings `lint-context` and `lint-lessons` are referenced in Done.
- **Fix**: Add `pactkit lint-testcase` reference in Check Phase 3 (Spec alignment section) where test case structure validation is relevant.

### R5: Remove 3 dead LANG_PROFILES keys
- **Current**: `test_dir`, `package_file`, `e2e_test_pattern` are defined in all 4 LANG_PROFILES entries but never consumed by any prompt or code logic.
- **Fix**: Remove these 3 keys from all 4 language profiles in `workflows.py`.
- **Consumed keys** (kept): `test_runner`, `file_ext`, `source_dirs`, `cleanup`, `test_map_pattern`, `lint_command`.

## Target Call Chain

```
workflows.py::HOTFIX_PROMPT  → R1 (add Phase 3.5), R2 (Phase 3.4 update)
commands.py::COMMANDS_CONTENT["project-act.md"]  → R3 (Phase 4.2 update)
commands.py::COMMANDS_CONTENT["project-check.md"]  → R4 (lint-testcase ref)
workflows.py::LANG_PROFILES  → R5 (remove dead keys)
```

## Acceptance Criteria

### AC1: Hotfix context update
- **Given**: HOTFIX_PROMPT text
- **When**: Read Phase 3.5
- **Then**: Contains `pactkit context`

### AC2: Hotfix board ref
- **Given**: HOTFIX_PROMPT text
- **When**: Read Phase 3.4
- **Then**: Contains `{BOARD_CMD} update_task`

### AC3: Act board ref
- **Given**: project-act prompt text
- **When**: Read Phase 4.2
- **Then**: Contains `{BOARD_CMD} update_task`

### AC4: lint-testcase referenced in Check
- **Given**: project-check prompt text
- **When**: Search for `lint-testcase`
- **Then**: At least 1 reference found

### AC5: Dead keys removed
- **Given**: LANG_PROFILES dict
- **When**: Check all 4 profiles
- **Then**: No `test_dir`, `package_file`, `e2e_test_pattern` keys exist

### AC6: Consumed keys intact
- **Given**: LANG_PROFILES dict
- **When**: Check all 4 profiles
- **Then**: All 6 consumed keys (`test_runner`, `file_ext`, `source_dirs`, `cleanup`, `test_map_pattern`, `lint_command`) still present

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/workflows.py` | Add Phase 3.5 to HOTFIX_PROMPT with `pactkit context` | None | Low |
| 2 | `src/pactkit/prompts/workflows.py` | Update Phase 3.4 with `{BOARD_CMD} update_task` ref | None | Low |
| 3 | `src/pactkit/prompts/commands.py` | Update Act Phase 4.2 with `{BOARD_CMD} update_task` | None | Low |
| 4 | `src/pactkit/prompts/commands.py` | Add `pactkit lint-testcase` to Check prompt | None | Low |
| 5 | `src/pactkit/prompts/workflows.py` | Remove 3 dead keys from 4 LANG_PROFILES entries | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (.py) |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error handling changes |
| SEC-8 | No | No dependency file changes |
