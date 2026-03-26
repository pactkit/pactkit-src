# STORY-slim-050: Sprint performance: eliminate redundant operations

| Field | Value |
|-------|-------|
| ID | STORY-slim-050 |
| Status | Done |
| Priority | P1 |
| Release | 2.5.0 |

## Background

`/project-sprint` orchestrates 5 subagents (Plan→Act→Check-QA∥Check-Security→Done) via SPRINT_PROMPT in `workflows.py`. Currently takes ~40 minutes due to redundant operations: double security scan, double regression, double visualize, unsuppressed Clarify Gate, and unnecessary `pactkit update` in Done. Manual PDCA (`/project-plan` → `/project-act` → `/project-done`) takes ~10-15 minutes for the same task.

Root cause: SPRINT_PROMPT naively chains full interactive playbooks without sprint-specific trimming. Each subagent has no awareness it's running inside a sprint. Additionally, Done Phase 2.5 unconditionally re-runs the full regression suite even when no source/test files changed since Act's regression — this wastes time in both sprint and manual PDCA.

## Target Call Chain

```
SPRINT_PROMPT (workflows.py:320-374)
  → TeamCreate / TaskCreate (blockedBy DAG)
  → Agent(system-architect) → project-plan.md (commands.py PLAN_PROMPT)
  → Agent(senior-developer)  → project-act.md  (commands.py ACT_PROMPT)
  → Agent(qa-engineer)       → project-check.md (commands.py CHECK_PROMPT)
  → Agent(security-auditor)  → inline OWASP (SPRINT_PROMPT Stage B)
  → Agent(repo-maintainer)   → project-done.md (commands.py DONE_PROMPT)
```

Two modification targets: (1) `SPRINT_PROMPT` — sprint-specific overrides to subagents; (2) Done playbook `project-done.md` in `commands.py` — make regression gate smart enough to skip when no code changed since last regression.

## Requirements

### R1: Remove duplicate Security Auditor (MUST)

Stage B currently spawns both `qa-engineer` (project-check.md Phase 1 = full SEC-1~8) and a separate `security-auditor` with an inline OWASP audit. The security scan is 100% redundant. Remove the Security Auditor from Stage B; rely solely on QA's Check Phase 1.

### R2: Done regression skips when no code changed (MUST)

Done Phase 2.5 currently runs regression unconditionally. It MUST first check `git diff --name-only` against the commit where Act's regression passed. If no source/test files changed since that commit, Done MUST skip regression with log: `"Regression: SKIP — no source/test changes since Act"`. This applies to both sprint and manual PDCA — the optimization is in the Done playbook itself, not a sprint-only override.

### R3: Suppress Clarify Gate in sprint mode (MUST)

Plan Phase 0.7 can trigger an interactive Clarify question loop that waits for user input, blocking the entire automated pipeline. Sprint MUST instruct the Plan subagent to skip the Clarify Gate (proceed with original input).

### R4: Skip `pactkit update` in Done during sprint (SHOULD)

Done Phase 4 step 0.5 runs `pactkit update` which redeploys all prompts/agents/skills/rules. This is unnecessary inside sprint where no prompt files were modified. Sprint SHOULD instruct Done to skip the redeploy.

### R5: Avoid double visualize and next-id (SHOULD)

- `pactkit visualize --lazy` runs in both Act Phase 4 and Done Phase 2. The second call is redundant (same source state). Sprint SHOULD instruct Done to skip visualize.
- `pactkit next-id` runs in both Sprint Phase 0 (Lead) and Plan Phase 3.1 (subagent). Sprint SHOULD pass the already-determined STORY-ID to Plan to avoid the duplicate call.

### R6: Sprint PROMPT stays under 3000 chars (MUST)

Current SPRINT_PROMPT is within the hard limit. The optimized version MUST also stay under 3000 chars (MEMORY: `SPRINT_PROMPT hard limit: < 3000 chars`).

## Acceptance Criteria

### AC1: Security Auditor removed from Stage B (R1)

- **Given** SPRINT_PROMPT defines Stage B with both qa-engineer and security-auditor
- **When** the optimized SPRINT_PROMPT is deployed
- **Then** Stage B only spawns qa-engineer (running project-check.md which includes SEC-1~8 in Phase 1), and no security-auditor subagent exists in the Stage B definition. TaskCreate count drops from 5 to 4.

### AC2: Done regression auto-skips when no code changed (R2)

- **Given** Done Phase 2.5 regression gate executes after Act has committed
- **When** no source or test files have changed since the last commit (Act's commit)
- **Then** Done playbook text instructs: check `git diff --name-only` for source/test changes before running regression; if none, skip with log `"Regression: SKIP — no source/test changes since Act"`

### AC3: Clarify Gate suppressed (R3)

- **Given** SPRINT_PROMPT instructs Plan subagent
- **When** Plan subagent executes in sprint context
- **Then** the Plan instruction text includes "Skip Phase 0.7 Clarify Gate" or equivalent directive

### AC4: `pactkit update` skipped in sprint Done (R4)

- **Given** SPRINT_PROMPT instructs Done subagent
- **When** Done subagent executes in sprint context
- **Then** the Done instruction text includes "Skip pactkit update in Phase 4" or equivalent directive

### AC5: Double visualize and next-id eliminated (R5)

- **Given** SPRINT_PROMPT optimizes Stage A instructions
- **When** Done and Plan subagents execute
- **Then** Done instruction includes "Skip visualize --lazy in Phase 2", and Plan instruction includes "Use STORY-ID {ID} (already determined)" or equivalent

### AC6: Prompt size within limit (R6)

- **Given** the optimized SPRINT_PROMPT
- **When** character count is measured
- **Then** total chars < 3000

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Modify Done playbook (`project-done.md` template) Phase 2.5: add git diff check before regression — skip if no source/test files changed | None | Low |
| 2 | `src/pactkit/prompts/workflows.py` | Rewrite SPRINT_PROMPT: remove Security Auditor from Stage B, add sprint-override instructions to Plan/Done subagent dispatch text (Clarify Gate, pactkit update, visualize, next-id) | None | Medium |
| 3 | `tests/unit/test_sprint_command.py` | Update/add tests: verify no security-auditor in Stage B, verify sprint override keywords, verify Done regression skip instruction, verify char count < 3000 | Steps 1-2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Prompt template change only, no user input handling |
| SEC-2 | N/A | No authentication/authorization changes |
| SEC-3 | N/A | No data storage changes |
| SEC-4 | N/A | No API endpoint changes |
| SEC-5 | N/A | No dependency changes |
| SEC-6 | N/A | No file system operations added |
| SEC-7 | N/A | No network operations added |
| SEC-8 | N/A | No credential handling changes |

## Out of Scope

- Modifying Plan/Act/Check playbooks — sprint overrides for those are instruction-level in SPRINT_PROMPT, not code changes in playbooks (exception: Done playbook gets the smart regression gate per R2)
- Adding a `--sprint-mode` CLI flag — the optimization is purely prompt-level
- Parallelizing Plan and Act stages — they have a genuine sequential dependency
- Reducing subagent cold-start overhead — this requires Claude Code platform changes, not prompt changes
