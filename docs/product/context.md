# Project Context (Auto-generated)
> Last updated: 2026-02-27T00:00:00Z by /project-done

## Sprint Status
- **In Progress**: 0 stories
- **Backlog**: 0 stories
- **Done**: 80 items archived
- **Current Version**: 1.4.0
- **Branch**: main

## Recent Completions
- STORY-054: Deployment Completeness Audit — E2E File Verification — `TestDeploymentCompleteness` class with 9 tests asserting exact VALID_* counts; closes loose `len >= 1` guard gap
- STORY-053: Impact-Based Regression via Call Graph Analysis — `visualize.py --reverse` + `impact` subcommand; `regression` config section; Done gate updated with Step 1.6 (Release Gate) + Step 1.7 (Impact-Based)
- STORY-052: Conditional GitHub Release — `release.github_release: false` config; pactkit-release skill Step 4 is now opt-in

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Deployment completeness tests must assert exact counts and exact names (not just `>= 1`) — loose guards like `len(files) >= 1` pass even when only 1 of 11 commands is deployed; importing `VALID_*` sets from config.py and asserting `set(found) == VALID_*` creates a self-updating contract that breaks on any future drift | STORY-054 |
| 2026-02 | Impact-based reverse BFS is a clean extension to forward BFS — extract `_scan_call_edges()` shared helper; `impact()` maps callers to test files via `test_{stem}.py` pattern, ~30 lines, no new dependencies | STORY-053 |
| 2026-02 | Adding a new config section requires 7 coordinated changes in config.py: get_default_config, DEEP_MERGE_KEYS, _BACKFILL_KEYS, KNOWN_KEYS, _rewrite_yaml write block, validate_config, and generate_default_yaml — plus 2 "full config" test fixtures | STORY-052 |
| 2026-02 | Command-to-skill promotion requires exhaustive audit of ALL stale-ref tests | BUG-025 |
| 2026-02 | Splitting an overloaded command into focused commands requires updating tests for intentional Spec-driven behavior changes | STORY-051 |

## Next Recommended Action
Sprint board is empty. Run `/project-plan` to plan a new Story, or `/project-design` for a greenfield feature.
