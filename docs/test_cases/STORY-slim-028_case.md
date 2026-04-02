# Test Cases: STORY-slim-028 — Configurable scan_excludes via pactkit.yaml

> Layer: API Level (unit tests — no browser required)
> Spec: `docs/specs/STORY-slim-028.md`
> Test File: `tests/unit/test_story_slim028.py`

---

## AC1: Default behavior unchanged (R1, R4)

**Scenario: No visualize section in pactkit.yaml — SCAN_EXCLUDES constant is used**

- **Given** a project directory with no `.claude/pactkit.yaml` or `.opencode/pactkit.yaml`
- **When** `_load_scan_excludes(root)` is called
- **Then** it returns `None`
- **And** `_scan_files(root)` falls back to the hardcoded `SCAN_EXCLUDES` constant
- **And** directories like `venv/` are still excluded from scan results
- **And** regular Python files in the project root are still found

**Scenario: SCAN_EXCLUDES constant retains backward-compat entries**

- **Given** the `SCAN_EXCLUDES` constant in `visualize.py`
- **When** inspected directly
- **Then** it contains `venv`, `.venv`, `__pycache__`, `.git` at minimum

---

## AC2: Custom excludes respected (R1, R4)

**Scenario: User-configured scan_excludes override the hardcoded constant**

- **Given** pactkit.yaml contains `visualize: { scan_excludes: [venv] }`
- **When** `_scan_files(root, scan_excludes=["venv"])` is called
- **And** a `skills/` directory with Python files exists alongside a `venv/` directory
- **Then** `skills/tool.py` is included in scan results (not in custom exclude list)
- **And** `venv/excluded.py` is excluded (in custom exclude list)

**Scenario: Empty custom excludes disables all exclusion**

- **Given** `scan_excludes=[]` is passed to `_scan_files()`
- **When** a `venv/` directory with Python files exists
- **Then** files inside `venv/` are included (nothing is excluded)

**Scenario: _load_scan_excludes reads from .claude/pactkit.yaml**

- **Given** `.claude/pactkit.yaml` contains a `visualize.scan_excludes` list
- **When** `_load_scan_excludes(root)` is called
- **Then** it returns the user-defined list (e.g., `["venv", "my_custom_dir"]`)

**Scenario: _load_scan_excludes falls back to .opencode/pactkit.yaml**

- **Given** no `.claude/pactkit.yaml` exists
- **And** `.opencode/pactkit.yaml` contains a `visualize.scan_excludes` list
- **When** `_load_scan_excludes(root)` is called
- **Then** it returns the list from the opencode config

**Scenario: _load_scan_excludes returns None when yaml has no visualize section**

- **Given** `.claude/pactkit.yaml` exists but contains no `visualize` key
- **When** `_load_scan_excludes(root)` is called
- **Then** it returns `None`

---

## AC3: pactkit init generates visualize config (R2)

**Scenario: get_default_config() includes visualize.scan_excludes**

- **Given** a call to `get_default_config()`
- **When** the result is inspected
- **Then** `config["visualize"]` exists as a dict
- **And** `config["visualize"]["scan_excludes"]` is a non-empty list
- **And** the list does NOT contain `skills`, `commands`, `rules`, or `agents`
- **And** the list DOES contain universal excludes: `venv`, `.venv`, `__pycache__`, `.git`, `node_modules`

**Scenario: generate_default_yaml() produces a visualize section**

- **Given** a call to `generate_default_yaml()`
- **When** the YAML string is inspected
- **Then** it contains `visualize:` and `scan_excludes:`
- **And** the visualize section does NOT contain `- skills`, `- commands`, `- rules`, or `- agents`

---

## AC4: auto_merge preserves user config (R3)

**Scenario: auto_merge backfills missing visualize section**

- **Given** a `pactkit.yaml` file with no `visualize` section
- **When** `auto_merge_config_file(path)` is called
- **Then** the returned additions list contains an entry referencing `visualize`
- **And** the written YAML now contains a `visualize.scan_excludes` key

**Scenario: auto_merge preserves existing user-defined visualize section**

- **Given** a `pactkit.yaml` with `visualize: { scan_excludes: [venv, custom_dir] }`
- **When** `auto_merge_config_file(path)` is called
- **Then** `visualize.scan_excludes` in the rewritten YAML equals `["venv", "custom_dir"]`
- **And** the user's custom entry is not replaced or merged with defaults

---

## Additional Coverage (load_config deep merge)

**Scenario: load_config with partial visualize section inherits list from user, not defaults**

- **Given** pactkit.yaml specifies `visualize: { scan_excludes: [venv, my_custom_dir] }`
- **When** `load_config(path)` is called
- **Then** `config["visualize"]["scan_excludes"]` equals `["venv", "my_custom_dir"]`
- **Note** scan_excludes is a list (shallow override), not a dict (deep merge)

**Scenario: load_config with no visualize section returns default excludes**

- **Given** pactkit.yaml contains no `visualize` key
- **When** `load_config(path)` is called
- **Then** `config["visualize"]["scan_excludes"]` equals the list from `get_default_config()`
