# STORY-010: Release v1.1.0 — 文档同步 + 版本发布

- **Priority**: 5 (Impact 5 / Effort 1)
- **Agent**: Repo Maintainer
- **Release**: 1.1.0
- **Depends on**: STORY-009

## Background

STORY-005 ~ STORY-009 带来了大量新功能（plugin 分发、session context、project-status、constitution sharpening、config auto-merge），但 PyPI 上仍是 v1.0.0。README 和 CLAUDE.md 中的数字过期（13 commands → 14, 846 tests → 909+）。

用户通过 `pip install pactkit` 安装后拿不到这些新功能。

## Requirements

### R1: Sync README.md (MUST)
- "13 commands" → "14 commands" (project-status added in STORY-007)
- "13 command playbooks" → "14 command playbooks"
- 添加 `/project-status` 到 PDCA+ Workflow 表格
- 保持 Quick Start 中 `pactkit update` 说明与 auto-merge 一致

### R2: Sync .claude/CLAUDE.md (MUST)
- "846 tests passing" → 当前实际数字
- "13 command playbooks" → "14 command playbooks"
- Architecture section 反映实际结构

### R3: Version alignment (MUST)
- `pyproject.toml`: `version = "1.1.0"`
- `config.py`: `get_default_config()` 中 `version` 保持 `"0.0.1"`（这是 **用户 yaml** 的默认版本，不是 PactKit 版本）
- `__init__.py`: `__version__` MUST 与 pyproject.toml 一致

### R4: CHANGELOG (SHOULD)
- 创建 `CHANGELOG.md`（如果不存在）
- 包含 v1.1.0 的变更列表：
  - feat: Config auto-merge on upgrade (STORY-009)
  - feat: /project-status cold-start command (STORY-007)
  - feat: Constitution sharpening — 55% token reduction (STORY-008)
  - feat: Session context protocol (STORY-006)
  - feat: Plugin & marketplace distribution (STORY-005)

### R5: Git tag (MUST)
- `git tag v1.1.0` after commit

### R6: PyPI publish readiness (SHOULD)
- `python -m build` MUST succeed
- `twine check dist/*` MUST pass
- 实际 `twine upload` 由用户手动执行（不自动发布）

## Acceptance Criteria

### Scenario 1: README accuracy
**Given** README.md exists
**When** user reads the command count and workflow table
**Then** it correctly says 14 commands and includes project-status

### Scenario 2: Version consistency
**Given** pyproject.toml, __init__.py
**When** user runs `pactkit version`
**Then** output shows "PactKit v1.1.0"

### Scenario 3: Build succeeds
**Given** source code with version 1.1.0
**When** `python -m build` is executed
**Then** wheel and sdist are generated without errors

### Scenario 4: Existing tests pass
**Given** version bump changes
**When** full test suite runs
**Then** all tests pass (no version-dependent test breakage)

## Implementation Notes

1. Target files: `README.md`, `.claude/CLAUDE.md`, `pyproject.toml`, `src/pactkit/__init__.py`
2. Check if any test asserts on `__version__` — update accordingly
3. The `config.py` default version (`0.0.1`) is the user yaml schema version, NOT the PactKit package version — do not change it

## Target Call Chain

```
No code logic change — documentation and metadata sync only.
pyproject.toml → __init__.py.__version__ → cli.py:main() → print(f"PactKit v{__version__}")
```
