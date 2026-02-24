# Project Context (Auto-generated)
> Last updated: 2026-02-24 by /project-done

## Sprint Status
- **In Progress**: 0 stories
- **Backlog**: 0 stories
- **Done**: 48 items archived (STORY-001~035, BUG-001~013)

## Recent Completions
- BUG-013: Deployer reads config from wrong path — consolidate to project-level $CWD/.claude/pactkit.yaml only
- BUG-012: Call graph noise filter — remove builtins and local method calls from visualize --mode call
- BUG-011: Fix stale command references in agent and skill prompt templates

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Single-source config requires three coordinated changes: read from CWD not HOME, generate at CWD not HOME, auto_merge must backfill entirely missing list keys — tests using target= without mocking Path.cwd() will leak CI files to the real project directory | BUG-013 |
| 2026-02 | AST-based call graphs must filter noise at two levels: _extract_calls should skip builtins and non-self attribute calls, and _build_call_graph should only emit edges where callees resolve to func_registry | BUG-012 |
| 2026-02 | Command-to-skill demotion requires exhaustive grep across ALL prompt modules — a single grep -r at demotion time would have caught all references in one pass | BUG-011 |
| 2026-02 | When adding new config sections, every serialization path must be updated — _rewrite_yaml, generate_default_yaml, and _BACKFILL_KEYS must stay in sync | BUG-010 |
| 2026-02 | Dual-config architecture (global ~/.claude vs project $CWD/.claude) means deployer must backfill both paths | BUG-009 |

## Next Recommended Action
Sprint board is empty. Use `/project-design` to start a new product cycle or `/project-plan` for a specific feature.
