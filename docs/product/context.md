# Project Context (Auto-generated)
> Last updated: 2026-02-26T20:30:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 66 items archived
- **Current Version**: 1.3.1
- **Branch**: main

## Current Story
None — board is clean.

## Recent Completions
- BUG-024: board.py regex flexible title format — accepts bare `### STORY-xxx:` titles
- STORY-041: Test Pyramid Restructuring — CLI E2E tests, integration separation, shared fixtures, CI tiering
- STORY-040: Project CLAUDE.md Layered Architecture — dual-file architecture with CLAUDE.local.md

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Read-side regex tolerance (`\[?...\]?:?`) is simpler than format detection — single shared `_TITLE_RE` constant fixes all 4 parse sites | BUG-024 |
| 2026-02 | Config rewriters must preserve unknown user-defined keys — round-trip safety for user extensions | BUG-023 |
| 2026-02 | Dual-file layered architecture separates framework and user content — enables safe regeneration | STORY-040 |
| 2026-02 | CLI tools need subprocess-based E2E tests — calling main() doesn't test entry point registration | STORY-041 |
| 2026-02 | Conditional steps marked "IF available" may be skipped — backfill safety net (Done 3.5.5) provides coverage | BUG-018 |

## Next Recommended Action
Run `/project-plan` to plan the next story, or `/project-design` for a new feature area.
