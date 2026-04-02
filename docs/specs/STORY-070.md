# STORY-070: OpenCode Format Compliance — Fix Spec-Implementation Gaps

| Field | Value |
|-------|-------|
| ID | STORY-070 |
| Status | Draft |
| Priority | P1 |
| Release | 1.6.9 |

## Background

STORY-069 和 BUG-035 完成了 OpenCode 部署格式的基础框架，但经过对照 OpenCode 官方文档（https://opencode.ai/docs/agents, /docs/commands, /docs/skills, /docs/rules, /docs/config）深度审计后，发现以下 Spec 要求未实现或实现不符合 OpenCode 实际格式：

### 发现的 7 个问题

| # | 严重度 | 问题 | Spec 引用 | 现状 |
|---|--------|------|-----------|------|
| 1 | **Critical** | Command frontmatter 未转换 | STORY-069 R8 | `allowed-tools: [Read, Write]` 仍然保留，OpenCode 应该用 `agent: build` |
| 2 | **Critical** | Agent 缺少 `mode` 字段 | STORY-069 R7 | 未生成 `mode: subagent`，OpenCode 要求此字段 |
| 3 | **High** | Agent `name` 字段多余 | OpenCode docs | OpenCode 用文件名作为 agent name，frontmatter 中的 `name` 字段被忽略 |
| 4 | **Medium** | Agent model 未映射为 provider 格式 | STORY-069 R7 | 输出 `model: inherit`，OpenCode 需要 `provider/model-id` 格式（如 `anthropic/claude-sonnet-4-20250514`），或省略以继承 |
| 5 | **Medium** | `upgrade` 命令不支持 opencode 格式 | CLI 一致性 | `upgrade_parser` choices 缺少 `opencode` |
| 6 | **Low** | `_deploy_opencode_json` 成为死代码 | BUG-035 移除调用 | 函数定义存在但 `_deploy_opencode()` 不调用，仅测试直接 import |
| 7 | **Low** | Agent 中 Claude Code 专有字段残留 | OpenCode docs | `permissionMode`, `memory`, `skills` 字段在 OpenCode 中无意义 |

## Requirements

### R1: Command frontmatter 转换为 OpenCode 格式 (MUST)

当 `format='opencode'` 时，command 文件的 frontmatter MUST 转换：

**当前（Claude Code 格式）**:
```yaml
---
description: "Analyze requirements"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---
```

**目标（OpenCode 格式）**:
```yaml
---
description: "Analyze requirements"
agent: build
---
```

转换规则：
- 移除 `allowed-tools` 字段
- 添加 `agent: build`（所有 PactKit 命令都由 build agent 执行）

### R2: Agent 添加 `mode: subagent` 字段 (MUST)

OpenCode agent frontmatter MUST 包含 `mode` 字段。所有 PactKit 自定义 agent MUST 设置为 `mode: subagent`。

**当前输出**:
```yaml
---
name: system-architect
description: High-level design and Intent Graph management.
tools:
  bash: true
  read: true
model: inherit
permissionMode: plan
---
```

**目标输出**:
```yaml
---
description: High-level design and Intent Graph management.
mode: subagent
tools:
  bash: true
  read: true
---
```

### R3: 移除 Agent 中的 `name` 字段 (MUST)

OpenCode 使用文件名作为 agent 名称（`system-architect.md` → agent name `system-architect`），frontmatter 中的 `name` 字段 MUST 被移除以避免混淆。

### R4: 清理 Agent 中 Claude Code 专有字段 (SHOULD)

以下 Claude Code 专有字段在 OpenCode 中无效，SHOULD 在 opencode 格式中被移除：
- `permissionMode` → 替换为 OpenCode 的 `permission` 对象
- `memory` → OpenCode 无对应概念
- `skills` → OpenCode 通过 skill tool 自动发现

保留有效字段：`description`, `mode`, `model`, `tools`, `prompt`, `temperature`, `steps`。

### R5: Agent model 格式适配 (SHOULD)

当 `model` 值为 PactKit 的简短标识（如 `opus`, `sonnet`, `haiku`）时，SHOULD 映射为 OpenCode 的 `provider/model-id` 格式。

映射表（基于用户的 provider 配置，无法硬编码通用值）：
- 如果 `model` 为 `inherit`：省略 `model` 字段（OpenCode 默认继承父 agent 的 model）
- 其他情况：保留原值（用户可在 opencode.json 中覆盖）

### R6: `upgrade` 命令支持 opencode 格式 (MUST)

