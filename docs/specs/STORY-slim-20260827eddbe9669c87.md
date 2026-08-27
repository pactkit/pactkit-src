# STORY-slim-20260827eddbe9669c87: Continuation 状态机补强：授权审计事件对与 outcome_unknown 恢复语义

| Field | Value |
|-------|-------|
| ID | STORY-slim-20260827eddbe9669c87 |
| Status | Done |
| Priority | P1 |
| Release | 2.24.0 |

## Background

来源：`docs/product/harness-comparison-2026-08-27.md` 的 P1-1/P1-2（backlog STORY-slim-20260827c67e3add6af5 / STORY-slim-202608277ec1236a7b99）。两项均为 P0 事件流（STORY-slim-20260827024e71df170f，已交付）的原生续篇——同一状态机、同一模块，合并为一个 Story。

**P1-1 缺口（授权决策无审计）**：P0 的 `blocker_raised`/`blocker_cleared` 事件记录了"等待"，但没有记录**决策**。dsh 的审计价值在 `approval/asked` + `approval/decided` 不可抵赖配对——企业合规问"谁在什么时候批准了这个操作"，PactKit 现在答不出。且现有状态机没有拒绝路径：`blocker_kind=authorization` 的 blocker 只能被"继续推进"隐式解除（= 批准），人类说"不"没有机器可表达的入口。

**P1-2 缺口（验证结局不可观测）**：Ctrl-C 在验证中途杀死进程后，run 的证据链没有任何痕迹。**考古发现**：P0 R3 的 enforcement 账本只在 `run_gate` 的终态路径写记录（full/degraded/unavailable）——进程在终态前被杀则什么都不写，账本无法检测中断。dsh 的解法是持久化屏障（副作用前先落盘）；PactKit 的对应物是**尝试围栏**：验证开始前先写 `running` 尝试记录，终态记录覆盖之——崩溃留下未闭合的围栏 = outcome unknown，机器可观测。恢复路径上，未闭合的围栏必须阻塞 resume（该次验证的结论不可信），重跑验证（产出干净结局记录）即解除。

## Requirements

### R1: 授权审计事件对 (MUST)

事件类型集扩展：`authorization_asked` / `authorization_granted` / `authorization_denied`。

- `authorization_asked`：checkpoint 以 `status=blocked, blocker_kind=authorization` 写入时自动追加（detail 含经清洗的 blocker 文本——审计需要"问的是什么"）
- `authorization_granted`：上一个 checkpoint 为 authorization-blocked、本次写入解除阻塞时自动追加
- `authorization_denied`：仅由 R2 的显式拒绝动作产生（自动路径无法观测人类说"不"）
- 三个事件在 store 与 engine 两条路径一致发射；detail 复用 `_sanitize_evidence`
- 事件流中已有的通用 `blocker_raised/cleared` 语义不变（新事件是审计层，不是替代）

### R2: 显式拒绝命令 (MUST)

新增 `pactkit continuation deny <story_id> --reason "<text>"`：

- 前置校验：该 story 的 checkpoint 当前为 `blocked` 且 `blocker_kind=authorization`，且该 asked 之后无未消化的 `authorization_denied`（重复拒绝报错）
- 动作：在 `_story_lock` 内（a）追加 `authorization_denied` 事件（reason 经清洗）；（b）以 blocked→blocked 重写 checkpoint，blocker 文本更新为 `denied: <reason>`（fingerprints 保持既有语义——blocked 写入沿用上一可信基线）
- 拒绝不存在的 run / 非 blocked / 非 authorization kind → 明确报错 exit 1，不产生任何写入
- `resume`/`status`/`finish_guard` 对 denied checkpoint 的输出反映拒绝状态（blocker 文本即证据）

### R3: 验证尝试围栏 (MUST)

enforcement 模块新增 `record_attempt(root, gate)`：在验证**开始前**写入 `{gate, status: "running", started_at: ts}`；`record_status` 的终态写入覆盖围栏记录。

- `commit_gate.run_gate` 入口处 `record_attempt`，各终态路径（full/unavailable/degraded/GitCollectionError）保持既有 `record_status` 不变
- `read_status` 返回 `status: "running"` 的记录时调用方可识别未闭合围栏
- 无围栏文件（旧项目/从未跑过 gate）→ 无 unknown，行为与现状一致（backward compat）

### R4: outcome_unknown 恢复语义 (MUST)

`ContinuationStore.resume` 与 `ContinuationEngine.finish_guard`（in_progress 分支）交叉检查 commit-gate 围栏：

- 存在 `status: "running"` 的未闭合 commit-gate 尝试 → resume 返回 blocked，理由 `verification outcome unknown: commit-gate attempt at <ts> never completed — re-run the gate`；finish_guard 的 in_progress 决策附同一理由
- 解除条件：重跑 commit-gate 产出终态记录（围栏闭合）——不需要新机制，重跑即恢复
- 并发场景（gate 正在运行时 resume）：同一阻塞理由如实呈现（"若验证仍在运行请等待，否则重跑"），不做时间窗猜测
- 检查只读、失败安全：围栏文件损坏/不可读 → 视为无围栏（不阻塞、不抛错）

### R5: stats 授权决策计数 (SHOULD)

`pactkit stats` 的每 run 摘要增加 `authorization_decisions: {asked, granted, denied}` 计数（从事件流聚合）。

## Acceptance Criteria

### AC1: 授权 asked/granted 自动配对 (R1)

- **Given** 一个 run 以 `blocked + blocker_kind=authorization` 写入，随后解除并推进
- **When** 读取事件流
- **Then** 存在 `authorization_asked`（detail 含 blocker 文本）与 `authorization_granted` 各至少一条；时间戳顺序 asked < granted；其他 blocker_kind（user_input/external_state）不产生 authorization 事件

