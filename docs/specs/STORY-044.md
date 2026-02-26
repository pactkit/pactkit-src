# STORY-044: Pre-Act Consistency Check — Left-Shift Quality Gate

| Field     | Value |
|-----------|-------|
| ID        | STORY-044 |
| Status    | Draft |
| Priority  | Medium |
| Release   | 1.3.1 |
| Author    | System Architect |
| Source    | Gap Analysis: SpecKit `/speckit.analyze` |

## Background

PactKit 的 Check phase（`/project-check`）在 Act 之后运行，验证的是代码实现与 Spec 的对齐。但在 Plan → Act 的交接点，Spec、Board 任务拆解、Test Case 三个文本工件之间的一致性没有人检查。

常见问题：
1. Spec 有 5 个 Requirements，但 Board 只拆了 3 个 Task（遗漏）
2. Board 有 Task 但在 Spec 中找不到对应 Requirement（scope creep）
3. Spec AC 定义了 6 个场景，但 Test Case 只覆盖了 4 个（覆盖缺口）

这些偏差在纯文本阶段就能发现，成本远低于在代码实现后才捕获。SpecKit 通过 optional 的 `/speckit.analyze` 命令提供类似功能。PactKit 需要将其集成为 **Act 入口的自动检查**。

## Target Call Chain

```
/project-act (commands.py)
  → Phase 0: Thinking Process (existing)
  → Phase 0.5: Spec Lint Gate (STORY-042)
  → Phase 0.6 (NEW): Consistency Check
    → _check_spec_board_alignment(story_id)
      → Parse Spec requirements (R1, R2, ...)
      → Parse Board tasks for the Story
      → Cross-reference: every R has a Task, every Task has an R
    → _check_spec_testcase_alignment(story_id)
      → Parse Spec ACs (AC1, AC2, ...)
      → Parse Test Case scenarios (if exists)
      → Cross-reference: every AC has a Scenario
    → Report: alignment matrix + gaps
    → IF critical gaps: WARN (do not block)
  → Phase 1: Precision Targeting (existing)
```

## Requirements

### R1: Spec ↔ Board Task 对齐检查 (MUST)

解析 Spec 的 `## Requirements` section 中所有 `### R{N}:` 子标题，与 Sprint Board 中该 Story 的 task 列表做交叉比对。

**检查规则：**

| Rule | Severity | Description |
|------|----------|-------------|
| Spec Requirement 无对应 Board Task | WARN | 需求可能被遗漏 |
| Board Task 无对应 Spec Requirement | WARN | 可能存在 scope creep |
| Task 数量与 Requirement 数量差异 > 50% | WARN | 拆解粒度可能不合理 |

**对齐判定逻辑：**
- 精确匹配：Task 名称包含 `R{N}` 标识符
- 模糊匹配：Task 名称的关键词与 Requirement 标题的关键词重叠度 ≥ 50%
- 如果 Board 中该 Story 有 `### Tasks` 格式，提取 `- [ ] Task Name` 列表

### R2: Spec AC ↔ Test Case 覆盖检查 (SHOULD)

解析 Spec 的 `## Acceptance Criteria` 中所有 AC 条目，与 `docs/test_cases/{STORY_ID}_case.md` 中的 Scenario 做交叉比对。

**检查规则：**

| Rule | Severity | Description |
|------|----------|-------------|
| AC 无对应 Test Case Scenario | INFO | 测试覆盖缺口（Test Case 可能在 Check 阶段才生成） |
| Test Case 不存在 | INFO | 正常情况（Test Case 在 Check 阶段生成） |

注意：Test Case 通常在 Check 阶段生成，因此此检查仅为 INFO 级别提示，不阻断也不 WARN。

### R3: Act Phase 集成 (MUST)

在 `project-act.md` playbook 中，STORY-042 的 Spec Lint Gate（Phase 0.5）之后、Phase 1 之前，插入 **Phase 0.6: Consistency Check**。

**行为：**
- 所有检查结果为 INFO/WARN 级别，**不阻断** Act 流程
- 输出对齐矩阵让开发者知悉当前状态
- 如果发现 WARN 级别的 gap，建议："Consider updating the Board tasks to match Spec requirements before proceeding."

### R4: 输出格式 (MUST)

```
## Consistency Check: STORY-XXX

### Spec ↔ Board Alignment
| Spec Requirement | Board Task | Status |
|------------------|------------|--------|
| R1: xxx          | Task: xxx  | Aligned |
| R2: xxx          | —          | ⚠️ Missing Task |
| —                | Task: yyy  | ⚠️ No matching Requirement |

### Spec AC ↔ Test Case Coverage
| AC | Test Case Scenario | Status |
|----|-------------------|--------|
| AC1: xxx | Scenario 1: xxx | Covered |
| AC2: xxx | — | ℹ️ Not yet covered |

### Summary
- Alignment: 3/5 requirements have matching tasks
- Coverage: 4/6 ACs have test case scenarios
- Action: [suggestions if gaps found]
```

### R5: Standalone Skill (MAY)

提供 `pactkit-analyze` 作为独立 skill，可在任何时间点手动调用：
```
/pactkit-analyze STORY-XXX
```
独立调用时执行相同的 R1 + R2 检查并输出报告。

## Acceptance Criteria

### AC1: 对齐完整时静默
**Given** STORY-XXX 的 Spec 有 3 个 Requirements，Board 有 3 个对应 Tasks
**When** 执行 `/project-act STORY-XXX`
**Then** Phase 0.6 输出对齐矩阵，所有状态为 "Aligned"
**And** Act 流程继续进入 Phase 1

### AC2: 检测到遗漏 Requirement
**Given** Spec 有 R1-R5 共 5 个 Requirements，Board 只有 3 个 Tasks
**When** 执行 `/project-act STORY-XXX`
**Then** Phase 0.6 输出对齐矩阵，2 个 Requirement 标记为 "⚠️ Missing Task"
**And** 输出建议 "Consider updating the Board tasks"
**And** Act 流程**不阻断**，继续进入 Phase 1

### AC3: 检测到 Scope Creep
**Given** Board 有一个 Task 在 Spec Requirements 中找不到对应
**When** 执行 `/project-act STORY-XXX`
**Then** Phase 0.6 标记该 Task 为 "⚠️ No matching Requirement"

### AC4: Test Case 不存在时为 INFO
**Given** `docs/test_cases/STORY-XXX_case.md` 不存在
**When** 执行 `/project-act STORY-XXX`
**Then** Phase 0.6 输出 "ℹ️ Test Case not yet created (normal — generated during Check phase)"
**And** 不输出 WARN

### AC5: 不阻断 Act
**Given** 任何 Consistency Check 结果
**When** 检查完成
**Then** Act 流程始终继续进入 Phase 1（Consistency Check 仅为 advisory）

## Out of Scope

- 自动修复对齐问题（本 Story 仅检测和报告）
- 校验 Spec 内容的语义正确性（STORY-042 覆盖结构，语义超出自动化范围）
- 校验代码实现与 Spec 的对齐（这是 `/project-check` 的职责）
