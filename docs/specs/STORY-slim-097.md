# STORY-slim-097: Dual-dimension Harness Audit: Config + Code

| Field | Value |
|-------|-------|
| ID | STORY-slim-097 |
| Status | Draft |
| Priority | P1 |
| Release | 2.9.14 |

## Background

Current H1-H7 harness audit (`audit.py`) checks only configuration presence (rules dir exists, settings.json exists, etc.). This gives a skewed picture: a project with perfect config but no tests scores high, while a project with excellent code quality but config in `~/.claude/` (global) scores low.

The audit needs two dimensions:
1. **Config dimension**: Is the AI coding harness configured? (project-level `.claude/` + user-global `~/.claude/`)
2. **Code dimension**: Is the codebase healthy for AI collaboration? (tests, complexity, git hygiene, docs)

Both dimensions contribute to the final score. The H1-H7 layer display is preserved for backward compatibility with the report dashboard.

## Requirements

### R1: Introduce `_all_config_dirs()` helper (MUST)

Scan both project-level (`.claude/`, `.opencode/`, `.codex/`) and user-global (`~/.claude/`) config directories. All H1-H6 config checks MUST use this helper instead of hardcoded `_CONFIG_DIRS` relative paths.

### R2: Add Code dimension checks to H1-H7 (MUST)

Each layer gets both a config check and a code check where applicable:

| Layer | Config checks (existing + global) | New Code checks |
|-------|----------------------------------|-----------------|
| H1 Prompt | claude_md, rules, agents, skills | — |
| H2 Context | memory | specs_exist, context_fresh |
| H3 Process | — | tests_exist, test_coverage_ratio (test files / source files >= 0.3), ci_config, ci_green |
| H4 Tools | settings, mcp | lint_clean (ruff/eslint exits 0) |
| H5 Safety | safety_rules, hooks | gitignore, no_secrets_committed (no .env/.key files tracked) |
| H6 Observe | — | docstring_coverage (>= 50%), changelog, commit_recent (7 days) |
| H7 Evolution | — | version_managed, git_tags, ci_publish |

### R3: Dual-dimension scoring formula (MUST)

```
Config Score  = passed_config_checks / total_config_checks × 50
Code Score    = passed_code_checks / total_code_checks × 50
Harness Score = Config Score + Code Score  (max 100)
```

The `score` and `ready` fields in `harness_audit.json` MUST remain compatible with `report.py` dashboard.

### R4: Layer level calculation includes both dimensions (MUST)

Each H layer level (L0-L3) is now determined by combined config + code checks:
- L1: any 1 check passes
- L2: all config checks pass OR all code checks pass
- L3: all config AND all code checks pass

The `layers` dict in JSON output retains `{level, name, checks}` format.

### R5: JSON output adds dimension breakdown (SHOULD)

Add optional `dimensions` field to `harness_audit.json`:
```json
{
  "dimensions": {
    "config": {"score": 45, "passed": 9, "total": 10},
    "code": {"score": 40, "passed": 8, "total": 10}
  }
}
```
This is additive — existing fields unchanged.

### R6: Config checks scan global `~/.claude/` (MUST)

H1 commands check, H2 hierarchy_of_truth, H4 mcp_config, H5 safety_rules/hooks, H6 self_audit_rule/retro MUST all use `_all_config_dirs()` to scan global config.

## Acceptance Criteria

### AC1: Global config detection (R1, R6)

- **Given** project has no `.claude/rules/` but `~/.claude/rules/` has rule files
- **When** `_check_h1(root)` runs
- **Then** `checks['rules']` is True

### AC2: Code dimension — test coverage ratio (R2)

- **Given** project has 10 source files and 4 test files
- **When** `_check_h3(root)` runs
- **Then** `checks['test_coverage_ratio']` is True (4/10 >= 0.3)

### AC3: Code dimension — lint clean (R2)

- **Given** project has `ruff` available and source passes lint
- **When** `_check_h4(root)` runs
- **Then** `checks['lint_clean']` is True

### AC4: Dual scoring (R3)

- **Given** 8/10 config checks pass and 7/10 code checks pass
- **When** `_compute_score()` runs
- **Then** score = 8/10×50 + 7/10×50 = 40+35 = 75

### AC5: JSON backward compatibility (R4, R5)

- **Given** audit runs
- **When** `harness_audit.json` is written
- **Then** `score`, `ready`, `layers` (H1-H7), `hotspots` fields are present with same structure. `dimensions` is new optional field.

### AC6: Layer level uses both dimensions (R4)

- **Given** H5 has safety_rules=True (config) and gitignore=True (code) but hooks_config=False and no_secrets=True
- **When** `_check_h5()` runs
- **Then** level >= L2 (not all config pass, but all code pass)

## Target Call Chain

```
audit(target) → _check_h1..h7(root)
  _check_h*(root):
    dirs = _all_config_dirs(root)   # NEW: project + global
    config_checks = {...}           # scan dirs for config
    code_checks = {...}             # scan project for code quality
    level = _compute_layer_level(config_checks, code_checks)  # NEW
  → _compute_score(layers) → applies dual formula (R3)
  → JSON output with dimensions breakdown (R5)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/audit.py` | Revert current global scan hack, add clean `_all_config_dirs()` | None | Low |
| 2 | `src/pactkit/audit.py` | Add code checks to H2-H6 (test_coverage_ratio, lint_clean, docstring_pct, no_secrets, commit_recent) | Step 1 | Medium |
| 3 | `src/pactkit/audit.py` | Update level calculation to use both dimensions | Step 2 | Medium |
| 4 | `src/pactkit/audit.py` | Update `_compute_score()` for dual-dimension formula | Step 3 | Low |
| 5 | `src/pactkit/audit.py` | Add `dimensions` to JSON output | Step 4 | Low |
| 6 | `tests/unit/test_audit.py` | Add tests for AC1-AC6 | Steps 1-5 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Internal tool, reads local files only |
| SEC-2 | N/A | No output encoding changes |
| SEC-3 | N/A | No auth |
| SEC-4 | N/A | No new HTML templates |
| SEC-5 | N/A | No new dependencies |
| SEC-6 | N/A | Local CLI tool |
| SEC-7 | N/A | No network access |
| SEC-8 | N/A | No dependency changes |

## Out of Scope

- Changing the H1-H7 layer names or report dashboard layout
- Adding new H8+ layers
- Changing hotspot calculation formula
- Multi-format audit (OpenCode, Codex-specific checks)
