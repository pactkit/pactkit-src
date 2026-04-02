# STORY-slim-011: Rule-Command Mapping — Context-Aware Rule Loading

| Field | Value |
|-------|-------|
| ID | STORY-slim-011 |
| Status | Draft |
| Priority | P1 |
| Release | 2.2.0 |

## Background

当前所有 rules (01-09) 对所有 PDCA 命令都全局可见，导致：
1. **Context 冗余**：每轮加载 ~15KB rules，很多与当前命令无关
2. **信噪比低**：AI 需要在无关规则中"找"相关的
3. **可能误导**：如 Done 阶段不应看到 TDD 规则，避免多此一举

## Requirements

### R1: 建立 Rule-Command 映射表
MUST 在代码中定义每个 command 需要的 rules 列表：

| Command | Rules |
|---------|-------|
| project-init | 01, 03, 07, 09 |
| project-plan | 01, 02, 03, 06, 07, 08, 09 |
| project-clarify | 01, 09 |
| project-act | 01, 02, 03, 06, 07, 08, 09 |
| project-check | 01, 02, 03, 06, 07, 09 |
| project-done | 01, 02, 03, 05, 06, 07, 09 |
| project-release | 01, 05, 09 |
| project-pr | 01, 05, 09 |
| project-hotfix | 01, 02, 03, 05, 07, 09 |
| project-design | 01, 03, 06, 08, 09 |
| project-sprint | 01, 02, 03, 04, 05, 06, 07, 08, 09 |

### R2: 09-credential-safety 全局加载
MUST 确保 09-credential-safety 在所有命令中加载，这是安全红线。

### R3: Claude Code 实现 — @import 方式
MUST 在 Claude Code 格式中，每个 command playbook 开头使用 `@import` 引入需要的 rules：
```markdown
@~/.claude/rules/01-core-protocol.md
@~/.claude/rules/09-credential-safety.md

# Command: Clarify (v1.0.0)
...
```
Claude Code 的 `@import` 是原生懒加载，AI 调用命令时才真正读取 rule 文件。

### R4: OpenCode 实现 — 内容嵌入方式
MUST 在 OpenCode 格式中，deployer 根据映射表将 rule 内容**直接嵌入**到 command playbook 的开头。
OpenCode 不支持 `@import` 语法，rule 内容必须是 inline 的。
嵌入格式：
```markdown
<!-- Rules: 01-core-protocol, 09-credential-safety -->

# Core Protocol
{01 的完整内容}

# Operational Safety Rules
{09 的完整内容}

---

# Command: Clarify (v1.0.0)
...
```

### R5: 平台差异对照表
MUST 实现时严格遵循以下平台差异：

| 维度 | Claude Code (classic) | OpenCode |
|------|----------------------|----------|
| Rule 注入方式 | `@~/.claude/rules/{file}` import | 内容直接嵌入 command 文件 |
| Rule 文件位置 | `~/.claude/rules/*.md` | `~/.config/opencode/rules/*.md` |
| Command 文件位置 | `~/.claude/commands/*.md` | `~/.config/opencode/commands/*.md` |
| CLAUDE.md / AGENTS.md | 移除全局 rule @import，改为 command 级别 | instructions 只保留 09，其余移至 command 级别 |
| 全局 always-load | 无（Claude Code @import 是按需的） | `opencode.json` instructions 中只保留 09-credential-safety |
| 向后兼容 | CLAUDE.md 保留 `@./docs/product/context.md` | AGENTS.md On-Demand Rules 引用列表保留为文档参考 |

### R6: 映射表可配置
SHOULD 支持用户在 `pactkit.yaml` 中覆盖默认映射：
```yaml
command_rules:
  project-act: [01, 02, 03, 08, 09]  # 用户自定义
```

### R7: 向后兼容
MUST 保持向后兼容：
- 如果用户没有配置 `command_rules`，使用默认映射
- 现有 AGENTS.md / CLAUDE.md 的全局 rule 引用保留为 fallback 文档

