# Project Context (Auto-generated)
> Last updated: 2026-02-26T12:00:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 62 items archived
- **Current Version**: 1.3.1
- **Branch**: main

## Current Story
None (board empty)

## Recent Completions
- BUG-023: _rewrite_yaml preserves unknown user-defined keys
- BUG-022: load_config deep merge for nested dict sections
- BUG-021: CLAUDE.md generation: LANG_PROFILES, platform-aware paths, Playbook alignment

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | When later Specs override earlier Specs (BUG-021 supersedes BUG-020), the tests for the earlier Spec must be updated | BUG-021 |
| 2026-02 | Nested dict config sections need deep merge at load time — shallow merge loses default sub-keys | BUG-022 |
| 2026-02 | Config rewriters must preserve unknown user-defined keys — round-trip safety for user extensions | BUG-023 |
| 2026-02 | Test isolation requires mocking both Path.home() AND Path.cwd() when testing deploy() | BUG-020 |
| 2026-02 | Config schema + function without deployment integration = dead code | BUG-019 |

## Next Recommended Action
Board is empty. Consider `/project-design` for new product ideation or `/project-plan` to add a new story.
