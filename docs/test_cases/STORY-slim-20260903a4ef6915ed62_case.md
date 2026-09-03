# Test Cases: STORY-slim-20260903a4ef6915ed62 — 规则遵循遥测与四类诊断闭环

> 实现位置:`tests/unit/test_rule_diagnostics.py`(17 用例)。

## TC-1: 事件白名单与不阻断 (R1, R6, AC2)

**Given** rules.jsonl 事件路径
**When** append_rule_event 写入合法/非法事件 + 磁盘故障注入
**Then** 载荷仅含白名单字段（event/guide/rule/spec/ts）；未知事件类型抛 ValueError；I/O 失败静默不阻断调用方
**Impl** `TestRuleEvents::*`

## TC-2: guide show 咽喉点 (R2, AC1)

**Given** 部署了 caching guide 的临时 root
**When** `guide show caching` / `guide show nope` / 穿越式名字
**Then** 输出内容+记录 guide_loaded；未知名 exit 1 列可用名；穿越名不解析（白名单）
**Impl** `TestGuideShow::*`

## TC-3: 信号 1 四类边界 (R3, AC3)

**Given** 四个构造场景（未部署 / guides: 排除 / 无 concern 场景 / concern 存在零加载）
**When** diagnose_guide 判定
**Then** 分别归 bug/config/rule_design/usage；config 给出含 `guides:` 的 yaml 修法；usage 带 medium 置信与绕过标注；finding 含 class/evidence/action 三元组
**Impl** `TestSignal1GuideZeroLoad::*`（注:①类判据经 E2E 修正为 guides: 键语义——rules: 管 capsule 不管 guide,原判据批量误报）

## TC-4: 信号 2 W012 边界 (R3)

**Given** 误报样本（触发但 Spec 有评估表）/ 高触发率 / 低触发率
**When** diagnose_w012 判定
**Then** 分别归 bug / usage / 无 finding
**Impl** `TestSignal2W012Rate::*`

## TC-5: 消费端接线 (R4, R5, AC4, AC5)

**Given** guides: 排除配置的 root / 排除配置给 garden
**When** doctor.check_rule_health / garden.check_dead_rules
**Then** doctor 输出 ①类 finding；garden 对 config 排除的 guide 不双报
**Impl** `TestConsumers::*`

## TC-6: 本地性红线 (R6, AC6)

**Given** 事件写入路径
**When** socket 注入断言
**Then** 无网络调用；载荷白名单（与 TC-1 互补锁定）
**Impl** `TestLocality::test_no_network_in_event_path`
