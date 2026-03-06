# Project Context (Auto-generated)
> Last updated: 2026-03-06 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: BUG-031, BUG-032

## Current Stories
None — sprint board empty.

## Recent Completions
- BUG-031: CLAUDE.local.md docstring contradicts managed block behavior — updated docstring and template comment, 4 tests
- BUG-032: Missing E2E CLI test for spec-lint subcommand — added 4 E2E subprocess tests
- STORY-065: Sprint Stage A Model Consistency — split Stage A into A1-Plan (opus) + A2-Act (sonnet)

## Active Branches
None

## Key Decisions
- When a new feature changes a file's lifecycle, update all docstrings and template comments that describe the old lifecycle — stale claims mislead developers and break assertion tests (BUG-031)
- When adding to a prompt with a hard char-size assertion, compute net delta before writing (STORY-065)
- Files that are both pactkit-managed and user-editable need `<!-- pactkit:block:start/end -->` markers (STORY-064)
- Prompts must use installed CLI commands (`pactkit spec-lint`) not project-relative paths (BUG-030)
- Playbook fallbacks must never block on user input — use config-first resolution + non-blocking defaults (BUG-029)

## Next Recommended Action
`/project-plan` — Sprint board is empty. Plan the next story.
