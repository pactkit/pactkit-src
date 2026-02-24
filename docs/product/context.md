# Project Context (Auto-generated)
> Last updated: 2026-02-24T20:00:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 19 stories (STORY-001 through STORY-016, BUG-001 through BUG-005)

## Recent Completions
- STORY-016: CLAUDE.md hygiene — language matching rule & project context cleanup
- STORY-015: Add conditional CI lint gate to Done and Act commands
- STORY-014: Release v1.1.3 — synced CHANGELOG, plugin repo, and PyPI

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Constitution rules are the cheapest way to change agent behavior — a 3-line language-matching rule makes all PDCA output respect user's language | STORY-016 |
| 2026-02 | Local PDCA must mirror CI checks — adding `lint_command` to `LANG_PROFILES` and a conditional CI Lint Gate closes the gap | STORY-015 |
| 2026-02 | Release hygiene requires syncing 5 artifacts — a release Story with explicit per-artifact tasks prevents omissions | STORY-014 |
| 2026-02 | When two functions classify the same data, they must use the same logic — align both to require `- [x]` for archival | BUG-005 |
| 2026-02 | Dead code from refactors passes all tests because it's a no-op — use AST-based source inspection tests to catch it | BUG-004 |

## Next Recommended Action
`/project-design` — Board is empty. Design new features or improvements.
