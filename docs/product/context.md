# Project Context (Auto-generated)
> Last updated: 2026-03-22T00:15:00+08:00 by /project-done

## Sprint Status
Backlog: 1 (STORY-slim-017) | In Progress: 0 | Done: 0

## Current Stories
- STORY-slim-017: Done Phase Deterministic Gate Migration — lessons append, invariants refresh, coverage gate (P2, 5 tasks)

## Recent Completions
- BUG-slim-004: Cross-Flow Integrity Gaps — 6 fixes across prompts, cli, deployer (12 new tests)
- STORY-slim-016: Test Mapping & Stack-Aware Lint CLI — 2 new modules, 15 tests
- STORY-slim-015: Doctor & Release CLI — 3 new modules, 23 tests

## Active Branches
- `main` — current production
- `feature/cython-build`

## Key Decisions
- Cross-flow audit: deploy() signature must accept agent= with default to avoid breaking 24+ callers
- Done Phase 2.5+3 still has largest MANUAL_IN_PROMPT blocks (lessons, invariants, coverage)
- Regression decision tree (Done 2.5 Steps 1.7+2) stays in prompt — involves judgment calls
- Config resolution in CLI modules: `find_pactkit_yaml()` → `load_config(yaml_path)` two-step pattern
- All zombie CLI subcommands now referenced: lint-context, lint-lessons in Done; spec-lint in Check

## Next Recommended Action
`/project-act STORY-slim-017` — migrate Done Phase deterministic gates to CLI (5 tasks)
