# Project Context (Auto-generated)
> Last updated: 2026-03-13 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: BUG-033

## Current Stories
None — sprint board empty.

## Recent Completions
- BUG-033: scaffold.py create_spec() template updated to pass spec-lint — metadata table format, R1 subsections, {VERSION} placeholder, 4 new tests
- BUG-031: CLAUDE.local.md docstring contradicts managed block behavior — updated docstring and template comment, 4 tests
- BUG-032: Missing E2E CLI test for spec-lint subcommand — added 4 E2E subprocess tests

## Active Branches
None

## Key Decisions
- When adding a validation linter, update all code generators to produce output that passes the new rules — test generator output against linter directly (BUG-033)
- When a new feature changes a file's lifecycle, update all docstrings and template comments that describe the old lifecycle (BUG-031)
- When adding to a prompt with a hard char-size assertion, compute net delta before writing (STORY-065)
- Files that are both pactkit-managed and user-editable need `<!-- pactkit:block:start/end -->` markers (STORY-064)
- Playbook fallbacks must never block on user input — use config-first resolution + non-blocking defaults (BUG-029)

## Next Recommended Action
`/project-plan` — Sprint board is empty. Plan the next story.
