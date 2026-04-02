# STORY-073: OpenCode Format Final Mile — Command Model Routing and Claude Code Residuals

| Field | Value |
|-------|-------|
| ID | STORY-073 |
| Status | Draft |
| Priority | P1 |
| Release | 1.6.9 |

## Background

STORY-069/070/071/072 完成了 OpenCode 部署格式的核心框架，但经过全量审计仍发现 4 类 Claude Code 残留硬编码：

1. **Command frontmatter 缺少 `model:` 字段** — `opencode.json` 里配了 agent model 路由，但 command 文件只有 `agent: build`，没有 `model:`。OpenCode command 的 `model:` 字段会覆盖 agent 默认模型，是实现命令级模型路由的正确方式。

2. **`/project-init` playbook 无条件创建 CLAUDE.md** — OpenCode 用户应创建 `AGENTS.md`，不是 `CLAUDE.md`。

3. **Config YAML 注释引用 `~/.claude/`** — 生成的 pactkit.yaml 文件中的注释写着 "deployed to ~/.claude/agents/"，OpenCode 用户看到会困惑。

4. **源码文档字符串中的 `~/.claude/skills/` 路径** — 不影响运行时但误导开发者。

## Requirements

### R1: Command frontmatter 添加 `model:` 字段 (MUST)

`_convert_command_frontmatter_opencode()` MUST 在 OpenCode 格式转换时添加 `model:` 字段。

模型映射策略基于命令的角色：

| Command | Role | Model |
|---------|------|-------|
| `project-plan` | 架构决策 | (不设 — 继承主模型，用户可切 Opus 4.5/4.6) |
| `project-act` | 代码实现 | `sonnet` |
| `project-check` | QA 审查 | `sonnet` |
| `project-done` | 代码提交 | `sonnet` |
| `project-init` | 环境初始化 | `sonnet` |
| `project-clarify` | 需求澄清 | (不设 — 继承主模型) |
| `project-release` | 发布管理 | `sonnet` |
| `project-pr` | PR 创建 | `sonnet` |
| `project-sprint` | Sprint 编排 | (不设 — 继承主模型，需要深度推理) |
| `project-hotfix` | 紧急修复 | `sonnet` |
| `project-design` | 产品设计 | (不设 — 继承主模型) |

命令模型通过 `pactkit.yaml` 的 `command_models` 配置段读取，MUST 支持用户覆盖：

```yaml
command_models:
  project-act: sonnet
  project-done: sonnet
  project-check: sonnet
```

OpenCode 部署时将简短 model 名映射为 `opencode.json` 中已配置的 provider model ID。映射逻辑：
- 读取 `~/.config/opencode/opencode.json` 中的 `provider` 配置
- 在所有 provider 的 `models` 中查找包含 `sonnet`/`opus`/`haiku` 关键字的 model ID
- 生成完整的 `provider/model-id` 格式（如 `nexus-anthropic-bedrock/claude-sonnet-4.6`）
- 如果找不到匹配：省略 `model:` 字段（继承主模型）

### R2: `/project-init` 条件分支创建 CLAUDE.md vs AGENTS.md (MUST)

`/project-init` playbook 的 Phase 1 Step 4 MUST 根据环境分支：

- Claude Code 环境：创建 `.claude/CLAUDE.md`（当前行为）
- OpenCode 环境：创建 `./AGENTS.md`（已有 Step 5 处理，Step 4 需加条件跳过）

### R3: Config YAML 注释格式无关化 (SHOULD)

`_rewrite_yaml()` 和 `generate_default_yaml()` 中的注释 SHOULD 更新为通用描述：

```
# 当前: "# Agents — AI role definitions deployed to ~/.claude/agents/"
# 改为: "# Agents — AI role definitions"
```

### R4: 源码文档字符串更新 (MAY)

`skills.py` 中的 "Classic deployment: `~/.claude/skills/...`" 等文档字符串 MAY 更新为包含两种路径的描述。

## Acceptance Criteria

### AC1: OpenCode command 包含 model

- **Given** `pactkit init --format opencode`
- **When** 读取 `~/.config/opencode/commands/project-act.md`
- **Then** frontmatter 包含 `model:` 字段

### AC2: Plan command 不设 model

- **Given** `pactkit init --format opencode`
- **When** 读取 `~/.config/opencode/commands/project-plan.md`
- **Then** frontmatter 不包含 `model:` 字段（继承主模型）

### AC3: Classic format 无 model 字段

- **Given** `pactkit init --format classic`
- **When** 读取 command 文件
- **Then** frontmatter 不包含 `model:` 字段

### AC4: project-init 条件分支

- **Given** OpenCode 环境
- **When** `/project-init` playbook 中 Step 4
- **Then** 跳过 CLAUDE.md 创建
- **And** 由 Step 5 创建 `./AGENTS.md`

### AC5: YAML 注释无 ~/.claude/

- **Given** 运行 `pactkit init`
- **When** 读取生成的 pactkit.yaml
- **Then** 注释中不包含 `~/.claude/`

### AC6: 用户可覆盖 command model

- **Given** `pactkit.yaml` 中 `command_models.project-act: opus`
- **When** OpenCode 部署
- **Then** `project-act.md` frontmatter 的 model 为 opus 对应的 provider model ID

## Target Call Chain

```
# Command model 路由
pactkit init --format opencode
→ _deploy_opencode()
  → _deploy_commands(opencode_format=True)
    → _convert_command_frontmatter_opencode(content, cmd_name, config)
      ├── 替换 allowed-tools → agent: build (已有)
      ├── 读取 command_models 配置
      ├── 查找 model 简称 → provider model ID 映射
      └── 添加 model: provider/model-id

# project-init 条件分支
/project-init Phase 1 Step 4:
→ 检测环境（.claude/ vs .opencode/）
→ Claude Code → 创建 .claude/CLAUDE.md
→ OpenCode → 跳过 CLAUDE.md，由 Step 5 创建 AGENTS.md
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/config.py` | 添加 `command_models` 到默认 schema | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | `_resolve_opencode_model_id()`: model 简称→provider model ID 映射 | None | Medium |
| 3 | `src/pactkit/generators/deployer.py` | `_convert_command_frontmatter_opencode()`: 添加 model 字段 | Step 1, 2 | Medium |
| 4 | `src/pactkit/generators/deployer.py` | `_deploy_commands()`: 传递 cmd_name 和 config | Step 3 | Low |
| 5 | `src/pactkit/prompts/commands.py:615` | `/project-init` Step 4: 条件分支 CLAUDE.md vs AGENTS.md | None | Low |
| 6 | `src/pactkit/config.py` | `_rewrite_yaml()`/`generate_default_yaml()`: 注释去掉 `~/.claude/` | None | Low |
| 7 | `src/pactkit/prompts/skills.py` | 文档字符串更新 | None | Low |
| 8 | `tests/unit/test_story073_*.py` | AC1-AC6 测试 | Step 1-7 | Low |

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

- `opencode.json` 中的 `command` 配置（OpenCode 原生，不由 PactKit 管理）
- 运行时动态模型切换（由用户通过 `/models` 手动操作）
- workflow 文件的 model 路由（`project-sprint` 等 workflow 是 Claude Code 专有的 multi-agent 编排，OpenCode 不支持）
- deployer.py 中非 playbook 路径的 `.claude/` 引用（classic format 专有代码，保持原样）
