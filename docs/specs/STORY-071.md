# STORY-071: OpenCode Config Parity — Rules Modularization, Permission, MCP

| Field | Value |
|-------|-------|
| ID | STORY-071 |
| Status | Draft |
| Priority | P1 |
| Release | 1.6.9 |

## Background

从 Claude Code 迁移到 OpenCode 后，发现三个配置对等性缺口：

### 问题 1: `.opencode/pactkit.yaml` 不存在

**结论：设计如此，不是遗漏。**

- `.claude/pactkit.yaml` 是 PactKit 部署工具的内部配置，告诉 `pactkit init` 部署哪些组件
- OpenCode 不认识 `pactkit.yaml`，它只认 `opencode.json`
- 项目级 `opencode.json` 由 `/project-init` playbook 生成（BUG-035 设计）
- `.opencode/` 目录是 OpenCode 的项目扩展目录（agents/commands/skills），类似 `.claude/`
- PactKit 的配置文件仍然保留在 `.claude/pactkit.yaml`，与 OpenCode 运行时配置互不干扰

**无需代码修改，但需要在 `/project-init` playbook 中明确说明这一点。**

### 问题 2: `~/.claude/settings.json` 配置映射

Claude Code `settings.json` 包含安全关键配置：

| Claude Code | OpenCode 对等 | 可映射? |
|---|---|---|
| `permissions.deny` (危险命令黑名单) | `permission.bash: { "rm -rf /*": "deny" }` | Yes |
| `defaultMode: bypassPermissions` | `permission: "allow"` | Yes |
| `allowAllEdits: true` | `permission.edit: "allow"` | Yes |
| `allowAllReads: true` | `permission.read: "allow"` | Yes (默认) |
| `env` 变量 | 无直接对等 | No |
| `hooks` | OpenCode 无对应 | No |
| `statusLine` | OpenCode 无对应 | No |
| `enabledPlugins` | `plugin` 配置 | No (不同生态) |

### 问题 3: MCP 配置缺失

Claude Code `settings.local.json` 中配置了 8 个 MCP servers，但 `opencode.json` 中完全没有 `mcp` 配置。

OpenCode 的 MCP 配置格式与 Claude Code 完全不同：
- Claude Code: `enabledMcpjsonServers: ["context7"]` (引用 `~/.claude/settings.json` 中的定义)
- OpenCode: `mcp: { "context7": { "type": "remote", "url": "https://mcp.context7.com/mcp" } }` (自包含定义)

## Requirements

### R1: `_deploy_opencode_json` 生成 permission 配置 (MUST)

`_deploy_opencode_json()` helper 函数生成的 `opencode.json` MUST 包含 `permission` 配置，映射 Claude Code 的安全防护语义：

```json
{
  "permission": {
    "edit": "allow",
    "bash": {
      "*": "allow",
      "rm -rf /*": "deny",
      "rm -rf /Users/*": "deny",
      "rm -rf /System/*": "deny",
      "sudo rm *": "deny",
      "sudo mkfs *": "deny",
      "curl * | sh": "deny",
      "wget * | sh": "deny"
    },
    "read": {
      "*": "allow",
      "*.env": "deny",
      "*.env.*": "deny",
      "*.env.example": "allow"
    }
  }
}
```

### R2: `_deploy_opencode_json` 生成 MCP 配置模板 (MUST)

`_deploy_opencode_json()` MUST 生成 `mcp` 配置，包含 PactKit 推荐的 MCP servers：

