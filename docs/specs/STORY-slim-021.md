# STORY-slim-021: Sectional Write for Large Document Generation

| Field | Value |
|-------|-------|
| ID | STORY-slim-021 |
| Status | Done |
| Priority | P1 |
| Release | 2.3.1 |

## Background

当 AI 执行 `/project-design` 生成 PRD 时，当前 playbook 要求 AI 在一个连续输出中完成全部 9 个 section（3 个 Group），然后在最后执行一次 `Write` 保存整个 PRD。对于中等复杂度的产品，PRD 可达 3000-5000 tokens，加上推理 token，很容易撞上模型输出限制或 API 超时。

### 根因分析

1. **延迟写入模式**：`DESIGN_PROMPT` Phase 1 Step 3 指示 "Save the completed PRD"，意味着 AI 必须在内存中持有整个 PRD 直到最后一步
2. **无中间 checkpoint**：虽然提到 "outputting progress after each group"，但只是打印进度，没有触发 Write/Edit 操作
3. **累积效应**：Phase 3 (Story Decomposition) 连续生成 5-10 个 Spec 文件，每个需要 scaffold + Read + fill + lint，累积 turn 数很大

### 影响范围

- `DESIGN_PROMPT` in `src/pactkit/prompts/workflows.py:608-768`
- Phase 1 (PRD): HIGH risk — 单次大文档
- Phase 3 (Specs): MEDIUM risk — 多文件连续生成
- Phase 1.6 (Prototypes): MEDIUM risk — 每个 HTML 页面独立但可能很大

## Target Call Chain

```
DESIGN_PROMPT (workflows.py:608)
  └─ Phase 1: PRD Generation
       ├─ scaffold create_prd → 创建空骨架 ✅ 已存在
       ├─ Read scaffolded file ✅ 已有
       ├─ Fill sections (Group A → B → C) ❌ 一次性输出，延迟 Write
       └─ Write: Save completed PRD ❌ 单次大写入
  └─ Phase 3: Story Decomposition
       └─ For each story: scaffold → Read → fill → lint ⚠️ 无 batch checkpoint
```

## Requirements

### R1: Sectional Write for PRD (MUST)
DESIGN_PROMPT Phase 1 MUST 在每个 Group 完成后立即执行 Write/Edit 操作将该 Group 的内容写入 `docs/product/prd.md`，而不是在所有 section 完成后才执行单次 Write。

### R2: Group 粒度 checkpoint (MUST)
每个 Group (A/B/C) 完成并写入后，MUST 输出一个 checkpoint 消息（例如 "Group A written. Proceeding to Group B."），确保 AI 有明确的中间停顿点。

### R3: Prototype 大小限制 (SHOULD)
Phase 1.6 HTML prototype SHOULD 控制在 200 行以内。如果页面复杂度导致超过 200 行，SHOULD 拆分为多个组件文件或简化。

### R4: Story Decomposition 批次化 (SHOULD)
Phase 3 连续生成多个 Spec 时，SHOULD 每 3 个 Spec 后输出一个进度 checkpoint（例如 "3/8 Specs created."），降低单次连续输出的负担。

### R5: 不改变最终产出 (MUST)
修改后的 playbook MUST 产出与当前版本完全相同的最终文件结构和内容格式。用户不应感知到任何输出差异。

### R6: 内置 Rule — 全局 Sectional Write 协议 (MUST)
MUST 在 PactKit 的 rule 系统中新增 `09-sectional-write` 规则，作为 **Core rule**（始终加载），约束 AI 在生成任何预期超过 300 行的文件时采用分段写入模式。此规则不区分文件类型 — 代码、文档、测试、HTML 均适用。不仅约束 PDCA command，也约束自由对话中的文件生成。

涉及文件：
- `src/pactkit/config.py` — `VALID_RULES` 新增 `"09-sectional-write"`
- `src/pactkit/prompts/rules.py` — `RULES_MODULES` 新增 `"sectional"` 内容，`RULES_CORE_FILES` 新增映射

### R7: Rule 内容规范 (MUST)
`09-sectional-write` 规则 MUST 包含以下要素：
- 适用条件（任何文件类型，预期超过 300 行）
- 操作步骤（Write skeleton → block-by-block Edit → checkpoint）
- 排除场景（短文件 < 300 行、小配置文件）
- 正反示例（anti-pattern vs correct pattern）

## Acceptance Criteria

### Scenario 1: PRD 分段写入

GIVEN DESIGN_PROMPT 已更新为 sectional write 模式
WHEN AI 执行 /project-design 生成 PRD
THEN Group A (Section 1.1-1.2) 完成后立即 Edit 写入 prd.md
AND Group B (Section 1.3-1.6) 完成后立即 Edit 追加写入 prd.md
AND Group C (Section 1.7-2.0) 完成后立即 Edit 追加写入 prd.md
AND 每个 Group 之间有 checkpoint 输出

### Scenario 2: Spec 批次 checkpoint

GIVEN Phase 3 需要生成 6 个 Spec
WHEN AI 执行 Story Decomposition
THEN 每 3 个 Spec 后输出进度 checkpoint
AND 所有 Spec 通过 spec-lint 校验

### Scenario 3: 最终产出一致性

GIVEN 一个已知的产品描述
WHEN 分别用旧版和新版 DESIGN_PROMPT 生成
THEN 最终 prd.md 包含完全相同的 9 个 section
AND docs/specs/ 下的 Spec 数量和格式一致

### Scenario 4: Rule 部署验证

GIVEN pactkit 已更新 VALID_RULES 和 RULES_MODULES
WHEN 用户运行 pactkit init 部署规则
THEN 09-sectional-write.md 文件出现在用户的 rules 目录中
AND VALID_RULES 包含 9 个元素
AND 部署后的规则文件内容包含 sectional write 协议

## Non-Goals
- 不改变 PRD 的内容结构或 section 数量
- 不改变 Spec 的格式或 scaffold 模板
- 不添加新的 CLI 命令或工具

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/config.py` | `VALID_RULES` 新增 `"09-sectional-write"` | None | Low |
| 2 | `src/pactkit/prompts/rules.py` | `RULES_MODULES` 新增 `"sectional"` 规则内容；`RULES_CORE_FILES` 新增映射 | Step 1 | Low |
| 3 | `src/pactkit/prompts/workflows.py` | 修改 DESIGN_PROMPT Phase 1: 每个 Group 后 Edit 追加写入 | None | Low |
| 4 | `src/pactkit/prompts/workflows.py` | 修改 DESIGN_PROMPT Phase 3: 添加批次 checkpoint 指令 | Step 3 | Low |
| 5 | `tests/unit/` | 测试 VALID_RULES 计数、RULES_MODULES 包含 sectional、DESIGN_PROMPT 包含 sectional write 指令 | Step 1, 2, 3, 4 | Low |
| 6 | 部署验证 | `pactkit init` 重新部署，验证 09-sectional-write.md 出现在 rules 目录 | Step 1-5 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Prompt text only, no source code logic |
| SEC-2 | N/A | No user input handling |
| SEC-3 | N/A | No authentication changes |
| SEC-4 | N/A | No data storage changes |
| SEC-5 | N/A | No API changes |
| SEC-6 | N/A | No dependency changes |
| SEC-7 | N/A | No infrastructure changes |
| SEC-8 | N/A | No secret handling |
