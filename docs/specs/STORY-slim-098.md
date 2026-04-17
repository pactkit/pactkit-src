# STORY-slim-098: PDCA Nudge Protocol — AI主动推荐PDCA命令

| Field | Value |
|-------|-------|
| ID | STORY-slim-098 |
| Status | Done |
| Priority | P1 |
| Release | 2.11.0 |

## Background

当用户与 AI 进行自由对话（非 PDCA 命令上下文）时，AI 经常分析出 bug、架构改进点、新功能需求等结论，但不会主动提示用户使用对应的 PDCA 命令来跟踪和实现这些结论。用户聊着聊着就忘了 PDCA 的存在，导致有价值的分析结果停留在对话中，没有进入 Spec → Act → Check → Done 的可追溯流程。

**现状**:
- `context.md` 的 `Next Recommended Action` 仅在用户主动查看时可见（被动）
- Routing Table (`04-routing-table.md`) 只描述"When NOT to use"，没有正向触发逻辑
- Core Protocol 仅在 Session Context 中建议 `/project-init`，对话中无 nudge 机制

**目标**: 新增 `11-pdca-nudge.md` 规则文件，定义 AI 在自由对话中检测到可行动结论时主动推荐 PDCA 命令的协议。

## Requirements

### R0: Core Protocol 锚定 (MUST)

在 `01-core-protocol.md` 中新增 `## PDCA Nudge` 小节（紧随 `## Session Context` 之后），声明原则：

```markdown
## PDCA Nudge
When AI analysis in free conversation (outside PDCA command context) yields actionable conclusions — bugs, architecture improvements, new feature needs — SHOULD recommend the appropriate PDCA command at the end of the reply. See `11-pdca-nudge.md` for trigger matrix and suppression rules.
```

**Why**: Core Protocol 是 AI 行为的"宪法"，是 system prompt 中最早被阅读的锚点。仅放 rules/ 会被 12+ 个规则平铺稀释；在 Core Protocol 中声明原则确保 nudge 被视为核心行为而非可选建议。

### R1: PDCA Nudge 触发矩阵 (MUST)

AI 在自由对话中（非 PDCA 命令执行上下文）检测到以下信号时，MUST 在回复末尾附加 PDCA 推荐提示：

| 信号类型 | 推荐命令 | 判断条件 |
|----------|----------|----------|
| 发现 bug / 错误行为 | `/project-hotfix` | 单文件修复，无设计决策 |
| 发现 bug + 涉及设计变更 | `/project-plan` | 多文件或需求不明确 |
| 识别出架构改进 | `/project-plan` | 涉及 2+ 文件修改 |
| 识别出新功能需求 | `/project-plan` | 单功能 |
| 识别出新产品/多功能需求 | `/project-design` | 3+ 个独立 story 的绿地项目 |
| 已有 Spec 的待实现需求 | `/project-act STORY-XXX` | Board 上有对应 story |
| 3+ 个独立改进项 | `/project-sprint` | 多个 story 可并行 |
| 代码质量问题（可快速修复） | `/project-hotfix` | 不涉及行为变更 |

### R2: Nudge 格式 (MUST)

推荐提示 MUST 使用以下固定格式，置于回复末尾（分析内容之后）：

```
💡 这个分析结果可以通过 `{command}` 来跟踪实现：
> {一句话说明为什么推荐这个命令}
```

### R3: 抑制条件 (MUST)

以下场景 MUST NOT 触发 nudge：
- 当前已在 PDCA 命令执行上下文中（Plan/Act/Check/Done/Sprint 等）
- 用户明确表示只想聊天、不想走流程
- 分析结论是对现有实现的确认（没有发现问题）
- 用户在同一对话中已经收到过相同命令的 nudge（去重）

### R4: 非阻塞 (SHOULD)

Nudge SHOULD 是非阻塞的建议，不改变 AI 当前回复的内容结构。AI 完整回答用户问题后，在末尾附加 nudge。用户可以忽略 nudge 继续对话。

