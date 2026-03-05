# Project Context (Auto-generated)
> Last updated: 2026-03-05 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: BUG-030

## Current Stories
None — board is empty.

## Recent Completions
- BUG-030: Spec Linter Path Not Found in External Projects — added `pactkit spec-lint` CLI, 14 tests
- BUG-029: project-init Stack Detection Fallback Causes CLI Hang — config-first + auto fallback, 8 tests
- BUG-028: Ghost DEV_REF residual in Check and Review — removed ghost refs, added 17 regression guard tests

## Active Branches
None

## Key Decisions
- Prompts must use installed CLI commands (`pactkit spec-lint`) not project-relative paths — hardcoded paths break in external projects (BUG-030)
- Playbook fallbacks must never block on user input — use config-first resolution + non-blocking defaults (BUG-029)
- Pre-existing tests form a hard constraint map when modifying prompt text — always build the map before editing
- Shared protocols in rules.py eliminate cross-playbook duplication (STORY-063)
- Constants protected by Spec-mandated tests must NOT be removed even if deployer.py never uses them (BUG-028)

## Next Recommended Action
Board is empty. Run `/project-design` for new features or `/project-plan` for next improvements.
