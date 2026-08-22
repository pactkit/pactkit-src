# Test Cases: STORY-slim-146 — 全 Skill 可恢复执行契约与 Act 断点续作

> Spec: docs/specs/STORY-slim-146.md
> Unit tests: tests/unit/test_story_slim146.py
> CLI E2E tests: tests/e2e/cli/test_story_slim146_cli.py

## TC-01: 全部 Runtime Skill 均有唯一恢复契约 (AC1, R1)

- **Given** canonical `SKILL_MANIFEST` 中的全部 runtime skill
- **When** 执行恢复契约完整性校验
- **Then** 每个 skill 恰有一个恢复类别和明确策略，未知或缺失条目导致校验失败

Verified by: `TestSkillRecoveryContracts::test_contracts_cover_manifest_exactly_once`

## TC-02: 安全边界原子保存且证据不可伪造 (AC2, R2, R3)

- **Given** Act 依次到达 preflight、RED、GREEN 与 regression/lint 边界
- **When** 通过唯一 checkpoint writer 保存证据并模拟写入失败或并发竞争
- **Then** 状态按顺序原子推进，旧状态不被半写覆盖，真实 Spec lint 与阶段证据均通过代码校验

Verified by: `TestContinuationStore::test_explicit_checkpoint_is_atomic_and_sanitized`, `test_checkpoint_holds_process_lock_across_read_validate_write`, `test_preflight_runs_real_spec_lint_instead_of_trusting_claim`

## TC-03: 新会话只读恢复到下一安全步骤 (AC3, R3, R4)

- **Given** 未过期的 GREEN checkpoint
- **When** 新会话运行 `continuation resume`
- **Then** 只输出 `regression_lint` 为下一步且 checkpoint 字节不变，不重复实现或 Board 写入

Verified by: `TestContinuationStore::test_resume_is_read_only_and_returns_next_safe_step`, `test_checkpoint_then_resume_is_read_only`

## TC-04: 过期或 blocked 状态不会被洗白 (AC4, R2, R4)

- **Given** Spec、Board、HEAD、工作树发生变化，或 checkpoint 为 blocked
- **When** 请求 resume 或继续推进
- **Then** 系统只读阻断并指出差异；blocked 保留最后可信指纹，必须显式 fresh preflight 才能建立新周期

Verified by: `test_changed_artifacts_block_resume_without_writing`, `test_changed_worktree_blocks_resume_without_writing`, `test_blocked_input_change_requires_explicit_fresh_preflight`

## TC-05: 完成门禁要求全量可追溯证据 (AC5, R3)

- **Given** 任一 MUST requirement、AC、测试、lint、回归或当前 Story Board task 缺失或为空
- **When** 尝试写入 completed checkpoint
- **Then** Core 拒绝完成，且真实运行 Spec linter、核对 Story 范围内的 Board task 与非空覆盖证据

Verified by: `test_completion_requires_all_evidence_and_board_tasks`, `test_completion_requires_coverage_for_every_must_requirement`, `test_completion_requires_coverage_for_every_acceptance_criterion`, `test_completion_requires_board_task_evidence_to_match_board`

## TC-06: 高副作用操作必须人工确认 (AC6, R1, R4)

- **Given** release/tag/publish、Board archive/snapshot/add_story、audit append 或 draw 等操作
- **When** 校验 skill 恢复契约或请求恢复
- **Then** 契约仅允许明确列出的幂等 Board 操作自动重跑，其余操作保持 manual confirmation

Verified by: `TestSkillRecoveryContracts::test_high_side_effect_skills_require_manual_confirmation`, `test_contracts_encode_operation_level_replay_exceptions`

## TC-07: 四种真实部署保留同一恢复语义且无越界写入 (AC7, R5)

- **Given** Classic、OpenCode、Codex、Copilot 的隔离 target、cwd 与 HOME
- **When** 使用真实 deployer 渲染 canonical project-act
- **Then** 四份产物均包含 resume/checkpoint/blocker/coverage 语义，不含已知损坏签名，且 target 外文件快照不变

Verified by: `TestSkillRecoveryContracts::test_canonical_act_keeps_recovery_semantics_in_every_profile`, `TestContinuationStore::test_real_adapter_deployments_keep_act_recovery_contract`

## TC-08: 旧项目与诊断工具安全兼容 (AC8, R6)

- **Given** 项目没有 checkpoint、只有 legacy context，或存在 corrupt/completed/stale checkpoint
- **When** 运行 status、resume、doctor 或 garden
- **Then** 命令不破坏已有状态；legacy 要求从 preflight 开始，doctor/garden 返回对应安全诊断且不泄漏绝对路径或 secret

Verified by: `test_legacy_handoff_requires_a_new_preflight_checkpoint`, `test_diagnostics_reports_corrupt_checkpoint`, `test_doctor_diagnostics_ignores_completed_but_garden_keeps_it`, `test_corrupt_checkpoint_error_does_not_expose_absolute_home_path`
