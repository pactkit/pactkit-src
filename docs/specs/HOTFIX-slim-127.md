# HOTFIX-slim-127: Add codegraph sync to all PDCA command source templates

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-127 |
| Status | Done |
| Priority | P2 |
| Release | 2.14.1 |

## Background

STORY-slim-124 introduced codegraph integration and added `codegraph sync` to the **deployed** skill files (`~/.claude/skills/project-*/SKILL.md`), but never back-ported the changes to the **source** templates in `pactkit-plugin/commands/`. Next `pactkit init --format plugin` deploy would overwrite the fixes.

Root cause: source/deploy drift — edits applied to deploy target instead of source of truth.

## Requirements

### R1: Codegraph sync in all code-mutating commands (MUST)

Every PDCA command that modifies source code or runs after code modification MUST include a conditional `codegraph sync` step in its source template (`pactkit-plugin/commands/`).

### R2: Codegraph auto-setup in plan (MUST)

`project-plan` source template MUST include the codegraph auto-setup step (init if missing).

## Acceptance Criteria

### AC1: Source templates contain codegraph steps (R1, R2)

- **Given** the pactkit source tree at `pactkit-plugin/commands/`
- **When** `grep -l "codegraph" pactkit-plugin/commands/project-*.md` is run
- **Then** it returns: project-plan.md, project-act.md, project-done.md, project-hotfix.md

### AC2: Deploy produces matching output (R1)

- **Given** source templates are updated
- **When** `pactkit init --format plugin` deploys to target
- **Then** deployed skill files contain the same codegraph steps

## Target Call Chain

N/A — this is a prompt/playbook change, no source code logic.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `pactkit-plugin/commands/project-plan.md` | Add codegraph auto-setup to Phase 1 Visual Scan | None | Low |
| 2 | `pactkit-plugin/commands/project-act.md` | Add codegraph sync to Phase 4 | None | Low |
| 3 | `pactkit-plugin/commands/project-done.md` | Add codegraph sync to Phase 2 | None | Low |
| 4 | `pactkit-plugin/commands/project-hotfix.md` | Add Phase 3.6 codegraph sync | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1~SEC-8 | N/A | Docs/prompts only, no code execution paths changed |

## Out of Scope

- Commands that don't touch source code (project-check, project-clarify, project-design, project-pr, project-init, project-release, project-sprint)
