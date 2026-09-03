# ADR-0002-guides-carry-operational-practice-content-not-ju: Guides carry operational practice content, not just decision prompts

| Field | Value |
|-------|-------|
| ID | ADR-0002-guides-carry-operational-practice-content-not-ju |
| Status | accepted |
| Date | 2026-09-03 |
| Supersedes | None |
| Superseded-by | None |

## Context

2026-09-03 用户两次指出 guide"太单薄"：22 个 guide 全为 ~20 行决策卡片，只提示该想到什么、不含好的标准是什么。该空缺由模型训练记忆（未验证知识）填补——是 R6 反编造问题的另一半：R6 要求查证后使用，但项目内应提供的查证源为空。实证链：Capability Assessment 遵循率 1/56（结构问题，W012 已解）→ 触发后的执行质量取决于内容（内容问题，本决策）。

## Options Considered

- **恢复 2.24 前厚内容并常驻**: 已被 2.24 推翻——600 行常驻注意力稀释，遵循率不随篇幅提升。
- **维持薄决策卡片 + 只靠 R6 查证纪律**: 模型被要求"查证"但项目内无查证源，退化为训练记忆或每次外部检索——质量不稳定且慢。
- **加载纪律 × 内容厚度的合成**: 2.24 的条件加载（一次 1-3 个、按 Spec 关键词路由、不占常驻预算）+ 操作型 Practice 段（判据表/红线/反模式+后果，40-60 行）。

## Decision

采用合成方案：GuideDefinition 新增可选 Practice 段（raw markdown，支持表格），guide 保持条件加载纪律，富化按"用户点名 + 遥测触发率"分批（首批判据：logging、module-design、error-recovery）。加载机制保证内容在正确时点到达上下文顶部；内容厚度保证到达后有可执行的标准，消除训练记忆补位。

## Consequences

- 正向：guide 成为项目内"已验证的最佳实践参考"，R6 的来源优先级第一级（项目自身）从空变为实
- 接受的风险：单 guide 内容膨胀失控（缓解：40-60 行上限 + 一次加载 1-3 个的既有纪律）；内容过时漂移（缓解：内容锚点断言测试）
- 后续：其余 20 个 guide 按 W012 遥测触发率分批富化
