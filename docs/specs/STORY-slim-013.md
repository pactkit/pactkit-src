# STORY-slim-013: Reduce Cognitive Overload in PDCA Command Prompts

| Field | Value |
|-------|-------|
| ID | STORY-slim-013 |
| Status | Draft |
| Priority | P1 |
| Release | 2.2.0 |

## Background

During `/project-plan` usage, the model occasionally enters an extended thinking loop, outputting "I was thinking too long. Let me just write." This is caused by two compounding factors:

1. **`(Mandatory)` label on Phase 0** — reinforces "must complete all thinking before output", causing the model to internally plan everything before producing any text.
2. **Dense Phase steps** — single phases with 7+ MUST requirements (e.g., Plan Phase 3 Step 2) create high cognitive load per step.

A partial fix was already applied to `commands.py` (removed `(Mandatory)` from 5 Phase 0 headers, added `Execution Style` directive for incremental output). This story completes the fix across `workflows.py` and adds Phase splitting for the densest steps.

## Target Call Chain

```
pactkit deploy → deployer._render_prompt() → prompts/commands.py (COMMAND_PROMPTS dict)
                                             → prompts/workflows.py (TRACE_PROMPT, DRAW_PROMPT, etc.)
```

## Requirements

### R1: Remove (Mandatory) from workflows.py Phase 0 headers
MUST remove `(Mandatory)` from Phase 0 headers in `workflows.py` at these 5 locations:
- `TRACE_PROMPT` line 16: `Phase 0: The Thinking Process (Mandatory)` → `Phase 0: The Thinking Process`
- `DRAW_PROMPT` line 238: `Phase 0: The Thinking Process (Mandatory)` → `Phase 0: The Thinking Process`
- `REVIEW_PROMPT` line 412: `Phase 0: PR Information Retrieval (Mandatory)` → `Phase 0: PR Information Retrieval`
- `HOTFIX_PROMPT` line 580: `Phase 0: Locate & Register (Mandatory)` → `Phase 0: Locate & Register`
- `DESIGN_PROMPT` line 633: `Phase 0: The Thinking Process (Mandatory)` → `Phase 0: The Thinking Process`

### R2: Preserve legitimate (Mandatory) labels
MUST NOT remove `(Mandatory)` from `DRAW_REF_ANTI_BUGS` line 217 (rules section, not Phase 0) or `commands.py` line 168 (Spec Lint Gate — hard blocking gate).

### R3: Add Execution Style directive to Design command
SHOULD add `Execution Style` directive (incremental output) to `DESIGN_PROMPT` Phase 0 — it has the heaviest Phase 1 (PRD generation with 10 sub-sections).

### R4: Split Plan Phase 3 into sub-phases
MUST split `commands.py` Plan Phase 3 (Deliverables) into explicit sub-phases with intermediate output checkpoints:
- Phase 3.1: Story ID Generation (existing Step 1)
- Phase 3.2: Write Spec (existing Step 2, the 7-MUST monolith — now isolated as a focused step)
- Phase 3.3: Board + Memory + Context (existing Steps 3-5, lightweight wrap-up)

### R5: Add output checkpoint after ID generation
SHOULD add an explicit output checkpoint between Phase 3.1 and 3.2: "Story ID determined: {ID}. Writing Spec now."

### R6: Split Design Phase 1 into logical groups
SHOULD split `workflows.py` Design Phase 1 (PRD Generation) sub-sections into 3 logical groups with intermediate output:
- Group A (Sections 1.1-1.2): Product Overview + User Personas
- Group B (Sections 1.3-1.6): Features + Architecture + Pages + Prototypes
- Group C (Sections 1.7-2.0): API + NFR + Metrics + Roadmap

### R7: Deploy and verify both targets
MUST run `pactkit init` and `pactkit init --format opencode` after changes to verify both deployment targets receive the updated prompts. MUST verify all existing tests pass (no behavioral change, prompt-only modifications).

## Out of Scope

- Modifying Phase 0 structure in lightweight commands (project-init, project-clarify) — already minimal
- Changing the `DRAW_REF_ANTI_BUGS` mandatory label — this is a rules constraint, not a thinking phase
- Changing the Spec Lint Gate mandatory label in project-act — this is a hard blocking gate

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/workflows.py` | Remove 5 `(Mandatory)` labels from Phase 0 headers | None | Low |
| 2 | `src/pactkit/prompts/workflows.py` | Add `Execution Style` directive to DESIGN_PROMPT Phase 0 | Step 1 | Low |
| 3 | `src/pactkit/prompts/commands.py` | Split Plan Phase 3 into Phase 3.1/3.2/3.3 with output checkpoint | None | Medium |
| 4 | `src/pactkit/prompts/workflows.py` | Add group markers to Design Phase 1 sub-sections | Step 2 | Low |
| 5 | Deploy & verify | `pactkit init` + `pactkit init --format opencode` | Steps 1-4 | Low |

## Acceptance Criteria

### Scenario 1: (Mandatory) labels removed from workflows.py
- **Given** the current `workflows.py` has 5 Phase 0 headers with `(Mandatory)`
- **When** the changes are applied
- **Then** `grep -c "(Mandatory)" workflows.py` returns exactly 1 (only `DRAW_REF_ANTI_BUGS`)

### Scenario 2: Execution Style directive present in dense commands
- **Given** the updated `commands.py` and `workflows.py`
- **When** searching for `Execution Style` directives
- **Then** the directive appears in: Plan Phase 0, Act Phase 0, Check Phase 0, Design Phase 0 (minimum 4 commands)

### Scenario 3: Plan Phase 3 sub-steps
- **Given** the updated Plan command prompt
- **When** the model executes `/project-plan`
- **Then** Phase 3 contains explicit sub-phases (3.1, 3.2, 3.3) with an output checkpoint after ID generation

### Scenario 4: Design Phase 1 grouping
- **Given** the updated Design command prompt
- **When** the model executes `/project-design`
- **Then** Phase 1 sub-sections are organized into 3 logical groups (A, B, C) with intermediate output markers

### Scenario 5: No test regression
- **Given** all prompt changes applied
- **When** running `pytest tests/ -v`
- **Then** all tests pass (prompt changes are text-only, no logic change)

### Scenario 6: Both deployment targets updated
- **Given** changes deployed via `pactkit init` and `pactkit init --format opencode`
- **When** reading deployed command files
- **Then** no `(Mandatory)` appears in any Phase 0 header (except Spec Lint Gate and Anti-Bug Rules)

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (prompts/commands.py, prompts/workflows.py) |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error handling changes |
| SEC-8 | No | No dependency changes |
