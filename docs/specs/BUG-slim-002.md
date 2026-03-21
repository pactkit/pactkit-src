# BUG-slim-002: Rules-Commands Instruction Collision Causes Plan/Act Stall

| Field | Value |
|-------|-------|
| ID | BUG-slim-002 |
| Status | Draft |
| Priority | P1 |
| Release | 2.2.0 |

## Background

When running `/project-plan` or `/project-act`, the AI agent frequently stalls (long thinking time, repeated actions, or apparent hang). Root cause analysis reveals that the global Rules (`01-core-protocol`, `02-hierarchy-of-truth`) contain instructions that **duplicate or conflict with** the phase-ordered instructions inside Command playbooks. The AI attempts to satisfy both layers simultaneously, resulting in repeated execution (e.g., `visualize` triggered up to 5 times per Story cycle), logical deadlocks (Rule 02 demands "read Spec before modifying code" but Plan is creating the Spec), and cascading sub-flows (Init Guard auto-triggers a full 7-phase `/project-init`).

## Root Cause Analysis

| ID | Problem | Source | Impact |
|----|---------|--------|--------|
| RC-1 | Rule 01 "Visual First" triggers `visualize` (3 modes) independently of Command-internal visualize phases | `rules.py` RULES_MODULES["core"] | 2-3x redundant visualize runs per command |
| RC-2 | Rule 02 "Operating Guidelines" requires reading Spec before code modification, but Plan is creating the Spec (does not exist yet) | `rules.py` RULES_MODULES["hierarchy"] | Logical deadlock / wasted search for nonexistent file |
| RC-3 | Plan Phase 0.5 Init Guard auto-executes full `/project-init` (7 phases) when any marker is missing | `commands.py` COMMANDS_CONTENT["project-plan.md"] | Cascading 7-phase sub-flow mid-Plan |
| RC-4 | Plan Phase 0.7 Clarify Gate auto-triggers on 2 High signals without escape hatch | `commands.py` COMMANDS_CONTENT["project-plan.md"] | Implicit blocking wait for user input |
| RC-5 | Act Phase 0.6 Consistency Check does full Spec/Board/TestCase cross-reference before any code is written | `commands.py` COMMANDS_CONTENT["project-act.md"] | Heavy text parsing phase that adds latency |
| RC-6 | Act runs visualize 3 separate times: Phase 1 (trace), Phase 4 (Lazy Visualize), plus Rule 01 (Visual First) | Multiple sources | 3x redundant visualize in Act alone |

## Target Call Chain

```
User invokes /project-plan or /project-act
  -> Claude Code loads CLAUDE.md (@import all 8 rules)
    -> Rule 01 "Visual First" fires (visualize x3 modes)
    -> Rule 02 "Operating Guidelines" fires (search for Spec)
  -> Command playbook executes
    -> Phase 0.5 Init Guard (may cascade to /project-init x7 phases)
    -> Phase 0.7 Clarify Gate (may block on user input)
    -> Phase 1 Archaeology/Trace (visualize again)
    -> [Act only] Phase 0.6 Consistency Check (heavy parsing)
    -> [Act only] Phase 4 Lazy Visualize (visualize again)
```

## Requirements

### R1: PDCA Command Exemption for Visual First
Rule 01 "Visual First" MUST include a PDCA exemption clause stating that when a PDCA command (`/project-plan`, `/project-act`, `/project-check`, `/project-done`, `/project-hotfix`, `/project-sprint`, `/project-design`, `/project-init`) is active, the command's own visualize phases take precedence and the global "Visual First" rule is suppressed.

### R2: Plan-Phase Exemption for Operating Guidelines
Rule 02 "Operating Guidelines" MUST include a clause exempting `/project-plan` and `/project-design` from the "read Spec before modifying code" requirement, since these commands create (not modify) Specs.

### R3: Init Guard Downgrade to Suggestion-and-Stop
Plan Phase 0.5 Init Guard MUST be changed from auto-executing `/project-init` to printing a warning message and STOPPING. The user can then manually run `/project-init` if needed.

### R4: Clarify Gate Threshold Increase
Plan Phase 0.7 Clarify Gate SHOULD raise the auto-trigger threshold: require 2 High + 1 Medium signal (instead of 2 High alone). Single-sentence input (< 15 words) SHOULD be downgraded from Medium to Low signal.

### R5: Act Consistency Check Simplification
Act Phase 0.6 Consistency Check SHOULD be simplified to a lightweight existence check (does Spec exist? does Board entry exist?) instead of full cross-reference parsing. The detailed Spec-Board-TestCase alignment analysis SHOULD be deferred to `/project-check`.

### R6: Act Visualize Deduplication
Act Phase 1 MUST NOT run `visualize` if Phase 4 Lazy Visualize will run it anyway. Phase 1 SHOULD only run `visualize --focus <module>` (single targeted mode), not the full 3-mode scan. The full 3-mode scan remains in Phase 4 (post-implementation) via Lazy Visualize Protocol.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/rules.py` | Add PDCA exemption to "Visual First" in RULES_MODULES["core"] (R1) | None | Low |
| 2 | `src/pactkit/prompts/rules.py` | Add Plan/Design exemption to "Operating Guidelines" in RULES_MODULES["hierarchy"] (R2) | None | Low |
| 3 | `src/pactkit/prompts/commands.py` | Rewrite Plan Phase 0.5 Init Guard: warn + STOP instead of auto-execute (R3) | None | Low |
| 4 | `src/pactkit/prompts/commands.py` | Adjust Clarify Gate threshold in Plan Phase 0.7 (R4) | None | Low |
| 5 | `src/pactkit/prompts/commands.py` | Simplify Act Phase 0.6 to lightweight existence check (R5) | None | Low |
| 6 | `src/pactkit/prompts/commands.py` | Deduplicate Act visualize: Phase 1 focus-only, Phase 4 full Lazy Visualize (R6) | None | Low |
| 7 | `tests/` | Add/update tests to verify prompt content changes | Steps 1-6 | Low |

## Acceptance Criteria

### AC1: Visual First PDCA Exemption
Given Rule 01 "Visual First" is deployed
When a PDCA command (e.g., `/project-act`) is active
Then the rule text includes a PDCA exemption clause and does not independently trigger visualize

### AC2: Plan-Phase Spec Read Exemption
Given Rule 02 "Operating Guidelines" is deployed
When `/project-plan` or `/project-design` is active
Then the rule text exempts these commands from "read Spec before modifying code"

### AC3: Init Guard Warns Instead of Auto-Executing
Given Plan Phase 0.5 Init Guard detects a missing marker
When the guard evaluates
Then it prints a warning with the missing markers and STOPs, without auto-executing `/project-init`

### AC4: Clarify Gate Higher Threshold
Given Plan Phase 0.7 Clarify Gate is evaluating user input
When the input has exactly 2 High signals but 0 Medium signals
Then Clarify is suggested (not auto-triggered)

### AC5: Act Lightweight Consistency Check
Given Act Phase 0.6 is executing
When it checks Spec-Board alignment
Then it only verifies existence (Spec file exists, Board entry exists) without cross-reference parsing

### AC6: Act Visualize Runs Once Per Phase
Given Act Phase 1 and Phase 4 both reference visualize
When Act executes end-to-end
Then Phase 1 runs only `--focus <module>` (1 mode) and Phase 4 runs Lazy Visualize (conditional 3 modes), with no duplication from Rule 01

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Python source files modified (rules.py, commands.py) |
| SEC-2 | No | No user input handling — prompt template changes only |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session logic |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error handling changes |
| SEC-8 | No | No dependency file changes |
