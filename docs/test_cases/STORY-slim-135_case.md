# Test Cases: STORY-slim-135 — Schema-driven pactkit.yaml governance

| Field | Value |
|-------|-------|
| Story | STORY-slim-135 |
| Level | API (unit) — tests/unit/test_story_slim135_config_schema.py |
| Generated | 2026-08-13 |
| Verdict | QA PASS |

---

## TC-01: 新 init yaml 极简 (R2)


- **Scenario**: Fresh init writes only stack and developer
  - **Given** an empty project directory
  - **When** generate_default_yaml("python") is rendered
  - **Then** the output contains "stack: python" and developer
  - **And** it contains no ci/check/e2e/visualize/regression default sections
  - **And** it points to "pactkit schema config" for discoverability
  - **And** non-empty line count is at most 12

## TC-02: schema 单一事实源 (R1, R3)


- **Scenario**: Default config keys equal non-optional schema keys
  - **Given** the CONFIG_SCHEMA registry
  - **When** get_default_config() is called
  - **Then** its key set equals the non-optional schema entries

- **Scenario**: Adding a key requires one registry entry
  - **Given** a schema entry with default/deep_merge/kind metadata
  - **When** defaults and validation run
  - **Then** both derive from the same entry with no per-key branches

## TC-03: 解析等价性 golden 测试 (R6)


- **Scenario**: Golden fixtures merge identically
  - **Given** a fixture yaml (94-line legacy, 3 repo copies, empty, minimal, unknown-keys)
  - **When** load_config() merges it
  - **Then** the result matches the pre-refactor golden snapshot key by key

## TC-04: 重写路径统一渲染 (R3)


- **Scenario**: Minimal file stays minimal after rewrite
  - **Given** a pactkit.yaml with only stack and developer
  - **When** _rewrite_yaml rewrites it
  - **Then** no ci/check/e2e sections are re-inflated

- **Scenario**: Explicit and unknown keys survive rewrite
  - **Given** data with explicit ci/regression sections and a custom key
  - **When** _rewrite_yaml rewrites it
  - **Then** all explicit values and the custom key are preserved

## TC-05: 副本漂移被检测并修复 (R4)


- **Scenario**: Drift across .claude and .codex copies is reported
  - **Given** copies with different developer values
  - **When** check_config_copy_drift runs
  - **Then** drift is True and the developer key is named

- **Scenario**: Sync copies canonical (.claude) content to all copies
  - **Given** drifting copies
  - **When** sync_config_copies runs
  - **Then** all copies are byte-identical to the canonical copy
  - **And** the canonical choice follows CANONICAL_PREFERENCE, not key count

## TC-06: schema config 可查全部键 (R5)


- **Scenario**: Report lists every key with default, effective value and source
  - **Given** a project with a .claude/pactkit.yaml
  - **When** schema_config_report runs
  - **Then** every schema key appears with effective/default/source fields
  - **And** keys from the file cite the file; others cite "default"

## TC-07: 测试套件全通过 (R1-R6)


- **Scenario**: Full suite green
  - **When** .venv/bin/pytest tests/ runs
  - **Then** all tests pass except the pre-existing test_story_slim132 failure
