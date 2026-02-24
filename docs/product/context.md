# Project Context (Auto-generated)
> Last updated: 2026-02-24T23:45:00+08:00 by /project-done

## Sprint Status
- **In Progress**: 0 stories
- **Backlog**: 0 stories
- **Done**: 35 stories (STORY-001 through STORY-030, BUG-001 through BUG-005)

## Recent Completions
- STORY-030: Smart Lint Integration in Done Command
- STORY-029: Enhanced Doctor Diagnostics
- STORY-028: Context-Aware Rule Scoping

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Nested YAML structures (hooks) in agent frontmatter require PyYAML serialization; model default should be `inherit` | STORY-024 |
| 2026-02 | All new features must be conditional/opt-in by default — CI/CD, issue tracking, hooks, and lint blocking are all disabled by default | STORY-025~030 |
| 2026-02 | Hook safety requires three rules: command-type only, report-only (exit 0), and opt-in (disabled by default) | STORY-027 |
| 2026-02 | Rule scoping via includeFiles frontmatter enables glob-targeted governance without forking rule modules | STORY-028 |
| 2026-02 | Prompt hooks on read-only agents are redundant when tools/disallowedTools already block Write/Edit | Hotfix post-STORY-024 |

## Next Recommended Action
Board is empty. Run `/project-design` to plan the next product iteration, or `/project-plan` to add a specific Story.
