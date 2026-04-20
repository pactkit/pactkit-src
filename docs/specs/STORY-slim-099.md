# STORY-slim-099: Add Act Phase reference to Shared Protocols Context.md section

| Field | Value |
|-------|-------|
| ID | STORY-slim-099 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.2 |

## Background

The Shared Protocols rule `07-shared-protocols.md` defines the Context.md Canonical Format and lists which PDCA phases reference it: `Init Phase 6, Plan Phase 3, Done Phase 4.5`. However, `/project-act` Phase 4 also updates context.md via `pactkit context --continuation` (source template in `commands.py:202`), but this reference is missing from the Shared Protocols listing.

Additionally, the deployed plugin version (`pactkit-plugin/commands/project-act.md`) is missing Act Phase 4 step 3 (`pactkit context --continuation`), which exists in the source template. This causes context.md to not reflect Act progress when a session is interrupted before `/project-done`.

**Impact**: When a user runs `/project-plan` → `/project-act` and exits without running `/project-done`, context.md remains frozen at the Plan snapshot. New sessions cold-start with stale state.

## Requirements

### R1: Shared Protocols Reference Update (MUST)

The `Context.md Canonical Format` section in `07-shared-protocols.md` MUST include `Act Phase 4` in its "Referenced by" line, alongside the existing `Init Phase 6, Plan Phase 3, Done Phase 4.5`.

### R2: Deployed Plugin Sync (MUST)

The deployed `pactkit-plugin/commands/project-act.md` MUST include Act Phase 4 step 3 (`pactkit context --continuation`) matching the source template in `commands.py`. This is achieved by running `pactkit update` (redeploy).

## Acceptance Criteria

### AC1: Shared Protocols includes Act Phase 4 (R1)

- **Given** the file `~/.claude/rules/07-shared-protocols.md` exists
- **When** reading the `Context.md Canonical Format` section's "Referenced by" line
- **Then** it contains `Act Phase 4` alongside `Init Phase 6, Plan Phase 3, Done Phase 4.5`

### AC2: Deployed Act playbook includes context update step (R2)

- **Given** `pactkit update` has been run after this change
- **When** reading `pactkit-plugin/commands/project-act.md` Phase 4
- **Then** step 3 contains `pactkit context --continuation --last-command "/project-act {STORY_ID}" --phase "Phase 4: complete"`

### AC3: Source template consistency (R2)

- **Given** the source template in `src/pactkit/prompts/commands.py`
- **When** comparing Act Phase 4 steps between source and deployed
- **Then** the deployed version matches the source template (no drift)

## Target Call Chain

```
User runs /project-act STORY-XXX
  → Act Phase 4 (Sync & Document)
    → pactkit context --continuation --last-command "/project-act STORY-XXX" --phase "Phase 4: complete"
      → context_gen.generate_context(continuation_args={...})
        → writes docs/product/context.md (full regeneration + Agent Continuation section)
```

Source template: `src/pactkit/prompts/commands.py:199-202`
Shared Protocols: `~/.claude/rules/07-shared-protocols.md:14` (referenced by list)
Deployed plugin: `pactkit-plugin/commands/project-act.md:68-70`

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/rules.py` | Add `Act Phase 4` to Context.md Canonical Format "Referenced by" line | None | Low |
| 2 | Run `pactkit update` | Redeploy to sync `pactkit-plugin/commands/project-act.md` | Step 1 | Low |
| 3 | Verify deployed file | Confirm Act Phase 4 step 3 present in deployed playbook | Step 2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | docs/prompt-only change, no user input handling |
| SEC-2 | N/A | docs/prompt-only change, no input validation |
| SEC-3 | N/A | no database interaction |
| SEC-4 | N/A | no frontend files |
| SEC-5 | N/A | no auth/session changes |
| SEC-6 | N/A | no API endpoints |
| SEC-7 | N/A | no error handling changes |
| SEC-8 | N/A | no dependency changes |

## Out of Scope

- Changing the `pactkit context` CLI behavior or `context_gen.py` logic
- Adding new context.md sections or changing the canonical format
- Modifying other PDCA commands' context update behavior
