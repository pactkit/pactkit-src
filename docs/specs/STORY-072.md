# STORY-072: Multi-Developer Story ID Prefix for Merge-Safe Collaboration

| Field | Value |
|-------|-------|
| ID | STORY-072 |
| Status | Draft |
| Priority | P1 |
| Release | 1.6.9 |

## Background

### 问题 1：Story ID 冲突

PactKit 的 Story ID 由 LLM 本地递增猜测，多人协作时不同分支会生成相同 ID，导致 merge 冲突。

### 问题 2：pactkit.yaml 与 OpenCode 的矛盾

`pactkit.yaml` 硬编码在 `.claude/pactkit.yaml`。纯 OpenCode 用户没有 `.claude/` 目录，也不应该被迫创建。

**`pactkit.yaml` 是 PactKit CLI 自己的配置文件**，应该跟着 AI 工具的项目目录约定走：
- Claude Code 用户：`.claude/pactkit.yaml`
- OpenCode 用户：`.opencode/pactkit.yaml`

两个路径对称、互不干扰。

### 方案

1. **pactkit.yaml 路径解耦**：`load_config()` 按优先级查找 `.claude/pactkit.yaml` → `.opencode/pactkit.yaml`。生成时感知环境，写到对应目录。
2. **developer 前缀**：Story ID 变为 `STORY-{prefix}-{NNN}`，从根本上消除多人 ID 冲突。

### 配置文件归属关系（修正后）

```
文件                              归属          存放位置
──────────────────────────────────────────────────────────
.claude/pactkit.yaml              PactKit CLI   Claude Code 项目
.opencode/pactkit.yaml            PactKit CLI   OpenCode 项目
opencode.json                     OpenCode      项目根目录
~/.config/opencode/opencode.json  OpenCode      全局
```

### load_config() 查找优先级

```
1. .claude/pactkit.yaml      ← Claude Code 环境（向后兼容）
2. .opencode/pactkit.yaml    ← OpenCode 环境
3. 返回默认配置               ← 都不存在
```

### Story ID 冲突分析（developer 前缀改进后）

| 文件 | 改进前 | 改进后 |
|------|--------|--------|
| `docs/specs/*.md` | Critical（同名） | **零冲突** |
| `tests/unit/test_story*` | Critical（同名） | **零冲突** |
| `sprint_board.md` | Critical（同位置插入） | **Auto-merge 通常成功** |
| `context.md` | High（全文覆盖） | 不变（取后方） |
| `lessons.md` | Low（同行附近追加） | **Auto-merge 通常成功** |

## Requirements

### R1: `load_config()` 多路径查找 (MUST)

`config.py:load_config()` 当 `path=None` 时 MUST 按以下顺序查找：

1. `$CWD/.claude/pactkit.yaml`（Claude Code 环境）
2. `$CWD/.opencode/pactkit.yaml`（OpenCode 环境）
3. 返回默认配置

第一个存在的文件胜出。两者共存时 `.claude/` 优先（向后兼容）。

### R2: pactkit.yaml 生成路径感知 (MUST)

`_generate_project_pactkit_yaml()` MUST 感知环境：

- `.claude/` 目录存在 → 生成到 `.claude/pactkit.yaml`（当前行为）
- `.opencode/` 目录存在且 `.claude/` 不存在 → 生成到 `.opencode/pactkit.yaml`
- 都不存在 → 生成到 `.claude/pactkit.yaml`（默认，保持向后兼容）

### R3: `pactkit.yaml` 新增 `developer` 字段 (MUST)

```yaml
developer: alice
```

- 小写字母 + 数字 + 连字符，长度 2-20
- 默认值：空字符串（单人模式，行为与当前一致）

### R4: `/project-plan` 使用前缀生成 Story ID (MUST)

读取 `developer` 字段：
- 有值：ID 格式 `STORY-{developer}-{NNN}`
- 空/不存在：ID 格式 `STORY-{NNN}`（向后兼容）

NNN 递增基于 `docs/specs/` 中同前缀的最大编号 +1。

### R5: `/project-plan` playbook 更新 (MUST)

Phase 3 增加指令：
```
Read `developer` from pactkit.yaml (check .claude/ then .opencode/).
If set, use ID format: STORY-{developer}-{NNN}.
If not set, use ID format: STORY-{NNN}.
```

### R6: `/project-init` playbook 更新 (MUST)

OpenCode 环境检测部分更新：
```
Ensure pactkit.yaml exists:
- Claude Code: .claude/pactkit.yaml (already handled)
- OpenCode: .opencode/pactkit.yaml (generate if missing)
```

### R7: Config 校验 (SHOULD)

`config.py` SHOULD 校验 `developer` 字段格式。无效值打印 warning 但不阻塞。

### R8: Playbook 路径引用更新 (MUST)

commands.py 中所有硬编码 `.claude/pactkit.yaml` 的 playbook 指令 MUST 更新为 `pactkit.yaml (in .claude/ or .opencode/)`。

## Acceptance Criteria

### AC1: Claude Code 用户不受影响

