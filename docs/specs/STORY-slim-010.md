# STORY-slim-010: Version Sync Fix & Deployer DRY Refactor

| Field | Value |
|-------|-------|
| ID | STORY-slim-010 |
| Status | Done |
| Priority | P2 |
| Release | 2.1.1 |

## Summary

修复 `.claude/pactkit.yaml` 版本号不一致（2.2.0 → 2.1.1）导致的测试失败，以及提取 `deployer.py` 中 3 处重复的 `rule_id_to_key` 反向映射构建和 2 处重复的 `skill_md` 渲染逻辑为独立辅助函数。

这两个问题都是纯重构/修正，不改变任何功能行为。

## Background

### 问题 1: 版本号不一致
- `pyproject.toml:7` → `2.1.1`（规范源）
- `src/pactkit/__init__.py:3` → `2.1.1`（同步）
- `.opencode/pactkit.yaml:5` → `2.1.1`（同步）
- `.claude/pactkit.yaml:5` → `2.2.0`（不一致）
- 导致 `test_pactkit_yaml_version_matches_pyproject` 测试失败

### 问题 2: DRY 违反
`deployer.py` 中存在以下重复代码：

**Violation A — rule_id_to_key 构建（100% 重复，2 处）:**
- `_deploy_rules()` 第 532-535 行
- `_deploy_claude_md_inline()` 第 1308-1311 行

**Violation B — rule_id_to_filename 变体（同算法，不同值）:**
- `_deploy_claude_md()` 第 570-573 行

**Violation C — skill_md 渲染（100% 重复，2 处）:**
- `_deploy_skills()` 第 460-464 行（scripted skills 循环）
- `_deploy_skills()` 第 476-480 行（prompt-only skills 循环）

## Target Call Chain

```
deployer.py
├── _deploy_rules(rules_dir, enabled_rules)
│   └── rule_id_to_key = {build reverse map}  ← Violation A1
├── _deploy_claude_md(claude_root, enabled_rules)
│   └── rule_id_to_filename = {build reverse map}  ← Violation B
├── _deploy_claude_md_inline(plugin_root, skills_prefix)
│   └── rule_id_to_key = {build reverse map}  ← Violation A2
└── _deploy_skills(skills_dir, enabled_skills, profile, _prefix)
    ├── Loop 1 (scripted): skill_md = render(...)  ← Violation C1
    └── Loop 2 (prompt-only): skill_md = render(...)  ← Violation C2
```

## Requirements

### R1: Version Sync
MUST fix `.claude/pactkit.yaml` version from `2.2.0` to `2.1.1` to match pyproject.toml.

### R2: Extract rule_id_to_key Helper
MUST extract `_build_rule_id_to_key()` helper to eliminate Violation A (2 identical blocks).

### R3: Extract rule_id_to_filename Helper
MUST extract `_build_rule_id_to_filename()` helper or parametrize to handle Violation B (variant).

### R4: Extract skill_md Render Helper
MUST extract `_render_skill_md()` helper to eliminate Violation C (2 identical blocks).

### R5: No Behavioral Change
MUST NOT change any functional behavior — all existing tests MUST continue to pass.

### R6: Line Count Reduction
SHOULD reduce total line count in deployer.py by eliminating duplication.

## Out of Scope

- Type annotations (separate story)
- Refactoring `_generate_project_claude_md()` complexity (separate story)
- Adding new unit tests for extracted helpers (existing integration tests cover all paths)

## Acceptance Criteria

### AC1: Version Consistency

GIVEN all version files exist
WHEN I run `pytest tests/unit/test_story014_release.py -v`
THEN test_pactkit_yaml_version_matches_pyproject PASSES
AND all 4 version files contain "2.1.1"

### AC2: rule_id_to_key Helper

GIVEN deployer.py has a `_build_rule_id_to_key()` function
WHEN `_deploy_rules()` needs the reverse map
THEN it calls `_build_rule_id_to_key()` instead of inline building
AND `_deploy_claude_md_inline()` also calls the same helper

### AC3: rule_id_to_filename Helper

GIVEN deployer.py has a `_build_rule_id_to_filename()` function
WHEN `_deploy_claude_md()` needs the reverse map
THEN it calls `_build_rule_id_to_filename()` instead of inline building

### AC4: skill_md Render Helper

GIVEN deployer.py has a `_render_skill_md()` function
WHEN `_deploy_skills()` renders SKILL.md for scripted or prompt-only skills
THEN both loops call `_render_skill_md()` with the same arguments
AND the rendered output is identical to the previous inline logic

### AC5: Full Test Suite Green

GIVEN the refactoring is complete
WHEN I run `pytest tests/ -v`
THEN all 2324+ tests pass (the previously failing version test is now fixed)
AND ruff check produces no errors

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `.claude/pactkit.yaml` | Fix version `2.2.0` → `"2.1.1"` | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | Extract `_build_rule_id_to_key()` helper | None | Low |
| 3 | `src/pactkit/generators/deployer.py` | Extract `_build_rule_id_to_filename()` helper | None | Low |
| 4 | `src/pactkit/generators/deployer.py` | Extract `_render_skill_md()` helper | None | Low |
| 5 | `src/pactkit/generators/deployer.py` | Replace 5 inline blocks with helper calls | Step 2, 3, 4 | Low |
| 6 | Full test suite | Run `pytest tests/ -v` + `ruff check` | Step 1-5 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (deployer.py) |
| SEC-2 | No | No user input handling changes |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend code |
| SEC-5 | No | No auth/session changes |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No exception handling changes |
| SEC-8 | No | No dependency changes |
