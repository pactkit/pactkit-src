# STORY-slim-125: Add model frontmatter to all PDCA command/skill prompts

| Field | Value |
|-------|-------|
| ID | STORY-slim-125 |
| Status | Done |
| Priority | P1 |
| Release | 2.14.0 |

## Background

Of 11 PDCA command/skill prompts deployed by PactKit, only 2 (`project-plan: opus`, `project-act: sonnet`) have `model:` in their frontmatter. The remaining 9 rely on Claude Code's session-level default model. This means heavier commands like `project-design` run on whatever model the user happens to have active, rather than the appropriate model for the task complexity.

The `model:` frontmatter field in SKILL.md tells Claude Code which model to use when invoking that skill. Adding it ensures consistent model routing regardless of the user's session default.

## Requirements

### R1: All PDCA commands MUST have model frontmatter (MUST)

Every command/skill prompt in `src/pactkit/prompts/commands.py` and `src/pactkit/prompts/workflows.py` MUST include a `model:` field in its frontmatter block. Assignment:

| Command | Model | Rationale |
|---------|-------|-----------|
| project-plan | opus | Architecture + deep reasoning (already set) |
| project-act | sonnet | Code implementation (already set) |
| project-design | opus | Product design requires deep reasoning |
| project-check | sonnet | QA verification |
| project-done | sonnet | Housekeeping/commit |
| project-hotfix | sonnet | Quick fix |
| project-init | sonnet | Scaffolding |
| project-pr | sonnet | PR creation |
| project-release | sonnet | Release ops |
| project-sprint | sonnet | Orchestration (subagents have own models) |
| project-clarify | sonnet | Requirement clarification |

### R2: Deploy produces correct model in SKILL.md (MUST)

After `pactkit update`, every deployed `~/.claude/skills/project-*/SKILL.md` MUST contain the correct `model:` line in its YAML frontmatter.

## Acceptance Criteria

### AC1: All commands have model field (R1)

- **Given** the source prompts in `commands.py` and `workflows.py`
- **When** their frontmatter is parsed
- **Then** every command prompt contains a `model:` field with value `opus` or `sonnet`

### AC2: Deploy produces model in SKILL.md (R2)

- **Given** `pactkit update` is run
- **When** deployed SKILL.md files are inspected
- **Then** all 11 `project-*` skills contain `model:` in frontmatter

### AC3: project-design uses opus (R1)

- **Given** the `project-design` prompt in `workflows.py`
- **When** its frontmatter is read
- **Then** `model: opus` is present

## Target Call Chain

```
commands.py / workflows.py (prompt string with frontmatter)
  → deployer.py _deploy_skills()
    → writes ~/.claude/skills/project-*/SKILL.md
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Add `model: sonnet` to check, done, clarify, init, release, pr frontmatter | None | Low |
| 2 | `src/pactkit/prompts/workflows.py` | Add `model: sonnet` to sprint, hotfix; `model: opus` to design | None | Low |
| 3 | `tests/unit/` | Test that all command prompts have model field | Steps 1-2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 through SEC-8 | N/A | Prompt-only changes, no user input, no external systems |

## Out of Scope

- Changing embedded skill models (pactkit-trace, pactkit-draw, etc.) — already assigned
- Validating model availability at runtime (Claude Code handles gracefully)
- Adding model field to agent definitions (separate mechanism via `agent_models` config)
