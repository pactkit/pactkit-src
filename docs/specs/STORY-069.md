# STORY-069: OpenCode Deployment Format Support

| Field | Value |
|-------|-------|
| ID | STORY-069 |
| Status | Draft |
| Priority | P1 |
| Release | 1.6.9 |

---

## Background

公司即将禁止使用 Claude Code，需要支持 OpenCode 作为替代方案。OpenCode (anomalyco/opencode) 是一个开源的 AI 编程助手，支持多种 LLM 提供商（包括 Gemini），并且**原生兼容 Claude Code 的配置文件**（CLAUDE.md, .claude/skills/）。

本 Story 为 PactKit 添加 `--format opencode` 部署模式，使 PactKit 能够生成 OpenCode 原生格式的配置文件，同时保留所有核心功能：
- 项目指令 (AGENTS.md)
- Agents (自定义角色)
- Commands (斜杠命令)
- Skills (可执行技能)
- Rules (规则模块，inline 到 AGENTS.md)
- MCP 服务器配置
- Sprint Board 和 Story 管理工作流

## Requirements

### R1: 新增 `--format opencode` 部署模式 (MUST)

`pactkit init --format opencode` MUST 生成 OpenCode 原生格式的配置文件。

### R2: 全局部署 — `~/.config/opencode/` (MUST)

全局部署 MUST 写入以下目录结构：
```
~/.config/opencode/
├── opencode.json         # 全局配置 (仅结构模板，不含 API key)
├── AGENTS.md             # 全局指令 (inline rules)
├── agents/               # agent 定义
│   ├── system-architect.md
│   ├── senior-developer.md
│   └── ...
├── commands/             # 命令定义
│   ├── project-plan.md
│   ├── project-act.md
│   └── ...
└── skills/               # 技能定义
    ├── pactkit-visualize/
    │   ├── SKILL.md
    │   └── scripts/visualize.py
    ├── pactkit-board/
    └── ...
```

### R3: 项目级部署 — `.opencode/` + 项目根 (MUST)

项目级部署 MUST 写入：
```
./                        # 项目根目录
├── opencode.json         # 项目配置
├── AGENTS.md             # 项目指令
└── .opencode/            # 项目专用目录
    ├── agents/
    ├── commands/
    └── skills/
```

### R4: AGENTS.md 生成 — inline rules (MUST)

OpenCode 不支持 `@import` 语法，AGENTS.md MUST 将所有 rules 内联到一个文件中，格式与 `_deploy_claude_md_inline()` 一致。

### R5: Skills 路径重写 (MUST)

Skills 中的 `~/.claude/skills` 路径 MUST 重写为 `~/.config/opencode/skills`。

### R6: opencode.json 生成 (MUST)

opencode.json MUST 包含以下结构：
```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md", "docs/product/context.md"],
  "agent": {
    "build": { "model": "inherit" },
    "plan": { "model": "inherit" }
  }
}
```

注意：`provider` 配置由用户自行管理，PactKit 不生成 API key 相关配置。

### R7: Agent 格式转换 (MUST)

Claude Code agent 格式 MUST 转换为 OpenCode 格式：

**Claude Code 格式**:
```yaml
---
name: senior-developer
description: "..."
tools: [Read, Write, Edit, Bash]
model: sonnet
---
```

**OpenCode 格式**:
```yaml
---
description: "..."
mode: subagent
model: anthropic/claude-sonnet-4-20250514
tools:
  write: true
  edit: true
  bash: true
---
```

### R8: Command 格式转换 (MUST)

Claude Code command 格式 MUST 转换为 OpenCode 格式：

**Claude Code 格式**:
```yaml
---
description: "Analyze requirements"
allowed-tools: [Read, Write]
---
```

**OpenCode 格式**:
```yaml
---
description: "Analyze requirements"
agent: build
---
```

### R9: MCP 配置提示 (SHOULD)

部署完成后 SHOULD 打印 MCP 配置提示：
```
📦 Configure MCP servers in opencode.json:
{
  "mcp": {
    "context7": { "type": "stdio", "command": "npx", "args": ["context7"] }
  }
}
```

### R10: 兼容性保留 (MUST)

OpenCode 原生支持读取 CLAUDE.md 和 .claude/skills/，但 `--format opencode` 模式 MUST 生成 OpenCode 原生格式（AGENTS.md, .opencode/），不依赖兼容层。

### R11: CLI 参数更新 (MUST)

`pactkit init --format` 的 help 文本 MUST 更新为包含 `opencode` 选项：
```
--format {classic,plugin,marketplace,opencode}
```

## Acceptance Criteria

### AC1: 全局部署生成正确目录结构

