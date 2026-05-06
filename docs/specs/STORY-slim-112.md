# STORY-slim-112: Rules 架构重构：全局原则 vs 按需操作规程

| Field | Value |
|-------|-------|
| ID | STORY-slim-112 |
| Status | Draft |
| Priority | P1 |
| Release | 2.12.0 |

## Background

### 问题

当前 PactKit 部署 11 个 rule 文件到 `~/.claude/rules/`。Claude Code harness 对该目录执行**全量自动加载**——每次对话都注入全部 ~800 行规则，即使用户只是问个简单问题。

更糟糕的是，当 skill（如 `/project-plan`）被调用时，其 `@import` 再次加载相同 rules，导致**同一内容在 context 中出现两次**。

### 分类分析

对 11 个 PactKit-managed rules 进行原则分类：

| Rule | 行数 | 内容本质 | 归属判断 |
|------|:----:|----------|----------|
| 01-core-protocol | 62 | PACT 原则、session、TDD、信号强度 | **全局** — 永远需要 |
| 02-hierarchy-of-truth | 26 | Code is Law / Spec > Code | **全局** — 核心原则 |
| 03-file-atlas | 14 | 文件路径查找表 | **全局** — 极小，导航必需 |
| 04-routing-table | 81 | Command 路由参考 | **全局** — PactKit 使用方式 |
| 05-workflow-conventions | 39 | Git commit/branch 规范 | **按需** — 只有 Done/PR/Release 需要 |
| 06-mcp-integration | 55 | MCP server 使用指南 | **按需** — 只有 Act/Check/Design 需要 |
| 07-shared-protocols | 38 | Lazy Visualize / Test Mapping | **按需** — 只有执行阶段需要 |
| 08-architecture-principles | 146 | SOLID、DRY、安全、缓存等 | **混合** — 核心原则(DRY/hardcode)全局，其余按需 |
| 09-sectional-write | 29 | 大文件写入策略 | **按需** — 只有生成文件时需要 |
| 11-pdca-nudge | 43 | PDCA 推荐触发规则 | **全局** — 闲聊时也需要触发 |
| 12-solution-design | 161 | 框架能力评估流程 | **按需** — 只有 Plan/Act 需要 |

**Token 节约估算**：将按需规则从全局移除后，每次非 PDCA 对话节省 ~468 行 / ~3500 tokens。

### 核心设计决策

**全局 rules（永远在场的原则）**：
- **P.A.C.T 流程** — 告诉 AI "你有这些能力，应该怎么选"
- **不允许 hardcode** — DRY / No Magic Values（从 08 中提取）
- **复用代码** — 先查有没有，别重复造轮子（从 08/12 中提取）
- **Spec is Law / Code is Truth** — 三层真理体系
- **AI is creative, Code is deterministic** — LLM ≠ Calculator
- **PDCA Nudge** — 闲聊时也能推荐下一步
- **File Atlas** — 导航地图，极小
- **Routing Table** — PactKit 使用方式

**按需 rules（skill 调用时才加载）**：
- Workflow conventions (Git 规范)
- MCP integration (server 使用)
- Shared protocols (visualize/test mapping)
- Architecture details (完整 SOLID 细节)
- Sectional write (大文件策略)
- Solution design (框架评估流程)

## Requirements

### R1: 全局 rules 精简为核心原则 (MUST)

`~/.claude/rules/` 部署后只保留以下文件：
- `01-core-protocol.md` — PACT 原则、session context、TDD、信号强度、语言匹配
- `02-hierarchy-of-truth.md` — Spec > Tests > Code 三层真理
- `03-file-atlas.md` — 路径导航
- `04-routing-table.md` — PactKit 使用方式/command 路由
- `05-principles.md` — **新建**，从 08/12 中提取的永远在场原则：
  - No Magic Values / DRY
  - 复用优先（查框架 → 查项目已有 → 才新写）
  - Code Enforces, Prompt Instructs (LLM ≠ Calculator)
  - Dependency Direction (不允许反向 import)
- `11-pdca-nudge.md` — 闲聊推荐

总计 6 个文件，约 ~330 行（从 799 行降至 ~330 行，减少 ~59%）。

