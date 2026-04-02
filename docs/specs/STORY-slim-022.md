# STORY-slim-022: E2E Testing Framework — Config-Driven Check Phase

| Field | Value |
|-------|-------|
| ID | STORY-slim-022 |
| Status | Done |
| Priority | P2 |
| Release | 2.3.1 |

## Background

PactKit's `/project-check` (CHECK_PROMPT) currently has a hardcoded Phase 4 with two strategies:
- Strategy A: API Level (`tests/e2e/api/`)
- Strategy B: Browser Level (`tests/e2e/browser/`)

These strategies are always presented regardless of project type. A CLI-only project (like PactKit itself) doesn't need browser or API E2E — it needs subprocess-based CLI testing. A frontend-only project doesn't need API E2E. The strategy selection should be driven by `pactkit.yaml` configuration, not hardcoded assumptions.

Additionally, there is no `e2e` configuration section in `pactkit.yaml`. The config pipeline (`get_default_config` → `load_config` → `validate_config` → `generate_default_yaml`) needs a new `e2e` section.

## Target Call Chain

```
config.py:get_default_config()       → add e2e defaults
config.py:DEEP_MERGE_KEYS            → add "e2e"
config.py:validate_config()          → add e2e validation
config.py:generate_default_yaml()    → add e2e YAML output
config.py:VALID_E2E_TYPES            → new frozenset
commands.py:COMMANDS_CONTENT["project-check.md"]  → Phase 4 config-driven
```

## Requirements

### R1: VALID_E2E_TYPES Constant
`config.py` MUST define `VALID_E2E_TYPES = frozenset({"none", "cli", "frontend", "backend", "fullstack"})`.

### R2: Default Config
`get_default_config()` MUST include an `e2e` section with defaults:
- `type`: `"none"` (opt-in, not opt-out)
- `blocking`: `False` (E2E failures are warnings, not gates)
- `test_dir`: `"tests/e2e"` (output directory for generated E2E scripts)
- `env_file`: `".env.test"` (test-specific environment variables file)

### R3: Config Deep Merge
`DEEP_MERGE_KEYS` MUST include `"e2e"` so partial user config is deep-merged with defaults.

### R4: Config Validation
`validate_config()` MUST warn on:
- `e2e.type` not in `VALID_E2E_TYPES`
- `e2e.blocking` not a boolean
- `e2e.test_dir` not a string (if provided)
- `e2e.env_file` not a string (if provided)

Frontend-specific keys (`api_spec`, `mock`, `server`) and backend-specific keys (`api_spec`, `db`) SHOULD be accepted without validation — they are prompt-consumed, not code-consumed.

### R9: E2E Environment File
E2E tests that need credentials (API tokens, DB connection strings) MUST read from `e2e.env_file` (default: `.env.test`), NOT from production `.env`.
- CHECK_PROMPT Phase 4 MUST instruct the agent to load `e2e.env_file` before running E2E tests.
- If the file does not exist, WARN but do not block (some E2E types like `cli` may not need credentials).
- The `.env.test` file SHOULD be in `.gitignore` (same as `.env`).

### R5: YAML Generation
`generate_default_yaml()` MUST output the `e2e` section with a comment explaining the 5 types.

### R6: CHECK_PROMPT Phase 4 Config-Driven
CHECK_PROMPT Phase 4 MUST be rewritten to:
1. Read `e2e.type` from `pactkit.yaml`
2. If `type: none` → skip E2E phase entirely with log
3. If `type: cli` → generate subprocess-based CLI E2E (`tests/e2e/cli/`)
4. If `type: frontend` → generate Playwright + MSW browser E2E (`tests/e2e/browser/`)
5. If `type: backend` → generate httpx/requests API E2E (`tests/e2e/api/`)
6. If `type: fullstack` → generate docker-compose + Playwright E2E
7. Reference `e2e.blocking` to determine if failures are WARN or BLOCK

### R7: CHECK_PROMPT Cleanup Strategy
CHECK_PROMPT Phase 4 MUST instruct the agent to clean up test artifacts after execution:
- `cli`: temp directories via pytest `tmp_path` fixture
- `frontend`: MSW interceptors (in-memory, auto-cleanup)
- `backend`: test DB transaction rollback via pytest fixtures
- `fullstack`: `docker-compose down -v`