- **Given** 用户运行 `pactkit init --format opencode -t ~/.config/opencode`
- **When** 部署完成
- **Then** `~/.config/opencode/` 包含 AGENTS.md, agents/, commands/, skills/ 子目录
- **And** 所有 9 个 agents、11 个 commands、10 个 skills 均已部署

### AC2: 项目级部署生成正确目录结构

- **Given** 用户在项目目录运行 `pactkit init --format opencode`
- **When** 部署完成
- **Then** 项目根目录包含 `opencode.json` 和 `AGENTS.md`
- **And** `.opencode/` 目录包含 agents/, commands/, skills/ 子目录

### AC3: AGENTS.md 包含所有 rules 内联

- **Given** 部署完成
- **When** 读取 `AGENTS.md`
- **Then** 文件包含所有 7 个 rule 模块的完整内容
- **And** 不包含 `@~/.claude/rules/` 引用

### AC4: Skills 路径正确重写

- **Given** 部署完成
- **When** 读取任意 SKILL.md 或 agent/command 文件
- **Then** 所有路径引用为 `~/.config/opencode/skills` 而非 `~/.claude/skills`

### AC5: opencode.json 结构正确

- **Given** 部署完成
- **When** 读取 `opencode.json`
- **Then** JSON 有效且包含 `$schema`, `instructions`, `agent` 字段
- **And** 不包含 `provider` 或 `apiKey` 字段

### AC6: CLI --format opencode 可用

- **Given** 用户运行 `pactkit init --help`
- **When** 查看 `--format` 参数
- **Then** 选项列表包含 `opencode`

## Target Call Chain

```
User → pactkit init --format opencode
     → cli.py:main() → init_command()
     → deployer.py:deploy(format='opencode')
     → _deploy_opencode()
         ├── _deploy_skills() with OPENCODE_SKILLS_PREFIX
         ├── _deploy_agents_md_inline() — inline all rules
         ├── _deploy_agents() with opencode format
         ├── _deploy_commands() with opencode format
         ├── _deploy_opencode_json()
         └── _print_mcp_recommendations_opencode()
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/config.py` | 无需修改 — VALID_FORMATS 在 deployer.py | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | 添加 `'opencode'` 到 VALID_FORMATS | None | Low |
| 3 | `src/pactkit/generators/deployer.py` | 添加 OPENCODE_SKILLS_PREFIX 常量 | None | Low |
| 4 | `src/pactkit/generators/deployer.py` | 添加 `_deploy_opencode()` 函数 | Step 2,3 | Medium |
| 5 | `src/pactkit/generators/deployer.py` | 添加 `_deploy_opencode_json()` 函数 | Step 4 | Low |
| 6 | `src/pactkit/generators/deployer.py` | 添加 `_deploy_agents_md_inline()` — 复用 `_deploy_claude_md_inline` 逻辑 | Step 4 | Low |
| 7 | `src/pactkit/generators/deployer.py` | 修改 `deploy()` 路由到 opencode | Step 4 | Low |
| 8 | `src/pactkit/cli.py` | 更新 --format choices 包含 opencode | Step 7 | Low |
| 9 | `tests/unit/test_story069_opencode_format.py` | 添加 AC1-AC6 测试 | Step 8 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (deployer.py, cli.py) |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend rendering |
| SEC-5 | No | No auth handling — API keys explicitly excluded from generation |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error message exposure |
| SEC-8 | No | No dependency changes |

## Out of Scope

- 自动生成 `provider` 或 API key 配置（用户自行管理）
- OpenCode TUI 配置（`tui.json`）生成
- OpenCode 桌面版支持
- 从 Claude Code 到 OpenCode 的自动迁移工具
- OpenCode 特有功能（LSP、subagent routing）的配置

## Appendix: OpenCode vs Claude Code Structure Mapping

| Claude Code | OpenCode | Notes |
|-------------|----------|-------|
| `~/.claude/` | `~/.config/opencode/` | Global root |
| `~/.claude/CLAUDE.md` | `~/.config/opencode/AGENTS.md` | Global instructions |
| `~/.claude/rules/*.md` | (inline in AGENTS.md) | No separate rules dir |
| `~/.claude/agents/*.md` | `~/.config/opencode/agents/*.md` | Same structure |
| `~/.claude/commands/*.md` | `~/.config/opencode/commands/*.md` | Same structure |
| `~/.claude/skills/*/SKILL.md` | `~/.config/opencode/skills/*/SKILL.md` | Same structure |
| `.claude/pactkit.yaml` | `opencode.json` | Project config (JSON) |
| `.claude/CLAUDE.md` | `AGENTS.md` | Project instructions |
| `.claude/CLAUDE.local.md` | (user section in AGENTS.md) | User customization |
