# Project Context (Auto-generated)
> Last updated: 2026-02-24 by /project-done

## Sprint Status
- **In Progress**: 0 stories
- **Backlog**: 0 stories
- **Done**: 49 items archived (STORY-001~035, BUG-001~014)

## Recent Completions
- BUG-014: Version hygiene — unified stale spec Release fields, prompt template versions, and CHANGELOG entries to v1.2.0
- BUG-013: Single-source config consolidation — config reads exclusively from $CWD/.claude/pactkit.yaml
- BUG-012: Call graph noise filter — skip builtins and non-self attribute calls in visualize --mode call

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | When adding new config sections, every serialization path must be updated — _rewrite_yaml, generate_default_yaml, and _BACKFILL_KEYS are three separate places that must stay in sync | BUG-010 |
| 2026-02 | Command-to-skill demotion requires exhaustive grep across ALL prompt modules — a single grep -r at demotion time would have caught all references in one pass | BUG-011 |
| 2026-02 | AST-based call graphs must filter noise at two levels: _extract_calls should skip builtins and non-self attribute calls, and _build_call_graph should only emit edges where callees resolve to func_registry | BUG-012 |
| 2026-02 | Single-source config requires three coordinated changes: read from CWD not HOME, generate at CWD not HOME, auto_merge must backfill entirely missing list keys | BUG-013 |
| 2026-02 | Internal prompt iteration versions (v16.2~v23.0) diverged silently from package versions — version hygiene requires a single grep audit across all prompts/ and skills/ at each release; cross-referencing CHANGELOG with spec Release fields catches phantom versions that were never actually released | BUG-014 |

## Next Recommended Action
Sprint board is empty. Use `/project-design` for a new product feature or `/project-plan` to plan the next improvement.
