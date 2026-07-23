# STORY-slim-134: remove model field from command frontmatter

| Field | Value |
|-------|-------|
| ID | STORY-slim-134 |
| Status | Done |
| Priority | P1 |
| Release | 2.17.0 |

## Background

Claude Code 在读取 command frontmatter 中的 `model: sonnet` / `model: opus` 字段时，会将 alias 解析成 Anthropic 官方最新的 model ID（如 `us.anthropic.claude-sonnet-4-5-20250929-v1:0`）。但企业用户通过 Bedrock 代理（如 genai-nexus）接入时，其部署往往只启用了较旧版本的模型，导致 VS Code 插件环境下所有 `/project-*` 命令都因模型不可用而报错。

移除 frontmatter 中的 `model:` 字段后，command 会继承用户当前 session 的默认模型（由用户的 `ANTHROPIC_DEFAULT_SONNET_MODEL` 等环境变量或 Claude Code 设置控制），不再主动切换，从而避免 Bedrock 兼容性问题。

## Requirements

### R1: 移除 prompts/commands.py 中的 model 字段 (MUST)

删除 `src/pactkit/prompts/commands.py` 中所有 command 字符串 frontmatter 里的 `model:` 行。涉及 9 处（`model: opus` × 2，`model: sonnet` × 7）。

### R2: 移除 prompts/workflows.py 中的 model 字段 (MUST)

删除 `src/pactkit/prompts/workflows.py` 中所有 command 字符串 frontmatter 里的 `model:` 行。涉及 4 处（`model: opus` × 1，`model: sonnet` × 3）。

### R3: 同步更新 pactkit-plugin/commands/ (MUST)

执行 `pactkit deploy --format plugin` 重新生成 `pactkit-plugin/commands/*.md`，确保 generated artifact 与 source 一致。

### R4: 不影响 sprint 内联 model 引用 (MUST NOT)

`workflows.py` 中 sprint 命令正文里对 `model: sonnet` 的**文本说明**（如 `A1 model: opus`）不得修改——这些是给 LLM 读的 prompt 指令，不是 frontmatter 字段。

## Acceptance Criteria

### AC1: commands.py 无 model 字段 (R1)

- **Given** `src/pactkit/prompts/commands.py` 中各 command 字符串的 YAML frontmatter
- **When** 检查每个 `---` 块内的字段列表
- **Then** 不存在任何 `model:` 行；`description:` 和 `allowed-tools:` 字段保持不变

### AC2: workflows.py 无 model 字段 (R2)

- **Given** `src/pactkit/prompts/workflows.py` 中各 command 字符串的 YAML frontmatter
- **When** 检查每个 `---` 块内的字段列表
- **Then** 不存在任何 `model:` 行；正文中对模型的文字引用保持不变

### AC3: plugin artifact 与 source 一致 (R3)

- **Given** R1/R2 修改完成后执行 `pactkit deploy --format plugin`
- **When** 检查 `pactkit-plugin/commands/*.md` 各文件的 frontmatter
- **Then** 所有文件 frontmatter 中均无 `model:` 字段

### AC5: sprint 正文模型引用不变 (R4)

- **Given** R1/R2 修改完成
- **When** 检查 `workflows.py` 中 sprint 命令正文（非 frontmatter）的内容
- **Then** `A1 (system-architect, model: opus)`、`A2 (senior-developer, model: sonnet)` 等文字说明保持不变

### AC4: 测试套件全通过 (R1-R4)

- **Given** 修改完成
- **When** 运行 `.venv/bin/pytest tests/ -v`
- **Then** 所有测试通过，无新失败

## Target Call Chain

```
src/pactkit/prompts/commands.py (COMMANDS_CONTENT 字符串常量，含 model: 字段)
src/pactkit/prompts/workflows.py (SPRINT_PROMPT / HOTFIX_PROMPT 等，含 model: 字段)
  → deployer._deploy_commands() — 原样写出字符串到文件
  → pactkit-plugin/commands/*.md (generated artifact)
  → Claude Code frontmatter 解析 → model alias → Bedrock model ID
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/commands.py` | 删除所有 frontmatter 中的 `model:` 行（9 处） | None | Low |
| 2 | `src/pactkit/prompts/workflows.py` | 删除所有 frontmatter 中的 `model:` 行（4 处） | Step 1 | Low |
| 3 | 运行测试 | `.venv/bin/pytest tests/ -v` 确保无回归 | Step 1-2 | Low |
| 4 | `pactkit-plugin/commands/` | `pactkit deploy --format plugin` 重新生成 artifact | Step 1-2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | 仅删除字符串字段，无新代码逻辑引入 |
| SEC-2 | N/A | 无输入处理变更 |
| SEC-3 | N/A | 无数据库相关 |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无认证/会话逻辑变更 |
| SEC-6 | N/A | 无 API/路由变更 |
| SEC-7 | N/A | 无错误处理变更 |
| SEC-8 | N/A | 无依赖变更 |

## Out of Scope

- 不修改 `deployer.py` 中的 frontmatter 处理逻辑
- 不为用户提供 model fallback 配置机制（该需求已明确放弃）
- 不修改 sprint/hotfix 正文中对模型的文字说明（R4）