### R8: 防回退 — 映射闭环保障
MUST 通过测试确保映射表的完整性闭环：
1. **Rule 覆盖检查**：RULES_FILES 中每个 rule key 必须至少出现在 COMMAND_RULES_MAP 的某个 command 列表中
2. **Command 覆盖检查**：COMMANDS_CONTENT 中每个 command 必须在 COMMAND_RULES_MAP 中有对应的 key
3. **安全规则强制**：COMMAND_RULES_MAP 中每个 command 的 rules 列表必须包含 "credential"
4. **新增 Rule 流程**：任何新增 rule 到 RULES_FILES 的 PR，必须同时更新 COMMAND_RULES_MAP，否则 CI 失败

## Acceptance Criteria

### AC1: 映射表定义
Given 代码库中定义了 COMMAND_RULES_MAP
When deployer 读取该映射
Then 每个 command 对应的 rules 列表与 R1 表格一致

### AC2: Claude Code 部署 — @import 注入
Given 用户运行 `pactkit init --format classic`
When 部署 project-clarify 命令
Then `~/.claude/commands/project-clarify.md` 开头包含：
```
@~/.claude/rules/01-core-protocol.md
@~/.claude/rules/09-credential-safety.md
```
And 不包含其他 rule 的 @import

### AC3: Claude Code 部署 — 全量命令验证
Given 用户运行 `pactkit init --format classic`
When 部署 project-act 命令
Then `~/.claude/commands/project-act.md` 开头包含 01, 02, 03, 06, 07, 08, 09 的 @import
And 不包含 04, 05 的 @import

### AC4: OpenCode 部署 — 内容嵌入
Given 用户运行 `pactkit init --format opencode`
When 部署 project-clarify 命令
Then `~/.config/opencode/commands/project-clarify.md` 内嵌了 01 和 09 的 rule 全文内容
And 不包含其他 rule 的内容

### AC5: OpenCode 部署 — 全量命令验证
Given 用户运行 `pactkit init --format opencode`
When 部署 project-act 命令
Then `~/.config/opencode/commands/project-act.md` 内嵌了 01, 02, 03, 06, 07, 08, 09 的 rule 全文内容
And 不包含 04, 05 的内容

### AC6: 安全规则全覆盖（含强制注入）
Given 任意 command 的映射配置（默认或用户自定义）
When 该 command 被部署到任意格式（classic/opencode）
Then 09-credential-safety 必定包含在内
And 即使用户自定义 command_rules 里漏掉了 09，deployer 也自动补上

### AC7: 用户自定义覆盖
Given `pactkit.yaml` 包含 `command_rules.project-act: [01, 02, 09]`
When 运行 `pactkit update`
Then project-act 只加载 01, 02, 09 三个 rules（09 已包含无需补上）

### AC8: 防回退 — 新 Rule 必须映射
Given RULES_FILES 中新增了一个 rule key（如 "retrieval"）
When 该 key 不存在于 COMMAND_RULES_MAP 的任何 command 列表中
Then 测试 `test_all_rules_mapped_to_at_least_one_command` 失败
And 错误信息包含未映射的 rule key 名称

### AC9: 防回退 — 新 Command 必须映射
Given COMMANDS_CONTENT 中新增了一个 command（如 "project-foo.md"）
When 该 command 不存在于 COMMAND_RULES_MAP 的 key 中
Then 测试 `test_all_commands_have_rule_mapping` 失败
And 错误信息包含未映射的 command 名称

### AC10: 防回退 — 安全规则不可遗漏
Given COMMAND_RULES_MAP 中某个 command 的列表不包含 "credential"
Then 测试 `test_credential_safety_in_all_commands` 失败
And 错误信息指出哪个 command 缺少安全规则

### AC11: Claude Code CLAUDE.md 更新
Given 映射表已生效
When 部署 classic 格式
Then CLAUDE.md 不再包含全局 @import 所有 rules（rule 加载已下沉到 command 级别）
And CLAUDE.md 仍保留 `@./docs/product/context.md`

### AC12: OpenCode AGENTS.md / opencode.json 更新
Given 映射表已生效
When 部署 opencode 格式
Then opencode.json instructions 中只保留 `rules/09-credential-safety.md`（其余 rule 通过 command 注入）
And AGENTS.md 的 On-Demand Rules 引用列表保留为文档参考，不影响 instructions

