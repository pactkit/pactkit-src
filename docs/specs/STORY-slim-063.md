# STORY-slim-063: Migrate Claude Code commands to skills deployment

| Field | Value |
|-------|-------|
| ID | STORY-slim-063 |
| Status | Done |
| Priority | P1 |
| Release | 2.7.0 |

## Background

Claude Code has evolved: skills (`~/.claude/skills/{name}/SKILL.md`) are now the recommended mechanism over legacy commands (`~/.claude/commands/{name}.md`). Skills take precedence when both exist with the same name, and they unlock capabilities like `context: fork`, supporting file directories, and `user-invocable` frontmatter.

Currently PactKit deploys 11 PDCA commands to `~/.claude/commands/` as flat `.md` files, and 10 embedded skills to `~/.claude/skills/` as subdirectories. This story migrates the 11 commands into the skills directory, unifying all 21 PactKit-deployed prompt files under one location.

Scope: **classic format only** (Claude Code). OpenCode (no commands) and Codex (independent prompts dir) are unaffected.

## Requirements

### R1: Deploy commands as skills (MUST)

`_deploy_commands()` MUST write command files to `{skills_dir}/{name}/SKILL.md` (subdirectory structure) instead of `{commands_dir}/{name}.md` (flat file). The content format (@ rule imports, frontmatter with `description` and `allowed-tools`, body) MUST remain identical.

### R2: Merge VALID_COMMANDS into VALID_SKILLS (MUST)

`config.py` MUST merge the 11 command names into `VALID_SKILLS`, resulting in 21 total entries. `VALID_COMMANDS` MAY be retained as an alias or subset for backward compatibility with pactkit.yaml `commands:` section, but deployment MUST target skills directory.

### R3: Legacy cleanup (MUST)

`_cleanup_legacy()` MUST remove old `~/.claude/commands/project-*.md` files on `pactkit update` to prevent stale command files shadowed by the new skills.

### R4: pactkit.yaml backward compatibility (MUST)

The `commands:` key in `pactkit.yaml` MUST continue to work for selective deployment. Internally the deployer reads both `commands` and `skills` sections and deploys all to `skills_dir/`.

### R5: Cross-format isolation (MUST)

This change MUST only affect the `classic` format. OpenCode and Codex deployers MUST NOT be modified. The `has_custom_commands` field in FormatProfile MAY be deprecated for classic but MUST NOT break other formats.

### R6: Prompt source unchanged (SHOULD)

`src/pactkit/prompts/commands.py` SHOULD NOT require content changes. Only the deployment target path changes.

## Acceptance Criteria

### AC1: Commands deployed to skills directory (R1)

- **Given** `pactkit update` runs for classic format
- **When** deployment completes
- **Then** all 11 commands exist as `~/.claude/skills/project-{name}/SKILL.md` with correct content (@ imports, frontmatter, body)

### AC2: VALID_SKILLS contains all 21 entries (R2)

- **Given** `config.py` is imported
- **When** `VALID_SKILLS` is inspected
- **Then** it contains the 10 original skills + 11 command-turned-skills = 21 total

### AC3: Legacy command files removed (R3)

- **Given** old `~/.claude/commands/project-*.md` files exist from a previous version
- **When** `pactkit update` runs
- **Then** all `project-*.md` files in `commands/` are removed (non-PactKit files like `ultra-think.md` are preserved)

### AC4: pactkit.yaml commands section still works (R4)

- **Given** pactkit.yaml has `commands: [project-plan, project-act]` (subset)
- **When** selective deployment runs
- **Then** only `project-plan` and `project-act` are deployed to skills dir; other commands are skipped

### AC5: Codex and OpenCode unaffected (R5)

- **Given** a Codex or OpenCode deployer
- **When** deployment runs
- **Then** no changes to their command/prompt deployment paths

### AC6: Existing 10 skills coexist (R1)

- **Given** the 10 embedded skills (pactkit-trace, pactkit-board, etc.) already in `~/.claude/skills/`
- **When** 11 commands are also deployed to `~/.claude/skills/`
- **Then** all 21 coexist without conflicts (different names, no overwrites)

## Target Call Chain

```
pactkit update → _deploy_classic() [deployer.py:259]
  → _deploy_commands(commands_dir, ...) [deployer.py:762]
    → atomic_write(commands_dir / f"{name}.md", content) [deployer.py:822]
  → _deploy_skills(skills_dir, ...) [deployer.py:402]
    → atomic_write(skills_dir / name / "SKILL.md", content) [deployer.py:463]
```

After migration:
```
pactkit update → _deploy_classic() [deployer.py:259]
  → _deploy_commands(skills_dir, ...) [deployer.py:762]  # target changed
    → atomic_write(skills_dir / name / "SKILL.md", content)  # subdirectory
  → _deploy_skills(skills_dir, ...) [deployer.py:402]  # unchanged
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/config.py` | Merge 11 commands into VALID_SKILLS (21 total), keep VALID_COMMANDS as reference set | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | Modify `_deploy_commands()` to write `{target_dir}/{name}/SKILL.md` instead of `{target_dir}/{name}.md` | Step 1 | Medium |
| 3 | `src/pactkit/generators/deployer.py` | Modify `_deploy_classic()` to pass `skills_dir` to `_deploy_commands()` instead of `commands_dir` | Step 2 | Medium |
| 4 | `src/pactkit/generators/deployer.py` | Add legacy cleanup in `_cleanup_legacy()` to remove `commands/project-*.md` files | Step 3 | Low |
| 5 | `tests/` | Update tests: deployment assertions, VALID_SKILLS count, legacy cleanup | Steps 1-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | No new code paths — deployment target path change only |
| SEC-2 | N/A | No user input handling |
| SEC-3 | N/A | No database |
| SEC-4 | N/A | No frontend |
| SEC-5 | N/A | No auth changes — file write paths only |
| SEC-6 | N/A | No API routes |
| SEC-7 | N/A | Existing error handling (atomic_write) unchanged |
| SEC-8 | N/A | No dependency changes |

## Out of Scope

- OpenCode and Codex deployer changes
- Prompt content changes (`src/pactkit/prompts/commands.py`)
- New skill-only features (`context: fork`, etc.) — future story
- `ultra-think.md` and other non-PactKit command files in `~/.claude/commands/`
