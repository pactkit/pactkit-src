# STORY-slim-128: Engineering Concerns: Guide-based NFR enforcement

| Field | Value |
|-------|-------|
| ID | STORY-slim-128 |
| Status | Draft |
| Priority | P1 |
| Release | 2.16.0 |

## Background

LLM 编程时系统性缺失非功能性需求（NFR）考量：并发模型、超时策略、缓存一致性、内存管理等。
现有 PactKit 规则体系中，`06-solution-design.md` 只覆盖"复用已有组件"，缺乏对其他 12 类工程关注点的引导。

核心矛盾：如果把所有 NFR 规则放入常驻 prompt，context 膨胀导致注意力衰减；如果不放，LLM 就忽略它们。

解决方案：**按需加载的指南系统** — 一个轻量触发索引（常驻，~40行）+ 13 个精炼指南文件（按需加载，每个 <50 行）。
Plan 阶段：根据需求关键词强制回答 NFR 决策问题（写入 Spec）。
Act 阶段：根据 Spec 中标注的 concerns，动态加载对应指南作为实现约束。

### 调用链
```
rules.py (RULES_MODULES["engineering"]) → deployer._deploy_rules() → ~/.claude/skills/_rules/07-engineering-concerns.md
rules.py (GUIDES_FILES) → deployer._deploy_guides() → ~/.claude/skills/_rules/guides/*.md
commands.py (plan Phase 2 扩展) → deployed SKILL.md
commands.py (act Phase 1.5 扩展) → deployed SKILL.md
```

## Requirements

### R1: Trigger Index Rule (MUST)

新增 `RULES_MODULES["engineering"]` 和 `RULES_ONDEMAND_FILES["engineering"]`，部署为 `07-engineering-concerns.md`。
内容为触发索引表（~40行）：列出关键词→concern 映射，以及 concern→guide 文件的路由表。
此文件通过 `@import` 被 plan/act 命令加载。

### R2: Guides Deployment Mechanism (MUST)

在 `deployer.py` 中新增 `_deploy_guides()` 函数，将 13 个精炼指南文件部署到 `~/.claude/skills/_rules/guides/` 目录。
所有 format 均需支持：Claude Code（文件部署）、OpenCode（inline 或文件）、Codex（文件）、Copilot（文件）。
指南文件源定义在新文件 `src/pactkit/prompts/guides.py` 中（避免 `rules.py` 过长）。

### R3: Guides Content — 13 Engineering Guides (MUST)

每个指南文件 < 50 行，格式统一：决策表 + MUST 清单 + NEVER 清单 + 代码模板。
覆盖：concurrency、async-patterns、configuration、observability、module-design、database、caching、api-integration、event-driven、resilience、memory-management、code-review-first、component-reuse。

### R4: Plan Command Enhancement (MUST)

`project-plan` Phase 2 新增 "Engineering Concerns Assessment" 步骤：
- 扫描需求关键词（定时/API/数据库/缓存/事件/并发等）
- 匹配到的 concern → Spec 的 Technical Design 中 MUST 包含对应 NFR 决策
- 未匹配 → 不强制（避免噪音）

### R5: Act Command Enhancement (MUST)

`project-act` 新增 Phase 1.5 "Engineering Concerns Loading"：
- 读取 Spec 的 Technical Design → 识别标注的 engineering concerns
- 加载对应的指南文件（`read` 指令）
- MUST 只加载相关的 1-3 个，NEVER 全部加载

### R6: Config Integration (SHOULD)

在 `VALID_RULES` 中注册 `"07-engineering-concerns"`。
在 `COMMAND_RULES_MAP` 中为 `project-plan` 和 `project-act` 添加 `"engineering"` key。
支持通过 `pactkit.yaml` 的 `rules` 配置项禁用。

### R7: Multi-format Parity (MUST)

OpenCode、Codex、Copilot 格式均需部署 guides 内容：
- OpenCode/Codex：作为独立文件部署到对应 rules 目录，或 inline 嵌入
- Copilot：写入对应的 prompt 文件中（copilot 不支持动态文件引用，需 inline）
- 各格式 plan/act playbook 均需包含 engineering concerns phase

## Acceptance Criteria

### AC1: Trigger Index Deployed (R1, R6)