### AC13: Token 节省验证
Given project-clarify 命令
When 优化前后对比
Then rule context 从 ~15KB 降到 ~2.5KB（节省 80%+）

## Analysis Summary

### Rule 职责矩阵

| Rule | 核心职责 |
|------|----------|
| 01-core-protocol | 会话上下文、Visual First、TDD、语言匹配、Subagent 模型选择 |
| 02-hierarchy-of-truth | Spec > Tests > Code、冲突解决、RFC 协议、Pre-existing Test 保护 |
| 03-file-atlas | 文件位置速查表 |
| 04-routing-table | Command→Agent 映射、Skill 归属 |
| 05-workflow-conventions | Git Commit 格式、分支命名、PR 规范 |
| 06-mcp-integration | MCP 服务器按阶段使用指南 |
| 07-shared-protocols | Lazy Visualize、Test Mapping、Context.md 格式 |
| 08-architecture-principles | SOLID/DRY、OCP、DIP、安全原则 |
| 09-credential-safety | 凭证保护、破坏性操作防护 |

### 优化效果预估

| Command | 当前 | 优化后 | 节省 |
|---------|------|--------|------|
| project-clarify | ~15KB | ~2.5KB | **83%** |
| project-release | ~15KB | ~3KB | **80%** |
| project-pr | ~15KB | ~3KB | **80%** |
| project-done | ~15KB | ~9KB | **40%** |
| project-check | ~15KB | ~9KB | **40%** |
| project-act | ~15KB | ~12KB | **20%** |
| project-plan | ~15KB | ~12KB | **20%** |

### 特殊考虑

1. **04-routing-table 只有 Sprint 需要**：其他命令已知自己角色，不需要路由
2. **08-architecture-principles 只有设计/实现需要**：Done/Release/PR/Check 不涉及架构决策
3. **02-hierarchy-of-truth 在 Done 和 Hotfix 中部分适用**：
   - Done: Phase 2.5 Regression Gate 需要 Pre-existing Test Protocol
   - Hotfix: Phase 2 test failure handling 需要 Pre-existing Test Protocol
   - 但不需要 RFC Protocol 和完整的 Spec Amendment 流程
4. **07-shared-protocols 在 Check 中也需要**：Check Phase 5 使用了 Test Mapping Protocol
5. **01-core-protocol 在 Hotfix 中部分适用**：TDD 和 Visual First 被豁免，但 Language Matching 和 Subagent Model Selection 仍需要

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/rules.py` | 新增 COMMAND_RULES_MAP 常量 | None | Low |
| 2 | `src/pactkit/config.py` | 支持 `command_rules` 配置解析 | Step 1 | Low |
| 3 | `src/pactkit/generators/deployer.py` | Classic 格式：command 开头生成 @import 头 | Step 1 | Medium |
| 4 | `src/pactkit/generators/deployer.py` | OpenCode 格式：command 开头内嵌 rule 内容 | Step 1 | Medium |
| 5 | `src/pactkit/generators/deployer.py` | Classic 格式：CLAUDE.md 移除全局 rule @import | Step 3 | Medium |
| 6 | `src/pactkit/generators/deployer.py` | OpenCode 格式：更新 AGENTS.md + opencode.json instructions | Step 4 | Medium |
| 7 | `tests/unit/test_story_slim011_*.py` | AC1-AC13 测试（含防回退测试） | Step 1-6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | 不涉及 secrets |
| SEC-2 | No | 不涉及用户输入 |
| SEC-3 | No | 不涉及数据库 |
| SEC-4 | No | 不涉及前端渲染 |
| SEC-5 | No | 不涉及认证 |
| SEC-6 | No | 不涉及 API 端点 |
| SEC-7 | No | 不涉及错误处理 |
| SEC-8 | No | 不涉及依赖变更 |

## Out of Scope

- Rule 内容本身的修改（只改加载方式）
- 新 rule 的添加
- Agent 级别的 rule 映射（本 Story 只做 Command 级别）
- Plugin/Marketplace 格式（暂不支持 command 级别 rule 注入）
