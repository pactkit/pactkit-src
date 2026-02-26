# Project Context (Auto-generated)
> Last updated: 2026-02-26T16:30:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 63 items archived
- **Current Version**: 1.3.1
- **Branch**: main

## Current Story
None (Sprint complete)

## Recent Completions
- STORY-040: Project CLAUDE.md Layered Architecture — Separate Framework and User Content
- BUG-023: _rewrite_yaml preserves unknown user-defined keys
- BUG-022: load_config deep merge for nested dict sections

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Dual-file layered architecture separates framework (CLAUDE.md) and user (CLAUDE.local.md) content — enables safe regeneration while preserving customizations | STORY-040 |
| 2026-02 | Config rewriters must preserve unknown user-defined keys — round-trip safety for user extensions | BUG-023 |
| 2026-02 | Nested dict config sections need deep merge at load time — shallow merge loses default sub-keys | BUG-022 |
| 2026-02 | When later Specs override earlier Specs (BUG-021 supersedes BUG-020), the tests for the earlier Spec must be updated | BUG-021 |
| 2026-02 | Config schema + function without deployment integration = dead code | BUG-019 |

## Next Recommended Action
Sprint complete. Run `/project-design` for new feature or `/project-plan` for backlog story.
