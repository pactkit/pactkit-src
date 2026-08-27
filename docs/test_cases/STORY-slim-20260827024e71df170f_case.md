# Test Cases: STORY-slim-20260827024e71df170f — P0 可观测性与拦截力升级

## TC-1: 事件流写入与投影一致 (R1, AC1)

**Given** 一个进行中的 Act run
**When** `ContinuationStore.checkpoint()` 推进步骤
**Then** `events/<story_id>.jsonl` 追加 `step_entered`/`checkpoint_written`；checkpoint JSON 与事件流末状态一致；`read`/`finish_guard`/`continuation status` 行为不变
**覆盖** `tests/unit/test_run_events.py::TestStoreCheckpointEvents::test_ac1_checkpoint_emits_events_and_projection_consistent`

## TC-2: 阻塞事件成对且无 secret (R1, AC2)

**Given** run 以 blocked 写入（blocker_kind=user_input）后解除
**When** 读取事件流
**Then** `blocker_raised`/`blocker_cleared` 成对、detail 含 blocker_kind、全文无 secret 明文
**覆盖** `test_run_events.py::TestStoreCheckpointEvents::test_ac2_blocker_pair_recorded_with_kind`

## TC-3: 崩溃安全 (R1, AC3)

**Given** 事件文件已有完整行
**When** 追加半行后中断再读取
**Then** 损坏行跳过并计数，完整行幸存，checkpoint 读写不受影响
**覆盖** `test_run_events.py`（primitives + store 两个测试）

## TC-4: stats 聚合与旧 run 降级 (R2, AC4)

**Given** 含 blocker 的 run 事件流 + 一个无事件文件的旧 checkpoint
**When** `pactkit stats --format json` / 人类模式 / `continuation events`
**Then** 输出 duration/blocker 分桶/步骤返工；旧 run 计入 `events: unavailable` 且 exit 0
**覆盖** `tests/unit/test_run_stats.py`（7 个测试，含 CLI 子进程级）

## TC-5: golden CLI snapshot 同步 (R2, AC5)

**Given** stats/events/doctor --json 加入 argparse
**When** CLI e2e 运行
**Then** golden 快照更新且全绿
**覆盖** `tests/unit/test_cli_help_surface.py` + `tests/fixtures/cli_help_golden/`

## TC-6: gate 状态可查询 (R3, AC6)

**Given** commit-gate 自锁保护路径触发（内部异常）
**When** `pactkit doctor --json`
**Then** enforcement 段含 `commit_gate: degraded` 及原因；正常态为 `full`
**覆盖** `tests/unit/test_enforcement.py`（8 个测试）

## TC-7: Codex hooks 部署与信任提示 (R4, AC7)

**Given** 项目执行 codex 格式部署
**When** `install_codex_hook` / `ensure_gate_channel(root, "codex")`
**Then** `.codex/hooks.json` 含 PreToolUse Bash→`pactkit commit-gate --hook` 条目；输出含信任确认提示；既有 `config.toml` 字节不变
**覆盖** `tests/unit/test_codex_hook_channel.py::TestInstallCodexHook`（含 sha256 前后比对）

## TC-8: 用户 hook 条目不越权 (R4, AC8)

**Given** hooks.json 已存在且含用户条目（含其他事件如 SessionStart）
**When** 重复部署
**Then** 用户条目与事件原样保留；PactKit 条目幂等追加/刷新；非法 JSON 保持不动；`enterprise.no_git` 整体跳过
**覆盖** `TestInstallCodexHook`（append/idempotent/invalid/no_git 四个测试）

## TC-9: doctor Codex 能力检测 (R4/R5, AC9)

**Given** 本机 codex ≥0.114（探测注入 0.149.1）
**When** `pactkit doctor` / `--json`
**Then** engine=available + hooks_json 部署状态 + entry 存在性；无 codex 二进制或旧版本（0.100）报 unavailable 且警告含版本阈值
**覆盖** `TestDoctorCodexHookCapability`（4 个测试，含 doctor --json 子进程级）

## TC-10: hook_entry 双宿主兼容 (R4)

**Given** Codex payload（tool_name=Bash、字符串或 legacy 数组 command、cwd 字段）
**When** `hook_entry`
**Then** 数组 command 归一化后仍拦截 git commit；payload cwd 用于 root 解析；非 git 命令 exit 0
**覆盖** `TestHookEntryCodexPayloads`（4 个测试）

## TC-11: R5 能力标志复核结论

**Given** codex FormatProfile 的 `excluded_agent_fields` 含 "hooks"、`supports_model_routing=False`
**When** 复核（本 Story 考古）
**Then** 两者均为刻意设计（Codex 无 agent frontmatter hooks 概念；模型表为 Claude 层级专属且 adapter 剥离）——结论记录于 `profiles.py` 注释；真实 hook 能力由 doctor 检测报告，不从 prompt 级标志推断
**覆盖** `profiles.py` R5 review 注释 + TC-9

## TC-12: 既有回归

**Given** 本 Story 全部变更
**When** `pytest tests/unit/ tests/e2e/ tests/integration/ -q`
**Then** 全量通过（4689 passed）；`test_commit_gate.py` codex 通道断言更新为新契约（过时契约分类）
