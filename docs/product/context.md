# Project Context (Auto-generated)
> Last updated: 2026-03-23T17:08:19+08:00 by pactkit context

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
codex-integration
  codex-test
  codex/analyze-features-for-codex-integration
  develop
  feature/cython-build
* main
  opencode-test

## Key Decisions
- cli.py visualize --lazy was a decision-only tool that printed guidance but never called lazy_visualize.run_visualize_graphs(); always trace the execution path from CLI handler to actual side-effect to confirm end-to-end behavior
- 5 test files independently hardcoded LANG_PROFILES required keys — define canonical key sets as frozenset in schemas.py (LANG_PROFILE_REQUIRED_KEYS) so all consumers import from one source; when adding test assertions on dict keys, always check schemas.py first
- Monolithic prompt Phase 3.2 in commands.py caused AI thinking stalls; splitting into 4 sub-phases (3.2a-3.2d) with output checkpoints forces incremental generation and eliminates the bottleneck
- code-explorer maxTurns reduced from 50 to 15 in agents.py; Plan Phase 1 now requires bounded Explore prompts with target/scope/limit/output via Delegation Template in commands.py
- Added 09-sectional-write as core rule in src/pactkit/prompts/rules.py RULES_MODULES. Threshold 300 lines based on P75-P90 analysis of specs/source/tests. Applies to any file type.

## Next Recommended Action
`/project-design`
