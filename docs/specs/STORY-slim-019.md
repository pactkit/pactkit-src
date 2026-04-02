# STORY-slim-019: Split Plan Phase 3.2 into Sub-Steps to Eliminate Spec-Writing Stall

| Field | Value |
|-------|-------|
| ID | STORY-slim-019 |
| Status | Done |
| Priority | P1 |
| Release | 2.3.0 |

## Background

When running `/project-plan`, the AI stalls for an extended period during Phase 3.2 (Write Spec). Root cause: Phase 3.2 is a monolithic step that requires the AI to simultaneously plan metadata, requirements, acceptance criteria, implementation steps, security scope (8 SEC rules), and lint self-check — all before producing any output. This creates a large reasoning bottleneck.

## Target Call Chain

```
User invokes /project-plan
  → CLI expands skill → loads COMMAND_PROMPTS["project-plan.md"]
    → Phase 3.2 (Write Spec) ← THIS IS THE BOTTLENECK
      → Single Write tool call with full Spec content
```

Source: `src/pactkit/prompts/commands.py` lines 82-128 (the `project-plan.md` prompt template).

## Requirements

### R1: Split Phase 3.2 into sub-phases
1. **MUST** split Phase 3.2 into 4 sub-phases (3.2a, 3.2b, 3.2c, 3.2d), each with a distinct output checkpoint.
2. **MUST** preserve all existing Spec content requirements — no section may be dropped.
3. **MUST** add an explicit output checkpoint instruction between each sub-phase so the AI produces incremental output.

### R2: Condense Security Scope fallback
4. **SHOULD** move the Security Scope manual fallback table into a shorter reference (CLI-first, manual as brief fallback).

### R3: No side effects
5. **MUST NOT** change the Spec file format or section structure — only the prompt instructions for _how_ to produce the Spec.
6. **MUST NOT** alter any other Phase (0, 0.5, 0.7, 1, 2, 3.1, 3.3).

### Sub-Phase Breakdown

| Sub-Phase | Responsibility | Output Checkpoint |
|-----------|---------------|-------------------|
| 3.2a | Write Spec skeleton: metadata table + Requirements section | "Spec skeleton written. Adding acceptance criteria." |
| 3.2b | Write Acceptance Criteria (Given/When/Then) + optional Implementation Steps | "Acceptance criteria written. Running security scope." |
| 3.2c | Run `pactkit sec-scope` or manual SEC-1~SEC-8, append Security Scope section | "Security scope appended. Running lint." |
| 3.2d | Run `pactkit spec-lint`, self-correct if ERRORs, re-run until clean | "Spec lint passed." |

## Acceptance Criteria

### Scenario 1: Normal Plan flow with sub-phase checkpoints
- **Given** a user runs `/project-plan "some feature"`
- **When** the AI reaches Phase 3.2
- **Then** it produces output at each sub-phase checkpoint (3.2a → 3.2b → 3.2c → 3.2d)
- **And** the final Spec contains all required sections (metadata, requirements, acceptance criteria, security scope)

### Scenario 2: Spec lint failure triggers self-correction only in 3.2d
- **Given** the AI has written the Spec through phases 3.2a-3.2c
- **When** `pactkit spec-lint` reports ERRORs in phase 3.2d
- **Then** the AI self-corrects and re-runs lint
- **And** phases 3.2a-3.2c are NOT re-executed

### Scenario 3: sec-scope CLI available
- **Given** `pactkit sec-scope` is available
- **When** the AI reaches phase 3.2c
- **Then** it runs the CLI command and appends the output directly
- **And** does NOT perform manual SEC-1~SEC-8 analysis

### Scenario 4: sec-scope CLI unavailable
- **Given** `pactkit sec-scope` is NOT available
- **When** the AI reaches phase 3.2c
- **Then** it applies SEC rules manually using the condensed reference table
- **And** the output format matches the standard Security Scope table

## Non-Goals
- Changing the output Spec file format (sections, headings, metadata table structure)
- Modifying any Phase other than 3.2
- Adding new required Spec sections

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Replace Phase 3.2 block (lines 82-128) with 4 sub-phases (3.2a-3.2d) | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Prompt text change only, no source code logic |
| SEC-2 | N/A | No user input handling |
| SEC-3 | N/A | No data layer |
| SEC-4 | N/A | No frontend |
| SEC-5 | N/A | No auth |
| SEC-6 | N/A | No API routes |
| SEC-7 | N/A | No error handling changes |
| SEC-8 | N/A | No dependency changes |
