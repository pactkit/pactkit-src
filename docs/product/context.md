# Project Context (Auto-generated)
> Last updated: 2026-03-05 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-064

## Current Stories
None — board is empty.

## Recent Completions
- STORY-064: Persist Venv Config in CLAUDE.local.md Managed Block — `_upsert_venv_managed_block()`, 10 tests
- BUG-030: Spec Linter Path Not Found in External Projects — added `pactkit spec-lint` CLI, 14 tests
- BUG-029: project-init Stack Detection Fallback Causes CLI Hang — config-first + auto fallback, 8 tests

## Active Branches
None

## Key Decisions
- Files that are both pactkit-managed and user-editable need `<!-- pactkit:block:start/end -->` markers — `_upsert_venv_managed_block()` pattern (STORY-064)
- Prompts must use installed CLI commands (`pactkit spec-lint`) not project-relative paths — hardcoded paths break in external projects (BUG-030)
- Playbook fallbacks must never block on user input — use config-first resolution + non-blocking defaults (BUG-029)
- Pre-existing tests form a hard constraint map when modifying prompt text — always build the map before editing
- Shared protocols in rules.py eliminate cross-playbook duplication (STORY-063)

## Next Recommended Action
Board is empty. Run `/project-design` for new features or `/project-plan` for next improvements.