### AC2: deny 命令写入审计 (R2)

- **Given** 一个 authorization-blocked 的 checkpoint
- **When** `pactkit continuation deny <story_id> --reason "scope too broad"`
- **Then** 事件流新增 `authorization_denied`（detail 含 reason）；checkpoint 仍为 blocked 且 blocker 以 `denied:` 开头；重复 deny 报错且无二次写入

### AC3: deny 前置校验 (R2)

- **Given** 一个 in_progress（非 blocked）的 run
- **When** 执行 deny
- **Then** exit 1，错误信息说明仅 authorization-blocked 可拒绝；事件流与 checkpoint 无任何变更

### AC4: 围栏开合 (R3)

- **Given** commit-gate 正常完成一次运行
- **When** 读取 enforcement 记录
- **Then** 记录为终态（full/degraded/unavailable），无残留 `running` 状态

### AC5: Ctrl-C 留下未闭合围栏 (R3)

- **Given** 模拟 run_gate 在终态记录前抛出/被杀（monkeypatch record_status 前的路径抛错）
- **When** 读取 enforcement 记录
- **Then** 记录为 `status: "running"`（围栏未闭合）

### AC6: outcome_unknown 阻塞与解除 (R4)

- **Given** 一个 in_progress 的 run + 未闭合的 commit-gate 围栏
- **When** `resume` / `finish_guard`
- **Then** resume 返回 blocked 且理由含 "outcome unknown"；finish_guard 附同一理由
- **When** commit-gate 重跑并产出终态记录后再次 resume
- **Then** 围栏闭合，resume 恢复正常决策（无 unknown 理由）

### AC7: 无围栏时行为不变 (R3, R4)

- **Given** 一个 2.24.0 之前创建的项目（无任何 enforcement 记录）
- **When** resume / finish_guard
- **Then** 决策与现状完全一致（无新增理由、无阻塞）

### AC8: stats 决策计数 (R5)

- **Given** 一个含 asked→denied 剧情的 run 事件流
- **When** `pactkit stats --format json`
- **Then** 该 run 的 `authorization_decisions` 为 `{asked: 1, granted: 0, denied: 1}`

## Target Call Chain

- **R1**: `continuation.py` `_emit_checkpoint_events`（store）/`_emit_run_events`（engine）— blocker 转移处按 blocker_kind 增发审计事件；`run_events.py` `EVENT_TYPES` 扩展
- **R2**: `cli.py` continuation 子命令新增 `deny` → `ContinuationStore.deny(story_id, reason)`（新方法，`_story_lock` 内事件追加 + blocked 重写）
- **R3/R4**: `enforcement.py` `record_attempt` + `read_status` 识别 running → `commit_gate.py:run_gate` 入口围栏 → `continuation.py` `resume`/`finish_guard` 交叉检查
- **R5**: `run_stats.py` `_summarize` 聚合 authorization 事件计数

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `run_events.py` + `continuation.py` | R1 审计事件发射（双路径） + 单测 AC1 | None | Low |
| 2 | `continuation.py` + `cli.py` | R2 deny 命令（锁内） + 单测 AC2/AC3 + golden CLI 更新 | Step 1 | Medium（blocked→blocked 重写语义） |
| 3 | `enforcement.py` + `commit_gate.py` | R3 围栏 API + 接入 + 单测 AC4/AC5 | None | Low |
| 4 | `continuation.py` | R4 resume/finish_guard 交叉检查 + 单测 AC6/AC7 | Step 3 | Medium（resume 决策面被 32 callers 依赖） |
| 5 | `run_stats.py` | R5 决策计数 + 单测 AC8 | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | deny 是授权语义写入——前置校验 MUST 不可绕过（非 authorization-blocked 拒绝写入） |
| SEC-2 | Yes | deny --reason 与事件 detail 为外部输入，清洗路径必须覆盖；围栏 JSON 损坏降级不抛错 |
| SEC-3 | Yes | 事件流与围栏持久化含 blocker/reason 派生文本，复用既有 redaction |
| SEC-4 | No | 无前端文件 |
| SEC-5 | Yes | 授权审计正是 SEC-5 主题：决策记录不可抵赖（asked/denied 配对 + 时间戳） |
| SEC-6 | No | 无 API/route 文件 |
| SEC-7 | Yes | 围栏读取失败安全（视为无围栏）；resume 阻塞理由必须可操作（指向重跑命令） |
| SEC-8 | No | 无依赖清单变更 |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | STORY-slim-20260827024e71df170f（已交付：事件流 + enforcement 账本是本 Story 的地基） |
| Provides | 授权审计事件词汇表（asked/granted/denied）；`record_attempt` 围栏 API —— 后续 gate（coverage/finish）可复用同一围栏 |
| Touches | `src/pactkit/run_events.py`, `continuation.py`, `enforcement.py`, `commit_gate.py`, `cli.py`, `run_stats.py`, 对应 tests + golden CLI |
| Conflict risk | MEDIUM（resume/finish_guard 决策面有 32+ callers；deny 触碰 blocked 重写路径） |

## Out of Scope

- P1-3 设计决策记录、P1-4 Codex 插件形态、P1-5 write_scope 编译（backlog 另行立 story）
- coverage-gate / finish-gate 的围栏接入（本 Story 只接 commit-gate；`record_attempt` API 已为其余 gate 预留）
- 授权的"谁"（actor identity）——事件记录决策与时间，actor 身份需宿主会话身份体系，超出治理层边界
- 撤销 denial / denial 后重开授权（deny 后按状态机语义需新的 asked 周期，走既有 checkpoint 流程）