## Acceptance Criteria

### AC1: Bug 分析触发 hotfix 推荐 (R1, R2)

- **Given** 用户在自由对话中请求分析某段代码
- **When** AI 发现一个单文件 bug（如逻辑错误、边界条件缺失）
- **Then** AI 回复完整分析后，末尾附加 `/project-hotfix` nudge

### AC2: 架构建议触发 plan 推荐 (R1, R2)

- **Given** 用户在自由对话中讨论代码结构
- **When** AI 识别出涉及 2+ 文件的架构改进建议
- **Then** AI 回复完整分析后，末尾附加 `/project-plan` nudge

### AC3: PDCA 上下文内不触发 (R3)

- **Given** 用户正在执行 `/project-act STORY-XXX`
- **When** AI 在实现过程中发现额外的改进点
- **Then** AI 不附加 nudge（当前已在 PDCA 上下文中）

### AC4: 去重抑制 (R3)

- **Given** AI 在同一对话中已推荐过 `/project-plan`
- **When** AI 再次发现可以走 `/project-plan` 的结论
- **Then** AI 不重复推荐相同命令

### AC5: 非阻塞体验 (R4)

- **Given** 用户提问 "这段代码有什么问题？"
- **When** AI 分析完成并附加 nudge
- **Then** nudge 在回复末尾，不打断分析内容的完整性；用户可直接继续下一个问题而无需回应 nudge

### AC6: 双层锚定部署验证 (R0)

- **Given** 运行 `pactkit deploy`
- **When** 检查部署产物 `~/.claude/rules/01-core-protocol.md`
- **Then** 文件包含 `## PDCA Nudge` 小节，且内容引用 `11-pdca-nudge.md`

## Target Call Chain

无代码调用链。本 Story 变更的是 prompt 规则文件（`~/.claude/rules/11-pdca-nudge.md`），属于 PactKit 部署产物。
- 规则文件通过 `pactkit deploy` 部署到 `~/.claude/rules/` 目录
- 规则文件被 Claude Code 在 session 启动时自动加载
- 规则内容直接影响 AI 行为，无代码执行路径

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/templates/rules/01-core-protocol.md` | 在 `## Session Context` 之后新增 `## PDCA Nudge` 小节（3-4 行原则声明 + 指向 11-pdca-nudge.md） | None | Low |
| 2 | `src/pactkit/templates/rules/11-pdca-nudge.md` | 新建规则模板，定义完整触发矩阵、格式模板、抑制条件 | None | Low |
| 3 | `src/pactkit/config.py` | 在 `VALID_RULES` 列表中添加 `11-pdca-nudge` | Step 2 | Low |
| 4 | `tests/unit/test_deploy_rules.py` | 添加测试：验证新规则被 deploy 包含 | Step 2-3 | Low |
| 5 | `pactkit deploy` (验证) | 运行 deploy，确认 01-core-protocol.md 含 PDCA Nudge 节 + 11-pdca-nudge.md 出现在 `~/.claude/rules/` | Step 1-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | 变更仅为 prompt 规则文本，不涉及可执行代码逻辑 |
| SEC-2 | N/A | 无用户输入处理 |
| SEC-3 | N/A | 无数据库操作 |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无认证逻辑 |
| SEC-6 | N/A | 无 API/路由 |
| SEC-7 | N/A | 无错误处理变更（config.py 仅增加列表项） |
| SEC-8 | N/A | 无依赖变更 |

## Out of Scope

- 不修改任何 PDCA 命令的 playbook（Plan/Act/Check/Done 等）
- 不修改 Routing Table (`04-routing-table.md`)  — nudge 是补充，不改变现有路由逻辑
- 不实现自动执行 PDCA 命令 — nudge 仅推荐，由用户决定是否执行
- 不修改 `context.md` 的 `Next Recommended Action` 机制 — 两者互补（context.md 是 session 级，nudge 是对话级）
