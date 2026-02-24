# Project Context (Auto-generated)
> Last updated: 2026-02-24T16:00:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 17 stories (STORY-001 through STORY-004, STORY-007 through STORY-014, BUG-001 through BUG-005)

## Recent Completions
- STORY-014: Release v1.1.3 — synced CHANGELOG, plugin repo, and PyPI
- BUG-005: board.py archive vs classify inconsistent for taskless stories — added `[x]` guard
- BUG-004: deployer.py dead set() call in _deploy_rules — removed dead code

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Release hygiene requires syncing 5 artifacts (CHANGELOG, pyproject.toml, __init__.py, plugin repo, PyPI) — a release Story with explicit per-artifact tasks prevents omissions | STORY-014 |
| 2026-02 | When two functions classify the same data, they must use the same logic — align both to require `- [x]` for archival | BUG-005 |
| 2026-02 | Dead code from refactors passes all tests because it's a no-op — use AST-based source inspection tests to catch it | BUG-004 |
| 2026-02 | When iterating `ast.Import.names`, each alias must be processed individually; also deduplicate edges with a `seen` set | BUG-003 |
| 2026-02 | Deploy-time path rewriting (template stays canonical, deployer rewrites at write time) is the correct pattern for multi-mode deployment | BUG-002 |

## Next Recommended Action
`/project-design` — Board is empty. Design new features or improvements.
