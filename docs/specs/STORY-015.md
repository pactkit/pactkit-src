# Spec STORY-015: Add conditional CI lint gate to Done command
- **Release**: 1.1.3

## Context
GitHub CI fails after every push because the PDCA workflow has no lint gate. The CI workflow (`.github/workflows/ci.yml`) runs `ruff check src/ tests/` which catches lint errors (e.g., unused imports) that the local Done command never checks. This creates a pattern where all tests pass locally, the commit is made, pushed, and then CI fails.

## Root Cause
1. `LANG_PROFILES` in `workflows.py` has no `lint_command` field
2. The Done command's Phase 2.5 (Regression Gate) only runs tests, not lint
3. The Act command's Phase 3 regression check also only runs tests

## Target Call Chain
```
/project-done → Phase 2.5 Regression Gate → [NEW] Step 2.7: CI Lint Gate
  → detect .github/workflows/*.yml OR .gitlab-ci.yml OR Makefile lint target
  → extract lint command from LANG_PROFILES[stack].lint_command
  → run lint command
  → gate: if lint fails, STOP (same as test failure)
```

## Requirements
1. **MUST** add a `lint_command` field to each entry in `LANG_PROFILES` (workflows.py)
   - Python: `ruff check src/ tests/` (auto-detect from pyproject.toml `[tool.ruff]`)
   - Node: `npx eslint .` (auto-detect from `.eslintrc*` or `eslint.config.*`)
   - Go: `golangci-lint run` (auto-detect from `.golangci.yml`)
   - Java: `mvn checkstyle:check` (auto-detect from `pom.xml`)
2. **MUST** add a new Step 2.7 "CI Lint Gate" to the Done command (Phase 2.5)
   - Condition: IF a CI config file exists (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `Makefile` with lint target, or `lint_command` in `LANG_PROFILES`)
   - Action: Run the `lint_command` from `LANG_PROFILES` for the detected stack
   - Gate: If lint fails, STOP immediately. Do NOT proceed to commit.
   - Skip: If no CI config and no lint_command detected, skip silently with note "No CI lint config detected — skipping lint gate."
3. **MUST** fix the current CI failures: remove unused `from pathlib import Path` in `test_bug003_multi_import.py` and `test_bug005_archive_taskless.py`
4. **SHOULD** also add the lint gate to the Act command's Phase 3 regression check (after tests pass, before declaring GREEN)
5. **MAY** auto-detect the lint command from CI config YAML if `LANG_PROFILES` doesn't specify one

## Acceptance Criteria

### Scenario 1: Done command runs lint when CI config exists
Given a project with `.github/workflows/ci.yml` containing a ruff lint step
When `/project-done` is executed
Then the lint command runs before commit
And if lint fails, the commit is blocked

### Scenario 2: Done command skips lint when no CI config exists
Given a project with no `.github/workflows/` directory and no lint_command in LANG_PROFILES
When `/project-done` is executed
Then the lint gate is skipped silently
And the rest of the Done phases proceed normally

### Scenario 3: LANG_PROFILES includes lint_command for all stacks
Given the `LANG_PROFILES` dictionary in `workflows.py`
When inspected
Then each language entry has a `lint_command` key with a sensible default

### Scenario 4: Existing CI lint errors are fixed
Given the current codebase
When `ruff check src/ tests/` is run
Then zero lint errors are reported

### Scenario 5: Act command also runs lint after regression
Given a project with a `lint_command` in LANG_PROFILES
When `/project-act` Phase 3 regression check completes
Then the lint command also runs as a post-test verification
