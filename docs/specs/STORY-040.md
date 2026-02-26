# STORY-040: Project CLAUDE.md Layered Architecture — Separate Framework and User Content

- **Status**: Draft
- **Priority**: High
- **Release**: 1.4.0
- **Author**: System Architect
- **Created**: 2026-02-26

## Problem Statement

Project-level `$CWD/.claude/CLAUDE.md` currently uses a **write-once, never-touch** policy (BUG-021 R1). This creates a dilemma:

1. **PactKit upgrades can't deliver new template content** — If PactKit adds new sections (e.g., new LANG_PROFILES fields, improved venv instructions), users with existing CLAUDE.md never receive them.
2. **Backup-then-regenerate loses user customizations** — The BUG-020 approach (backup → overwrite) was rejected precisely because users add project-specific instructions (architecture notes, team conventions, custom rules) to CLAUDE.md.

Root cause: **framework content and user content are co-located in a single file**, making safe regeneration impossible.

## Solution: Dual-File Layered Architecture

Split project CLAUDE.md into two files with clear ownership:

```
$CWD/.claude/
├── CLAUDE.md              ← PactKit-managed (regenerated on every update)
├── CLAUDE.local.md        ← User-owned (never touched by PactKit after initial creation)
└── pactkit.yaml           ← Config (unchanged)
```

**CLAUDE.md** is the framework file — PactKit regenerates it on every `pactkit init/update`. It imports user content via `@` reference:

```markdown
# project-name — Project Context

## Virtual Environment
...

## Dev Commands
...

@./docs/product/context.md
@./.claude/CLAUDE.local.md
```

**CLAUDE.local.md** is the user file — PactKit creates an empty template on first run, then never modifies it again:

```markdown
# Project Local Instructions
# Add your custom Claude Code instructions below.
# PactKit will never overwrite this file.
```

## Target Call Chain

```
cli.py:main()
  → deployer.py:deploy()
    → deployer.py:_deploy_classic()
      → deployer.py:_generate_project_claude_md()        # RENAMED: no longer "if_missing"
      │   ├── Always regenerates CLAUDE.md (framework content)
      │   └── deployer.py:_generate_claude_local_md_if_missing()  # NEW
      │       └── Creates CLAUDE.local.md only if missing
      → deployer.py:_deploy_claude_md()                   # Global — unchanged
```

## Requirements

### R1: CLAUDE.md MUST be regenerated on every deploy
- `_generate_project_claude_md_if_missing()` MUST be renamed to `_generate_project_claude_md()`.
- The **skip-if-exists guard** (line 674) MUST be removed.
- The function MUST always overwrite `$CWD/.claude/CLAUDE.md` with the latest template.
- The HOME directory guard (line 668-669) MUST be preserved.
- The preview-mode guard (`target is None` at line 134) MUST be preserved.

### R2: CLAUDE.md MUST import CLAUDE.local.md via `@` reference
- The generated CLAUDE.md MUST include `@./.claude/CLAUDE.local.md` as the last `@` import line.
- Order: framework content → `@./docs/product/context.md` → `@./.claude/CLAUDE.local.md`.

### R3: CLAUDE.local.md MUST be created only if missing
- A new function `_generate_claude_local_md_if_missing()` MUST be created.
- It MUST write a minimal template with a comment header explaining the file's purpose.
- It MUST NOT modify an existing `CLAUDE.local.md` under any circumstances.
- It MUST be called from `_generate_project_claude_md()` (not from the caller).

### R4: User content in existing CLAUDE.md SHOULD be migrated
- On first run after upgrade, if `CLAUDE.md` exists but `CLAUDE.local.md` does not:
  - The function SHOULD detect whether the existing `CLAUDE.md` was user-modified (compare structure against expected PactKit template).
  - If user modifications are detected, the function SHOULD copy the existing `CLAUDE.md` content to `CLAUDE.local.md` before overwriting.
  - A simple heuristic is sufficient: if the file does NOT start with `# {project_name}` or does NOT contain the expected PactKit sections, treat it as user-modified.
- If no user modifications are detected (pure PactKit template), skip migration.

### R5: Global CLAUDE.md behavior MUST remain unchanged
- `_deploy_claude_md()` (lines 347-364) MUST NOT be modified.
- The always-overwrite policy for `~/.claude/CLAUDE.md` is correct and intentional.

### R6: Existing guards MUST be preserved
- HOME directory guard: `if project_root.resolve() == Path.home().resolve(): return`
- Preview-mode guard: only call when `target is None`

## Acceptance Criteria

### Scenario 1: Fresh project (no CLAUDE.md exists)
- **Given** a project with no `$CWD/.claude/CLAUDE.md` and no `$CWD/.claude/CLAUDE.local.md`
- **When** `pactkit init` is run
- **Then** `CLAUDE.md` is created with framework content (venv, dev commands, `@` imports)
- **And** `CLAUDE.local.md` is created with the empty template
- **And** `CLAUDE.md` contains `@./.claude/CLAUDE.local.md` as import

### Scenario 2: Subsequent update (both files exist)
- **Given** a project with existing `CLAUDE.md` and `CLAUDE.local.md` (user has added custom instructions)
- **When** `pactkit update` is run
- **Then** `CLAUDE.md` is regenerated with latest framework content
- **And** `CLAUDE.local.md` is NOT modified
- **And** user's custom instructions in `CLAUDE.local.md` remain intact

### Scenario 3: Upgrade migration (old CLAUDE.md with user content, no CLAUDE.local.md)
- **Given** a project with user-modified `CLAUDE.md` but no `CLAUDE.local.md`
- **When** `pactkit update` is run
- **Then** existing `CLAUDE.md` content is migrated to `CLAUDE.local.md`
- **And** `CLAUDE.md` is regenerated with latest framework content
- **And** `CLAUDE.md` imports the new `CLAUDE.local.md`

### Scenario 4: Upgrade migration (unmodified PactKit CLAUDE.md, no CLAUDE.local.md)
- **Given** a project with unmodified PactKit-generated `CLAUDE.md` but no `CLAUDE.local.md`
- **When** `pactkit update` is run
- **Then** `CLAUDE.local.md` is created with empty template (no migration needed)
- **And** `CLAUDE.md` is regenerated

### Scenario 5: HOME directory guard
- **Given** `Path.cwd() == Path.home()`
- **When** `_generate_project_claude_md()` is called
- **Then** no files are written (guard returns early)

### Scenario 6: Preview mode guard
- **Given** `pactkit init -t /tmp/preview`
- **When** deployment runs
- **Then** `_generate_project_claude_md()` is NOT called

## Non-Goals

- Modifying the global `~/.claude/CLAUDE.md` generation logic.
- Changing `pactkit.yaml` auto-merge behavior.
- Adding `CLAUDE.local.md` support for plugin/marketplace formats (future scope).
