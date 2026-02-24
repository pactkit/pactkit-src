# Project Context (Auto-generated)
> Last updated: 2026-02-24T12:00:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 16 stories (STORY-001 through STORY-004, STORY-007 through STORY-013, BUG-001 through BUG-005)

## Recent Completions
- BUG-005: board.py archive vs classify inconsistent for taskless stories — added `[x]` guard
- BUG-004: deployer.py dead set() call in _deploy_rules — removed dead code
- BUG-003: visualize.py ast.Import only captures last alias — fixed multi-import + dedup

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | When two functions classify the same data, they must use the same logic — align both to require `- [x]` for archival | BUG-005 |
| 2026-02 | Dead code from refactors passes all tests because it's a no-op — use AST-based source inspection tests to catch it | BUG-004 |
| 2026-02 | When iterating `ast.Import.names`, each alias must be processed individually; also deduplicate edges with a `seen` set | BUG-003 |
| 2026-02 | Deploy-time path rewriting (template stays canonical, deployer rewrites at write time) is the correct pattern for multi-mode deployment | BUG-002 |
| 2026-02 | Skill SKILL.md prompts must use absolute paths for script invocations — the LLM runs bash from project cwd, not the skill base directory | BUG-001 |

## Next Recommended Action
Board is empty. Run `/project-design` to define new product features.
