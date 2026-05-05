# STORY-slim-110: project-design 集成 User Journey 生成

| Field | Value |
|-------|-------|
| ID | STORY-slim-110 |
| Status | Draft |
| Priority | P1 |
| Release | 2.12.0 |

## Background

STORY-slim-109 定义了 `docs/e2e/journey.md` 规范，但旅程定义的**生成时机**尚未明确。用户旅程应在产品设计阶段（`/project-design`）由 Architect 定义，因为：
- 旅程是跨 story 的，必须在 story 拆分之前就存在
- Design Phase 1.5 已经定义了 Page/Screen，旅程是 Screen 之间的连接方式
- 旅程定义为后续每个 story 的 E2E 提供上下文锚点

## Requirements

### R1: Design Phase 增加 Section 1.5.5 User Journeys (MUST)

在 `project-design/SKILL.md` 的 Phase 1 Group B 中，Section 1.5 (Page/Screen Design) 之后增加 Section 1.5.5：
- 基于 Persona + Page/Screen 定义生成核心用户旅程
- 输出写入 `docs/e2e/journey.md`（格式遵循 STORY-slim-109 规范）

### R2: 旅程覆盖所有 Persona 的主路径 (SHOULD)

每个 Persona（PRD Section 1.2）至少有一条对应的用户旅程，覆盖其核心 Job-to-be-Done。

### R3: 旅程与 Story 的映射关系 (SHOULD)

在 Phase 3 (Story Decomposition) 时，每个 Story 的 Spec 可标注其关联的旅程片段（如 "Journey 1, Step 2-3"），便于 Check Phase 4 定位要跑的 E2E 范围。

### R4: 旅程数量约束 (MUST)

MVP 阶段（Now horizon）旅程不超过 5 条，避免前期定义过多无法维护的旅程。

## Acceptance Criteria

### AC1: Design 输出包含 journey.md (R1)

- **Given** 用户执行 `/project-design "一个 AI chatbot 产品"`
- **When** Design Phase 1 Group B 执行完成
- **Then** `docs/e2e/journey.md` 被创建，包含至少 1 条用户旅程

### AC2: 旅程覆盖 Persona (R2)

- **Given** PRD 定义了 2 个 Persona（普通用户、管理员）
- **When** 生成 journey.md
- **Then** 至少有 2 条旅程，分别覆盖两个 Persona 的主路径

### AC3: 旅程数量不超限 (R4)

- **Given** 一个有 8 个 feature story 的 MVP
- **When** 生成 journey.md
- **Then** Now horizon 旅程 ≤ 5 条

### AC4: Playbook 阶段位置正确 (R1)

- **Given** 修改后的 `project-design/SKILL.md`
- **When** 查看 Phase 1 Group B 的 section 顺序
- **Then** Section 1.5.5 User Journeys 位于 Section 1.5 之后、Section 1.6 之前

## Target Call Chain

```
project-design/SKILL.md Phase 1 Group B
  → Section 1.5 Page/Screen Design
  → Section 1.5.5 User Journeys [新增]
    → 写入 docs/e2e/journey.md (STORY-slim-109 格式)
  → Section 1.6 Prototype Generation
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `~/.claude/skills/project-design/SKILL.md` | Phase 1 Group B 增加 Section 1.5.5 | STORY-slim-109 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | Playbook 文本变更 |
| SEC-2 | No | 无用户输入处理 |
| SEC-3 | No | 无数据库 |
| SEC-4 | No | 无 UI |
| SEC-5 | No | 无认证 |
| SEC-6 | No | 无接口 |
| SEC-7 | No | 无错误输出 |
| SEC-8 | No | 无依赖变更 |

## Out of Scope

- journey.md 的自动 lint/验证工具
- 已有项目的旅程追补生成（只在新项目 Design 时生成）
- 旅程与 CI pipeline 的自动绑定
