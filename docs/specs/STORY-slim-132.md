# STORY-slim-132: Decouple codegraph commands from hardcoded prompt

| Field | Value |
|-------|-------|
| ID | STORY-slim-132 |
| Status | Done |
| Priority | P1 |
| Release | 2.16.0 |

## Background

PactKit 在 `prompts/skills.py`、`generators/deployer.py`、全局 `~/.claude/CLAUDE.md` 中硬编码了 codegraph CLI 的具体命令列表（callers、callees、impact、query、explore 等）。每次 codegraph 升级改命令签名（如 1.1.x 中 `context` → `explore`），pactkit 必须同步修改多处，违反 DRY 且产生维护耦合。

方案 B：将命令列表替换为一条通用指令（"run `codegraph --help` for available commands"），让 AI 在运行时按需查询最新命令。

## Requirements

### R1: Remove hardcoded codegraph command list from prompt templates (MUST)

从 `skills.py` 的 "Direct codegraph CLI" 代码块中移除具体命令列表，替换为 `codegraph --help` 指引。

### R2: Remove hardcoded codegraph command list from deployer CLAUDE.md generator (MUST)

从 `deployer.py` 的 codegraph section 生成逻辑中移除命令枚举，替换为通用指引。

### R3: Update global CLAUDE.md Codegraph Priority section (MUST)

将 `~/.claude/CLAUDE.md` 中的命令列表替换为通用指引。

### R4: Remove hardcoded MCP tool name list (SHOULD)

从 `skills.py:108` 中移除具体 MCP 工具名列表——MCP 工具通过 ToolSearch 动态发现，无需硬编码。

### R5: Retain pactkit query commands (MUST NOT remove)

`pactkit query --callers/--callees/--chain` 是 pactkit 自身的 CLI 命令，不依赖 codegraph 命令签名，MUST NOT 移除。

## Acceptance Criteria

### AC1: skills.py no longer contains codegraph command examples (R1, R4)

- **Given** skills.py 的 codegraph mode section
- **When** 读取 "Direct codegraph CLI" 代码块内容
- **Then** 只包含 `codegraph --help` 指引，不包含 `codegraph callers`/`callees`/`impact`/`query`/`explore`/`affected`/`status` 等具体命令

### AC2: deployer generates slim codegraph section (R2)

- **Given** 一个存在 `.codegraph/` 目录的项目
- **When** 运行 `pactkit init` 或 `pactkit update`
- **Then** 生成的 CLAUDE.md codegraph section 只包含通用指引，不枚举具体命令

### AC3: pactkit query commands preserved (R5)

- **Given** skills.py 的 codegraph mode section
- **When** 读取 "Unified pactkit query" 代码块
- **Then** `pactkit query --callers/--callees/--chain` 示例仍然存在

### AC4: Global CLAUDE.md updated (R3)

- **Given** `~/.claude/CLAUDE.md` 的 Codegraph Priority section
- **When** 读取该 section
- **Then** 只包含通用指引 + `codegraph --help`，不枚举命令

## Target Call Chain

```
pactkit init/update
  → deployer._generate_project_claude_md()
    → deployer._generate_claude_md_content()  [L1469: if .codegraph exists]
      → writes CLAUDE.md managed block

skills.py (static prompt template, injected at trace/plan time)
  → "Direct codegraph CLI" block [L98-105]
  → MCP tools line [L108]
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/skills.py` | 替换 L98-108 codegraph 命令块为 help 指引 | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | 替换 L1472-1478 命令列表为通用指引 | None | Low |
| 3 | `~/.claude/CLAUDE.md` | 替换 Codegraph Priority 命令列表 | None | Low |
| 4 | `.claude/CLAUDE.md` | 由 Step 2 的 deployer 变更自动覆盖（下次 update） | Step 2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 ~ SEC-8 | N/A | docs/prompt-only change, no code execution paths affected |

## Out of Scope

- 不动 `pactkit query` 命令（pactkit 自身 CLI，不依赖 codegraph 签名）
- 不做"生成时动态捕获"（方案 A）——用户明确选择方案 B
- 不抽 codegraph 命令数据源常量——方案 B 下无需此抽象
