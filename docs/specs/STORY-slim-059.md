# STORY-slim-059: Remove dead codex profile and slim down core package

| Field | Value |
|-------|-------|
| ID | STORY-slim-059 |
| Status | Done |
| Priority | P1 |
| Release | v2.6.0 |

## Background

Codex CLI 已被拆分到独立项目 (`~/workspaces/pactguard/` 等)，不再使用 PactKit 核心的 codex profile。但 `profiles.py` 中仍保留 codex FormatProfile（line 149-168, 20 行），deployer.py 中残留 3 处 codex 引用，`config.py` 的 `VALID_FORMATS` 仍包含 `codex`。这些死代码增加了维护负担和认知成本。

同时，经过 STORY-slim-057（提取 DeployerBase）和 STORY-slim-058（提取 pactkit-opencode）后，deployer.py 将从 1685 行缩减至约 800 行（仅保留 ClassicDeployer + DeployerBase + PluginDeployer）。本 Story 进一步清理死代码，使 core 包精简到只包含 Classic（Claude Code）部署逻辑。

跨文件 codex 引用分布（共 18 处）：
- `profiles.py`: 10 处（FormatProfile 定义 + PACTKIT_YAML_CANDIDATES）
- `deployer.py`: 3 处
- `prompts/rules.py`: 3 处
- `prompts/commands.py`: 1 处
- `skills/scaffold.py`: 1 处

## Requirements

### R1: 移除 codex FormatProfile (MUST)

从 `profiles.py` 中删除 `codex` FormatProfile 条目（line 149-168）和 `PACTKIT_YAML_CANDIDATES` 中的 codex 路径。

### R2: 移除 codex 分支代码 (MUST)

从 `deployer.py` 中删除所有 codex 条件分支（`if format == "codex"` 等）。从 `prompts/rules.py`, `prompts/commands.py`, `skills/scaffold.py` 中删除 codex 相关注释和条件逻辑。

### R3: 更新 VALID_FORMATS (MUST)

从 `config.py` 的 `VALID_FORMATS` 中移除 `codex`。由于 `VALID_FORMATS` 现在从 `profiles.py` 的 `FORMAT_PROFILES.keys()` 自动派生，删除 profile 即自动移除。

### R4: 更新测试 (MUST)

所有引用 codex format 的测试 MUST 被删除或修改。不能有测试依赖 codex profile 的存在。

### R5: deployer.py 行数目标 (SHOULD)

完成 057+058+059 后，`deployer.py` SHOULD 不超过 900 行（从当前 1685 行缩减 ~47%）。

### R6: _DEPLOYMENT_MODES 保持不变 (MUST)

`plugin` 和 `marketplace` 部署模式不受影响。它们不是环境格式，不依赖 codex profile。

## Acceptance Criteria

### AC1: codex profile 不存在 (R1)

- **Given** 完成清理后的 `profiles.py`
- **When** `from pactkit.profiles import FORMAT_PROFILES` 执行
- **Then** `"codex" not in FORMAT_PROFILES` 为 True

### AC2: pactkit init --format codex 报错 (R1, R3)

- **Given** 清理完成后的 pactkit
- **When** 执行 `pactkit init --format codex`
- **Then** 报错: `"Unknown format: 'codex'"` 并退出码 1

### AC3: 零 codex 引用 (R2)

- **Given** 清理完成后的 `src/pactkit/`
- **When** `grep -r "codex" src/pactkit/` 执行
- **Then** 匹配数为 0（CHANGELOG 和 docs 中的历史引用除外）

### AC4: 所有测试通过 (R4)

- **Given** 更新后的测试套件
- **When** `pytest tests/ -v` 执行
- **Then** 全部通过，无 codex 相关测试残留

### AC5: plugin/marketplace 不受影响 (R6)

- **Given** 清理完成后的 pactkit
- **When** 执行 `pactkit init --format plugin --target /tmp/test-plugin`
- **Then** Plugin 部署正常完成，不受 codex 移除影响

### AC6: deployer.py 瘦身 (R5)

- **Given** 完成 057+058+059 的完整重构
- **When** `wc -l src/pactkit/generators/deployer.py` 执行
- **Then** 行数 ≤ 900

## Target Call Chain

无新调用链。本 Story 为纯删除操作。

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/profiles.py` | 删除 codex FormatProfile (line 149-168)，从 PACTKIT_YAML_CANDIDATES 移除 codex 路径 | STORY-slim-058 | Low |
| 2 | `src/pactkit/generators/deployer.py` | 删除 codex 条件分支和相关常量 | Step 1 | Low |
| 3 | `src/pactkit/prompts/rules.py` | 删除 codex 相关引用（3 处）| Step 1 | Low |
| 4 | `src/pactkit/prompts/commands.py` | 删除 codex 相关引用（1 处）| Step 1 | Low |
| 5 | `src/pactkit/skills/scaffold.py` | 删除 codex 相关引用（1 处）| Step 1 | Low |
| 6 | `tests/` | 删除或修改所有 codex 相关测试 | Steps 1-5 | Medium — 需确认测试覆盖范围 |
| 7 | `tests/` | 运行全量回归测试 | Step 6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | 纯删除操作 |
| SEC-2 Authentication | N/A | 无变更 |
| SEC-3 Path Traversal | N/A | 无变更 |
| SEC-4 Injection | N/A | 无变更 |
| SEC-5 Secrets | N/A | 无变更 |
| SEC-6 Dependencies | N/A | 无新依赖 |
| SEC-7 Config Safety | N/A | 无变更 |
| SEC-8 Data Exposure | N/A | 无变更 |

## Out of Scope

- 重构 DeployerBase（STORY-slim-057）
- 提取 pactkit-opencode（STORY-slim-058）
- 修改 Classic 部署逻辑
- 修改 plugin/marketplace 部署模式
- 历史文档中的 codex 引用（CHANGELOG, docs/specs 中的历史 story）
