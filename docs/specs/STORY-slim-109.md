# STORY-slim-109: E2E journey.md 规范定义与 File Atlas 集成

| Field | Value |
|-------|-------|
| ID | STORY-slim-109 |
| Status | Draft |
| Priority | P1 |
| Release | 2.12.0 |

## Background

当前 PactKit 的 E2E 测试以 story 为单位（Check Phase 4），但真实用户验收是跨 story 的用户旅程。缺少一个"旅程定义"规范，导致：
- 每个 story 的 E2E 各自独立，拼不成完整流程
- LLM 生成 E2E 时从零猜旅程，质量不稳定
- Release 前没有端到端的用户流信心

需要定义 `docs/e2e/journey.md` 作为用户旅程的 Tier 1 来源，并注册到 File Atlas。

## Requirements

### R1: journey.md 格式规范 (MUST)

定义 `docs/e2e/journey.md` 的标准格式：
- 每个旅程包含：旅程名称、步骤序列、每步的断言、前置 fixture
- 步骤标注执行层（`[client]` / `[server]` / `[server+client]`）
- 断言分为"结构断言"（MUST）和"内容断言"（MUST NOT for AI 生成内容）

### R2: File Atlas 注册 (MUST)

在 `03-file-atlas.md` 中注册 `docs/e2e/journey.md` 路径及用途说明。

### R3: 与 Check Phase 4 的关系 (MUST)

在 Check Phase 4 (E2E Execution) 中增加指导：
- 如果 `docs/e2e/journey.md` 存在，E2E 测试应覆盖当前 story 涉及的旅程片段
- journey.md 是旅程的定义来源，test_case 是单个 story 的验收来源

### R4: AI 内容断言策略文档 (SHOULD)

在 journey.md 规范中包含"AI 生成内容断言指南"：
- 断言结构存在（SQL 块、图表组件、回答区域）
- 断言非空
- 不断言具体文字内容或数值

## Acceptance Criteria

### AC1: journey.md 格式可解析 (R1)

- **Given** 一个按规范格式编写的 `docs/e2e/journey.md`
- **When** QA Engineer 在 Check Phase 4 读取该文件
- **Then** 能明确识别每个旅程的步骤、断言和 fixture

### AC2: File Atlas 包含 journey.md (R2)

- **Given** 更新后的 `03-file-atlas.md`
- **When** 查看 File Atlas 表格
- **Then** 包含 `docs/e2e/journey.md` 条目，Purpose 为 "User Journey Definitions"

### AC3: Check Phase 4 引用 journey.md (R3)

- **Given** 项目存在 `docs/e2e/journey.md`
- **When** 执行 `/project-check` Phase 4
- **Then** E2E 执行时参考 journey.md 中的旅程定义

### AC4: AI 断言策略有指导 (R4)

- **Given** journey.md 规范文档
- **When** 定义 AI chatbot 类旅程的断言
- **Then** 规范明确指出"断言结构不断言内容"策略

## Target Call Chain

```
docs/e2e/journey.md (新增规范文件)
  ← 03-file-atlas.md (注册路径)
  ← project-check/SKILL.md Phase 4 (引用)
  ← project-design/SKILL.md Phase 1.5.5 (生成来源，见 STORY-slim-110)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `~/.claude/rules/03-file-atlas.md` | 增加 journey.md 路径注册 | None | Low |
| 2 | `docs/e2e/journey.md` | 创建格式规范模板（含 AI 断言策略） | None | Low |
| 3 | `~/.claude/skills/project-check/SKILL.md` | Phase 4 增加 journey.md 引用指导 | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | 文档规范变更，无代码 |
| SEC-2 | No | 无用户输入 |
| SEC-3 | No | 无数据库 |
| SEC-4 | No | 无 UI |
| SEC-5 | No | 无认证 |
| SEC-6 | No | 无接口 |
| SEC-7 | No | 无错误输出 |
| SEC-8 | No | 无依赖变更 |

## Out of Scope

- E2E 模板库（属于各项目自身，不放 pactkit core）
- Spec `e2e: affected` 标记（过度设计，由 LLM 在 Check 时自行判断）
- Done/Release 双级运行机制（现有 `e2e.blocking` 配置已覆盖）
- journey.md 的自动 lint 工具（留待未来需求驱动）
