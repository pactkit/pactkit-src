# STORY-slim-009: Lazy Rule Loading — Split instructions into Always-Load Core + On-Demand @Reference

| Field | Value |
|-------|-------|
| ID | STORY-slim-009 |
| Status | Draft |
| Priority | P0 |
| Release | 2.1.1 |
| Depends | STORY-slim-005 (FormatProfile) |

## Background

### 问题

OpenCode 的 `instructions: ["rules/*.md"]` 把所有 10 个 rules 文件（21KB, ~5300 tokens）全量注入到**每轮对话的 system prompt** 中。加上 memory blocks（6KB）和 AGENTS.md，每轮固定开销达 **~7200 tokens** — 是 Claude Code（~3900 tokens）的 **1.85 倍**。

Claude Code 使用 `@import` 语法实现懒加载 — 引用的文件只在需要时展开。OpenCode 没有原生 `@import`，但官方文档（opencode.ai/docs/zh-cn/rules/）提供了等效机制：

> 在 AGENTS.md 中使用 `@rules/xxx.md` 引用，加上指令 "use Read tool to load on a need-to-know basis"，实现按需懒加载。

### 方案

将 rules 分为两层：

| Layer | 加载方式 | 文件 | Token 开销 |
|-------|---------|------|:---:|
| **Always-Load** | `instructions` 数组（全量注入） | 01-core, 02-hierarchy, 09-credential-safety | ~1400 |
| **On-Demand** | AGENTS.md 中 `@` 引用（AI 按需 Read） | 其余 7 个 rules | 0 (按需) |

效果：每轮固定开销从 ~7200 降到 **~2800 tokens**（-62%）。

### Always-Load 选取标准

| 标准 | 说明 |
|------|------|
| **安全相关** | 违反后果严重，不能依赖 AI 判断"是否需要读" |
| **每次对话都用** | session context 加载、visual-first、TDD — 每个任务都涉及 |
| **小体积** | 控制 always-load 层在 6KB 以内 |

## Requirements

### R1: RULES_CORE_FILES + RULES_ONDEMAND_FILES 分类 (MUST)

在 `profiles.py` 或 `rules.py` 中定义两个分组：

```python
# Always loaded via instructions (security + core workflow)
RULES_CORE_FILES = {
    "core": "01-core-protocol.md",
    "hierarchy": "02-hierarchy-of-truth.md",
    "credential": "09-credential-safety.md",
}

# Loaded on-demand via @reference in AGENTS.md
RULES_ONDEMAND_FILES = {
    "atlas": "03-file-atlas.md",
    "routing": "04-routing-table.md",
    "workflow": "05-workflow-conventions.md",
    "mcp": "06-mcp-integration.md",
    "shared": "07-shared-protocols.md",
    "architecture": "08-architecture-principles.md",
    "retrieval": "10-retrieval-routing.md",
}

# Full set (backward compat, used by deployer for file deployment)
RULES_FILES = {**RULES_CORE_FILES, **RULES_ONDEMAND_FILES}
```

Note: `09-credential-safety.md` 和 `10-retrieval-routing.md` 是用户文件（非 PactKit managed），但 09 因为安全性必须 always-load。10 是 on-demand。

### R2: _update_global_opencode_json() 写入 core-only instructions (MUST)

当前：
```python
config["instructions"] = ["rules/*.md"]  # 全量 glob
```

改为：
```python
# Only load core rules via instructions (always in context)
existing = config.get("instructions", [])
# Remove old glob if present
existing = [i for i in existing if i != "rules/*.md"]
# Add core rules (if not already present)
for filename in sorted(RULES_CORE_FILES.values()):
    path = f"rules/{filename}"
    if path not in existing:
        existing.append(path)
config["instructions"] = existing
```

这确保：
- 旧的 `rules/*.md` glob 被替换
- 只有 core rules 进入 instructions
- 用户已有的其他 instructions 保留（merge 策略）

### R3: _deploy_agents_md_inline() 生成 @引用索引 (MUST)

当前 AGENTS.md 只有 Quick Reference。改为包含 on-demand rules 的 `@` 引用：

```markdown
# PactKit Global Constitution (v{VERSION} Modular)

Core rules (01-core, 02-hierarchy, 09-credential-safety) are always loaded via `instructions`.

## On-Demand Rules

CRITICAL: When you encounter a file reference below (e.g., @rules/xxx.md), use your Read tool to load it on a need-to-know basis. Do NOT preemptively load all references — use lazy loading based on actual need.

- Architecture decisions, SOLID/DRY patterns: @rules/08-architecture-principles.md
- Agent/command routing table: @rules/04-routing-table.md
- MCP server integration guide: @rules/06-mcp-integration.md
- PDCA workflow conventions: @rules/05-workflow-conventions.md
- PDCA shared protocols (test mapping, visualize, context.md format): @rules/07-shared-protocols.md
- File atlas (project file locations): @rules/03-file-atlas.md
- Information retrieval routing (Context7 vs WebFetch): @rules/10-retrieval-routing.md

## Quick Reference

- **Specs** (`docs/specs/`) are the source of truth
- **Sprint Board**: `docs/product/sprint_board.md`
- **Architecture**: `docs/architecture/graphs/`
- **Commands**: Type `/` followed by command name (e.g., `/project-plan`)

> **TIP**: Run `/project-init` to set up project governance and enable cross-session context.
```

