# Project Context (Auto-generated)
> Last updated: 2026-02-25 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 52 items archived (STORY-001~036, BUG-001~016)
- **Current Version**: 1.3.0

## Recent Completions
- STORY-036: Sync pactkit.dev documentation with current README and codebase (23 content gaps fixed)
- BUG-015: Removed redundant pactkit.yml CI workflow (11 test failures resolved)
- BUG-016: Added GitHub Release pages for v1.2.0 and v1.3.0

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Documentation drift accumulates silently across config changes — multi-repo docs require a sync checklist on every breaking change | STORY-036 |
| 2026-02 | All new features must be conditional/opt-in by default — CI/CD, issue tracking, hooks, and lint blocking are all disabled by default and only activate when explicitly configured | STORY-025~030 |
| 2026-02 | Internal prompt iteration versions (v16.2~v23.0) diverged silently from package versions — version hygiene requires a single grep audit across all prompts/ and skills/ at each release | BUG-014 |
| 2026-02 | Single-source config requires three coordinated changes: read from CWD not HOME, generate at CWD not HOME, auto_merge must backfill entirely missing list keys | BUG-013 |
| 2026-02 | AST-based call graphs must filter noise at two levels: _extract_calls should skip builtins and non-self attribute calls, and _build_call_graph should only emit edges where callees resolve to func_registry | BUG-012 |

## Next Recommended Action
Sprint board is clean. Use `/project-design` for new product features or `/project-plan` for enhancements.
