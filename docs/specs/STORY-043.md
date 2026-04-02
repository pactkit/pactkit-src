# STORY-043: Active Clarify — Pre-Plan Requirement Disambiguation

| Field     | Value |
|-----------|-------|
| ID        | STORY-043 |
| Status    | Draft |
| Priority  | High |
| Release   | 1.3.1 |
| Author    | System Architect |
| Source    | Gap Analysis: SpecKit `/speckit.clarify` |

## Background

PactKit 当前的 Plan 阶段接受用户输入后直接生成 Spec。当用户输入模糊时（如"加个登录功能"），Plan 阶段会基于自身假设填充细节，导致 Spec 不符合用户真实意图，引发 Plan → Act → 发现偏差 → 重新 Plan 的返工循环。

PactKit 已有 **RFC Protocol**（Act 阶段发现不可行时 STOP），但这是**被动防守**——只在写代码时才触发。缺少**主动进攻**：在 Spec 写入之前，系统性地发现和消除需求模糊性。

SpecKit 提供 `/speckit.clarify` 作为 optional command 来解决此问题。PactKit 需要一个更强的版本：**集成到 Plan 流程中的自动检测 + 按需触发**，而非独立的手动命令。

## Target Call Chain

```
/project-plan (commands.py)
  → Phase 0: Thinking Process (existing)
  → Phase 0.5: Init Guard (existing)
  → Phase 0.7 (NEW): Clarify Gate
    → _detect_ambiguity(user_input)
      → Check against AMBIGUITY_SIGNALS checklist
      → IF ambiguity score > threshold:
        → Generate structured questions
        → Present to user, collect answers
        → Append answers to enriched_input
    → IF user declines clarify: proceed with original input
  → Phase 1: Archaeology (existing, uses enriched_input)
```

## Requirements

### R1: Ambiguity Detection (MUST)

在 Plan Phase 0 完成后、Phase 1 之前，新增 **Phase 0.7: Clarify Gate**。

**模糊性检测信号（AMBIGUITY_SIGNALS）：**

| Signal | Example | Weight |
|--------|---------|--------|
| 无量化指标 | "支持高并发" → 多少 QPS？ | High |
| 无边界条件 | "用户管理" → 哪些操作？CRUD？权限？ | High |
| 无技术约束 | "做个 API" → REST/GraphQL？认证方式？ | Medium |
| 单句输入（<15 words） | "加个登录功能" | Medium |
| 含模糊量词 | "一些"、"大量"、"快速"、"simple" | Low |
| 无目标用户 | 未指定谁在用这个功能 | Low |

**触发逻辑：**
- 如果检测到 ≥2 个 High 信号，或 ≥1 个 High + ≥2 个 Medium 信号：**自动触发** Clarify
- 如果检测到 ≥2 个 Medium 信号：**建议触发**（询问用户是否需要 clarify）
- 其他情况：静默跳过

### R2: Structured Question Generation (MUST)

当 Clarify 触发时，生成结构化问题列表。问题必须覆盖以下维度：

| Dimension | Question Template |
|-----------|-------------------|
| **Scope** | "这个功能包含哪些具体操作？请列举。" |
| **Users** | "谁是这个功能的目标用户？有几种角色？" |
| **Constraints** | "有没有技术约束？（如必须用某个框架、必须兼容某个系统）" |
| **Scale** | "预期数据量/并发量/用户量级？" |
| **Edge Cases** | "如果 [异常情况] 发生，期望的行为是什么？" |
| **Non-Goals** | "这个功能明确**不需要**做什么？" |

- 每次 Clarify 生成 3-6 个问题（不超过 6 个，避免用户疲劳）
- 问题按优先级排序（High 信号对应的维度优先）
- 使用用户的语言（遵循 Language Matching 规则）

### R3: 用户交互流程 (MUST)

1. 输出检测到的模糊性信号（简要说明）
2. 输出问题列表，编号标注
3. 等待用户回答
4. 用户可以选择：
   - **回答所有问题** → 答案合并为 enriched_input，传递给 Phase 1
   - **回答部分问题** → 已回答的合并，未回答的标记为"用户选择跳过"
   - **跳过 Clarify**（输入 "skip" 或类似指令）→ 使用原始输入继续
5. 无论用户选择哪个路径，都必须继续 Plan 流程（Clarify 不可阻断 Plan）

### R4: Plan Playbook 集成 (MUST)

修改 `project-plan.md` playbook（在 `commands.py` 的 `COMMANDS_CONTENT`）：
- 在 Phase 0.5（Init Guard）和 Phase 1（Archaeology）之间插入 Phase 0.7
- Phase 0.7 的输出（enriched_input）作为后续阶段的输入
- 如果 Clarify 被跳过，enriched_input = 原始 user_input

### R5: Standalone Command (SHOULD)

提供 `/project-clarify` 作为独立命令，允许用户在 Plan 之前单独运行：
- 新增 `project-clarify.md` playbook 到 `COMMANDS_CONTENT`
- 独立运行时，输出结构化的 clarified brief（可以直接作为 `/project-plan` 的输入）
- 更新路由表 `04-routing-table.md` 添加 Clarify 命令

### R6: Greenfield 场景强化 (SHOULD)

当 Plan Phase 0 检测到 Greenfield 信号时（已有逻辑），且用户确认不使用 `/project-design`：
- Clarify Gate MUST 强制触发（不依赖模糊性检测得分）
- 因为 Greenfield 场景天然缺乏上下文，主动消歧的价值最高

## Acceptance Criteria

### AC1: 模糊输入触发 Clarify
**Given** 用户执行 `/project-plan "加个登录功能"`
**When** Phase 0.7 检测到模糊性（单句、无边界条件、无技术约束）
**Then** 输出 3-6 个结构化问题
**And** 等待用户回答

### AC2: 清晰输入跳过 Clarify
**Given** 用户执行 `/project-plan "为 CLI 添加 --dry-run 参数，跳过所有文件写入操作，仅输出将要执行的动作列表到 stdout"`
**When** Phase 0.7 检测模糊性
**Then** 检测结果低于阈值
**And** 静默跳过 Clarify，直接进入 Phase 1

### AC3: 用户可跳过
**Given** Clarify 已触发并输出问题列表
**When** 用户输入 "skip" 或表示不需要 clarify
**Then** 使用原始输入继续 Plan 流程
**And** Plan 不被阻断

### AC4: Enriched Input 传递
**Given** 用户回答了 Clarify 问题
**When** Phase 1 开始
**Then** Phase 1 使用的上下文包含用户的原始输入 + Clarify 回答
**And** 生成的 Spec 反映了 Clarify 收集的信息

### AC5: Greenfield 强制触发
**Given** Plan Phase 0 检测到 Greenfield 信号且用户选择继续 Plan
**When** Phase 0.7 执行
**Then** Clarify 强制触发（不论模糊性得分）

### AC6: 语言匹配
**Given** 用户用中文输入需求
**When** Clarify 生成问题
**Then** 问题也用中文输出

## Out of Scope

- Clarify 不修改已有 Spec（它发生在 Spec 生成之前）
- Clarify 不替代 RFC Protocol（RFC 是 Act 阶段发现技术不可行时的升级路径）
- 不支持多轮 Clarify（一次问答后即进入 Plan，避免无限循环）