- **Given** PactKit 已安装，用户运行 `pactkit init`
- **When** deployer 执行 classic format 部署
- **Then** `~/.claude/skills/_rules/07-engineering-concerns.md` 文件存在，内容包含关键词→concern 映射表和 concern→guide 路由表

### AC2: All 13 Guides Deployed (R2, R3)

- **Given** 用户运行 `pactkit init` 或 `pactkit update`
- **When** deployer 执行部署
- **Then** `~/.claude/skills/_rules/guides/` 目录下存在 13 个 .md 文件，每个文件 < 50 行

### AC3: Plan Phase Triggers NFR Questions (R4)

- **Given** 一个包含 "从第三方 API 拉取数据存入数据库" 的 Story
- **When** Plan Phase 2 执行 Engineering Concerns Assessment
- **Then** Spec 的 Technical Design 中包含：并发模型决策、API 超时/重试策略、数据库连接管理策略

### AC4: Act Phase Loads Relevant Guides Only (R5)

- **Given** Spec 的 Technical Design 标注了 `concerns: [database, api-integration]`
- **When** Act Phase 1.5 执行
- **Then** 只加载 `guides/database.md` 和 `guides/api-integration.md`，不加载其他 11 个指南

### AC5: OpenCode/Codex/Copilot Parity (R7)

- **Given** 用户运行 `pactkit init --format opencode`
- **When** deployer 执行 OpenCode 格式部署
- **Then** 对应目录下存在 engineering concerns trigger index + guides 内容（inline 或文件形式）

## Target Call Chain

```
# 部署链
pactkit init/update
  → deployer._deploy_classic() (deployer.py:302)
    → _deploy_rules(claude_root, enabled_rules) (deployer.py:584)
      → atomic_write(ondemand_dir / "07-engineering-concerns.md") — R1
    → _deploy_guides(claude_root) (NEW) (deployer.py:NEW)
      → atomic_write(guides_dir / "*.md") x13 — R2
    → _deploy_commands(skills_dir, ...) (deployer.py:917)
      → _build_command_rules_header("project-plan") — includes "engineering" — R4
      → _build_command_rules_header("project-act") — includes "engineering" — R5

# 指南内容源
src/pactkit/prompts/guides.py (NEW)
  → GUIDES_FILES: dict[str, str]  — filename → content
  → Referenced by deployer._deploy_guides()
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/guides.py` | 新建：定义 GUIDES_FILES dict（13 个指南内容） | None | Low |
| 2 | `src/pactkit/prompts/rules.py` | 新增 RULES_MODULES["engineering"] 触发索引内容 + RULES_ONDEMAND_FILES 注册 | Step 1 | Low |
| 3 | `src/pactkit/config.py` | VALID_RULES 新增 "07-engineering-concerns" | Step 2 | Low |
| 4 | `src/pactkit/generators/deployer.py` | 新增 _deploy_guides() + 在 _deploy_classic/opencode/codex/copilot 中调用 | Steps 1-3 | Medium |
| 5 | `src/pactkit/prompts/commands.py` | plan Phase 2 新增 Engineering Concerns Assessment 段落 | Step 2 | Low |
| 6 | `src/pactkit/prompts/commands.py` | act 新增 Phase 1.5 Engineering Concerns Loading 段落 | Step 2 | Low |
| 7 | `src/pactkit/prompts/rules.py` | COMMAND_RULES_MAP 为 plan/act 添加 "engineering" | Step 3 | Low |
| 8 | `tests/unit/` | 测试：deployer 部署 guides 目录、plan/act 包含新 phase | All | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | No secrets involved — only prompt/doc content |
| SEC-2 | N/A | No user input processing |
| SEC-3 | N/A | No database queries |
| SEC-4 | N/A | No rendering |
| SEC-5 | N/A | No auth |
| SEC-6 | N/A | No endpoints |
| SEC-7 | N/A | No error messages |
| SEC-8 | N/A | No new dependencies |

## Out of Scope

- CI/lint 自动化检测（semgrep/ruff 自定义规则）— 后续 Story
- 指南文件的热加载/动态选择 AI 判断 — 本 Story 用关键词匹配，不用 LLM 判断
- Check 阶段的完整 13 项 checklist 验证 — 可选后续 Story
