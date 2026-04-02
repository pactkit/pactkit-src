# STORY-slim-070: Harness Garden — Codebase Quality Patrol

| Field | Value |
|-------|-------|
| ID | STORY-slim-070 |
| Status | Done |
| Priority | P1 |
| Release | 3.0.0 |

## Background

Inspired by OpenAI's "Entropy & Garbage Collection" concept from their Harness Engineering post: agent-generated code inevitably replicates existing patterns — including bad ones. Over time, codebases accumulate dead code, stale documentation, inconsistent naming, and orphaned artifacts. OpenAI's team spent 20% of each Friday manually cleaning "AI residue" before automating it with periodic Codex quality tasks.

PactKit currently has `doctor.py` for project health (orphaned specs, config drift, stale graphs, HLD drift) but no tool for **codebase quality patrol** — scanning source code and project artifacts for entropy signals and generating actionable cleanup suggestions.

This story adds `pactkit garden` — a new CLI subcommand that scans for codebase entropy and reports actionable findings, following the established `doctor.py` pure-function pattern.

## Requirements

### R1: Dead Code Detection (MUST)

`pactkit garden` MUST scan source files for dead code signals:
- Unused imports (via `ruff` `F401` output parsing if ruff is available, else regex heuristic)
- Functions/classes defined but never referenced within the project (cross-file grep)
- Empty `except: pass` blocks

Output: structured list of findings with file path, line number, and finding type.

### R2: Stale Documentation Detection (MUST)

`pactkit garden` MUST scan `docs/` for stale documentation signals:
- Spec files with Status=Done that reference files no longer existing (path references in Implementation Steps)
- Test case files (`docs/test_cases/`) referencing spec IDs not in `docs/specs/`
- `context.md` with "Last updated" date older than 7 days

### R3: Pattern Duplication Detection (SHOULD)

`pactkit garden` SHOULD detect code duplication signals:
- Identical or near-identical function signatures across different modules (same name + same parameter count)
- Multiple inline copies of canonical constants (regex for `# Canonical:` comments and verify targets still match)

### R4: CLI Interface (MUST)

`pactkit garden` MUST support:
- `pactkit garden` — full scan, human-readable output
- `pactkit garden --json` — machine-readable JSON output
- `pactkit garden --scope <path>` — scan only specified directory
- Exit code 0 if no findings, 1 if any findings exist

### R5: Pure Function Architecture (MUST)

Each check MUST be a pure function accepting `project_root: Path` and returning a typed dict, following the `doctor.py` pattern. The CLI layer MUST only orchestrate calls and format output.

## Acceptance Criteria

### AC1: Dead Import Detected (R1)

- **Given** a Python file with `import os` but `os` is never used in the file
- **When** `pactkit garden` runs
- **Then** output includes `[DEAD-IMPORT] src/example.py:3 — unused import 'os'`

### AC2: Stale Spec Reference (R2)

- **Given** a Done spec referencing `src/old_module.py` in Implementation Steps, but that file was deleted
- **When** `pactkit garden` runs
- **Then** output includes `[STALE-DOC] docs/specs/STORY-xxx.md — references non-existent file 'src/old_module.py'`

### AC3: Stale Context Detected (R2)

- **Given** `context.md` with "Last updated: 2026-03-20" and today is 2026-03-31
- **When** `pactkit garden` runs
- **Then** output includes `[STALE-CTX] context.md — last updated 11 days ago (threshold: 7 days)`

### AC4: JSON Output (R4)

- **Given** any findings exist
- **When** `pactkit garden --json` runs
- **Then** output is valid JSON with structure `{"findings": [{"type": str, "file": str, "line": int|null, "message": str}], "total": int}`

### AC5: Scoped Scan (R4)

- **Given** dead imports in both `src/pactkit/` and `src/pactkit/skills/`
- **When** `pactkit garden --scope src/pactkit/skills/` runs
- **Then** only findings within `src/pactkit/skills/` are reported

### AC6: Clean Exit (R4)

- **Given** no entropy findings in the project
- **When** `pactkit garden` runs
- **Then** output is `Garden: all clear — no findings` and exit code is 0

### AC7: Duplication Detection (R3)

- **Given** two modules with functions `def calculate_total(items, tax)` in both `src/billing.py` and `src/invoice.py`
- **When** `pactkit garden` runs
- **Then** output includes `[DUP-FUNC] calculate_total(items, tax) — found in src/billing.py:10 and src/invoice.py:25`

### AC8: Pure Function Contract (R5)

- **Given** `check_dead_imports(project_root)` is called directly
- **When** the function executes
- **Then** it returns `{"findings": [...]}` without any side effects (no file writes, no prints)

## Target Call Chain

```
pactkit garden [--json] [--scope <path>]
  → cli.py: garden command dispatch
  → garden.py: run_garden(root, scope=None, json_output=False)
    → check_dead_imports(root, scope) → {"findings": [...]}
    → check_stale_docs(root, scope) → {"findings": [...]}
    → check_pattern_duplication(root, scope) → {"findings": [...]}
    → aggregate findings
    → if json_output: json.dumps(report)
    → else: format_garden_report(report)
    → return exit_code (0 or 1)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_garden.py` | TDD: tests for all 3 check functions + CLI integration | None | Low |
| 2 | `src/pactkit/garden.py` | Implement `check_dead_imports()`, `check_stale_docs()`, `check_pattern_duplication()`, `run_garden()` | None | Low |
| 3 | `src/pactkit/cli.py` | Add `garden` subcommand with `--json` and `--scope` flags | Step 2 | Low |
| 4 | `src/pactkit/config.py` | Add `pactkit-garden` to `VALID_SKILLS` | Step 3 | Low |
| 5 | `tests/e2e/cli/test_cli_e2e.py` | E2E test: `pactkit garden` subprocess call | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Input Validation) | MUST | `--scope` path must be validated (no traversal above project root) |
| SEC-2 (Auth) | N/A | No auth changes |
| SEC-3 (Injection) | N/A | No command construction from user input |
| SEC-4 (Secrets) | N/A | No credential handling |
| SEC-5 (CORS) | N/A | CLI-only |
| SEC-6 (Path Traversal) | MUST | `--scope` must resolve within `project_root` |
| SEC-7 (DoS) | N/A | File scan bounded by project size |
| SEC-8 (Dependencies) | N/A | No new dependencies (ruff is optional) |

## Out of Scope

- Auto-fix capabilities (garden reports only, does not modify files)
- Cross-language dead code detection (Python only for v3.0.0; extend via LANG_PROFILES later)
- Git history analysis (e.g., "file not modified in 6 months")
- Integration with CI pipelines (future: `pactkit garden --ci` exit code for PR gates)
