# STORY-slim-125: Add model frontmatter to all PDCA command/skill prompts

| Field | Value |
|-------|-------|
| ID | STORY-slim-125 |
| Status | Done |
| Priority | P1 |
| Release | 2.14.0 |

## Background

Originally (v2.14.0), all PDCA command frontmatter included a `model:` field to ensure consistent model routing. However, this caused breakage in enterprise Bedrock deployments: Claude Code resolves `model: sonnet` to the latest Anthropic model ID (e.g., `us.anthropic.claude-sonnet-4-5-20250929-v1:0`), which may not be available in a user's Bedrock deployment.

Superseded by STORY-slim-134 (v2.17.0): the `model:` field is removed from all command frontmatter. Commands now inherit the user's session-level default model, which is controlled by environment variables (`ANTHROPIC_DEFAULT_SONNET_MODEL`, etc.) that the user configures for their provider.

## Requirements

### R1: No PDCA command has model frontmatter (MUST)

No command/skill prompt in `src/pactkit/prompts/commands.py` or `src/pactkit/prompts/workflows.py` MUST include a `model:` field in its frontmatter block. Commands inherit the session default model.

### R2: Deploy produces no model field in SKILL.md (MUST)

After `pactkit update`, no deployed `~/.claude/skills/project-*/SKILL.md` MUST contain a `model:` line in its YAML frontmatter.

## Acceptance Criteria

### AC1: No command has model field (R1)

- **Given** the source prompts in `commands.py` and `workflows.py`
- **When** their frontmatter is parsed
- **Then** no command prompt contains a `model:` field

### AC2: Deploy produces no model in SKILL.md (R2)

- **Given** `pactkit update` is run
- **When** deployed SKILL.md files are inspected
- **Then** no `project-*` skill contains `model:` in frontmatter

### AC3: project-design has no model field (R1)

- **Given** the `project-design` prompt in `workflows.py`
- **When** its frontmatter is read
- **Then** no `model:` field is present

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
