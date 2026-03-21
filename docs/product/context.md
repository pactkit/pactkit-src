# Project Context (Auto-generated)
> Last updated: 2026-03-22T00:30:00+08:00 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 0

## Current Stories
(none — sprint board empty)

## Recent Completions
- STORY-slim-017: Done Phase Deterministic Gate Migration — 3 new modules, 20 tests
- BUG-slim-004: Cross-Flow Integrity Gaps — 6 fixes across prompts, cli, deployer (12 tests)
- STORY-slim-016: Test Mapping & Stack-Aware Lint CLI — 2 new modules, 15 tests

## Active Branches
- `main` — current production
- `feature/cython-build`

## Key Decisions
- Done Phase deterministic operations (lessons dedup, invariants refresh, coverage gate) migrated to CLI
- Prompt delegation preserves fallback instructions for environments without pactkit CLI
- Jaccard similarity (threshold 0.5) for lesson dedup; 3-tier coverage thresholds (80/50)
- Cross-flow audit: deploy() signature must accept agent= with default to avoid breaking callers
- All zombie CLI subcommands now referenced in prompts

## Next Recommended Action
Sprint board empty. Run `/project-design` for new product features or `/project-plan` for improvements.
