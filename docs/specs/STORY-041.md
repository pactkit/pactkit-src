# STORY-041: Test Pyramid Restructuring — E2E Layer & Unit Test Rationalization

| Field     | Value |
|-----------|-------|
| ID        | STORY-041 |
| Status    | Draft |
| Priority  | High |
| Release   | 1.4.0 |
| Author    | System Architect |

## Background

PactKit's test suite has grown to 96 unit test files / 1484 tests / 16,078 LOC against ~5,572 LOC of source code (ratio 2.9:1). Analysis reveals three structural problems:

1. **~55% of tests are low-value keyword-in-string assertions** — manually encoding that prompt templates contain specific words, without verifying behavior.
2. **~27 files are integration tests masquerading as unit tests** — calling full `deploy()` with filesystem I/O, but living in `tests/unit/`.
3. **E2E layer is completely absent** — `tests/e2e/api/` and `tests/e2e/browser/` exist as empty scaffolding artifacts from the generic `/project-init` template, but PactKit is a pure CLI tool with no API or browser surface.

The CLI entry point (`cli.py` → argparse → `deploy()`) has never been tested via subprocess. Exit codes, entry point registration, help output, and error handling are unverified.

## Target Call Chain

```
User CLI invocation (subprocess)
  → pactkit.cli:main()          # pyproject.toml entry point
    → argparse routing           # init|update|upgrade|version
      → deploy(target, format)   # deployer.py
        → _deploy_classic()      # 10+ sub-deployers
        → _deploy_plugin()
        → _deploy_marketplace()
```

## Requirements

### R1: CLI E2E Test Suite (MUST)

Create `tests/e2e/cli/` directory containing subprocess-based tests that invoke `pactkit` as a black-box CLI.

**Scenarios:**
- `pactkit version` — stdout matches version pattern, exit code 0
- `pactkit init -t <tmp>` — classic format: all expected files created (agents, commands, skills, rules, CLAUDE.md)
- `pactkit init --format plugin -t <tmp>` — plugin format: plugin.json, inlined CLAUDE.md
- `pactkit init --format marketplace -t <tmp>` — marketplace wrapper
- `pactkit init -t <tmp>` (selective config) — only enabled components deployed
- `pactkit init -t <tmp>` (idempotent) — second run produces identical output
- `pactkit` (no args) — prints help, exit code != 0
- Error case: invalid `--format` value — stderr message, non-zero exit

### R2: E2E Directory Restructure (MUST)

- Remove empty `tests/e2e/api/` and `tests/e2e/browser/` directories
- Create `tests/e2e/cli/` as the e2e home for CLI subprocess tests
- Update the File Atlas rule (`03-file-atlas.md`) and `/project-init` scaffold logic:
  - Detect project stack/type (CLI vs API vs Web)
  - Generate appropriate e2e subdirectories instead of always `api/` + `browser/`

### R3: Integration Test Separation (SHOULD)

Move deploy-calling tests from `tests/unit/` to `tests/integration/`:
- All files that call `deploy()` or `_deploy_*()` directly with filesystem I/O
- Create `tests/integration/` directory
- Add pytest markers: `@pytest.mark.integration` for deploy tests, `@pytest.mark.e2e` for CLI tests
- Update `pytest.ini` / `pyproject.toml` to support `pytest -m "not integration"` for fast runs

### R4: Prompt String Test Consolidation (SHOULD)

Consolidate ~45 keyword-in-string test files into a lightweight snapshot approach:
- Create `tests/unit/test_prompt_snapshots.py` using a parameterized approach
- Each prompt module gets a list of **structural invariants** (not arbitrary keywords)
- Reduce from ~770 string assertions to ~100 meaningful structural checks
- Candidates for removal: tests that only assert a single keyword exists in a multi-KB string

### R5: Shared Test Fixtures (MAY)

Create `tests/conftest.py` with shared fixtures:
- `deploy_env(tmp_path)` — pre-configured temp directory with `Path.home()` and `Path.cwd()` mocking
- `sample_config(tmp_path)` — writes a default `pactkit.yaml` to tmp
- `pactkit_cli(tmp_path)` — subprocess runner with env isolation

### R6: CI Optimization (MAY)

Configure CI pipeline for tiered test execution:
- Fast tier: `pytest -m "not integration and not e2e"` — pure unit tests (< 10s)
- Medium tier: `pytest -m integration` — deploy integration tests
- Full tier: `pytest` — all tests including e2e

## Acceptance Criteria

### AC1: E2E CLI Tests Exist and Pass
**Given** PactKit is installed in the environment
**When** `pytest tests/e2e/ -v` is run
**Then** at least 8 CLI subprocess tests execute and pass
**And** tests cover all three formats (classic, plugin, marketplace) + version + help + error case

### AC2: E2E Directory Structure Matches Project Type
**Given** PactKit's `tests/e2e/` directory
**When** listing its contents
**Then** `tests/e2e/cli/` exists with test files
**And** `tests/e2e/api/` and `tests/e2e/browser/` do NOT exist

### AC3: Integration Tests Separated
**Given** tests that call `deploy()` with filesystem I/O
**When** examining their location
**Then** they are in `tests/integration/` (not `tests/unit/`)
**And** `pytest -m "not integration"` excludes them

### AC4: Unit Test Count Reduced
**Given** the prompt string test consolidation
**When** counting test files in `tests/unit/`
**Then** total unit test files are reduced by at least 30%
**And** all structural invariants are still verified

### AC5: Full Suite Still Passes
**Given** the restructured test pyramid
**When** `pytest tests/ -v` is run
**Then** all tests pass with zero regressions

## Out of Scope

- Rewriting the prompt templates themselves
- Adding API or browser testing capabilities to PactKit
- Changing PactKit's CLI interface
- Performance benchmarking of test execution time