- **Given** 项目有 `.claude/pactkit.yaml`
- **When** `load_config()`
- **Then** 读取 `.claude/pactkit.yaml`

### AC2: OpenCode 用户读取 .opencode/ 配置

- **Given** 项目只有 `.opencode/pactkit.yaml`（无 `.claude/`）
- **When** `load_config()`
- **Then** 读取 `.opencode/pactkit.yaml`

### AC3: 两者共存时 .claude/ 优先

- **Given** 两个文件都存在
- **When** `load_config()`
- **Then** 读取 `.claude/pactkit.yaml`

### AC4: OpenCode 环境生成到 .opencode/

- **Given** `.opencode/` 存在，`.claude/` 不存在
- **When** `pactkit init`
- **Then** `.opencode/pactkit.yaml` 被创建
- **And** `.claude/` 目录不被创建

### AC5: 有前缀时 Story ID 正确

- **Given** `developer: alice`
- **When** `/project-plan`
- **Then** ID 为 `STORY-alice-NNN`

### AC6: 无前缀时向后兼容

- **Given** `developer` 为空
- **When** `/project-plan`
- **Then** ID 为 `STORY-NNN`

### AC7: 两个前缀零冲突

- **Given** Alice: `STORY-alice-001.md`，Bob: `STORY-bob-001.md`
- **When** merge
- **Then** 无文件名冲突

### AC8: developer 字段校验

- **Given** `developer: Alice_123`
- **When** `pactkit update`
- **Then** 打印 warning

## Target Call Chain

```
# 配置读取（多路径）
load_config(path=None)
→ 尝试 $CWD/.claude/pactkit.yaml   → 存在则返回
→ 尝试 $CWD/.opencode/pactkit.yaml → 存在则返回
→ 返回默认配置

# 配置生成（环境感知）
_generate_project_pactkit_yaml()
→ .claude/ 存在？ → .claude/pactkit.yaml
→ .opencode/ 存在？ → .opencode/pactkit.yaml
→ 都不存在？ → .claude/pactkit.yaml（默认）

# Story 创建
/project-plan Phase 3:
→ load_config() → developer: alice
→ 扫描 docs/specs/STORY-alice-*.md → max N = 2
→ 生成 ID: STORY-alice-003
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/config.py:207` | `load_config()`: 多路径查找 `.claude/` → `.opencode/` → 默认 | None | Medium |
| 2 | `src/pactkit/config.py` | `developer` 字段加入默认 schema + 格式校验 | None | Low |
| 3 | `src/pactkit/generators/deployer.py:109,120-121` | `_deploy_classic()`: config 路径改用 `load_config()` 而非硬编码 | Step 1 | Medium |
| 4 | `src/pactkit/generators/deployer.py:802` | `_generate_project_pactkit_yaml()`: 环境感知 `.claude/` vs `.opencode/` | Step 1 | Medium |
| 5 | `src/pactkit/skills/board.py:171` | `snapshot()`: yaml_path 改用多路径查找 | Step 1 | Low |
| 6 | `src/pactkit/prompts/commands.py:32` | Init Guard: marker 检查改为 `.claude/pactkit.yaml` OR `.opencode/pactkit.yaml` | None | Low |
| 7 | `src/pactkit/prompts/commands.py:101` | Plan Phase 3: Release 字段读取路径更新 | None | Low |
| 8 | `src/pactkit/prompts/commands.py:596-608` | Init Phase 1: 配置生成/检查逻辑，支持 OpenCode 环境 | None | Low |
| 9 | `src/pactkit/prompts/commands.py:627` | **删除** 反向指令"Do NOT create pactkit.yaml in .opencode/" | None | Low |
| 10 | `src/pactkit/prompts/commands.py` | Plan Phase 3: developer 前缀 ID 生成指令 | Step 2 | Low |
| 11 | `src/pactkit/prompts/skills.py:394,402` | Doctor skill: drift 检测和配置验证路径更新 | None | Low |
| 12 | `src/pactkit/prompts/workflows.py:297` | Sprint workflow: agent_models 读取路径更新 | None | Low |
| 13 | `tests/unit/test_story072_*.py` | AC1-AC8 测试 | Step 1-12 | Low |

### 不需要改的引用（泛称 `pactkit.yaml`，无硬编码路径）

以下 commands.py 行只说 `pactkit.yaml`（无路径前缀），LLM 会通过 `load_config()` 或 file search 找到正确位置，无需改动：
- L40, L260, L261, L427, L464, L468, L504, L522, L530, L582, L671
- skills.py L414, L524
- agents.py L28

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend rendering |
| SEC-5 | No | No auth handling |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error message exposure |
| SEC-8 | No | No dependency changes |

## Out of Scope

- Board 文件拆分（单文件保持不变）
- context.md 冲突解决（全文覆盖，取后方）
- Graph 文件冲突（自动生成，merge 后重新生成）
- 已有 Story ID 迁移（历史 STORY-071 等保持不变）
- 完全移除 `.claude/` 路径支持（必须保持向后兼容）
- deployer.py 中非 load_config 路径的 `.claude/` 引用（通过入口点间接修复）
