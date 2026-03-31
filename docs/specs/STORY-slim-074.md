# STORY-slim-074: Fix init playbook: eliminate DETECTED_ENV, use template variables

| Field | Value |
|-------|-------|
| ID | STORY-slim-074 |
| Status | Done |
| Priority | P0 |
| Release | 2.9.4 |

## Background

The `project-init` playbook in `commands.py` contains a hardcoded `DETECTED_ENV` detection mechanism that only recognizes two IDE formats (classic/opencode). This causes three critical problems:

1. **Codex is never detected** — Codex users always fall through to `DETECTED_ENV=classic`, generating wrong file paths (`.codex/CLAUDE.md`) and wrong CLI flags (`pactkit init` instead of `pactkit init --format codex`).
2. **Hardcoded paths violate DIP** (Architecture Principle #3) — The playbook uses literal `.claude/`, `.opencode/`, `~/.config/opencode/` strings instead of the template variable system (`{PROJECT_CONFIG_DIR}`, `{PACTKIT_YAML}`, `{SKILLS_ROOT}`, etc.) that all other commands already use.
3. **OCP violation** — Adding a new format (e.g., `cursor`, `trae`) would require rewriting the init playbook's branching logic, instead of just adding a `FormatProfile` entry.

The root cause is that `DETECTED_ENV` runtime detection is unnecessary: the playbook is already deployed per-format by `_deploy_commands()`, so the agent inherently knows which IDE it runs in. The fix is to eliminate all format-branching and replace all hardcoded paths with template variables, making the playbook format-agnostic at source level.

## Requirements

### R1: Eliminate DETECTED_ENV runtime detection (MUST)

Remove all `DETECTED_ENV` variable assignment and branching from the init playbook source template. The deployed playbook MUST NOT attempt to detect which IDE is running at runtime.

### R2: Replace all hardcoded paths with template variables (MUST)

Every occurrence of `.claude/`, `.opencode/`, `.codex/`, `~/.config/opencode/`, `CLAUDE.md`, `AGENTS.md` in the init playbook source MUST be replaced with the corresponding template variable: `{PROJECT_CONFIG_DIR}`, `{GLOBAL_CONFIG_DIR}`, `{PACTKIT_YAML}`, `{INSTRUCTIONS_FILE}`, `{DISPLAY_NAME}`, `{SKILLS_ROOT}`, `{FORMAT_NAME}`.

### R3: Add {FORMAT_NAME} template variable (MUST)

Add `FORMAT_NAME` to `_render_prompt()` var_map in `deployer.py`, resolved from `profile.name` (e.g., `classic`, `opencode`, `codex`). This enables `pactkit init --format {FORMAT_NAME}` in the playbook.

### R4: Merge Phase 5-6 into a single format-agnostic flow (MUST)

The current Phase 1.5 (classic-specific project instructions) and Phase 1.6 (opencode-specific project setup) MUST be merged into a single format-agnostic flow that uses `{INSTRUCTIONS_FILE}` and `{PROJECT_CONFIG_DIR}` instead of per-format branches.

### R5: Deployed playbooks MUST be format-correct after `pactkit deploy` (MUST)

After deployment, the rendered init playbook for each format MUST contain only that format's paths. Zero cross-format path references allowed (e.g., Codex version must not mention `.claude/` or `.opencode/`).

## Acceptance Criteria

### AC1: No DETECTED_ENV in source template (R1)

- **Given** the init playbook source in `commands.py`
- **When** searching for `DETECTED_ENV` in the source template string
- **Then** zero occurrences are found

### AC2: No hardcoded IDE paths in source template (R2)

- **Given** the init playbook source in `commands.py`
- **When** searching for literal `.claude/`, `.opencode/`, `.codex/`, `~/.config/opencode`
- **Then** zero occurrences are found (all replaced by template variables)

### AC3: FORMAT_NAME resolves correctly for all 3 formats (R3)

- **Given** `_render_prompt()` is called with the init playbook template
- **When** rendering for classic/opencode/codex profiles
- **Then** `{FORMAT_NAME}` resolves to `classic`, `opencode`, `codex` respectively

### AC4: Deployed Classic init has only classic paths (R5)

- **Given** `pactkit deploy --format classic` has run
- **When** reading the deployed init playbook at `~/.claude/skills/project-init/SKILL.md`
- **Then** it contains `.claude/`, `CLAUDE.md`, `~/.claude/skills` — and zero references to `.opencode/`, `.codex/`, `AGENTS.md`

### AC5: Deployed Codex init has only codex paths (R5)

- **Given** `pactkit deploy --format codex` has run
- **When** reading the deployed init playbook at `~/.codex/skills/project-init/SKILL.md`
- **Then** it contains `.codex/`, `AGENTS.md`, `~/.codex/skills` — and zero references to `.claude/`, `.opencode/`, `CLAUDE.md`

### AC6: Deployed OpenCode init has only opencode paths (R5)

- **Given** `pactkit deploy --format opencode` has run
- **When** reading the deployed init playbook at `~/.config/opencode/commands/project-init.md`
- **Then** it contains `.opencode/`, `AGENTS.md`, `~/.config/opencode/skills` — and zero references to `.claude/`, `.codex/`, `CLAUDE.md`

### AC7: Single unified flow for project instructions (R4)

- **Given** the init playbook source in `commands.py`
- **When** examining Phase 1 structure
- **Then** there is ONE project instructions flow using `{PROJECT_CONFIG_DIR}/{INSTRUCTIONS_FILE}`, not separate Phase 5/6 per-format branches

### AC8: pactkit init/update uses {FORMAT_NAME} (R3)

- **Given** the rendered init playbook for any format
- **When** examining the `pactkit init` and `pactkit update` commands in the playbook
- **Then** they use `--format <resolved_format_name>` (e.g., `--format codex` for Codex)

## Target Call Chain

```
commands.py COMMANDS_CONTENT["project-init.md"]  (source template)
  → deployer.py _render_prompt(template, profile)  (replace {FORMAT_NAME}, {PROJECT_CONFIG_DIR}, etc.)
    → deployer.py _deploy_commands()  (write to per-format path)
      → ~/.claude/skills/project-init/SKILL.md     (classic)
      → ~/.config/opencode/commands/project-init.md (opencode)
      → ~/.codex/skills/project-init/SKILL.md       (codex)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/generators/deployer.py` | Add `FORMAT_NAME: profile.name` to `_render_prompt()` var_map | None | Low |
| 2 | `src/pactkit/prompts/commands.py` | Rewrite init playbook: remove DETECTED_ENV, replace hardcoded paths with template vars, merge Phase 5/6 | Step 1 | Medium |
| 3 | `tests/unit/test_init_playbook_074.py` | Test: no DETECTED_ENV in source, no hardcoded paths, FORMAT_NAME resolves, deployed output format-correct | Steps 1-2 | Low |
| 4 | Deployment verification | `pactkit deploy --format all` + grep deployed files for cross-format leaks | Step 2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Prompt template change only, no injection surface |
| SEC-2 | N/A | No new user input handling — template variables are code-controlled |
| SEC-3 | N/A | No database |
| SEC-4 | N/A | No frontend |
| SEC-5 | N/A | No auth change |
| SEC-6 | N/A | No API change |
| SEC-7 | N/A | No error handling change |
| SEC-8 | N/A | No dependency change |

## Out of Scope

- Rewriting other commands (project-act, project-check, etc.) — they already use template variables correctly
- Adding new FormatProfile fields — existing fields are sufficient
- Changing `_deploy_commands()` logic — only the template source and var_map change
- OpenCode-specific `opencode.json` generation — moved to a `{DISPLAY_NAME}`-conditional instruction, not a hardcoded branch
