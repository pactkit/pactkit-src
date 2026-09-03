# ADR-0003-rule-telemetry-is-consumed-at-code-touchpoints-w: Rule telemetry is consumed at code touchpoints with diagnosis classification, not dashboards

| Field | Value |
|-------|-------|
| ID | ADR-0003-rule-telemetry-is-consumed-at-code-touchpoints-w |
| Status | accepted |
| Date | 2026-09-03 |
| Supersedes | None |
| Superseded-by | None |

## Context

2026-09-03 规则层大改造后暴露：规则有效性只能靠一次性考古（487MB transcript 挖掘）；用户对遥测 story 的第一反应是"什么时候会去使用这些数据"——正中"没人读的仪表盘"风险。与条件触发规则 ~2% 遵循率同构：被动等人读的报表遵循率同样趋零。

## Options Considered

- **埋点+stats 报表**: 用户主动跑 stats 查看——与"条件触发规则"相同的低遵循率风险；且只回答"发生了什么"不回答"该改什么"。
- **doctor/garden code 层消费**: 阈值检查进 doctor（done Phase 2 必经点自动触达）、死规则进 garden 巡检——数据在用户本来就会看的地方自动浮现。
- **带诊断分类的消费**: 消费不止于告警——每个 finding 归因四类（config/bug/usage/rule_design）并给出精确动作（yaml 键值/报 issue/流程建议/裁撤反馈），否则用户仍需自行判断"是参数还是 bug"。

## Decision

采用"code 层触点 + 四类诊断分类"：遥测消费端必须是 doctor WARN / garden 建议（或既有流程必经点），禁止新建"看报表"仪式；每个 finding MUST 携带 class/evidence/action 三元组——区分 PactKit 参数问题、PactKit bug、使用习惯、规则设计四类归因。guide 加载经 `pactkit guide show` 咽喉点观测（用户裁决 2026-09-03）。

## Consequences

- 正向：数据在 done/garden 流程自动浮现（本日 doctor Rule conflict 被看到处理 3 次实证该路径有效）；④ rule_design 类使遥测回流指导 PactKit 自身规则迭代（裁撤/升级 code 强制）
- 接受的风险：guide show 咽喉点可被裸 Read 绕过——③ 类归因标注中置信度；诊断判据边界错误会误导用户——纯函数决策树 + 边界单测锁定
- 数据本地性红线：全部事件仅落 .pactkit/（gitignored），永不外发（企业隐私）
