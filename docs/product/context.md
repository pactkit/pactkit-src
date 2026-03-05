# Project Context (Auto-generated)
> Last updated: 2026-03-05 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-065

## Current Stories
None — sprint board empty.

## Recent Completions
- STORY-065: Sprint Stage A Model Consistency — split Stage A into A1-Plan (opus) + A2-Act (sonnet), config-aware via pactkit.yaml agent_models
- STORY-064: Persist Venv Config in CLAUDE.local.md Managed Block — `_upsert_venv_managed_block()`, 10 tests
- BUG-030: Spec Linter Path Not Found in External Projects — added `pactkit spec-lint` CLI, 14 tests

## Active Branches
None

## Key Decisions
- When adding to a prompt with a hard char-size assertion, compute net delta (new_bytes - replaced_bytes) before writing; compact inline format for A1/A2 kept SPRINT_PROMPT under 3000 chars (STORY-065)
- Files that are both pactkit-managed and user-editable need `<!-- pactkit:block:start/end -->` markers — `_upsert_venv_managed_block()` pattern (STORY-064)
- Prompts must use installed CLI commands (`pactkit spec-lint`) not project-relative paths — hardcoded paths break in external projects (BUG-030)
- Playbook fallbacks must never block on user input — use config-first resolution + non-blocking defaults (BUG-029)
- Pre-existing tests form a hard constraint map when modifying prompt text — always build the map before editing

## Next Recommended Action
`/project-plan` — Sprint board is empty. Plan the next story.
