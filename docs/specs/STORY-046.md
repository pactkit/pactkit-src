# STORY-046: Multi-Agent Compatibility Layer

| Field     | Value |
|-----------|-------|
| ID        | STORY-046 |
| Status    | Draft |
| Priority  | Low |
| Release   | 1.4.0 |
| Author    | System Architect |
| Source    | Gap Analysis: OpenSpec 20+ agents, SpecKit 16+ agents |

## Background

PactKit 目前绑定 Claude Code 的 slash command 机制（`/project-plan`, `/project-act` 等），command playbooks 以 Python string 形式存储在 `src/pactkit/prompts/commands.py` 中，通过 `deployer.py` 部署为 `.claude/commands/*.md` 文件。

这意味着非 Claude Code 的 AI Agent（Cursor, GitHub Copilot, Windsurf, Gemini CLI 等）无法使用 PactKit 的 PDCA 工作流。OpenSpec 通过 profile system 支持 20+ agents，SpecKit 通过 `--ai-commands-dir` 支持 16+ agents。

这是一个战略级 gap——SpecKit 72.1k stars 证明了 SDD 的市场规模存在，但 PactKit 目前只能触达 Claude Code 用户群。

## Requirements

### R1: Agent Adapter Architecture (MUST)

设计适配器层，将 PactKit command playbooks 转换为不同 Agent 的原生格式：

| Agent | Native Format | Directory Convention |
|-------|---------------|---------------------|
| Claude Code | `.claude/commands/*.md` (frontmatter + markdown) | `.claude/` |
| Cursor | `.cursor/rules/*.mdc` (markdown with metadata) | `.cursor/rules/` |
| GitHub Copilot | `.github/copilot-instructions.md` (single file) | `.github/` |
| Windsurf | `.windsurfrules` (single file) | project root |
| Generic | `.ai/commands/*.md` (plain markdown) | `.ai/` |

### R2: CLI Flag (MUST)

扩展 `pactkit init` 和 `pactkit update` 支持 `--agent` flag：
```bash
pactkit init --agent claude      # current behavior (default)
pactkit init --agent cursor      # deploy to .cursor/rules/
pactkit init --agent copilot     # deploy to .github/
pactkit init --agent all         # deploy to all supported formats
```

### R3: Format Transformer (MUST)

实现 `src/pactkit/generators/adapter.py` 提供格式转换：
- 输入：PactKit 内部的 command playbook string
- 输出：目标 Agent 格式的文件内容
- 转换逻辑：保留核心工作流语义，适配格式差异（frontmatter → metadata、slash command → prompt instruction）

### R4: pactkit.yaml 配置 (SHOULD)

在 `pactkit.yaml` 中新增 `agents` section：
```yaml
agents:
  - claude     # always included
  - cursor
  - copilot
```

### R5: 核心 Playbook 不变 (MUST)

适配器层为 **add-on**，不修改现有 Claude Code playbooks 的内容或结构。Claude Code 仍然是 first-class 支持。

## Acceptance Criteria

### AC1: Cursor 格式部署
**Given** 运行 `pactkit init --agent cursor`
**When** 部署完成
**Then** `.cursor/rules/` 目录包含转换后的 command 文件
**And** 文件格式符合 Cursor rules 约定

### AC2: 默认行为不变
**Given** 运行 `pactkit init`（无 --agent flag）
**When** 部署完成
**Then** 仅部署 `.claude/` 目录
**And** 行为与当前版本完全一致

### AC3: Multi-agent 部署
**Given** 运行 `pactkit init --agent all`
**When** 部署完成
**Then** 所有支持的 Agent 格式目录都包含对应文件

## Out of Scope

- 实现每个 Agent 的原生 skill/tool 机制（仅做 command playbook 的格式适配）
- 保证在非 Claude Code Agent 上的功能等价性（部分 PactKit 特性依赖 Claude Code 的 tool 系统）
- MCP 集成在其他 Agent 上的适配
