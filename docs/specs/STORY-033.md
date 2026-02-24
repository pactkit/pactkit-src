# STORY-033: Config auto-backfill for missing sections on update

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.3.0 |

## Context

When PactKit adds new config sections (hooks, ci, issue_tracker, lint_blocking, auto_fix, rule_scopes, agent_models) in newer versions, existing users' `pactkit.yaml` files don't get updated because:

1. `_generate_config_if_missing()` only writes if the file doesn't exist
2. `auto_merge_config_file()` only handles list-type keys (agents/commands/skills/rules)
3. `_rewrite_yaml()` only writes list sections + exclude — it drops non-list sections

Running `pactkit update` re-deploys all files correctly (because `load_config()` merges defaults at runtime), but the YAML on disk remains incomplete, confusing users who don't see hooks/ci/etc. in their config.

## Target Call Chain

```
pactkit update
  → deploy() → _deploy_classic()
    → auto_merge_config_file(yaml_path)   ← extend here
      → _rewrite_yaml()                    ← extend here
    → load_config(yaml_path)
```

## Requirements

1. `auto_merge_config_file()` MUST backfill missing non-list config sections with their defaults from `get_default_config()`
2. Sections to backfill: `ci`, `issue_tracker`, `hooks`, `lint_blocking`, `auto_fix`
3. Backfill MUST NOT overwrite user's existing values — only add sections that are completely absent
4. `_rewrite_yaml()` MUST write all config sections (ci, issue_tracker, hooks, lint_blocking, auto_fix) — not just lists
5. The backfill report SHOULD include what sections were added (e.g., `"section: hooks"`)
6. `pactkit init` on a fresh directory MUST still generate a complete config (existing behavior unchanged)

## Acceptance Criteria

### AC1: Missing non-list sections are backfilled
- **Given** a pactkit.yaml with only `stack`, `version`, `root` (no hooks/ci/etc.)
- **When** `auto_merge_config_file()` is called
- **Then** the file on disk now contains `hooks`, `ci`, `issue_tracker`, `lint_blocking`, `auto_fix` with default values
- **And** original `stack`, `version`, `root` values are preserved

### AC2: Existing user values are not overwritten
- **Given** a pactkit.yaml with `hooks: {pre_commit_lint: true}`
- **When** `auto_merge_config_file()` is called
- **Then** `pre_commit_lint` remains `true`
- **And** missing hook keys within the section are NOT added (respect user's explicit config)

### AC3: _rewrite_yaml writes all sections
- **Given** a config dict with hooks, ci, issue_tracker, lint_blocking, auto_fix
- **When** `_rewrite_yaml()` is called
- **Then** the written file contains all these sections with correct formatting

### AC4: Backfill reports added sections
- **Given** a minimal pactkit.yaml missing hooks and ci sections
- **When** `auto_merge_config_file()` is called
- **Then** return value includes entries like `"section: hooks"`, `"section: ci"`

### AC5: Fresh init still generates complete config
- **Given** no pactkit.yaml exists
- **When** `pactkit init` runs
- **Then** generated pactkit.yaml contains all sections (existing behavior unchanged)
