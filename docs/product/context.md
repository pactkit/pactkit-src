# Project Context (Auto-generated)
> Last updated: 2026-02-26T17:30:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 1 story (STORY-041 R3-R6 remaining)
- **Done**: 64 items archived
- **Current Version**: 1.3.1
- **Branch**: main

## Current Story
STORY-041: Test Pyramid Restructuring — R1/R2 done, R3-R6 (SHOULD/MAY) remaining

## Recent Completions
- STORY-041 R1-R2: CLI E2E test suite (16 tests), directory restructure
- STORY-040: Project CLAUDE.md Layered Architecture
- BUG-023: _rewrite_yaml preserves unknown user-defined keys

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | CLI tools need subprocess-based E2E tests in addition to unit tests — calling main() directly doesn't test entry point registration, argparse routing, or exit codes | STORY-041 |
| 2026-02 | Dual-file layered architecture separates framework (CLAUDE.md) and user (CLAUDE.local.md) content — enables safe regeneration while preserving customizations | STORY-040 |
| 2026-02 | Config rewriters must preserve unknown user-defined keys — round-trip safety for user extensions | BUG-023 |
| 2026-02 | Nested dict config sections need deep merge at load time — shallow merge loses default sub-keys | BUG-022 |
| 2026-02 | When later Specs override earlier Specs, the tests for the earlier Spec must be updated | BUG-021 |

## Next Recommended Action
继续 `/project-act` 实现 STORY-041 R3-R6 (SHOULD/MAY)，或开始新 Story。