`cli.py` 中 `upgrade_parser` 的 `--format` choices MUST 包含 `opencode`，与 `init_parser` 和 `update_parser` 保持一致。

### R7: 清理 `_deploy_opencode_json` 死代码 (MAY)

`_deploy_opencode_json()` 函数当前仅被测试调用。MAY 将其标记为 `# Used by /project-init playbook` 的工具函数，或通过其他方式确认其存在意义。

### R8: Agent routing reference 路径验证 (MUST)

Agent 文件中的 routing reference MUST 指向正确路径。当前输出 `~/.config/opencode/AGENTS.md`，需要验证该路径与 OpenCode 的 AGENTS.md 加载路径一致。

经验证，OpenCode 的全局 AGENTS.md 确实在 `~/.config/opencode/AGENTS.md`，**此项已正确**。

## Acceptance Criteria

### AC1: Command frontmatter 转换

- **Given** 用户运行 `pactkit init --format opencode`
- **When** 部署完成，读取任意 command 文件（如 `project-plan.md`）
- **Then** frontmatter 包含 `agent: build`
- **And** frontmatter 不包含 `allowed-tools`

### AC2: Agent mode 字段

- **Given** 用户运行 `pactkit init --format opencode`
- **When** 部署完成，读取任意 agent 文件（如 `system-architect.md`）
- **Then** frontmatter 包含 `mode: subagent`
- **And** frontmatter 不包含 `name` 字段

### AC3: Agent Claude Code 字段清理

- **Given** 用户运行 `pactkit init --format opencode`
- **When** 部署完成，读取所有 agent 文件
- **Then** frontmatter 不包含 `permissionMode`, `memory`, `skills` 字段

### AC4: Agent model inherit 省略

- **Given** agent 的 model 配置为 `inherit`
- **When** 以 opencode 格式部署
- **Then** frontmatter 中不输出 `model` 字段（OpenCode 默认行为即继承）

### AC5: upgrade 命令支持 opencode

- **Given** 用户运行 `pactkit upgrade --format opencode -t /tmp/test`
- **When** 命令完成
- **Then** 输出结构与 `pactkit init --format opencode` 一致

### AC6: 现有测试不回归

- **Given** 修改后的代码
- **When** 运行全部测试
- **Then** 所有现有测试通过（允许更新 opencode 格式相关测试以匹配新行为）

## Target Call Chain

```
User → pactkit init --format opencode
     → cli.py:main() → deploy(format='opencode')
     → deployer.py:_deploy_opencode()
         ├── _deploy_skills()                    # 无变化
         ├── _deploy_agents_md_inline()           # 无变化
         ├── _deploy_agents(opencode_format=True) # R2,R3,R4,R5 修改点
         │   └── 新逻辑: 添加 mode, 移除 name/permissionMode/memory/skills
         ├── _deploy_commands(opencode_format=True) # R1 新参数
         │   └── 新逻辑: 替换 allowed-tools 为 agent: build
         └── print summary
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/generators/deployer.py` | `_deploy_agents()`: 添加 `mode: subagent`，移除 `name`，清理 Claude Code 专有字段 | None | Medium |
| 2 | `src/pactkit/generators/deployer.py` | `_deploy_agents()`: 当 model=inherit 时省略 model 字段 | Step 1 | Low |
| 3 | `src/pactkit/generators/deployer.py` | `_deploy_commands()`: 添加 `opencode_format` 参数，替换 frontmatter | None | Medium |
| 4 | `src/pactkit/generators/deployer.py` | `_deploy_opencode()`: 传递 `opencode_format=True` 给 `_deploy_commands()` | Step 3 | Low |
| 5 | `src/pactkit/cli.py` | `upgrade_parser` choices 添加 `opencode` | None | Low |
| 6 | `tests/unit/test_story070_opencode_compliance.py` | 添加 AC1-AC6 测试 | Step 1-5 | Low |
| 7 | `tests/unit/test_story069_opencode_format.py` | 更新已有测试以匹配新格式 | Step 1-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (deployer.py, cli.py) |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend rendering |
| SEC-5 | No | No auth handling |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error message exposure |
| SEC-8 | No | No dependency changes |

## Out of Scope

- OpenCode 的 `permission` 对象完整映射（如 `bash: { "git *": "allow" }` 粒度控制）
- Agent model 的 `provider/model-id` 自动映射（取决于用户的 provider 配置）
- OpenCode TUI 配置（`tui.json`）
- `_deploy_opencode_json` 的最终处理（保留为 /project-init 工具函数）
- 项目级 `.opencode/` 目录结构（由 /project-init playbook 处理）