```json
{
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

注意：
- 仅包含不需要 API key 的公共 MCP servers
- Memory MCP 和 Playwright MCP 是本地类型，需要 npx 命令，SHOULD 以注释形式提供示例
- 由于 JSON 不支持注释，SHOULD 在部署完成后打印配置提示

### R3: `/project-init` playbook 说明 pactkit.yaml 关系 (MUST)

`/project-init` playbook 的 OpenCode 检测部分 MUST 说明：
- `pactkit.yaml` 保留在 `.claude/` 目录（PactKit 部署工具配置）
- `opencode.json` 是 OpenCode 运行时配置（项目级）
- 两者互不干扰，PactKit 不在 `.opencode/` 下生成 `pactkit.yaml`

### R4: MCP 推荐打印更新 (SHOULD)

`_print_mcp_recommendations_opencode()` SHOULD 更新打印内容，包含更完整的配置示例，覆盖 local 和 remote 两种类型。

### R5: opencode.json 保留用户已有配置 (MUST)

`_deploy_opencode_json()` 在生成配置时 MUST NOT 覆盖用户已有的 `provider` 配置。如果 `opencode.json` 已存在，MUST 合并而非覆盖。

注意：当前 `_deploy_opencode_json()` 只被 `/project-init` playbook（prompt 指令）调用，不被代码调用。此 requirement 适用于未来可能的代码调用场景，当前实现为全新写入即可。

### R6: 全局 AGENTS.md 模块化拆分 (MUST)

当前 `_deploy_agents_md_inline()` 将所有 rules 内联到单个 `~/.config/opencode/AGENTS.md`（12KB, 273行），过于庞大。

MUST 改为模块化拆分，与 Claude Code 的 `_deploy_rules()` 对称：

**目标结构**:
```
~/.config/opencode/
├── AGENTS.md              ← 瘦身至 header + 简要说明 (< 30行)
├── rules/
│   ├── 01-core-protocol.md
│   ├── 02-hierarchy-of-truth.md
│   ├── 03-file-atlas.md
│   ├── 04-routing-table.md
│   ├── 05-workflow-conventions.md
│   ├── 06-mcp-integration.md
│   └── 07-shared-protocols.md
└── opencode.json          ← instructions 包含 "rules/*.md"
```

实现方式：
- `_deploy_opencode()` 复用已有的 `_deploy_rules()` 将 rule 文件写到 `rules/` 子目录
- `_deploy_agents_md_inline()` 改为 `_deploy_agents_md_slim()`：只写 header + TIP
- 全局 `opencode.json` MUST 在 `instructions` 中包含 `"rules/*.md"` 以加载拆分后的 rules
- 全局 `opencode.json` 写入时 MUST 保留用户已有的 `provider` 等字段（合并策略）

### R7: 全局 opencode.json 写入策略 (MUST)

`_deploy_opencode()` MUST 生成/更新全局 `~/.config/opencode/opencode.json`，包含 `instructions: ["rules/*.md"]`。

写入策略：
- 如果文件不存在：生成包含 `instructions` 字段的新文件
- 如果文件已存在：读取已有内容，仅添加/更新 `instructions` 字段，保留 `provider`、`permission`、`mcp` 等用户配置

## Acceptance Criteria

### AC1: opencode.json 包含 permission

- **Given** 调用 `_deploy_opencode_json()` 生成 opencode.json
- **When** 读取生成的 JSON 文件
- **Then** 包含 `permission` 字段
- **And** `permission.bash` 包含危险命令 deny 规则
- **And** `permission.read` 包含 `.env` 文件 deny 规则

### AC2: opencode.json 包含 MCP 模板

- **Given** 调用 `_deploy_opencode_json()` 生成 opencode.json
- **When** 读取生成的 JSON 文件
- **Then** 包含 `mcp` 字段
- **And** `mcp.context7` 存在且 type 为 remote

### AC3: opencode.json 保留已有字段

- **Given** 生成的 opencode.json
- **When** 读取 JSON 文件
- **Then** 仍然包含 `$schema`, `instructions` 字段

### AC4: project-init playbook 包含 pactkit.yaml 说明

- **Given** `/project-init` playbook 内容
- **When** 检测到 OpenCode 环境
- **Then** 打印说明：pactkit.yaml 在 `.claude/` 下，不在 `.opencode/` 下

### AC5: 经典格式无变化

- **Given** 以 classic 格式部署
- **When** 生成 CLAUDE.md 和 agents
- **Then** 行为与修改前一致（无 permission/mcp 变更）

### AC6: 全局 AGENTS.md 拆分

- **Given** 用户运行 `pactkit init --format opencode`
- **When** 部署完成
- **Then** `~/.config/opencode/rules/` 目录存在且包含 7 个 rule 文件
- **And** `~/.config/opencode/AGENTS.md` 少于 30 行

### AC7: 全局 opencode.json 包含 instructions

- **Given** 用户运行 `pactkit init --format opencode`
- **When** 读取 `~/.config/opencode/opencode.json`
- **Then** 包含 `instructions` 字段
- **And** `instructions` 数组包含 `"rules/*.md"`
- **And** 用户已有的 `provider` 配置被保留

## Target Call Chain

```
# 全局部署
pactkit init --format opencode
→ _deploy_opencode()
  ├── _deploy_rules(rules_dir, ...)            # R6: 复用已有函数写 rules/*.md
  ├── _deploy_agents_md_slim(opencode_root)    # R6: 瘦身版 AGENTS.md
  ├── _update_global_opencode_json()           # R7: merge instructions 到全局 json
  ├── _deploy_agents(opencode_format=True)     # 已有
  ├── _deploy_commands(opencode_format=True)   # 已有
  ├── _deploy_skills(...)                      # 已有
  └── _print_mcp_recommendations_opencode()    # R4: 更新打印

# 项目级初始化（由 /project-init playbook 调用）
/project-init
→ 检测 OpenCode 环境
→ deployer.py:_deploy_opencode_json(project_root)
  ├── 生成 $schema, instructions  # 已有
  ├── 生成 permission 配置         # R1 新增
  └── 生成 mcp 模板配置            # R2 新增
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/generators/deployer.py` | `_deploy_opencode()`: 调用 `_deploy_rules()` 写 rules/ 到 opencode_root | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | `_deploy_agents_md_inline()` → `_deploy_agents_md_slim()`: 只写 header | Step 1 | Low |
| 3 | `src/pactkit/generators/deployer.py` | 新增 `_update_global_opencode_json()`: merge instructions 到全局 json | Step 1 | Medium |
| 4 | `src/pactkit/generators/deployer.py` | `_deploy_opencode_json()`: 添加 `permission` + `mcp` 配置 | None | Low |
| 5 | `src/pactkit/generators/deployer.py` | `_print_mcp_recommendations_opencode()`: 更新打印内容 | None | Low |
| 6 | `src/pactkit/prompts/commands.py` | `/project-init` playbook: 添加 pactkit.yaml 位置说明 | None | Low |
| 7 | `tests/unit/test_story071_opencode_config_parity.py` | 添加 AC1-AC7 测试 | Step 1-6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (deployer.py, commands.py) |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend rendering |
| SEC-5 | No | No auth handling — MCP keys left to user |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error message exposure |
| SEC-8 | No | No dependency changes |

## Out of Scope

- `settings.json` 中 `env` 变量的映射（OpenCode 无对等）
- `settings.json` 中 `hooks` 的映射（OpenCode 无对等）
- `settings.json` 中 `statusLine` 的映射（OpenCode 无对等）
- `settings.json` 中 `enabledPlugins` 的映射（不同生态系统）
- `.opencode/pactkit.yaml` 的生成（设计决策：不需要）
- 用户 `provider` 和 `apiKey` 配置（用户自行管理）
- 项目级 opencode.json 的智能合并（当前为 /project-init 首次生成场景）
