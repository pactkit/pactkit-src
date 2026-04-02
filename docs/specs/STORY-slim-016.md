# STORY-slim-016: Test Mapping & Stack-Aware Lint CLI

| Field | Value |
|-------|-------|
| ID | STORY-slim-016 |
| Status | Draft |
| Priority | P2 |
| Release | 2.2.0 |

## Background

The STORY-slim-014 audit identified two recurring deterministic operations duplicated across 4+ command playbooks: the Test Mapping Protocol and the Stack-Aware Lint Gate. Both are pure pattern-matching + config-reading operations that the LLM currently executes manually each time, with risk of inconsistency.

### Current State

**Test Mapping Protocol** — referenced in Act Phase 3, Check Phase 3.5, Done Phase 2.5, and Hotfix Phase 2:
- Maps changed source files to corresponding test files using `LANG_PROFILES[stack].test_map_pattern`
- The LLM manually applies the pattern (e.g., `src/pactkit/foo.py` → `tests/unit/test_foo.py`)
- Each invocation risks different interpretation of the pattern

**Stack-Aware Lint Gate** — in Done Phase 2.5 Step 2.7:
- Detects project stack (already in `cleaners.detect_stack()`)
- Reads `lint_command` from `LANG_PROFILES`
- Reads `auto_fix` and `lint_blocking` from `pactkit.yaml`
- Runs the lint command with appropriate flags
- The LLM assembles these 4 config reads + 1 shell execution manually each time

## Target Call Chain

```
pactkit CLI → cli.py → new subcommands:
  pactkit test-map <file1> [file2...] → test_mapper.py → map_to_tests()
  pactkit lint [--fix]                → lint_runner.py → run_lint()
```

## Requirements

### R1: pactkit test-map — Source-to-test file mapping
MUST implement `map_to_tests(changed_files, project_root)` that:
- Detects stack from project root (reuse `cleaners.detect_stack()`)
- Reads `test_map_pattern` from `LANG_PROFILES[stack]`
- For each source file, applies the pattern to derive the expected test file path
- Returns only test files that actually exist on disk
- If no pattern found for stack or no test files exist, returns empty list with reason

Pattern semantics by stack:
| Stack | Pattern | Example |
|-------|---------|---------|
| python | `tests/unit/test_{module}.py` | `src/pactkit/cli.py` → `tests/unit/test_cli.py` |
| node | `__tests__/{module}.test.ts` | `src/app.ts` → `__tests__/app.test.ts` |
| go | `{package}/{module}_test.go` | `pkg/auth/login.go` → `pkg/auth/login_test.go` |
| java | `src/test/java/{package}/{module}Test.java` | `src/main/java/com/app/User.java` → `src/test/java/com/app/UserTest.java` |

### R2: pactkit lint — Stack-aware lint runner
MUST implement `run_lint(project_root, fix=False)` that:
- Detects stack (reuse `cleaners.detect_stack()`)
- Reads `lint_command` from `LANG_PROFILES[stack]`
- Reads `auto_fix` and `lint_blocking` from `pactkit.yaml` (via `config.load_config()`)
- If `fix=True` or `auto_fix=True` in config: runs lint with fix flag first (e.g., `ruff check --fix` for Python)
- Runs lint in check mode
- Returns structured result: `(exit_code, stdout, blocking)`
- If no lint command for stack: returns skip result with message

### R3: CLI wiring
MUST add `test-map` and `lint` subcommands to `cli.py`:
- `pactkit test-map <file1> [file2...]` — prints test file paths, one per line
- `pactkit lint [--fix]` — runs stack-aware lint, exits with lint exit code if blocking

### R4: Prompt delegation
MUST update prompts to delegate to CLI commands:
- Act Phase 3 Regression Check: replace "use Test Mapping Protocol" with `pactkit test-map <files>`
- Done Phase 2.5 Step 2.7: replace manual stack detection + lint assembly with `pactkit lint`
- Check Phase 3.5 and Hotfix Phase 2: replace "Apply Test Mapping Protocol" with `pactkit test-map`

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/test_mapper.py` (new) | Implement R1 source-to-test mapping | None | Low |
| 2 | `src/pactkit/lint_runner.py` (new) | Implement R2 stack-aware lint | None | Medium |
| 3 | `src/pactkit/cli.py` | Add test-map and lint subcommands | Steps 1-2 | Low |
| 4 | `src/pactkit/prompts/commands.py` | Update Act, Done, Check, Hotfix prompts | Step 3 | Medium |
| 5 | `src/pactkit/prompts/workflows.py` | Update HOTFIX_PROMPT if applicable | Step 3 | Low |
| 6 | Tests | TDD for test_mapper.py and lint_runner.py | Steps 1-2 | Low |

## Acceptance Criteria

### Scenario 1: pactkit test-map maps Python source to test
- **Given** a Python project with `src/pactkit/cli.py`
- **And** `tests/unit/test_cli.py` exists on disk
- **When** running `pactkit test-map src/pactkit/cli.py`
- **Then** output contains `tests/unit/test_cli.py`

### Scenario 2: pactkit test-map returns empty for no match
- **Given** a Python project with `src/pactkit/brand_new.py`
- **And** no `tests/unit/test_brand_new.py` exists
- **When** running `pactkit test-map src/pactkit/brand_new.py`
- **Then** output is empty (exit code 0)

### Scenario 3: pactkit test-map handles multiple files
- **Given** `tests/unit/test_cli.py` and `tests/unit/test_config.py` exist
- **When** running `pactkit test-map src/pactkit/cli.py src/pactkit/config.py`
- **Then** output contains both test file paths

### Scenario 4: pactkit lint runs correct command for stack
- **Given** a Python project (pyproject.toml present)
- **When** running `pactkit lint`
- **Then** the `ruff check src/ tests/` command is executed (from LANG_PROFILES["python"]["lint_command"])

### Scenario 5: pactkit lint --fix applies auto-fix
- **Given** a Python project with lint errors
- **When** running `pactkit lint --fix`
- **Then** `ruff check --fix src/ tests/` is run first, then `ruff check src/ tests/`

### Scenario 6: pactkit lint respects lint_blocking config
- **Given** `pactkit.yaml` has `lint_blocking: true`
- **And** lint errors exist
- **When** running `pactkit lint`
- **Then** exit code is non-zero (blocking)

### Scenario 7: pactkit lint skips if no command configured
- **Given** a project with unknown stack (no marker files)
- **When** running `pactkit lint`
- **Then** output is "No lint command configured — skipping" with exit code 0

### Scenario 8: All existing tests pass
- **Given** all changes applied
- **When** running `pytest tests/ -v`
- **Then** all existing tests pass with zero failures

## Out of Scope

- Custom test mapping patterns from user config (use LANG_PROFILES only for now)
- Multi-stack projects (detect primary stack only)
- Lint auto-fix for non-Python stacks (Python-specific `--fix` flag logic only)

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified/created |
| SEC-2 | Yes | lint_runner executes shell commands from config |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No API endpoints |
| SEC-7 | Yes | Shell command execution needs error handling |
| SEC-8 | No | No dependency file changes |
