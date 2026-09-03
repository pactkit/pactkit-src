# STORY-slim-20260903b5ce6be5f7e0: Guide 实践层:Practice 段机制+observability/module-design/error-recovery 三 guide 富化

| Field | Value |
|-------|-------|
| ID | STORY-slim-20260903b5ce6be5f7e0 |
| Status | Done |
| Priority | P1 |
| Release | 2.26.0 |

## Background

2026-09-03 用户两次指出 guide 内容"太单薄"（"就那么简单的一句话，能起到作用么"）。诊断：22 个 guide 全部是 ~20 行决策卡片（Trigger/Questions 六段式），只提示"该想到什么"，不含"好的标准是什么"——该空缺由模型训练记忆填补，即未验证知识，直接导致用户此前抱怨的"AI 自己编造、不查业内最佳实践"。这是 R6（Knowledge Provenance）问题的另一半：R6 要求查证后再用，但项目内本应提供的查证源是空的。

两个时代的正确合成（ADR-0002 记录）：2.24 的加载纪律（条件触发、一次 1-3 个、不占常驻预算）× 2.24 前的内容厚度（判据表/红线/反模式+后果）。本 story 为第一批三个 guide（用户点名的 observability/logging 与 module-design/拆分 + 高频 error-recovery），后续批次按 W012 遥测触发率排。

## Technical Design

### Lateral Scan Results

- Operation "guide 渲染段": 1 处（GuideDefinition.render, guides.py:29）→ 复用：practice 非空时在 Defaults 后插入 verbatim 块
- Operation "guide 内容定义": 1 处（GUIDE_DEFINITIONS + _guide）→ 复用：加 keyword-only practice 参数
- Operation "guide 结构测试": 1 处（test_guides_are_native_seven_section_documents）→ 复用并扩展

### Capability Assessment

| Need | Source | Decision |
|------|--------|----------|
| 渲染可选段 | 项目自有 GuideDefinition.render | Reuse |
| 内容格式 | raw markdown block（表格必须原样渲染，不进 bullet join） | New（机制扩展） |
| 预算影响 | guides 条件加载、不占 COMMANDS_CONTENT 15% 预算 | 无冲突（已核实测试只计 COMMANDS_CONTENT） |

## Requirements

### R1: Practice 段机制 (MUST)

GuideDefinition MUST 新增 `practice: str = ""` 字段（frozen dataclass 带默认值，现有 22 个 guide 零改动）；`_guide()` MUST 接受 keyword-only `practice` 参数；`render()` 在 practice 非空时于 Defaults 之后渲染 `## Practice` 段（verbatim 原样输出，支持表格，不做 bullet 前缀）。

### R2: observability Practice——日志管理 (MUST)

observability.md 的 Practice 段 MUST 含操作型内容（40-60 行）：日志级别判据表（ERROR/WARN/INFO/DEBUG 各自用于与绝不用于）、结构化字段约定（correlation 字段跨层可串联、event= 动词开头、字段名 snake_case、不拼 message）、体量治理红线（循环内禁止逐条 INFO、批量记汇总、redaction 在 log 入口统一做而非各调用点自查）、反模式各附一行后果（log-and-rethrow、级别当流程控制）。

### R3: module-design Practice——模块拆分判据 (MUST)

module-design.md 的 Practice 段 MUST 含：拆分判据（单句职责表述测试——说不出一句话的职责就该拆、公共接口面参考线、行数参考线 500 行评估线）、分层规则（domain 不 import infrastructure、循环依赖 = 分层违规修结构不修症状）、提取时机 vs 过早抽象的判别、命名约定（模块名按职责不按技术）。

### R4: error-recovery Practice——错误分类学 (MUST)

error-recovery.md 的 Practice 段 MUST 含：错误三分类（transient 可重试 / permanent 不可重试 / programming 编程错误不重试直接修）与分类决策树、用户面与日志面文案分离（用户看行动建议、日志看诊断细节，同一错误两副面孔）、重试边界（bounded backoff 参数化、幂等键防重复）、错误类型层次设计（一个基类 + 按恢复策略分子类，不按来源分）。

### R5: 结构测试扩展 (MUST)

