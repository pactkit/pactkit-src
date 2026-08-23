# Test Cases: STORY-slim-20260823de7e85d6042a — Codex Stop Hook 强制续跑与真实宿主完成门禁

> Spec: docs/specs/STORY-slim-20260823de7e85d6042a.md
> Core tests: tests/unit/test_story_slim_stop_hook.py
> Codex adapter tests: pactkit-codex/tests/unit/test_story014_stop_hook.py

## TC-01: 未完成 workflow 由原生 Stop Hook 阻止结束 (AC1, R1, R3, R8)

- **Given** Codex 已安装受信任的同步 Stop hook，当前 PactKit run 尚未完成
- **When** Codex 触发 Stop 事件且 Core finish guard 要求继续
- **Then** handler 只输出合法 `decision: block` JSON，携带 run、workflow、下一步骤和 reason code，并让同一 run 继续执行

Verified by: `test_incomplete_workflow_blocks_stop_and_records_sanitized_trace`, `test_real_hook_observation_promotes_manifest_only_after_block_then_done`

## TC-02: Session 绑定与 active run 解析保持确定性 (AC3, AC4, R2)

- **Given** session/turn 已绑定、仅有一个 active run、没有 active run及存在多个 active run四种状态
- **When** Stop handler 解析当前工作流
- **Then** 优先采用散列后的 session 绑定，仅在唯一 active run 时回退；普通对话放行，多 run 歧义不猜测

Verified by: `test_session_binding_hashes_identifiers_and_resolves_bound_run`, `test_resolve_host_run_rejects_multiple_active_runs`, `test_no_active_run_allows_normal_stop`, `test_ambiguous_runs_fail_safe_without_guessing`

## TC-03: 完成和真实人工边界允许结束 (AC2, R3, R5)

- **Given** run 已通过 completion validation，或 Core 返回需要用户授权/外部输入的 `await_user`
- **When** Stop hook 映射 finish guard 决策
- **Then** handler 返回空对象允许结束，不伪造完成，也不自动执行 commit、archive、tag、publish、release、push 或 PR

Verified by: `test_completed_workflow_allows_stop_and_records_done`, `test_await_user_allows_stop_without_crossing_manual_boundary`

## TC-04: 重入、无进展和完成态不可逆 (AC5, R4)

- **Given** Stop hook 已处于 continuation 重入、步骤无进展、attempt 超限或 run 已 completed
- **When** handler 再次触发 host continuation
- **Then** 系统不会无限 block，安全转为 handoff；completed generic run 不会被 legacy checkpoint 或 resume failure 降级

Verified by: `test_recursive_stop_does_not_loop_on_ambiguous_state`, `test_completed_generic_act_is_not_downgraded_by_legacy_checkpoint`, `test_completed_run_is_immutable_to_resume_failure`

## TC-05: Hook 输入、日志和失败路径保持安全 (AC9, R1, R9)

- **Given** 有效或损坏的 Stop stdin、cwd、session/turn ID 和不可信 last assistant message
- **When** handler 解析事件、调用 Core 并记录 observation
- **Then** stdout 始终符合 Hook JSON schema；日志只含不可逆引用和决策元数据，不保存消息、凭证或 evidence payload，错误路径稳定且不改业务 artifact

Verified by: `test_invalid_event_fails_closed_with_valid_json`, `test_trace_never_persists_last_assistant_message_or_evidence`, `test_cli_invalid_json_emits_valid_block_response`

## TC-06: 部署与卸载无损管理用户 Hooks (AC6, R1, R7)

- **Given** `hooks.json` 已包含用户或其他插件的 handlers
- **When** 首次部署、重复部署、升级和卸载 PactKit Stop hook
- **Then** adapter 只新增、替换或移除 PactKit-owned entry，保留其他内容且不产生重复 handler；配置不含开发仓库绝对路径

Verified by: `test_deploy_stop_hook_merges_idempotently_and_preserves_user_hooks`, `test_remove_stop_hook_only_removes_owned_entry`, `test_packaged_console_script_uses_stable_command_name`

## TC-07: Capability 必须基于真实信任和同 run 闭环 (AC7, AC8, R6)

- **Given** Hook 分别处于仅安装、未信任、只观察 block、跨 run 分散观察，以及同一 run 已观察 block→done 的状态
- **When** adapter、manifest 与 doctor 计算 continuation capability
- **Then** 只有 hash、协议、信任和同 run 闭环全部匹配时才报告 `completion_hook=true`、`auto_resume_available=true` 和 `guarantee_level=host`

Verified by: `test_installed_but_unobserved_hook_does_not_claim_host_guarantee`, `test_validation_requires_block_and_done_on_same_run`, `test_real_hook_observation_promotes_manifest_only_after_block_then_done`, `test_doctor_reports_codex_hook_capability_states`

## TC-08: Core session/turn 绑定不泄露宿主标识 (R2, R9)

- **Given** Codex 提供原始 session_id 与 turn_id
- **When** workflow start 或 Stop fallback 建立 host binding
- **Then** continuation state 与绑定索引只保存 SHA-256 引用，并始终用 generic run_id 调用 finish guard

Verified by: `test_session_binding_hashes_identifiers_and_resolves_bound_run`, `test_completed_generic_act_is_not_downgraded_by_legacy_checkpoint`

## TC-09: Adapter 复用 Core 决策而不复制 workflow 规则 (R3, R4, R5)

- **Given** Core 返回 done、await_user、continue_current_turn、resume_session 或安全失败决策
- **When** Codex adapter 处理 Stop
- **Then** adapter 通过 `HostContinuationRunner` 映射宿主响应，步骤、evidence、lease、attempt 与人工操作规则仍由 Core 管理

Verified by: `test_incomplete_workflow_blocks_stop_and_records_sanitized_trace`, `test_completed_workflow_allows_stop_and_records_done`, `test_await_user_allows_stop_without_crossing_manual_boundary`

## TC-10: Plan 与 Done 的阶段总结不能绕过完成门 (AC1, AC10, R8)

- **Given** 真实 Codex run 在 Plan 或 Done 中只输出阶段总结，仍有 HLD、Board、归档、部署或提交步骤未完成
- **When** 宿主触发 Stop hook
- **Then** 真实 observation 先记录 block 并继续同一 run，只有 completion checkpoint 验证后记录 done 和允许 task completion

Verified by: `test_real_hook_observation_promotes_manifest_only_after_block_then_done`; host evidence: `~/.codex/pactkit-hook-state.json` run `run-aabc8bc4cbf34f4d883f4cdad26be00f`