### R8: Blast Radius Control
This story MUST NOT modify any other command prompts (Plan, Act, Done, Sprint, Hotfix, etc.). Only `config.py` and `commands.py` (CHECK_PROMPT section) are in scope.

## Acceptance Criteria

### AC1: Default E2E Config
GIVEN a fresh `get_default_config()` call
WHEN the config is returned
THEN `config["e2e"]` equals `{"type": "none", "blocking": False, "test_dir": "tests/e2e", "env_file": ".env.test"}`

### AC2: VALID_E2E_TYPES
GIVEN `VALID_E2E_TYPES` is imported from `config.py`
WHEN checked
THEN it contains exactly `{"none", "cli", "frontend", "backend", "fullstack"}`

### AC3: Deep Merge
GIVEN a user `pactkit.yaml` with `e2e: { type: cli }`
WHEN `load_config()` merges with defaults
THEN `config["e2e"]` equals `{"type": "cli", "blocking": False, "test_dir": "tests/e2e", "env_file": ".env.test"}`

### AC4: Validation Warns on Invalid Type
GIVEN a config with `e2e: { type: invalid_type }`
WHEN `validate_config()` runs
THEN a warning is emitted containing "e2e.type"

### AC5: YAML Generation Includes E2E
GIVEN `generate_default_yaml()` is called
WHEN the output is parsed
THEN it contains `e2e:` section with `type: none`

### AC6: CHECK_PROMPT Reads Config
GIVEN CHECK_PROMPT text
WHEN Phase 4 is examined
THEN it references `pactkit.yaml` and `e2e.type` for strategy selection

### AC7: CHECK_PROMPT Has All 5 Types
GIVEN CHECK_PROMPT text
WHEN Phase 4 is examined
THEN it contains strategies for `none`, `cli`, `frontend`, `backend`, and `fullstack`

### AC8: CHECK_PROMPT References Blocking
GIVEN CHECK_PROMPT text
WHEN Phase 4 or Phase 5 is examined
THEN it references `e2e.blocking` for WARN vs BLOCK behavior

### AC9: CHECK_PROMPT References Cleanup
GIVEN CHECK_PROMPT text
WHEN Phase 4 is examined
THEN it contains cleanup instructions for each E2E type

### AC10: No Other Commands Modified
GIVEN git diff of this story
WHEN non-config/non-check files are examined
THEN no other command prompts (PLAN_PROMPT, ACT_PROMPT, DONE_PROMPT, etc.) are modified

### AC11: Default env_file
GIVEN a fresh `get_default_config()` call
WHEN the config is returned
THEN `config["e2e"]["env_file"]` equals `".env.test"`

### AC12: CHECK_PROMPT References env_file
GIVEN CHECK_PROMPT text
WHEN Phase 4 is examined
THEN it references `e2e.env_file` or `env_file` for loading test credentials

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/config.py` | Add `VALID_E2E_TYPES` frozenset | None | Low |
| 2 | `src/pactkit/config.py` | Add `e2e` to `get_default_config()` | Step 1 | Low |
| 3 | `src/pactkit/config.py` | Add `"e2e"` to `DEEP_MERGE_KEYS` | Step 2 | Low |
| 4 | `src/pactkit/config.py` | Add e2e validation to `validate_config()` | Step 1 | Low |
| 5 | `src/pactkit/config.py` | Add e2e section to `generate_default_yaml()` | Step 2 | Low |
| 6 | `src/pactkit/prompts/commands.py` | Rewrite CHECK_PROMPT Phase 4 | Step 1 | Medium |
| 7 | `src/pactkit/prompts/commands.py` | Add env_file reference to Phase 4 | Step 6 | Low |
| 8 | `tests/unit/test_story_slim022.py` | Unit tests for R1-R9 | Steps 1-7 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | env_file path references test credentials — must not leak production secrets |
| SEC-2 | N/A | Config validation only (warning-based) |
| SEC-3 | N/A | No database queries |
| SEC-4 | N/A | No user content rendering |
| SEC-5 | N/A | No authentication |
| SEC-6 | N/A | No endpoints |
| SEC-7 | N/A | No error messages to users |
| SEC-8 | N/A | No new dependencies |
