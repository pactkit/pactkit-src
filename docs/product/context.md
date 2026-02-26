# Project Context (Auto-generated)
> Last updated: 2026-02-26T22:00:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 72 items archived
- **Current Version**: 1.3.1
- **Branch**: main

## Current Story
None — board is clean.

## Recent Completions
- STORY-047: Enterprise Configuration Flags — pactkit.yaml enterprise section + CLI --no-git/--no-external/--non-interactive flags
- STORY-046: Multi-Agent Compatibility Layer — adapter.py for cursor/copilot/generic; --agent CLI flag
- STORY-045: Auto-PR Enhancement — Done Phase 4.2 structured PR body generation

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Non-AI linters must strip fenced code blocks before searching for headings — `## Section` inside ``` blocks shadows real sections and produces false positives | STORY-042 |
| 2026-02 | Subprocess CLI tests must use absolute paths — CWD changes from other tests break relative paths; anchor with `Path(__file__).parents[2]` | STORY-042 |
| 2026-02 | Parallel agent implementation of independent prompt changes is safe when targeting different strings — but count-based tests must be updated after merge | STORY-043/044/045 |
| 2026-02 | Adding a new command requires 4 touch points: commands.py, config.py VALID_COMMANDS, rules.py routing table, and ~6 count assertion test files | STORY-043 |
| 2026-02 | Read-side regex tolerance (`\[?...\]?:?`) is simpler than format detection — single shared `_TITLE_RE` constant fixes all 4 parse sites | BUG-024 |

## Next Recommended Action
Run `/project-plan` to plan the next story, or `/project-design` for a new feature area.
