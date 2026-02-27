# Project Context (Auto-generated)
> Last updated: 2026-02-27T00:00:00Z by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 79 items archived
- **Current Version**: 1.4.0
- **Branch**: main

## Recent Completions
- STORY-053: Impact-Based Regression via Call Graph Analysis — `visualize.py --reverse` + `impact` subcommand; `regression` config section; Done gate updated with Step 1.6 (Release Gate) + Step 1.7 (Impact-Based)
- STORY-052: Conditional GitHub Release — `release.github_release: false` config; pactkit-release skill Step 4 is now opt-in
- BUG-025: project-release delegates to pactkit-release skill — eliminates duplication, adds version auto-detection

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Impact-based reverse BFS is a clean extension to forward BFS — extract `_scan_call_edges()` shared helper; `impact()` maps callers to test files via `test_{stem}.py` pattern, ~30 lines, no new dependencies | STORY-053 |
| 2026-02 | Adding a new config section requires 7 coordinated changes in config.py: get_default_config, DEEP_MERGE_KEYS, _BACKFILL_KEYS, KNOWN_KEYS, _rewrite_yaml write block, validate_config, and generate_default_yaml — plus 2 "full config" test fixtures | STORY-052 |
| 2026-02 | Command-to-skill promotion requires exhaustive audit of ALL stale-ref tests | BUG-025 |
| 2026-02 | Splitting an overloaded command into focused commands requires updating tests for intentional Spec-driven behavior changes | STORY-051 |
| 2026-02 | Regression decision trees need a doc-only shortcut before any other heuristic | STORY-050 |

## Next Recommended Action
Board is empty. Run `/project-design` to start a new product feature, or `/project-plan` to write a new Story.
