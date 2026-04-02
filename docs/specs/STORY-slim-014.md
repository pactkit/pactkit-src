# STORY-slim-014: Code is the Law — Deterministic Rule Migration

| Field | Value |
|-------|-------|
| ID | STORY-slim-014 |
| Status | Draft |
| Priority | P0 |
| Release | 2.2.0 |

## Background

PactKit currently has ~95 rules governing PDCA workflow. Approximately 40 are already enforced by Python code (spec_linter, config validation, board operations), but ~25 deterministic rules still live only in Markdown prompts, relying on AI to "follow instructions" — creating non-deterministic execution. Additionally, key Python modules have no IP protection (plain .py files are trivially copyable).

This story migrates deterministic rules from MD prompts to Python code and compiles core modules to .so for IP protection.

### Current State (Audit Results)

- **Already coded**: ~40 rules (spec_linter 13, config 12, board 4, schemas 6, profiles 3, deployer 5+)
- **MD-only deterministic**: ~25 rules (init guard, story ID generation, regression decision, lint gate, context update, etc.)
- **Heuristic (stay in MD)**: ~30 rules (intent analysis, code writing, security assessment, language matching)
- **Dangerous dual-write**: VALID_AGENTS/COMMANDS in config.py vs routing-table.md, branch naming in scaffold.py vs workflow-conventions.md
- **.so feasibility**: All 8 core Python files have zero exec()/eval()/dynamic loading — 100% Cython-compatible

## Target Call Chain

```
pactkit CLI → cli.py → new subcommands (guard, next-id, clean, regression, context, sec-scope)
                     → existing subcommands (spec-lint, init, update)
                     → visualize --lazy (source change detection + conditional dispatch)
                     → deployer.py → _render_prompt() → slimmed prompts (commands.py, workflows.py)
                     → Cython build → .so files in dist/
```

## Requirements

### R1: New CLI subcommands for deterministic operations
MUST extract the following deterministic operations from prompt text into `pactkit` CLI subcommands:

| Subcommand | Current Location | Logic |
|------------|-----------------|-------|
| `pactkit guard` | Plan Phase 0.5 | Check 3 init markers + config completeness |
| `pactkit next-id` | Plan Phase 3.1 | Scan docs/specs/, read developer, return next STORY-{dev}-{NNN} |
| `pactkit clean` | Done Phase 2 | Remove LANG_PROFILES[stack].cleanup artifacts |
| `pactkit regression` | Done Phase 2.5 | Doc-only shortcut, version bump detection, impact analysis decision tree |
| `pactkit context` | Done Phase 4.5 | Generate context.md from board + git + lessons |
| `pactkit sec-scope` | Plan Phase 3.2 | SEC-1~SEC-8 applicability from file paths + content patterns |

### R2: Document structure validators
MUST add validators for document types that currently have schemas but no enforcement:

| Validator | Schema Source | Current State |
|-----------|-------------|--------------|
| `pactkit lint-context` | `schemas.py:CONTEXT_SECTIONS` | Only prompt-enforced |
| `pactkit lint-lessons` | `schemas.py:LESSONS_ROW_FORMAT` | Only prompt-enforced |
| `pactkit lint-testcase` | `schemas.py:TEST_CASE_SCENARIO_PATTERN` | Only prompt-enforced |

### R3: Eliminate dual-write between Python and MD
MUST auto-generate routing table content from Python constants so there is one source of truth:

- `VALID_AGENTS` / `VALID_COMMANDS` / `VALID_SKILLS` in `config.py` → auto-generate `04-routing-table.md` content at deploy time via `_render_prompt()`
- `_BRANCH_PREFIX_MAP` in `scaffold.py` → remove from `05-workflow-conventions.md` prose, reference code as canonical
- `CONTEXT_SECTIONS` in `schemas.py` → auto-generate `07-shared-protocols.md` Context.md format section

### R4: Slim prompt templates
MUST replace deterministic instruction blocks in prompts with CLI invocations:

**Before** (prompt text instructs AI to do file operations):
```
1. Read `developer` from `pactkit.yaml`
2. Scan `docs/specs/` for existing files with same prefix
3. Find max number, increment by 1
```

**After** (prompt delegates to code):
```
1. Run `pactkit next-id` to get the next Story ID.
```

### R5: Backward compatibility
MUST maintain all existing CLI commands and Python API signatures unchanged. The refactoring is internal — no user-facing behavior change except new subcommands added.

### R6: Security Scope auto-detection
MUST extract the SEC-1~SEC-8 applicability logic from prompt text into a `pactkit sec-scope` subcommand:

- Accepts a list of changed file paths (from `git diff --name-only` or explicit args)
- Applies the file-path pattern matching rules currently described in Plan Phase 3.2 Security Scope section:
  | Check | Pattern |
  |-------|---------|
  | SEC-1 | Any `.py`, `.js`, `.ts`, `.go`, `.java` file |
  | SEC-2 | File contains `request.`, `form.`, `input`, `argv`, `sys.stdin`, `process.argv` |
  | SEC-3 | Path matches `models/`, `dao/`, `repository/`; or contains SQL/ORM patterns |
  | SEC-4 | Path matches `.tsx`, `.vue`, `.svelte`, `.html`; or contains `innerHTML`, `dangerouslySetInnerHTML` |
  | SEC-5 | Path matches `auth/`, `session/`, `login/`; or contains `token`, `jwt`, `cookie`, `session` |
  | SEC-6 | Path matches `api/`, `routes/`, `endpoints/`, `controllers/` |
  | SEC-7 | Path matches `api/`, `routes/`; or contains exception handling patterns |
  | SEC-8 | File matches `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml` |
