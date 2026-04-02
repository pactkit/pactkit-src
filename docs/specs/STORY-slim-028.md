# STORY-slim-028: Configurable scan_excludes via pactkit.yaml

| Field | Value |
|-------|-------|
| ID | STORY-slim-028 |
| Status | Done |
| Priority | P0 — Impact 5, Effort 2 |
| Release | 2.3.7 |

## Background

`visualize.py` hardcodes `SCAN_EXCLUDES = {'venv', 'skills', 'commands', 'rules', 'agents', ...}`. This causes two problems: (1) PactKit's own `skills/` is silently excluded, and (2) user projects with common directory names like `commands/` (Go) or `agents/` (any framework) lose visibility. Users have no way to override this. The fix must keep default behavior unchanged for backward compatibility while allowing configuration.

## Requirements

### R1: pactkit.yaml `visualize.scan_excludes` config key (MUST)

Add a `visualize.scan_excludes` section to `get_default_config()`. When present, `_scan_files()` MUST use the configured list instead of the hardcoded `SCAN_EXCLUDES`. When absent, the current hardcoded `SCAN_EXCLUDES` MUST be used unchanged (backward compat).

### R2: `pactkit init` auto-generates visualize config (MUST)

`pactkit init` MUST auto-populate `visualize.scan_excludes` with a sensible default based on `detect_stack()`. The default list MUST include only truly universal excludes (`venv`, `node_modules`, `.git`, `__pycache__`, `dist`, `build`, `site-packages`) and stack-specific excludes (e.g., `vendor` for Go). Project-specific directories like `skills`, `commands`, `rules`, `agents` MUST NOT be in the default.

### R3: auto_merge backfills visualize section (MUST)

`auto_merge_config_file()` MUST backfill the `visualize` section for existing projects that upgrade PactKit. Existing user-defined values MUST NOT be overwritten.

### R4: _scan_files reads config (MUST)

`_scan_files()` MUST accept an optional `config` parameter. When provided, read `visualize.scan_excludes` from it. When not provided, fall back to the current `SCAN_EXCLUDES` constant.

## Acceptance Criteria

### AC1: Default behavior unchanged (R1, R4)

- **Given** a project with no `visualize` section in pactkit.yaml
- **When** running `pactkit visualize`
- **Then** the graph output is identical to the current behavior (same nodes, same edges)

### AC2: Custom excludes respected (R1, R4)

- **Given** pactkit.yaml contains `visualize: { scan_excludes: [venv, .git, __pycache__] }`
- **When** running `pactkit visualize`
- **Then** directories like `skills/`, `commands/` are scanned (not in exclude list)

### AC3: pactkit init generates visualize config (R2)

- **Given** a Python project with `pyproject.toml`
- **When** running `pactkit init`
- **Then** generated pactkit.yaml contains `visualize.scan_excludes` with universal defaults, without `skills`/`commands`/`rules`/`agents`

### AC4: auto_merge preserves user config (R3)

- **Given** a project with existing `visualize.scan_excludes: [venv, custom_dir]`
- **When** PactKit upgrades and runs `auto_merge`
- **Then** the user's `[venv, custom_dir]` is preserved, not overwritten

## Target Call Chain

```
pactkit visualize
  → load_config() → config['visualize']['scan_excludes']
  → _scan_files(root, config=config)
  → uses config excludes if present, else SCAN_EXCLUDES constant
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim028.py` | Tests for configurable excludes, backward compat, auto_merge backfill, generate_default_yaml output, _rewrite_yaml serialization | None | Low |
| 2 | `src/pactkit/config.py` :: `get_default_config()` | Add `"visualize": {"scan_excludes": [universal defaults]}` to returned dict | None | Low |
| 3 | `src/pactkit/config.py` :: `load_config()` | Add `"visualize"` to `DEEP_MERGE_KEYS` set so partial user overrides merge correctly | Step 2 | Low |
| 4 | `src/pactkit/config.py` :: `auto_merge_config_file()` | Add `"visualize"` to `_BACKFILL_KEYS` tuple so existing projects get the section on upgrade | Step 2 | Low |
| 5 | `src/pactkit/config.py` :: `_rewrite_yaml()` | Add `"visualize"` to `KNOWN_KEYS` set; add serialization block for visualize section (list format) | Step 2 | Low |
| 6 | `src/pactkit/config.py` :: `generate_default_yaml()` | Add visualize section serialization (list format with comment) | Step 2 | Low |
| 7 | `src/pactkit/skills/visualize.py` :: `_scan_files()` | Add optional `scan_excludes=None` parameter; when provided, use it as the excludes set; when None, use `SCAN_EXCLUDES` constant | None | Medium |
| 8 | `src/pactkit/skills/visualize.py` :: `visualize()` | Load pactkit.yaml via inline YAML read (standalone-safe), extract `scan_excludes`, pass to `_scan_files()` | Step 7 | Medium |
| 9 | `src/pactkit/skills/visualize.py` :: `impact()` | Same as Step 8: load config inline, pass `scan_excludes` to `_scan_files()` | Step 7 | Low |
| 10 | `src/pactkit/lazy_visualize.py` :: `run_visualize_single()` / `run_visualize_graphs()` | No changes needed (subprocess invocation; visualize.py reads config internally) | Step 8 | None |

### Design Note: Standalone Script Config Access

`visualize.py` is deployed as a standalone script (no `pactkit` imports available). It MUST read
`pactkit.yaml` directly using `yaml.safe_load()` (PyYAML is in `_SHARED_HEADER` imports via the
standard library json/os/sys, but yaml is NOT). Two options:

**Option A (Recommended)**: Add a lightweight `_load_scan_excludes(root)` helper in `visualize.py`
that searches for `.claude/pactkit.yaml` or `.opencode/pactkit.yaml`, reads it with `yaml.safe_load()`
(guarded by `try/except ImportError`), and returns the list or `None`. This keeps the script
self-contained and fails gracefully if PyYAML is not available.

**Option B**: Pass `scan_excludes` as a CLI argument (`--scan-excludes venv,.git,__pycache__`) from
`lazy_visualize.py` which has access to `load_config()`. This avoids YAML parsing in the standalone
script but requires changing the subprocess invocation in `lazy_visualize.py`.

**Decision**: Option A is preferred because it also works when the script is invoked directly by
AI agents (the primary use case for standalone scripts), not just via `pactkit visualize` CLI.

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Config values used as directory name match, not as paths |
| SEC-2 through SEC-8 | N/A | No auth, crypto, injection, or dependency changes |

## Out of Scope

- Multi-language file discovery (STORY-slim-029)
- LanguageAnalyzer interface (STORY-slim-030)
- Impact test mapping (STORY-slim-031)
