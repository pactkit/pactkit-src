# STORY-slim-024: Spec Lint W007 — Requirement-AC Coverage Check

| Field | Value |
|-------|-------|
| ID | STORY-slim-024 |
| Status | Done |
| Priority | P2 |
| Release | 2.3.3 |

## Background

STORY-slim-022 had `api_spec` mentioned in R4 as "prompt-consumed" but no corresponding AC tested for it. The implementation strictly followed AC coverage, missing the SHOULD requirement. Root cause: **SHOULD requirements without AC coverage get silently dropped**.

A new lint rule W007 will warn when any `### R{N}:` is not referenced by any `### AC{M}:` body. This ensures every requirement — including SHOULD — has at least one testable scenario.

## Target Call Chain

```
spec_linter.py:validate_spec()
  → _check_requirements_section()  # extracts R{N} IDs
  → _check_acceptance_criteria()   # extracts AC{M} bodies
  → _check_req_ac_coverage()       # NEW: cross-checks R{N} ↔ AC{M}
```

## Requirements

### R1: Extract Requirement IDs
`spec_linter.py` MUST extract all `### R{N}:` IDs from the Requirements section (e.g., `R1`, `R2`, `R3`).

### R2: Scan AC Bodies for R{N} References
`spec_linter.py` MUST scan each `### AC{M}:` body for references to requirement IDs (pattern: `R{N}` as word boundary, e.g., `R1`, `R2`).

### R3: W007 Warning Rule
For each R{N} that is NOT referenced by any AC body, `spec_linter.py` MUST emit:
- Rule ID: `W007`
- Message: `Requirement R{N} has no corresponding AC reference`
- Severity: WARNING (does not block `/project-act`)

### R4: SHOULD Emphasis
The W007 warning message SHOULD specifically note when the unreferenced requirement uses SHOULD keyword, as these are most at risk of being dropped.

### R5: Blast Radius
Only `spec_linter.py` is modified. No changes to commands, prompts, or other modules.

## Out of Scope
- Automated AC generation for missing coverage
- Done Phase Spec Alignment Check (separate story)
- Requirement → Implementation traceability

## Acceptance Criteria

### AC1: W007 Fires on Unreferenced R{N}
Given a spec with `### R1:`, `### R2:`, `### R3:`
And AC section only references `R1` and `R2`
When `pactkit spec-lint` runs
Then W007 warning is emitted for `R3`

### AC2: No W007 When All R{N} Covered
Given a spec where every R{N} is referenced by at least one AC
When `pactkit spec-lint` runs
Then no W007 warning is emitted

### AC3: Case Insensitive R{N} Matching
Given AC body contains "r1" (lowercase)
When checking coverage for R1
Then R1 is considered covered (case insensitive)

### AC4: W007 Does Not Block
Given a spec with W007 warning
When `pactkit spec-lint` exit code is checked
Then exit code is 0 (warnings don't block)

### AC5: SHOULD Emphasis in Message
Given a spec with uncovered R{N} containing SHOULD keyword
When W007 warning is emitted
Then message includes "(SHOULD)" indicator

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/skills/spec_linter.py` | Add `_extract_requirement_ids()` helper | None | Low |
| 2 | `src/pactkit/skills/spec_linter.py` | Add `_check_req_ac_coverage()` function | Step 1 | Low |
| 3 | `src/pactkit/skills/spec_linter.py` | Call from `validate_spec()` | Step 2 | Low |
| 4 | `tests/unit/test_story_slim024.py` | Unit tests for AC1-AC5 | Steps 1-3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Lint tool only, no execution |
| SEC-2 | N/A | Reads local files, no user input |
| SEC-3 | N/A | No database |
| SEC-4 | N/A | No frontend |
| SEC-5 | N/A | No auth |
| SEC-6 | N/A | No API |
| SEC-7 | N/A | No error exposure |
| SEC-8 | N/A | No dependencies |
