# Project Context (Auto-generated)
> Last updated: 2026-03-04 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: BUG-028

## Current Stories
None — board is empty.

## Recent Completions
- BUG-028: Ghost DEV_REF residual in Check and Review — removed ghost refs, added 17 regression guard tests
- STORY-063: PDCA Playbook Prompt Slimming (22.5% reduction, shared protocols, Sprint Protocol-Only)
- STORY-062: Print MCP recommendations after init/update

## Active Branches
None

## Key Decisions
- BUG-028 R3 (dead code removal) CANCELLED — 33 tests in test_stack_references.py protect constants (STORY-026 Spec)
- Constants in references.py are Spec-mandated but not yet deployed — a future Story could inject them via deployer.py
- Pre-existing tests form a hard constraint map when modifying prompt text — always build the map before editing
- Shared protocols in rules.py eliminate cross-playbook duplication (STORY-063)

## Next Recommended Action
Board is empty. Run `/project-design` for new features or `/project-plan` for next improvements.
