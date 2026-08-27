# Test Cases: STORY-slim-20260827eddbe9669c87 — 授权审计事件对与 outcome_unknown 恢复语义

## TC-1: 授权 asked/granted 自动配对 (R1, AC1)

**Given** run 以 `blocked + blocker_kind=authorization` 写入后解除推进
**When** 读取事件流
**Then** `authorization_asked`（detail 含清洗后的 blocker 文本）与 `authorization_granted` 按时间序成对；user_input/external_state kind 不产生 authorization 事件
**覆盖** `tests/unit/test_continuation_hardening.py::TestAuthorizationAuditEvents`

## TC-2: deny 写入审计并重写 blocker (R2, AC2)

**Given** authorization-blocked 的 checkpoint
**When** `ContinuationStore.deny(story, reason)`
**Then** 事件流新增 `authorization_denied`（detail 含 reason）；checkpoint blocker 变为 `denied: <reason>`；重复 deny 报 "already denied"
**覆盖** `TestDenyCommand`

## TC-3: deny 前置校验 (R2, AC3)

**Given** in_progress（非 blocked）的 run
**When** deny
**Then** ContinuationError（CLI exit 1），零写入
**覆盖** `TestDenyCommand::test_ac3_*`

## TC-4: 围栏正常开合 (R3, AC4)

**Given** commit-gate 完整跑完一次
**When** 读取 enforcement 记录
**Then** 终态（非 running）
**覆盖** `TestAttemptFencing::test_ac4_completed_run_leaves_terminal_record`

## TC-5: Ctrl-C 留下未闭合围栏 (R3, AC5)

**Given** run_gate 在终态记录前被 KeyboardInterrupt 中断（KeyboardInterrupt 是 BaseException，穿透 self-lock 的 except Exception）
**When** 读取 enforcement 记录
**Then** `status: "running"`；损坏围栏文件读取为 None（视为无围栏）
**覆盖** `TestAttemptFencing::test_ac5_interrupted_run_leaves_open_fence` + corrupt fence 测试

## TC-6: outcome_unknown 阻塞与解除 (R4, AC6)

**Given** in_progress run + 未闭合围栏
**When** `resume` / `finish_guard`
**Then** resume blocked 且理由含 "outcome unknown"；finish_guard 附同一理由；围栏闭合（终态记录写入）后 resume 恢复 `resume_at` 且无 unknown 理由
**覆盖** `TestOutcomeUnknownRecovery`

## TC-7: 无围栏行为不变 (R3/R4, AC7)

**Given** 无任何 enforcement 记录的项目
**When** resume
**Then** 决策与 2.24.0 前完全一致（`resume_at` + 空 reasons）
**覆盖** `TestOutcomeUnknownRecovery::test_ac7_no_fence_behaves_as_before`

## TC-8: stats 授权决策计数 (R5, AC8)

**Given** 含 asked→denied 剧情的事件流
**When** `pactkit stats --format json`
**Then** `authorization_decisions == {asked: 1, granted: 0, denied: 1}`
**覆盖** `TestStatsAuthorizationCounts`

## TC-9: 既有回归

**Given** 本 Story 全部变更
**When** `pytest tests/unit/ tests/e2e/ tests/integration/ -q`
**Then** 4703 passed（4689 + 14 新测试）；golden CLI（continuation.txt）含 deny 子命令
