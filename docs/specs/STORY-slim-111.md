# STORY-slim-111: Check Phase 4 Playwright 断言策略指南

| Field | Value |
|-------|-------|
| ID | STORY-slim-111 |
| Status | Draft |
| Priority | P1 |
| Release | 2.12.0 |

## Background

Check Phase 4 当前的 E2E 执行指导是框架级的（按 `e2e.type` 分路由），但缺乏**断言策略**指导。特别是 AI chatbot 类产品（如 pactsearch），LLM 生成 E2E 时容易犯两类错误：
1. 用 CSS selector 定位元素（脆，UI 微调就断）
2. 对 AI 生成内容做精确断言（永远会失败）

需要在 Check Phase 4 增加 Playwright 断言策略指南，指导 LLM 写出稳定的 E2E 测试。

## Requirements

### R1: 元素定位策略优先级 (MUST)

在 Check Phase 4 中明确 Playwright 元素定位优先级：
1. Accessibility role + name（最稳定）
2. `data-testid` 属性（次选）
3. CSS selector（最脆，仅在前两者不可用时使用）

### R2: AI 生成内容断言策略 (MUST)

对 AI/LLM 生成的动态内容，断言策略为：
- MUST 断言：结构存在（代码块、图表组件、回答区域）
- MUST 断言：内容非空
- MUST 断言：无 error/exception 状态
- MUST NOT 断言：具体文字内容
- MUST NOT 断言：具体数值

### R3: 等待策略 (SHOULD)

对异步 AI 响应的等待策略指导：
- 用 loading 状态消失作为完成信号（而非固定 timeout）
- 用 streaming 完成标记（如 `[data-streaming="false"]`）作为备选

### R4: 与 journey.md 配合 (SHOULD)

断言策略应与 STORY-slim-109 的 journey.md 格式兼容——旅程中定义的断言应遵循此策略指南。

## Acceptance Criteria

### AC1: 定位策略写入 playbook (R1)

- **Given** 修改后的 `project-check/SKILL.md` Phase 4
- **When** LLM 执行 E2E 测试生成
- **Then** playbook 明确指导优先使用 `get_by_role` 而非 CSS selector

### AC2: AI 内容断言有明确边界 (R2)

- **Given** 一个 chatbot 产品的 E2E 测试场景
- **When** LLM 读取 Check Phase 4 指南
- **Then** 指南明确列出"可断言"和"不可断言"的分界

### AC3: 等待策略有指导 (R3)

- **Given** 一个需要等待 AI 响应的 E2E 步骤
- **When** LLM 编写等待逻辑
- **Then** playbook 指导使用状态信号而非固定 sleep

## Target Call Chain

```
project-check/SKILL.md Phase 4 (E2E Execution)
  → [新增] Playwright 断言策略指南段落
    → 定位优先级
    → AI 内容断言边界
    → 等待策略
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `~/.claude/skills/project-check/SKILL.md` | Phase 4 增加断言策略指南段落 | None | Low |

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

- Playwright MCP 的代码实现变更
- 视觉回归测试（screenshot diff）策略
- 非 Playwright 的 E2E 框架（Cypress, Selenium 等）
- E2E 测试模板库的代码生成
