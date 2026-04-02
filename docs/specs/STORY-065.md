# STORY-065: Sprint Stage A Model Consistency — Split Plan (opus) and Act (sonnet)

| Field | Value |
|-------|-------|
| ID | STORY-065 |
| Status | Draft |
| Priority | High |
| Release | 1.6.7 |

## Background

The rule in `~/.claude/rules/01-core-protocol.md` specifies:
- **opus**: Complex architecture decisions, deep reasoning, multi-step planning → Plan phase
- **sonnet**: Code implementation, test writing, most tasks → Act/Check/Done phases

Sprint Stage B (Check) and Stage C (Close) already correctly pass `model: sonnet`
explicitly. However, Stage A (Build) does NOT specify a model — it only has a comment
"default (Opus)" in the reference table that carries no runtime weight. When the user
session is Sonnet, Stage A's Plan and Act both run on Sonnet, violating the rule.

Additionally, Stage A currently merges Plan and Act into one agent, making it
impossible to assign different models to them. Since Plan = architecture analysis
(should be opus) and Act = code implementation (should be sonnet), they must be split.

The model values must be config-aware: `pactkit.yaml` already supports an `agent_models`
dict (`system-architect: opus`, `senior-developer: sonnet`, etc.) for per-agent model
overrides. Hardcoding opus/sonnet in the prompt bypasses user config and will hard-fail
if the user's API tier doesn't include opus access. The Sprint Phase 0 MUST read
`agent_models` from `.claude/pactkit.yaml` and use those values, falling back to
recommended defaults (Plan=opus, Act=sonnet) only when not configured.

## Target Call Chain

```
SPRINT_PROMPT (workflows.py)
  Phase 0: Setup
    → Read .claude/pactkit.yaml                               ← ADD
    → plan_model  = agent_models['system-architect'] ?? 'opus'  ← ADD
    → act_model   = agent_models['senior-developer'] ?? 'sonnet' ← ADD

  Stage A: Build
    Stage A1: Plan
      → Agent(subagent_type="system-architect",
              model=plan_model,                               ← was: no model
              isolation="worktree")
      → runs project-plan.md
      → writes docs/specs/{STORY_ID}.md
    Stage A2: Act  (blockedBy: A1)
      → Agent(subagent_type="senior-developer",
              model=act_model,                               ← was: no model
              isolation="worktree")
      → reads docs/specs/{STORY_ID}.md
      → runs project-act.md
  Stage B: Check (unchanged, already model=sonnet)
  Stage C: Close (unchanged, already model=sonnet)
```

## Requirements

### R1: Stage A Explicit Model
Stage A of the Sprint workflow MUST explicitly pass model parameters rather than
relying on the session default. The Build stage comment "default (Opus)" MUST be
replaced with actual `model: opus` or `model: sonnet` annotations.

### R2: Plan Uses Opus (default)
The Plan sub-stage MUST launch a `system-architect` agent. The model MUST be
resolved via R7 (config-aware selection), defaulting to opus when not configured.

### R3: Act Uses Sonnet (default)
The Act sub-stage MUST launch a `senior-developer` agent. The model MUST be
resolved via R7 (config-aware selection), defaulting to sonnet when not configured.

### R7: Config-Aware Model Selection
Sprint Phase 0 MUST read `.claude/pactkit.yaml` and extract `agent_models` before
launching any subagent. Model resolution priority:

1. `agent_models['system-architect']` → Plan model (if present)
2. Default `opus` → Plan model (if key absent)
3. `agent_models['senior-developer']` → Act model (if present)
4. Default `sonnet` → Act model (if key absent)

If the resolved model is unavailable at runtime, Sprint SHOULD fall back to `sonnet`
with a warning rather than aborting the pipeline.

### R4: Isolation Preserved
Both Stage A1 (Plan) and Stage A2 (Act) MUST retain `isolation="worktree"` to
satisfy the pre-existing STORY-048 constraint (enforced by `test_story048_worktree_isolation.py`).

### R5: Stage Naming Preserved
The section heading "Stage A" MUST be retained (pre-existing tests locate stages
by their "Stage A/B/C" keywords). Sub-stages MUST be nested within "Stage A".

### R6: Reference Table Updated
The Subagent Reference table in SPRINT_PROMPT MUST be updated to show separate
rows for Plan and Act with their respective models.

## Out of Scope

- Changing Stage B (Check) or Stage C (Close) models — already correct
- Modifying any commands (project-plan.md, project-act.md) themselves
- Adding model selection logic to standalone (non-Sprint) commands — model
  selection only affects subagent spawning via the Agent tool

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (`workflows.py`) |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend code |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No public endpoints |
| SEC-7 | No | No exception handling changes |
| SEC-8 | No | No dependency changes |

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/workflows.py` | Add config-reading step to Sprint Phase 0: read `agent_models` from pactkit.yaml, resolve plan_model/act_model with fallback | None | Low |
| 2 | `src/pactkit/prompts/workflows.py` | Split Stage A into A1-Plan (model=plan_model) + A2-Act (model=act_model) | Step 1 | Medium |
| 3 | `src/pactkit/prompts/workflows.py` | Update Phase 0 TaskCreate list (5 tasks: Plan, Act, Check-QA, Check-Security, Close) | Step 2 | Low |
| 4 | `src/pactkit/prompts/workflows.py` | Update Subagent Reference table rows | Step 2 | Low |
| 5 | `tests/unit/test_story065_sprint_model.py` | Add tests verifying: Stage A1/A2 model annotations, agent_models config reading, fallback keywords | Steps 1–4 | Low |

## Acceptance Criteria

### AC1: Stage A1 uses opus
**Given** the SPRINT_PROMPT text
**When** inspected for Stage A content (between "Stage A" and "Stage B")
**Then** the text contains `model: opus` (or `model="opus"`) associated with the Plan sub-stage

### AC2: Stage A2 uses sonnet
**Given** the SPRINT_PROMPT text
**When** inspected for Stage A content
**Then** the text contains `model: sonnet` (or `model="sonnet"`) associated with the Act sub-stage

### AC3: Both Stage A sub-stages retain isolation
**Given** the SPRINT_PROMPT text
**When** the Stage A section (A1 + A2) is inspected
**Then** `isolation` appears in both sub-stages (pre-existing STORY-048 tests still pass)

### AC4: Reference table has separate Plan and Act rows
**Given** the Subagent Reference table in SPRINT_PROMPT
**When** inspected
**Then** separate rows exist for Plan (opus) and Act (sonnet)

### AC5: Pre-existing Stage A/B/C isolation tests still pass
**Given** the modified SPRINT_PROMPT
**When** `test_story048_worktree_isolation.py` is run
**Then** all tests pass (Stage A, B, C isolation assertions satisfied)

### AC6: Sprint Phase 0 reads agent_models from pactkit.yaml
**Given** the SPRINT_PROMPT Phase 0 section
**When** inspected
**Then** the text contains instructions to read `agent_models` from `.claude/pactkit.yaml`
**And** the text uses the resolved values for Stage A1 and A2 model parameters

### AC7: Fallback to defaults when agent_models not configured
**Given** the SPRINT_PROMPT Phase 0 section
**When** inspected
**Then** the text specifies fallback defaults: `opus` for Plan, `sonnet` for Act
**And** the text describes graceful degradation if the resolved model is unavailable