引用列表从 `RULES_ONDEMAND_FILES` 自动生成（DRY）。每个引用附带一行描述，帮助 AI 判断"什么时候需要读这个文件"。

### R4: CLAUDE_MD_TEMPLATE 不受影响 (MUST)

Classic 模式的 `CLAUDE_MD_TEMPLATE` 继续使用 `@import` 全量引用所有 rules — Claude Code 的 `@import` 本身就是懒加载的。

### R5: 用户自定义 rules 自动归入 on-demand (SHOULD)

用户在 `rules/` 目录下新增的 `.md` 文件（如 `09-credential-safety.md`, `10-retrieval-routing.md`）不在 `RULES_CORE_FILES` 中，不会被加入 `instructions`。

AGENTS.md 中可以加一段通用说明：
```markdown
Additional rules in `rules/` directory (user-managed) are available via Read tool.
```

### R6: pactkit.yaml 支持 core_rules 自定义 (SHOULD)

允许用户通过 `pactkit.yaml` 自定义哪些 rules 是 always-load：

```yaml
core_rules:
  - 01-core-protocol
  - 02-hierarchy-of-truth
  - 09-credential-safety
```

默认使用 `RULES_CORE_FILES`，用户可以 override。

## Acceptance Criteria

### AC1: instructions 只包含 core rules

- **Given** 运行 `pactkit update --format opencode`
- **When** 读取 `~/.config/opencode/opencode.json`
- **Then** `instructions` 数组只包含 `rules/01-core-protocol.md`, `rules/02-hierarchy-of-truth.md`, `rules/09-credential-safety.md`
- **And** 不包含 `rules/*.md` glob

### AC2: AGENTS.md 包含 @引用索引

- **Given** 运行 `pactkit update --format opencode`
- **When** 读取 `~/.config/opencode/AGENTS.md`
- **Then** 包含 `@rules/08-architecture-principles.md` 等 7 个 @引用
- **And** 包含 "use your Read tool to load it on a need-to-know basis"

### AC3: 所有 rules 文件仍然部署到 rules/ 目录

- **Given** 运行 `pactkit update --format opencode`
- **When** 检查 `~/.config/opencode/rules/`
- **Then** 仍然有 8 个文件（01~08），与之前一致
- **And** 用户文件（09, 10）不受影响

### AC4: Classic 模式不受影响

- **Given** 运行 `pactkit init --format classic -t /tmp/test`
- **When** 检查 `CLAUDE.md`
- **Then** 仍然包含所有 `@~/.claude/rules/*.md` 引用（Claude Code 的 @import 本身是懒加载）

### AC5: 用户已有 instructions 保留

- **Given** `opencode.json` 已有 `instructions: ["CONTRIBUTING.md", "rules/*.md"]`
- **When** 运行 `pactkit update --format opencode`
- **Then** `instructions` 变为 `["CONTRIBUTING.md", "rules/01-core-protocol.md", "rules/02-hierarchy-of-truth.md", "rules/09-credential-safety.md"]`
- **And** `CONTRIBUTING.md` 被保留，`rules/*.md` glob 被替换

### AC6: Token 开销验证

- **Given** 部署后的 system prompt 组件
- **When** 计算 instructions + AGENTS.md 总大小
- **Then** < 10KB (之前 21KB + 0.3KB = 21.3KB)

### AC7: 全量测试通过

- **Given** 修改后的代码
- **When** 运行 `pytest tests/ -v`
- **Then** 2307+ 通过，0 失败

## Implementation Steps

| Step | File | Action | Risk |
|------|------|--------|------|
| 1 | `src/pactkit/prompts/rules.py` | 拆分 `RULES_FILES` 为 `RULES_CORE_FILES` + `RULES_ONDEMAND_FILES` | Low |
| 2 | `src/pactkit/generators/deployer.py` | `_update_global_opencode_json()` 写入 core-only instructions + merge 用户已有 | Medium |
| 3 | `src/pactkit/generators/deployer.py` | `_deploy_agents_md_inline()` 生成 @引用索引 | Medium |
| 4 | `tests/` | 新增测试覆盖 AC1-AC7 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | credential-safety rule MUST be in always-load layer |
| SEC-2~8 | No | 配置变更，无业务逻辑 |

## Out of Scope

- Claude Code 的 `@import` 机制改动（已经是懒加载）
- OpenCode 内核的 instructions 加载机制（无法修改）
- Plugin 加载优化（agent-memory onnxruntime 问题是独立问题）
