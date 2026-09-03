# ADR-0001-compliance-enforcement-lives-in-code-gates-promp: Compliance enforcement lives in code gates; prompts only shape execution

| Field | Value |
|-------|-------|
| ID | ADR-0001-compliance-enforcement-lives-in-code-gates-promp |
| Status | accepted |
| Date | 2026-09-03 |
| Supersedes | None |
| Superseded-by | None |

## Context

2026-09-03 对话记录实证（487MB transcripts / 166 次 PDCA 调用）：条件触发的协议步骤遵循率天然极低——Capability Assessment 在 56 次 /project-plan 中仅产出 1 次（~2%），旧版 160 行规则的遵循率与一句话 capsule 无显著差异。同日代码层防线实测拦截 32 次 L1 违规尝试（secrets-gate 19 次），全部靠 code 兜底；而本 story 实现过程中，prompt 体积预算、adapter 路径完整性、死子命令检测三个 code gate 各抓到一次真实违规。

## Options Considered

- **Prompt-only（加长/细化规则文本）**: 2.24 前的常驻 600 行模式。已被否定——注意力稀释，遵循率不随篇幅提升，且常驻 token 成本高。
- **Code-only（全部下沉为 gate）**: 确定性约束的最强形态，但判断类语义（域材料相关性、设计权衡）无法机械判定，强行 code 化会产生误报门禁。
- **分层混合**: code 层保证"被触发"（lint W 规则、gate、不变量测试），prompt 层只负责"触发时做对"（capsule 写清产出物格式与判据）。

## Decision

采用分层混合：凡可机械判定的遵循保证（结构存在性、路由可达性、预算上限、路径完整性）MUST 下沉 code 层；prompt 层承载判断类指导并以可验证产出物（表格/检查点）形式表述。W012、TestEveryDeployedGuideIsRoutable、prompt 体积预算测试即本决策的首批实例。

## Consequences

- 正向：遵循保证不依赖模型注意力；防线可回归测试；新规则上线即被不变量覆盖
- 接受的风险：code 门禁的关键正则/逻辑若无直测会静默失效（同日 _INLINE_RANGE 死代码事故为证）——因此每个新 gate 必须伴随直测
- 后续：rule-level 遵循遥测（backlog 候选）以量化分层效果
