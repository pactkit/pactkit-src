# Test Cases: STORY-slim-20260905efced66ebc9c — 剧本-契约冲突修复 R1-R6

> 实现位置:`tests/unit/test_contract_conflict_fixes.py`(26 断言) + 镜像同步
> (`tests/unit/test_story_slim011_command_rules.py` SPEC_TABLE、
> `tests/unit/test_story037_regression_fix.py` AC1、golden 三件套)。

## TC-1: coverage 门禁降级 (R1, AC1)

**Given** 渲染后的 project-done 剧本
**When** 检查 Step 2.3（原 2.5）coverage 分级文本
**Then** 不含 "BLOCK for confirmation"；<50% 为 acceptance gap 报告并继续；≥80% PASS / 50–79% WARN 语义不变
**Impl** `TestR1CoverageGate::*`

## TC-2: Act 工具限制带记录回退 (R2, AC2)

**Given** 渲染后的 project-act 剧本
**When** 检查 Phase 1 Provider-Routed Scan 与 Phase 3 regression 段
**Then** "Do not invoke" 绝对禁令消失；两处含 "degradation reason" 记录路径；`--allow-fallback` 保留
**Impl** `TestR2RecordedFallback::*`

## TC-3: lesson-append 缺口报告 (R3, AC3)

**Given** 渲染后的 project-done 剧本
**When** lesson-append 不可用分支
**Then** 无 "stop and request a Core upgrade"；共享 Lesson 投影手写禁令保留
**Impl** `TestR3LessonAppendGap::*`

## TC-4: 任务勾选免强制询问 (R4, AC4)

**Given** 渲染后的 project-done 剧本
**When** 测试 GREEN 且任务未勾选分支
**Then** 无 "Tests passed but tasks are unchecked" 询问；指示核验证据后经 board complete-task 更新
**Impl** `TestR4TaskAutoFix::*`

## TC-5: 指纹机制行为 (R5, AC5)

**Given** tmp git 仓库（init + commit）
**When** `record_verification` 后分别：无变化 / 改 source / 改后 commit / 改 doc-only / 无记录 / 非 git 目录 / 穿越式 story ID
**Then** 依次：VERIFIED-CURRENT / STALE 含文件名 / STALE 含文件名 / VERIFIED-CURRENT / NO-RECORD / 降级消息且不写文件 / ValueError；记录含 schema_version/commit/fingerprint
**Impl** `TestR5RecordAndCheck::*`(9 断言)

## TC-6: 剧本接入指纹基线 (R5, AC6)

**Given** 渲染后的 project-act 与 project-done 剧本
**When** 检查 regression 段
**Then** Act 含 `regression --record` 指引；Done 含 `regression --check-record`；两剧本无 `HEAD~1`
**Impl** `TestR5PlaybookBaseline::*` + `test_story037::test_condition_1_is_verifiable`

## TC-7: 四命令挂载准确胶囊 (R6, AC7)

**Given** 更新后的 RULE_DEFINITIONS / COMMAND_RULES_MAP
**When** 校验 init/clarify/design/debug 映射与 phase-plan scope
**Then** 四命令各挂自己的胶囊；phase-plan scope=("project-plan",)；classic 部署的 project-init SKILL.md 含 init-contract.md @import 且无 plan-contract.md
**Impl** `TestR6PhaseCapsules::*` + `test_story_slim011::SPEC_TABLE`

## TC-8: 预算与级联完整性（063 补偿，用户批准方案）

**Given** COMMANDS_CONTENT 总量与 Done 回归门 Step 级联
**When** 063 预算测试与 057/050 级联测试运行
**Then** 总量 ≤ int(106611×0.85)（基线 +270 为 R5 核准增长）；Step 1.6 重复已删、FULL→Step 3 路由在 1.3、决策日志句并入 Step 2、SKIP/STORY-ONLY 格式保留
**Impl** `test_story063::TestAC7PromptSizeReduced` + `test_story057::TestRegressionGateCascade` + `test_story050::*`
