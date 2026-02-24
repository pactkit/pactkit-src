# Project Context (Auto-generated)
> Last updated: 2026-02-24 by /project-done

## Sprint Status
- **In Progress**: 0 stories
- **Backlog**: 0 stories
- **Done**: 45 items archived (STORY-001~035, BUG-001~010)

## Recent Completions
- BUG-010: Preserve agent_models and rule_scopes in _rewrite_yaml
- STORY-035: README and CHANGELOG documentation update
- BUG-009: Project-level config backfill

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Documentation-only stories benefit from test-driven verification — writing 30 assertion tests for README/CHANGELOG content before editing ensures no required content is missed and catches drift in future releases | STORY-035 |
| 2026-02 | When adding new config sections, every serialization path must be updated — _rewrite_yaml, generate_default_yaml, and _BACKFILL_KEYS are three separate places that must stay in sync | BUG-010 |
| 2026-02 | Dual-config architecture (global ~/.claude vs project $CWD/.claude) means deployer must backfill both paths | BUG-009 |
| 2026-02 | Prompt-only Init Guard extensions are cheap but boundary detection in tests is tricky — use the full header pattern instead of partial matches | STORY-034 |
| 2026-02 | Config file auto-merge must handle both list-type keys AND non-list sections | STORY-033 |

## Next Recommended Action
Sprint board is empty. Use `/project-design` for greenfield product ideation or `/project-plan` to add new stories.
