# STORY-064: Persist Venv Config in CLAUDE.local.md Managed Block

| Field | Value |
|-------|-------|
| ID | STORY-064 |
| Status | Draft |
| Priority | High |
| Release | 1.6.6 |

## Background

When `pactkit update` is run and venv detection fails (e.g., fresh git checkout,
venv directory doesn't exist yet, or venv path moved), the `## Virtual Environment`
section is silently dropped from `CLAUDE.md`. Claude Code then falls back to the
system Python instead of the project venv — causing `pip install` to pollute the
global environment and test commands to fail.

The fix: also write venv config to `CLAUDE.local.md` as a pactkit-managed block.
Since `CLAUDE.local.md` is never fully overwritten by pactkit, the venv instructions
persist even when detection fails on a subsequent update. The managed block uses
HTML comment markers so user customizations below it are never disturbed.

## Target Call Chain

```
pactkit init/update
  → deploy() [deployer.py:66]
    → _generate_project_claude_md(config) [deployer.py:708]
      → detect_venv() → venv_info              # existing
      → atomic_write(CLAUDE.md, venv section)  # existing — unchanged
      → _generate_claude_local_md_if_missing() # modified: inserts managed block
      → _upsert_venv_managed_block(            # NEW
            claude_local_path, venv_info)
```

## Requirements

### R1: Write Managed Block on First Init
When `pactkit init` is run and venv is detected, the deployer MUST write a
pactkit-managed block to `CLAUDE.local.md` containing the venv instructions.

The block MUST be delimited by:
```
<!-- pactkit:venv:start -->
...venv instructions...
<!-- pactkit:venv:end -->
```

The block MUST be placed at the top of `CLAUDE.local.md`, before any user content.

### R2: Persist Across Update When Detection Fails
When `pactkit update` is run and venv detection fails (venv directory not found),
the deployer MUST leave the existing managed block in `CLAUDE.local.md` unchanged.
It MUST NOT remove the block just because detection failed.

### R3: Update Block When Venv Path Changes
When `pactkit update` is run and venv is detected with a different path than what
is in the managed block, the deployer MUST update only the content between the
`<!-- pactkit:venv:start -->` and `<!-- pactkit:venv:end -->` markers.
User content outside the markers MUST be preserved.

### R4: Preserve User Customizations
The deployer MUST NOT modify any content in `CLAUDE.local.md` that is outside
the `<!-- pactkit:venv:start/end -->` markers. User customizations SHOULD remain
intact across all `pactkit update` runs.

### R5: No Block Written When No Venv
If no venv is detected at init time and no managed block exists yet, the deployer
MUST NOT write an empty managed block. Skip silently.

### R6: CLAUDE.md Unchanged
The existing `## Virtual Environment` section in `CLAUDE.md` MUST remain unchanged.
This story does not remove or modify the CLAUDE.md venv section.

## Out of Scope

- Removing the venv section from `CLAUDE.md` (pre-existing tests depend on it)
- Parsing `pactkit.yaml` at runtime via `@`-import in `CLAUDE.md`
- Adding new `pactkit spec-lint`-style commands for venv management

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (`deployer.py`) |
| SEC-2 | No | No user input handling — file paths come from internal config |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend code |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No public endpoints |
| SEC-7 | No | No API exception handling |
| SEC-8 | No | No dependency changes |

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/generators/deployer.py` | Add `_upsert_venv_managed_block(path, venv_info)` function | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | Modify `_generate_claude_local_md_if_missing()` to insert managed block on first create | Step 1 | Low |
| 3 | `src/pactkit/generators/deployer.py` | Call `_upsert_venv_managed_block()` after venv detection in `_generate_project_claude_md()` | Step 1, 2 | Low |
| 4 | `tests/unit/test_story064_venv_local_md.py` | Add tests for all ACs | Step 1–3 | Low |

## Acceptance Criteria

### AC1: Managed block written on first init with venv
**Given** a project with `.venv` directory present
**When** `pactkit init` is run
**Then** `.claude/CLAUDE.local.md` contains `<!-- pactkit:venv:start -->` ... `<!-- pactkit:venv:end -->` block with the correct venv paths

### AC2: Block persists when detection fails on update
**Given** `.claude/CLAUDE.local.md` has an existing managed block with `.venv` paths
**When** `pactkit update` is run with no venv directory present
**Then** the managed block in `CLAUDE.local.md` still contains the original `.venv` paths (not removed)
**And** `CLAUDE.md` may or may not contain the venv section (irrelevant to this AC)

### AC3: Block updated when venv path changes
**Given** `.claude/CLAUDE.local.md` has managed block with `old_venv` paths
**When** `pactkit update` is run with `new_venv` directory present
**Then** the managed block is updated to use `new_venv` paths
**And** user content outside markers is preserved

### AC4: User content preserved
**Given** `.claude/CLAUDE.local.md` has managed block at top + user custom content below
**When** `pactkit update` is run
**Then** user content below `<!-- pactkit:venv:end -->` is untouched

### AC5: No empty block created when no venv at init
**Given** a project with no venv directory
**When** `pactkit init` is run
**Then** `.claude/CLAUDE.local.md` does NOT contain `<!-- pactkit:venv:start -->` markers
