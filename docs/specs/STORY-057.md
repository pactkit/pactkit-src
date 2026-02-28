# Spec: STORY-057

## Metadata
| Field | Value |
|-------|-------|
| ID | STORY-057 |
| Title | Playbook Implicit Instruction Cleanup |
| Status | Draft |
| Priority | P2 |
| Author | System Architect |
| Created | 2026-02-28 |
| Release | 1.5.0 |

## Summary
Remove unverifiable implicit instructions from PDCA playbooks and add explicit labels to ambiguous signal classifications. Two targeted fixes that eliminate LLM non-determinism without changing any design logic or execution flow.

## Background
Deep analysis of the PDCA playbooks (Done Phase 2.5 Regression Gate and Plan Phase 0.7 Clarify Gate) revealed two specific structural defects:

1. **Done Phase 2.5 Step 1.5 (Fast-Suite Shortcut)**: Instructs the LLM to check "if the last test run completed in < 30 seconds", but there is no tool, artifact, or persistent state to obtain this value. The LLM can only guess from conversational memory, which is unreliable and non-reproducible across sessions. This step was identified as the only logically unexecutable instruction in the Regression Gate's 19-branch priority cascade.

2. **Plan Phase 0.7 Step 2 (Trigger Logic)**: References "High signals" and "Medium signals" but the 6 signals listed in Step 1 carry no explicit High/Medium labels. The LLM must infer the classification, producing non-deterministic trigger behavior — the same input may trigger or skip Clarify depending on which signals the LLM classifies as High vs Medium.

### What This Story Does NOT Change
- The Regression Gate priority cascade (Step 1.3 → 1.6 → 1.7 → Step 2 → FULL default) is preserved intact
- The Clarify Gate trigger logic (≥2 High → auto, 1 High + ≥2 Medium → auto, ≥2 Medium → suggest) is preserved intact
- No branches are added or removed from the Regression Gate
- No new config options are introduced

## Target Call Chain

```
Done Phase 2.5 Regression Gate:
  Step 1.3 (Doc-Only) → [Step 1.5 REMOVED] → Step 1.6 (Release Gate) → Step 1.7 (Impact) → Step 2 → Step 3

Plan Phase 0.7 Clarify Gate:
  Step 1 (Detect Ambiguity — signals now labeled) → Step 2 (Trigger Logic — unchanged) → Step 3–6
```

## Requirements

### R1: Remove Done Phase 2.5 Step 1.5 (Fast-Suite Shortcut)
The `### Step 1.5: Fast-Suite Shortcut` block MUST be removed from `project-done.md` in `commands.py`.

**R1.1**: After removal, the cascade flow MUST be: Step 1.3 (Doc-Only) fall-through goes directly to Step 1.6 (Release Gate). No renumbering of subsequent steps is needed — Step 1.6, 1.7, 2, 2.3, 2.5, 2.7, 3 retain their current numbers.

**R1.2**: No other playbook references Step 1.5 or the "Fast-Suite Shortcut" concept. Removal is self-contained.

### R2: Add Explicit Signal Labels to Plan Phase 0.7 Clarify Gate
Step 1 in the Clarify Gate MUST label each of the 6 ambiguity signals as `[High]` or `[Medium]`.

**R2.1**: The classification MUST be:

| Signal | Level | Rationale |
|--------|-------|-----------|
| No quantitative metrics | High | Core requirement gap — cannot write measurable AC without metrics |
| No boundary conditions | High | Core requirement gap — cannot define scope without boundaries |
| No technical constraints | Medium | Can often be inferred from existing codebase |
| Single sentence input (< 15 words) | Medium | Short inputs may still be precise |
| Vague quantifiers | Medium | Context-dependent severity |
| No target user specified | Medium | Can often be inferred from project context |

**R2.2**: The trigger logic thresholds in Step 2 (≥2 High → auto, 1 High + ≥2 Medium → auto, ≥2 Medium → suggest) MUST remain unchanged.

**R2.3**: The `project-clarify.md` playbook references the same signal list as "AMBIGUITY_SIGNALS checklist (same as Plan Phase 0.7)". No change needed there since it delegates to Plan's definition.

## Acceptance Criteria

### AC1: Regression Gate cascade preserved after Step 1.5 removal
**Given** a Done Phase 2.5 run where source files are changed
**When** Step 1.3 Doc-Only check determines source files exist (fall-through)
**Then** execution proceeds directly to Step 1.6 (Release Gate), not to any "fast-suite" check

### AC2: Step 1.5 text fully removed
**Given** the `COMMANDS_CONTENT['project-done.md']` string
**When** searching for "Fast-Suite Shortcut" or "Step 1.5" or "< 30 seconds"
**Then** none of these strings are found

### AC3: Clarify Gate signals explicitly labeled
**Given** the `COMMANDS_CONTENT['project-plan.md']` string, Phase 0.7 Step 1
**When** reading the 6 ambiguity signals
**Then** each signal line includes either `[High]` or `[Medium]` label

### AC4: Clarify Gate trigger logic unchanged
**Given** the `COMMANDS_CONTENT['project-plan.md']` string, Phase 0.7 Step 2
**When** reading the trigger thresholds
**Then** the thresholds remain: ≥2 High → auto-trigger, 1 High + ≥2 Medium → auto-trigger, ≥2 Medium → suggest

### AC5: All existing regression gate tests still pass
**Given** the 5 existing regression gate test files
**When** running `pytest tests/unit/test_smart_regression.py tests/unit/test_story037_regression_fix.py tests/unit/test_story050_doc_only_shortcut.py tests/unit/test_story053_impact_regression.py tests/unit/test_done_gates.py -v`
**Then** all tests pass (no regression from Step 1.5 removal)

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Remove Step 1.5 Fast-Suite Shortcut block from `project-done.md` | None | Low |
| 2 | `src/pactkit/prompts/commands.py` | Add `[High]`/`[Medium]` labels to Phase 0.7 Step 1 signal list in `project-plan.md` | None | Low |
| 3 | `tests/unit/test_story057_implicit_cleanup.py` | Add tests verifying AC1–AC4 | Step 1, 2 | Low |
| 4 | Existing test files | Run existing regression gate tests to confirm no breakage (AC5) | Step 1 | Low |

## Security Scope
| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | No source code logic, only prompt text |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database code |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth tokens |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error messages |
| SEC-8 | No | No dependency changes |

## Out of Scope
- Restructuring the Regression Gate cascade order (branches are correct as-is)
- Adding new regression strategies or config options
- Modifying the Clarify Gate trigger thresholds
- Renumbering existing Step IDs (1.6, 1.7, 2, etc.)