### R2: 按需 rules 移到 skill 可引用位置 (MUST)

将以下 rules 从 `~/.claude/rules/` 移除，**整个文件原封不动**部署到 skill 可 `@import` 的位置：
- `05-workflow-conventions.md`
- `06-mcp-integration.md`
- `07-shared-protocols.md`
- `08-architecture-principles.md`（完整保留，不删减）
- `09-sectional-write.md`
- `12-solution-design.md`

部署目标路径：`~/.claude/skills/_rules/` 或 `~/.claude/rules/ondemand/`（需确认 Claude Code `@import` 是否支持子目录引用）。

### R3: Skill @import 路径更新 (MUST)

所有 skill SKILL.md 文件的 `@import` 路径更新为新位置。例如：
```
# 旧
@~/.claude/rules/08-architecture-principles.md

# 新
@~/.claude/skills/_rules/08-architecture-principles.md
```

### R4: Deployer 逻辑更新 (MUST)

修改 `_deploy_rules()` 函数：
- 全局 rules 仍写入 `~/.claude/rules/`
- 按需 rules 写入新的按需目录
- 清理逻辑更新：不再删除按需目录中的文件用旧前缀匹配
- `RULES_CORE_FILES` / `RULES_ONDEMAND_FILES` 分类更新

### R5: 新建 05-principles.md 提取核心原则精华 (MUST)

从 `08-architecture-principles.md` 和 `12-solution-design.md` 中**提取**核心原则的精简版，写入新建的 `05-principles.md`。原文件整体挪走不做任何修改。

05-principles.md 是这些原则的"精简提醒版"（~60 行），确保 AI 在任何对话中都记住底线。完整细则仍在按需目录的 08 和 12 中，PDCA 执行时通过 @import 拉入。

### R6: 向后兼容 (MUST)

- 用户自定义 rules（`10-safety.md`、`13-skill-discovery.md`、`slim-01-*`）不受影响
- `RULES_MANAGED_PREFIXES` 更新，只清理全局 rules 中的 managed 文件
- `pactkit.yaml` 中的 `exclude_rules` 配置保持有效

### R7: 不丢失内容 (MUST NOT)

重构后，所有原有 rule 内容必须在某个位置可被加载到。不可出现"某条规则被移走后，对应 skill 的 @import 忘了更新"的情况。

## Acceptance Criteria

### AC1: 非 PDCA 对话 context 减少 (R1)

- **Given** 用户开启新对话，不调用任何 /project-* command
- **When** Claude Code 加载 `~/.claude/rules/` 目录
- **Then** 只加载 6 个文件（01, 02, 03, 04, 05-principles, 11），总行数 ≤ 350 行

### AC2: PDCA command 仍能获取全部规则 (R2, R3)

- **Given** 用户调用 `/project-plan`
- **When** skill 的 `@import` 加载按需 rules
- **Then** 08-architecture-principles、12-solution-design 等仍被加载到 context

### AC3: 按需 rules 不再全量加载 (R2)

- **Given** 用户开启新对话，不调用任何 command
- **When** 检查 context 内容
- **Then** 不包含 06-mcp-integration、07-shared-protocols、09-sectional-write、12-solution-design 内容

### AC4: Deployer 正确写入两个位置 (R4)

- **Given** 执行 `pactkit init --format classic`
- **When** 检查 `~/.claude/rules/` 和按需目录
- **Then** 全局 rules 在 `~/.claude/rules/`，按需 rules 在按需目录

### AC5: 全部测试通过 (R7)

- **Given** 重构完成
- **When** 运行 `.venv/bin/pytest tests/ -v`
- **Then** 所有既有测试通过（E2E completeness 测试需更新断言）

### AC6: 05-principles.md 包含核心原则 (R5)

- **Given** 新建的 `05-principles.md`
- **When** 读取其内容
- **Then** 包含：No Magic Values、DRY/Single Source of Truth、Code Enforces Prompt Instructs、Dependency Direction

## Target Call Chain

