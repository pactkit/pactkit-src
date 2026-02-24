# Project Context (Auto-generated)
> Last updated: 2026-02-24 by /project-done

## Sprint Status
- **In Progress**: 0 stories
- **Backlog**: 0 stories
- **Done**: 47 items archived (STORY-001~035, BUG-001~012)

## Recent Completions
- BUG-012: Call graph noise filter — remove builtins and local method calls from visualize --mode call
- BUG-011: Fix stale command references in agent and skill prompt templates
- BUG-010: Preserve agent_models and rule_scopes in _rewrite_yaml

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | AST-based call graphs must filter noise at two levels: _extract_calls should skip builtins and non-self attribute calls, and _build_call_graph should only emit edges where callees resolve to func_registry | BUG-012 |
| 2026-02 | Command-to-skill demotion requires exhaustive grep across ALL prompt modules — a single grep -r at demotion time would have caught all references in one pass | BUG-011 |
| 2026-02 | When adding new config sections, every serialization path must be updated — _rewrite_yaml, generate_default_yaml, and _BACKFILL_KEYS must stay in sync | BUG-010 |
| 2026-02 | Dual-config architecture (global ~/.claude vs project $CWD/.claude) means deployer must backfill both paths | BUG-009 |
| 2026-02 | Documentation-only stories benefit from test-driven verification | STORY-035 |

## Next Recommended Action
Sprint board is empty. Use `/project-design` for greenfield product ideation or `/project-plan` to add new stories.
