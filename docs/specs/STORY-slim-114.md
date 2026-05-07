# STORY-slim-114: Act Phase 4 Journey Sync — journey.md 维护闭环

| Field | Value |
|-------|-------|
| ID | STORY-slim-114 |
| Status | Done |
| Priority | P2 |
| Release | 2.13.0 |

## Background

### 问题

STORY-slim-109 定义了 `docs/e2e/journey.md` 格式规范，STORY-slim-110 让 `/project-design` 自动生成 journey.md，STORY-slim-111 让 `/project-check` 消费 journey.md 来确定 E2E 范围。

但**没有任何命令负责更新 journey.md**。当 `/project-act` 完成一个 story 并改变了用户流中的某个步骤时：
- journey.md 的步骤描述可能已过时
- 断言可能不再准确（新加了 UI 元素、改了 API schema）
- Check Phase 4 会基于 stale 的 journey 定义来确定 E2E 范围

这是一个 **create → consume without update** 的生命周期缺口。

### 方案

在 Act Phase 4 增加条件步骤 "Journey Sync"：
- 触发条件明确（journey.md 存在 + story 涉及旅程步骤）
- 行为轻量（读 + 判断 + 按需 Edit，不是全文重写）
- 无 hook，纯 playbook 步骤

### 同时修复：Design 阶段 Journey Annotation

STORY-slim-110 的 Design Phase 2 已要求"annotate each Story's Spec with the journey segment it relates to"，但这个标注没有标准格式。定义 annotation 格式使 Act Phase 4 能自动判断"当前 story 是否涉及 journey 步骤"。

## Requirements

### R1: Act Phase 4 新增 Journey Sync 步骤 (MUST)

在 Act Phase 4 的 "Sync & Document" 中增加步骤（位于 visualize 之后、board update 之前）：

```markdown
1b. **Journey Sync (Conditional)**:
    - **Skip if**: `docs/e2e/journey.md` does not exist in the project
    - **Skip if**: Current Story's Spec has no `## Journey Segment` section
    - **If triggered**:
      1. Read `docs/e2e/journey.md`
      2. Locate the journey step(s) referenced in the Spec's `## Journey Segment`
      3. Review: do the step assertions still hold after this Story's code changes?
      4. If outdated: Edit the affected step(s) — update assertions, add new structure assertions, or adjust step description
      5. If still accurate: skip with log "Journey steps verified — no update needed"
```

### R2: Spec 标注格式定义 (MUST)

定义 Spec 中标注 journey segment 的标准格式：

```markdown
## Journey Segment

- Journey: {Journey Name}
- Steps: {step numbers, e.g., "2-3" or "4"}
- Impact: {brief description of how this story affects the journey}
```

此 section 由 `/project-plan` Phase 3.2a 生成（如果 journey.md 存在），或由 `/project-design` Phase 2 自动添加。

### R3: Plan Phase 3.2a 条件生成 Journey Segment section (SHOULD)

修改 project-plan playbook 的 Phase 3.2a：
- **条件**: 如果项目有 `docs/e2e/journey.md`
- **行为**: 读 journey.md，判断当前 story 是否涉及某个 journey 的步骤，如果是则在 Spec 中添加 `## Journey Segment` section
- **不阻塞**: 如果不涉及任何 journey，不添加此 section（Act Phase 4 的 skip 条件自动生效）

### R4: 不引入新的 CLI 命令 (MUST NOT)

Journey Sync 是 playbook 行为指导，不需要新的 CLI 工具。AI 通过 Read + Edit 操作 journey.md 即可。理由：journey.md 内容是自由格式的 markdown，不适合结构化工具处理。

### R5: Merge over Replace 策略 (MUST)

Journey Sync 更新 journey.md 时 MUST 使用 Edit（增量修改），MUST NOT 使用 Write（全文覆盖）。journey.md 可能包含多个 journey，只改当前 story 涉及的步骤。

## Acceptance Criteria

### AC1: Journey Sync 在 Act Phase 4 存在 (R1)

- **Given** 修改后的 project-act SKILL.md
- **When** 读取 Phase 4 内容
- **Then** 存在步骤 "1b" 或 "Journey Sync" 标题，包含 skip 条件和触发行为

### AC2: 无 journey.md 时静默跳过 (R1)

- **Given** 项目没有 `docs/e2e/journey.md`
- **When** Act Phase 4 执行到 Journey Sync
- **Then** 静默跳过，无报错

### AC3: Spec 无 Journey Segment section 时跳过 (R1)

- **Given** 项目有 journey.md，但当前 Story 的 Spec 没有 `## Journey Segment`
- **When** Act Phase 4 执行到 Journey Sync
- **Then** 跳过，无更新

### AC4: Story 涉及 journey 步骤时触发更新 (R1)

- **Given** 项目有 journey.md，Story Spec 有 `## Journey Segment` 标注 "Journey: First Login, Steps: 2-3"
- **When** Act Phase 4 执行 Journey Sync
- **Then** 读取 journey.md 中 "First Login" journey 的 Step 2-3，检查断言是否需更新

### AC5: Spec scaffold 生成 Journey Segment (R2, R3)

- **Given** 项目有 `docs/e2e/journey.md` 定义了 3 个 journey
- **When** `/project-plan` 生成新 Spec
- **Then** Spec 中包含 `## Journey Segment` section（如果 story 涉及某个 journey）

## Target Call Chain

```
/project-act Phase 4:
  → 1. pactkit visualize --lazy (existing)
  → 1b. Journey Sync:
       → Check: does docs/e2e/journey.md exist? (Bash: test -f)
       → Check: does docs/specs/{ID}.md contain "## Journey Segment"? (grep)
       → If both: Read journey.md → locate affected steps → Edit if outdated
  → 2. Board update (existing)
  → 3. Context update (existing)

/project-plan Phase 3.2a (conditional):
  → Check: does docs/e2e/journey.md exist?
  → If yes: Read journey.md → match story scope to journey steps → add ## Journey Segment to Spec
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/commands.py` (act section) | Phase 4 新增 1b Journey Sync 步骤 | None | Low |
| 2 | `src/pactkit/prompts/commands.py` (plan section) | Phase 3.2a 增加条件 Journey Segment 生成 | None | Low |
| 3 | `src/pactkit/prompts/skills.py` (trace section) | 无变更（确认不冲突） | None | None |
| 4 | `tests/unit/test_story_slim114_journey_sync.py` | 验证 Act playbook 包含 Journey Sync 步骤文本 | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | 无秘钥变更 |
| SEC-2 | No | 无外部输入处理 |
| SEC-3 | No | 无数据库 |
| SEC-4 | No | 无 UI |
| SEC-5 | No | 无认证 |
| SEC-6 | No | 无接口 |
| SEC-7 | No | 无错误输出 |
| SEC-8 | No | 无依赖变更 |

## Out of Scope

- 新增 CLI 命令（journey.md 由 AI 通过 Read+Edit 操作）
- journey.md 的结构化 linter（内容是自由格式 markdown）
- Check Phase 4 修改（已由 STORY-slim-111 处理）
- Design Phase 1.5.5 修改（已由 STORY-slim-110 处理）
- 自动检测 journey 影响（需要 AI 判断力，不适合 Code Enforce）