```
pactkit init / pactkit update
  → deploy() in deployer.py
    → _deploy_classic()
      → _deploy_rules(claude_root, enabled_rules, ...)
        → [旧] 全部写入 ~/.claude/rules/
        → [新] 全局写入 ~/.claude/rules/, 按需写入 ~/.claude/skills/_rules/
      → _deploy_skills(...)
        → [新] skill SKILL.md 的 @import 路径指向按需目录
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/rules.py` | 拆分 RULES_CORE/ONDEMAND 分类，新增 05-principles 内容 | None | Medium |
| 2 | `src/pactkit/config.py` | 更新 VALID_RULES、RULES_MANAGED_PREFIXES | Step 1 | Low |
| 3 | `src/pactkit/generators/deployer.py` | _deploy_rules 写入两个目标目录 | Step 1-2 | Medium |
| 4 | `src/pactkit/prompts/commands.py` | 更新所有 command 的 @import 路径 | Step 3 | Low |
| 5 | `src/pactkit/prompts/workflows.py` | 更新 design 的 @import 路径 | Step 3 | Low |
| 6 | `tests/unit/test_cli_e2e.py` | 更新 completeness 断言 | Step 1-5 | Low |
| 7 | `tests/unit/` | 新增 test 验证两目录部署正确性 | Step 1-5 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | 无秘钥变更 |
| SEC-2 | No | 无用户输入处理变更 |
| SEC-3 | No | 无数据库 |
| SEC-4 | No | 无 UI |
| SEC-5 | No | 无认证 |
| SEC-6 | No | 无接口 |
| SEC-7 | No | 无错误输出变更 |
| SEC-8 | No | 无依赖变更 |

## Out of Scope

- 用户自定义 rules 的迁移（10-safety、13-skill-discovery、slim-01 保持原位）
- OpenCode / Codex / Copilot 格式的同步调整（本 story 只做 Classic format，其他格式 follow-up）
- Rule 内容的实质性修改（只做位置移动和拆分，不改写规则含义）
- `includeFiles` frontmatter 方案（已排除）

## Technical Design

### 目录结构（重构后）

```
~/.claude/rules/                    ← harness 全量加载（精简）
  01-core-protocol.md               ← PACT、session、TDD
  02-hierarchy-of-truth.md          ← Spec is Law
  03-file-atlas.md                  ← 路径导航
  04-routing-table.md               ← Command 使用方式
  05-principles.md                  ← 核心工程原则（新建，从 08/12 提取）
  11-pdca-nudge.md                  ← 闲聊推荐
  10-safety.md                      ← 用户自定义（不动）
  13-skill-discovery.md             ← 用户自定义（不动）
  slim-01-operational-discipline.md ← 用户自定义（不动）

~/.claude/skills/_rules/            ← 按需加载（skill @import）
  05-workflow-conventions.md        ← Git 规范
  06-mcp-integration.md             ← MCP 使用
  07-shared-protocols.md            ← Visualize/Test Mapping
  08-architecture-principles.md     ← SOLID 13 条完整细则
  09-sectional-write.md             ← 大文件策略
  12-solution-design.md             ← 框架评估流程
```

### 05-principles.md 内容来源

从现有 rules 中提取的"永远在场"原则：

| 原则 | 原文件 | 原 Section |
|------|--------|-----------|
| No Magic Values | 12-solution-design.md | Implementation Constraints |
| Single Source of Truth / DRY | 08-architecture-principles.md | §1 |
| No Dual-Write | 08-architecture-principles.md | §1 No Dual-Write |
| Code Enforces, Prompt Instructs | 08-architecture-principles.md | §10 |
| Dependency Direction | 12-solution-design.md | Implementation Constraints |
| Dead Code Hygiene | 08-architecture-principles.md | §13 |
| Open-Closed Principle (brief) | 08-architecture-principles.md | §2 (缩写版) |

### Skill @import 路径变更示例

```markdown
# project-plan SKILL.md (旧)
@~/.claude/rules/08-architecture-principles.md
@~/.claude/rules/12-solution-design.md

# project-plan SKILL.md (新)
@~/.claude/skills/_rules/08-architecture-principles.md
@~/.claude/skills/_rules/12-solution-design.md
```
