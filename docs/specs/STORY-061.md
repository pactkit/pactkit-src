# STORY-061: Remove Redundant `<thinking>` Block Instructions from PDCA Playbooks

| Field       | Value                                |
|-------------|--------------------------------------|
| ID          | STORY-061                            |
| Type        | Refactor                             |
| Priority    | Medium                               |
| Estimate    | S (small)                            |
| Release     | 1.6.0                                |
| Status      | Planned                              |
| Spec Author | System Architect                     |

## Summary

Remove all explicit `> **INSTRUCTION**: Output a <thinking> block` directives from PDCA command and workflow playbooks. Claude models have native extended thinking capability — these instructions are redundant, waste ~50-100 output tokens per invocation, and clutter the output.

## Requirements

### R1: Remove thinking instructions from commands.py
All `> **INSTRUCTION**: Output a <thinking> block` lines in `COMMANDS_CONTENT` entries MUST be removed. The Phase 0 section header and numbered steps that follow MUST be preserved.

### R2: Remove thinking instructions from workflows.py
All `> **INSTRUCTION**: Output a <thinking> block` lines in workflow prompts (TRACE_PROMPT, DRAW_PROMPT, SPRINT_PROMPT, REVIEW_PROMPT, HOTFIX_PROMPT, DESIGN_PROMPT) MUST be removed. The Phase 0 section header and numbered steps MUST be preserved.

### R3: Update impacted test
The test `test_phase0_still_thinking` in `tests/unit/test_design_command.py` MUST be updated to reflect the removal. It SHOULD verify that the Phase 0 section still exists but no longer assert that "thinking" is present.

## Acceptance Criteria

### AC1: No thinking instructions in commands.py
**Given** the `COMMANDS_CONTENT` dictionary in `commands.py`
**When** all values are searched for `> **INSTRUCTION**: Output a <thinking> block`
**Then** zero matches are found

### AC2: No thinking instructions in workflows.py
**Given** all workflow prompt constants in `workflows.py`
**When** searched for `> **INSTRUCTION**: Output a <thinking> block`
**Then** zero matches are found

### AC3: Phase 0 sections preserved
**Given** any command or workflow playbook
**When** the Phase 0 section is read
**Then** it still contains the numbered analysis steps (the content after the removed instruction line)

### AC4: Test updated
**Given** `test_design_command.py::test_phase0_still_thinking`
**When** the test runs
**Then** it passes and verifies Phase 0 exists without asserting `thinking` presence

### AC5: All existing tests pass
**Given** the full test suite
**When** `pytest tests/` is run
**Then** all tests pass (no regressions)

## Target Call Chain

```
commands.py  →  COMMANDS_CONTENT["project-plan.md"]   line 18
                COMMANDS_CONTENT["project-check.md"]   line 281
                COMMANDS_CONTENT["project-done.md"]    line 437
                COMMANDS_CONTENT["project-init.md"]    line 697

workflows.py →  TRACE_PROMPT                           line 17
                DRAW_PROMPT                            line 184
                SPRINT_PROMPT                          line 309
                REVIEW_PROMPT                          line 468
                HOTFIX_PROMPT                          line 637
                DESIGN_PROMPT                          line 695
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Remove 4 thinking instruction lines | None | Low |
| 2 | `src/pactkit/prompts/workflows.py` | Remove 6 thinking instruction lines | None | Low |
| 3 | `tests/unit/test_story061_remove_thinking.py` | Create test asserting no thinking instructions remain | Step 1, 2 | Low |
| 4 | `tests/unit/test_design_command.py` | Update `test_phase0_still_thinking` to not assert thinking | Step 2 | Low |
