# STORY-037: Fix regression decision tree — replace unverifiable conditions

- **Release**: 1.3.0
- **Priority**: High
- **Type**: Enhancement (Prompt-only)

## Problem

The Done command's regression decision tree (Phase 2.5) requires ALL 6 conditions to be TRUE for incremental testing. In practice, two conditions are structurally unsatisfiable:

1. **Condition 1**: "code_graph.mmd exists AND was updated in the current session (not stale)" — the LLM has no session boundary concept, making this unverifiable.
2. **Condition 3**: "ALL changed source files have direct test mappings via `test_map_pattern`" — `test_map_pattern` assumes `tests/unit/test_{module}.py` naming, but most real projects (including PactKit itself) name tests by feature/Story, not by module.

Combined effect: the incremental path is dead code. Full regression runs 100% of the time.

Additionally, the Act command's regression says "plus the full test suite if unsure about change scope" — conservative LLMs always interpret this as "run everything."

## Requirements

### Done Regression (Phase 2.5)

- **MUST** replace Condition 1 with a verifiable check: "code_graph.mmd exists AND was modified within the last commit (check via `git diff HEAD~1 --name-only` includes `code_graph.mmd`)"
- **MUST** replace Condition 3 with a fallback-tolerant check: "At least ONE changed source file has a direct test mapping, OR the total test count is below 500 (fast enough for full suite)"
- **SHOULD** add a fast-suite threshold: if total test execution time < 30 seconds (based on last run), skip the decision tree and always run full regression (no point optimizing for small suites)
- **SHOULD** add decision logging: after evaluating the decision tree, output which path was chosen and which condition(s) determined the outcome (e.g., "Regression: FULL — Condition 4 failed: config.py imported by 5 modules")
- **MUST NOT** change the safe-by-default principle — full regression remains the default

### Act Regression (Phase 3, Step 3)

- **SHOULD** replace "plus the full test suite if unsure about change scope" with explicit criteria: "Run full suite only if changed files touch a module imported by 3+ other modules per code_graph.mmd; otherwise run mapped tests only"
- **MUST** preserve the pre-existing test failure STOP protocol

### Preserved Conditions

The following conditions remain unchanged (they are verifiable and well-designed):
- Changed source files ≤ 3
- NO test infrastructure files changed
- NO version change in pactkit.yaml
- NO changed file imported by 3+ other modules

## Acceptance Criteria

### AC1: Condition 1 is verifiable
- **Given** the Done command evaluates the regression decision tree
- **When** `code_graph.mmd` appears in `git diff HEAD~1 --name-only`
- **Then** Condition 1 evaluates to TRUE (graph was updated in recent commit)

### AC2: Condition 3 tolerates non-standard naming
- **Given** test files are named by feature (e.g., `test_smart_regression.py`) not by module
- **When** the decision tree evaluates Condition 3
- **Then** the fallback threshold (test count < 500) allows full suite as an acceptable path without blocking incremental for projects that do follow module naming

### AC3: Decision logging present
- **Given** the Done command completes the regression gate
- **When** the decision tree is evaluated
- **Then** the output includes which path was chosen and which condition(s) drove the decision

### AC4: Act regression uses explicit criteria
- **Given** the Act command reaches the regression check
- **When** changed files are limited to modules with low fan-in
- **Then** only mapped tests run (not the full suite)

## Target Call Chain

All changes are prompt-only in `src/pactkit/prompts/commands.py`:
- Done: `CMD_DONE_MD` → Phase 2.5 Decision Tree (lines ~335-383)
- Act: `CMD_ACT_MD` → Phase 3 Step 3 Regression Check (lines ~143-153)

No runtime code changes needed.
