# Project Context (Auto-generated)
> Last updated: 2026-02-27T10:00:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 73 items archived
- **Current Version**: 1.4.0
- **Branch**: main

## Current Story
None — board is clean.

## Recent Completions
- STORY-048: Worktree Isolation for Subagent Sprint — isolation="worktree" on all Sprint subagent Task calls
- STORY-047: Enterprise Configuration Flags — pactkit.yaml enterprise section + CLI --no-git/--no-external/--non-interactive flags
- STORY-046: Multi-Agent Compatibility Layer — adapter.py for cursor/copilot/generic; --agent CLI flag

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Worktree isolation for subagent Sprint is a prompt-only change — Stage A/C need git merge while Stage B only needs file copy for reports | STORY-048 |
| 2026-02 | Non-AI linters must strip fenced code blocks before searching for headings — `## Section` inside ``` blocks shadows real sections | STORY-042 |
| 2026-02 | Subprocess CLI tests must use absolute paths — CWD changes from other tests break relative paths; anchor with `Path(__file__).parents[2]` | STORY-042 |
| 2026-02 | Parallel agent implementation of independent prompt changes is safe when targeting different strings — but count-based tests must be updated after merge | STORY-043/044/045 |
| 2026-02 | Adding a new command requires 4 touch points: commands.py, config.py VALID_COMMANDS, rules.py routing table, and ~6 count assertion test files | STORY-043 |

## Next Recommended Action
Run `/project-plan` to plan the next story, or `/project-design` for a new feature area.
