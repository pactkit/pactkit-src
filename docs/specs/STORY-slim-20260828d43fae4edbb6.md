# STORY-slim-20260828d43fae4edbb6: Stack-aware commit-gate test commands (node/go/java)

| Field | Value |
|-------|-------|
| ID | STORY-slim-20260828d43fae4edbb6 |
| Status | Draft |
| Priority | P1 |
| Release | 2.25.0 |

## Background

PactKit recognizes `node`/`go`/`java` as project stacks (cleaners, lint
profiles), but the commit-gate's test invocation is hard-wired to pytest:
`run_pytest` builds a venv-aware `python -m pytest` command and always
appends `tests/unit/` when no test selection exists.  In a Node/Go/Java
project the gate therefore either fails to find pytest (self-lock WARN,
gate silently absent) or runs a meaningless Python suite.  Together with
HOTFIX-slim-20260828ee6cde3108fb (git hooks must not lock out machines
without pactkit), this story makes the gate actually enforce in
non-Python projects.

## Requirements

### R1: Stack-aware test command resolution (MUST)

`pactkit.utils` MUST provide `stack_test_command(root)` returning
`(stack, argv)` or `None`:

- Python present in `detect_stacks(root)` (or no markers at all) → the
  existing venv-aware `pytest_command(root)` — current behavior is the
  fallback and is never regressed (monorepos with Python test
  infrastructure keep pytest).
- `node` → `npm test --silent` when `package.json` has a non-empty
  `scripts.test`; `None` when it does not (no runner to invoke).
- `go` → `go test ./...`.
- `java` → `./mvnw -q test` when `mvnw` exists, else `mvn -q test` when
  `pom.xml` exists, else `./gradlew -q test` when `gradlew` exists, else
  `gradle -q test`.
- Unreadable/corrupt `package.json` → `None`, never an exception.

### R2: Gate runs the stack's suite (MUST)

`commit_gate.run_pytest` MUST dispatch through `stack_test_command`:
python keeps the pytest invocation verbatim (including `-rs -q` and the
`tests/unit/` default); non-python stacks run their full suite with the
resolved argv (per-file test selection is not attempted — mapped
selection is a Python-only capability today, and the impact strategy
already collapses to full for unmapped stacks).  A `None` resolution
MUST raise `GateUnavailable` so `run_gate` degrades to WARN + allow
(R3 self-lock protection) instead of running a wrong-suite command.

### R3: Doctor probe is stack-aware (MUST)

`enforcement.probe_commit_gate` MUST report availability for the actual
stack: python keeps the pytest-resolvability check; non-python stacks
probe the runner's presence (binary on PATH, or wrapper file existing)
and report UNAVAILABLE with a stack-specific reason otherwise.
`probe_push_gate` is unchanged (never runs tests).

### R4: Verdict semantics unchanged (MUST)

The gate verdict stays returncode-driven: a non-zero suite exit blocks
the commit with the output tail; `parse_pytest_summary` remains
best-effort for display (jest/vitest "N failed" lines match its regex;
`go test`/`mvn` counts may render as zero — the [FAIL] verdict and tail
lines carry the signal, and this limitation is accepted).

## Acceptance Criteria

### AC1: Python behavior unchanged (R1, R2)

- **Given** a project with Python markers (or no markers at all)
- **When** `stack_test_command(root)` is called
- **Then** it returns `("python", pytest_command(root))`, and `run_pytest` invokes pytest with `-rs -q` exactly as before

### AC2: Node resolution (R1)

- **Given** `package.json` with `"scripts": {"test": "vitest run"}` and no Python markers
- **When** `stack_test_command(root)` is called
- **Then** it returns `("node", ["npm", "test", "--silent"])`
- **Given** `package.json` without a `scripts.test` entry (or corrupt JSON)
- **Then** it returns `None`

### AC3: Go/Java resolution (R1)

- **Given** a project root containing only `go.mod`
- **When** `stack_test_command(root)` is called
- **Then** it returns `("go", ["go", "test", "./..."])`
- **Given** a project root containing `pom.xml` and `mvnw`
- **When** `stack_test_command(root)` is called
- **Then** it returns `("java", ["./mvnw", "-q", "test"])`; with `pom.xml` but no `mvnw` it returns `["mvn", "-q", "test"]`
- **Given** a project root containing `build.gradle` and `gradlew`
- **When** `stack_test_command(root)` is called
- **Then** it returns `("java", ["./gradlew", "-q", "test"])`

### AC4: Gate runs npm test and blocks on red (R2, R4)

- **Given** a Node project (package.json with test script) with a staged change
- **When** `run_gate` executes
- **Then** the invoked command is `npm test --silent` (test-file selection ignored), and returncode 1 blocks with `[FAIL]`
- **Given** a Node project whose `package.json` has no test script
- **Then** `run_gate` allows with a WARN mentioning gate unavailability (self-lock protection)

### AC5: Probe reports stack-specific status (R3)

- **Given** a Node project without a test script
- **When** `probe_commit_gate` runs
- **Then** status is UNAVAILABLE with a reason naming the missing runner — not "pytest not resolvable"

## Target Call Chain

```
cli.py (commit-gate dispatch) → commit_gate.run_gate (:391)
  └─ run_pytest (:120)                      # now stack-dispatched
       └─ utils.stack_test_command (new)    # detect_stacks + markers
            ├─ python → utils.pytest_command (existing, untouched)
            └─ node/go/java → canonical runner argv

enforcement.probe_commit_gate (:176)        # stack-aware availability
  └─ utils.stack_test_command
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/utils.py` | `stack_test_command(root)` with marker-based resolution | None | Low |
| 2 | `src/pactkit/commit_gate.py` | `run_pytest` dispatch + `GateUnavailable` on None | Step 1 | Medium |
| 3 | `src/pactkit/enforcement.py` | `probe_commit_gate` stack-aware runner check | Step 1 | Low |
| 4 | `tests/unit/test_stack_test_command.py` (new) | AC1-AC5 coverage | Steps 1-3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source changes; argv built from constants and marker-file presence — no shell string assembly, no eval |
| SEC-2 | Yes | `package.json` is external input: parsed with `json.loads` in try/except, shape-checked before use (R1 corrupt-input rule) |
| SEC-7 | Yes | Failure semantics: None resolution → GateUnavailable → WARN + allow (self-lock), never a crash and never a wrong-suite block |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | HOTFIX-slim-20260828ee6cde3108fb (same release train, code-independent) |
| Provides | `utils.stack_test_command` (consumed by commit_gate + enforcement probes) |
| Touches | `src/pactkit/utils.py`, `src/pactkit/commit_gate.py`, `src/pactkit/enforcement.py`, `tests/unit/` (new test file) |
| Conflict risk | LOW |

## Out of Scope

- Per-file test selection for non-python stacks (test_mapper stays Python-only)
- `package.json` scripts beyond `test` (no vitest/jest direct invocation tuning)
- Coverage gate for non-python stacks (coverage_gate stays pytest-based)
- npm distribution of the hooks (option C from the 2026-08-28 analysis)
- Windows-specific runner names (`npm.cmd` etc. — git-bash `npm` works)
