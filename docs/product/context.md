# Project Context (Auto-generated)
> Last updated: 2026-02-25 by /project-plan

## Sprint Status
- **Backlog**: 2 stories (BUG-015, BUG-016)
- **In Progress**: 0 stories
- **Done**: 49 items archived (STORY-001~035, BUG-001~014)
- **Current Version**: 1.3.0

## Recent Completions
- v1.3.0 release — version bump, architecture snapshot, CHANGELOG, PyPI, plugin repo sync
- BUG-014: Version hygiene — unified stale spec Release fields, prompt template versions, and CHANGELOG entries
- BUG-013: Single-source config consolidation — config reads exclusively from $CWD/.claude/pactkit.yaml

## Current Backlog
- **BUG-015**: PactKit CI workflow fails due to missing `pactkit init` step — redundant `pactkit.yml` workflow causes 11 test failures on every push
- **BUG-016**: GitHub Releases missing for v1.2.0 and v1.3.0 — tags exist but no GitHub Release page entries; `pactkit-release` skill lacks `gh release create` step

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
Two CI/release bugs in backlog. Use `/project-act` to implement fixes, or `/project-hotfix` for quick resolution.
