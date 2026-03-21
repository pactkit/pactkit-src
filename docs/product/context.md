# Project Context (Auto-generated)
> Last updated: 2026-03-21T20:31:43+08:00 by /project-done

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
- Config resolution in CLI modules must use `find_pactkit_yaml(project_root)` → `load_config(yaml_path)` two-step pattern — `load_config(project_root)` alone fails because pactkit.yaml lives in `.claude/` subdirectory, not project root; lint_runner.py and test_mapper.py both reuse `LANG_PROFILES` from workflows.py as canonical source for stack-specific patterns (test_map_pattern, lint_command), keeping DRY with the CI pipeline profiles
- Cross-flow integrity audits (comparing all PDCA commands end-to-end) catch gaps that per-command reviews miss — CLI subcommands with zero prompt references are dead code (`lint-context`, `lint-lessons`, `lint-testcase`); argparser flags without `deploy()` signature parity (`upgrade` missing `--agent`) fail silently; adding a new parameter to `deploy()` must use a default value to avoid breaking 24+ existing callers that don't pass it
- Done Phase deterministic operations (lessons dedup, invariants regex, coverage parsing) are pure text/regex/subprocess with zero AI judgment — `lessons.py` uses Jaccard similarity on word sets (threshold < 0.5) for dedup, `invariants.py` uses `re.sub()` for test count replacement, `coverage_gate.py` uses list-form `subprocess.run()` for pytest-cov (SEC-7 safe); prompt delegation must preserve fallback instructions ("if pactkit X unavailable, fall back to manual") so LLM can still operate without CLI installed
- Iterative cross-flow audits find deeper gaps each pass — BUG-slim-004 found 6 gaps, BUG-slim-005 found 5 more; dict keys defined but never consumed (`LANG_PROFILES.test_dir/package_file/e2e_test_pattern`) are invisible to grep-based prompt audits because they only exist in data structures; board update instructions must reference `{BOARD_CMD} update_task` script (not vague "mark as done") for deterministic execution; every CLI subcommand must have at least one prompt reference or it's dead code (`lint-testcase` had zero)
- cli.py visualize --lazy was a decision-only tool that printed guidance but never called lazy_visualize.run_visualize_graphs(); always trace the execution path from CLI handler to actual side-effect to confirm end-to-end behavior

## Next Recommended Action
`/project-act STORY-slim-018` (Systemic Cross-Flow Guards — Automated Validation for Prompt-CLI Integrity)