- Docs/tests-only shortcut: if ALL files match `docs/**`, `tests/**`, `*.md`, `README*` → all checks N/A
- Output: Markdown table ready to paste into `## Security Scope` section of a Spec

### R7: Lazy Visualize CLI
SHOULD add a `--lazy` flag to `pactkit visualize` (or a standalone `pactkit visualize-lazy`) that auto-detects source changes before running:

- Check `git diff --name-only HEAD` against `LANG_PROFILES[stack].source_dirs` and `file_ext`
- If zero source files changed AND `code_graph.mmd` exists → skip with message "Graph up-to-date — no source changes"
- If source files changed OR graph missing → run full visualize (file, class, call modes)
- This replaces the "Lazy Visualize Protocol" currently duplicated in Act Phase 4, Done Phase 2, and `07-shared-protocols.md`

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/cli.py` | Add `guard`, `next-id`, `clean`, `regression`, `context`, `sec-scope` subcommands | None | Medium |
| 2 | `src/pactkit/guards.py` (new) | Implement init guard + config completeness check | Step 1 | Low |
| 3 | `src/pactkit/id_generator.py` (new) | Implement next-id logic (scan specs, read developer) | Step 1 | Low |
| 4 | `src/pactkit/cleaners.py` (new) | Implement cleanup per LANG_PROFILES | Step 1 | Low |
| 5 | `src/pactkit/regression.py` (new) | Implement regression decision tree (doc-only, version bump, impact) | Step 1 | Medium |
| 6 | `src/pactkit/context_gen.py` (new) | Implement context.md generation from board + git + lessons | Step 1 | Medium |
| 7 | `src/pactkit/validators.py` (new) | Add lint-context, lint-lessons, lint-testcase validators | None | Low |
| 8 | `src/pactkit/prompts/commands.py` | Replace deterministic blocks with CLI invocations | Steps 1-7 | Medium |
| 9 | `src/pactkit/prompts/rules.py` | Auto-generate routing table from VALID_* constants | Step 3 | Low |
| 10 | `src/pactkit/sec_scope.py` (new) | Implement SEC-1~SEC-8 file-path pattern matching + content sniffing | Step 1 | Low |
| 11 | `src/pactkit/lazy_visualize.py` (new) | Implement source change detection + conditional visualize dispatch | None | Low |
| 12 | Tests | TDD for all new subcommands + validators | Steps 1-11 | Low |

## Acceptance Criteria

### Scenario 1: pactkit guard replaces Init Guard prompt
- **Given** a project missing `docs/product/sprint_board.md`
- **When** running `pactkit guard`
- **Then** exit code 1 with message listing missing markers

### Scenario 2: pactkit next-id replaces manual ID generation
- **Given** docs/specs/ contains STORY-slim-013.md as highest
- **When** running `pactkit next-id`
- **Then** output `STORY-slim-014`

### Scenario 3: pactkit regression replaces decision tree prompt
- **Given** only `docs/specs/STORY-slim-014.md` changed (doc-only)
- **When** running `pactkit regression`
- **Then** output `SKIP — doc-only change` with exit code 0

### Scenario 4: No dual-write between routing table and config.py
- **Given** a new agent added to `VALID_AGENTS` in config.py
- **When** running `pactkit init` to deploy
- **Then** the deployed `04-routing-table.md` automatically includes the new agent

### Scenario 5: Prompt text reduction
- **Given** the refactored commands.py
- **When** comparing char count before vs after
- **Then** deterministic instruction blocks are replaced by single-line CLI invocations, reducing total prompt size by >= 15%

### Scenario 6: pactkit sec-scope auto-detects security checks
- **Given** changed files include `src/pactkit/cli.py` and `pyproject.toml`
- **When** running `pactkit sec-scope src/pactkit/cli.py pyproject.toml`
- **Then** output a Markdown table with SEC-1=Yes (source code), SEC-2=Yes (argv), SEC-8=Yes (pyproject.toml), rest=No

### Scenario 7: pactkit sec-scope docs-only shortcut
- **Given** changed files are only `docs/specs/STORY-slim-014.md` and `README.md`
- **When** running `pactkit sec-scope docs/specs/STORY-slim-014.md README.md`
- **Then** output all SEC checks as N/A with reason "docs/tests only"

### Scenario 8: pactkit visualize --lazy skips when no source changes
- **Given** no source files changed (`git diff --name-only HEAD` returns only `docs/` files)
- **And** `docs/architecture/graphs/code_graph.mmd` exists
- **When** running `pactkit visualize --lazy`
- **Then** output "Graph up-to-date — no source changes" with exit code 0

### Scenario 9: All existing tests pass
- **Given** all refactoring applied (R1-R7)
- **When** running `pytest tests/ -v`
- **Then** 2397+ tests pass with zero failures

## Out of Scope

- Rewriting heuristic rules (intent analysis, code generation, security assessment) — these require AI judgment and stay in MD
- Cython .so compilation (R5/R6 removed — high maintenance burden, low IP protection ROI; consider SaaS/PyArmor/license-key if needed later)
- Skill script entry point refactor for .so compatibility (removed with .so compilation)
- Changing user-facing CLI interface for existing commands

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Multiple source files modified/created |
| SEC-2 | Yes | CLI subcommands parse argv |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No API endpoints |
| SEC-7 | Yes | New CLI commands need error handling |
| SEC-8 | No | No dependency file changes |
