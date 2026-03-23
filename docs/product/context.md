# Project Context (Auto-generated)
> Last updated: 2026-03-23T10:06:35+08:00 by pactkit context

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
- Done Phase deterministic operations (lessons dedup, invariants regex, coverage parsing) are pure text/regex/subprocess with zero AI judgment — `lessons.py` uses Jaccard similarity on word sets (threshold < 0.5) for dedup, `invariants.py` uses `re.sub()` for test count replacement, `coverage_gate.py` uses list-form `subprocess.run()` for pytest-cov (SEC-7 safe); prompt delegation must preserve fallback instructions ("if pactkit X unavailable, fall back to manual") so LLM can still operate without CLI installed
- Iterative cross-flow audits find deeper gaps each pass — BUG-slim-004 found 6 gaps, BUG-slim-005 found 5 more; dict keys defined but never consumed (`LANG_PROFILES.test_dir/package_file/e2e_test_pattern`) are invisible to grep-based prompt audits because they only exist in data structures; board update instructions must reference `{BOARD_CMD} update_task` script (not vague "mark as done") for deterministic execution; every CLI subcommand must have at least one prompt reference or it's dead code (`lint-testcase` had zero)
- cli.py visualize --lazy was a decision-only tool that printed guidance but never called lazy_visualize.run_visualize_graphs(); always trace the execution path from CLI handler to actual side-effect to confirm end-to-end behavior
- 5 test files independently hardcoded LANG_PROFILES required keys — define canonical key sets as frozenset in schemas.py (LANG_PROFILE_REQUIRED_KEYS) so all consumers import from one source; when adding test assertions on dict keys, always check schemas.py first
- Monolithic prompt Phase 3.2 in commands.py caused AI thinking stalls; splitting into 4 sub-phases (3.2a-3.2d) with output checkpoints forces incremental generation and eliminates the bottleneck

## Next Recommended Action
`/project-design`