七段测试扩展为：七段仍必需于全部 23 个 guide + Practice 可选；新增内容断言——三个富化 guide 的渲染产物含各自关键锚点（级别表/"single-sentence responsibility"/三分类），防内容漂移回归。

## Acceptance Criteria

### AC1: Practice 段机制 (R1)

- **Given** GuideDefinition(practice="| a | b |\n|---|---|")
- **When** render()
- **Then** 输出含 `## Practice` 段且表格原样（无 "- " 前缀）；practice="" 时无该段；现有 22 个 guide 渲染不变

### AC2: observability 富化 (R2)

- **Given** 渲染后的 observability.md
- **When** 检查 Practice 段
- **Then** 含四级别判据表、correlation 字段约定、循环禁打红线、log-and-rethrow 反模式及后果

### AC3: module-design 富化 (R3)

- **Given** 渲染后的 module-design.md
- **When** 检查 Practice 段
- **Then** 含单句职责测试、500 行评估线、domain→infra 依赖方向、循环依赖=分层违规

### AC4: error-recovery 富化 (R4)

- **Given** 渲染后的 error-recovery.md
- **When** 检查 Practice 段
- **Then** 含三分类决策树、用户面/日志面分离、bounded backoff、按恢复策略分类

### AC5: 结构测试与部署 (R5)

- **Given** 扩展后的结构测试与 pactkit update
- **When** 测试运行 + 部署后检查 ~/.claude/skills/_rules/guides/
- **Then** 测试全绿；三个 guide 的部署副本含 Practice 段

## Target Call Chain

- `src/pactkit/prompts/guides.py` — GuideDefinition.practice 字段 + render() Practice 段 + _guide() practice 参数 + 三个 guide 的 Practice 内容
- `tests/unit/test_story_pdca_semantics_v2.py` — 七段测试扩展（Practice 可选）
- `tests/unit/test_story_20260903b5_practice_guides.py`（新）— R1-R4 内容断言

## Implementation Inputs

| Path | Purpose |
|------|---------|
| `src/pactkit/prompts/guides.py:L13-L60` | GuideDefinition/_guide/render 现结构——R1 扩展点 |
| `tests/unit/test_story_pdca_semantics_v2.py:L118-L135` | 七段测试——R5 扩展对象 |
| `src/pactkit/prompts/rules.py:L733-L805` | engineering index 路由——确认三 guide 触发词已存在（无需改） |

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_20260903b5_practice_guides.py` | R1-R5 断言测试先写（RED） | None | Low |
| 2 | `src/pactkit/prompts/guides.py` | practice 字段 + render + _guide 参数 | 1 | Low |
| 3 | `src/pactkit/prompts/guides.py` | 三个 guide 的 Practice 内容写入 | 2 | Medium（内容质量是本 story 核心价值） |
| 4 | `tests/unit/test_story_pdca_semantics_v2.py` | 七段测试扩展 Practice 可选 | 1 | Low |
| 5 | `pactkit update` + 部署验证 | 三 guide 部署副本抽查 | 4 | Low |

## Security Scope

> 纯 prompt 内容与渲染格式扩展。`pactkit sec-scope` 对 guides.py 文件级扫描命中按 diff 实际评估：

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | 无 credential 处理；Practice 内容含 redaction 指导本身，非 secret |
| SEC-2 | No | 渲染输入为源码常量，无外部输入 |
| SEC-3 | No | 无数据库模式 |
| SEC-4 | No | 无前端文件 |
| SEC-5 | No | 无 auth 行为变化 |
| SEC-6 | No | 无 API/路由 |
| SEC-7 | No | 无错误处理弱化 |
| SEC-8 | No | 无依赖变化 |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | Guide Practice 段机制；三个 guide 的操作型内容（logging/拆分/错误分类） |
| Touches | `src/pactkit/prompts/guides.py`, `tests/unit/test_story_pdca_semantics_v2.py`, `tests/unit/`（新） |
| Conflict risk | LOW — guides.py 当日变更已提交（736fb74），工作区干净 |

## Out of Scope

- 其余 20 个 guide 的富化（第二批起，按 W012 遥测触发率排优先级）
- guide 内容的 i18n（英文为部署语言）
- Practice 段的独立 lint 规则（先看实际内容漂移情况）
- T3 项（SLO/portability/威胁建模等）
