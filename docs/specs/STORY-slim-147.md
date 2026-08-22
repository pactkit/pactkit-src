# STORY-slim-147: 全 Skill 执行可靠性协议与 Plan 可恢复工作流

| Field | Value |
|-------|-------|
| ID | STORY-slim-147 |
| Status | Done |
| Priority | P0 |
| Release | 2.21.0 |

## Background

STORY-slim-146 已为 `$project-act` 建立原子 checkpoint、Story 锁、输入指纹、证据校验和 completed 门禁，并为 13 个辅助 runtime Skill 声明恢复类别。该实现证明了可验证续跑能够防止 Codex 在 turn、上下文或工具边界中断后从头猜测，但当前 `ContinuationStore` 仍将命令、步骤、证据验证器、完成验证器和文件名主键写死为 Act 与 Story ID。

PactKit 实际部署入口包括 13 个 `pactkit-*` 辅助 Skill 和 12 个 `project-*` command Skill，共 25 个。现有恢复契约只覆盖前 13 个，`project-plan` 等 command 仍依赖聊天中的进度输出。Plan 还存在一个结构性差异：在 `pactkit next-id` 和 Spec scaffold 之前没有 Story ID，不能直接复用按 Story 命名的 Act checkpoint。

本 Story 将 Act-only 实现提炼为可注册的执行可靠性协议，为全部 25 个入口建立单一来源的分类与完整性门禁，并让 `$project-plan` 成为第二个完整接入的可恢复 workflow。它不是重写所有 Skill：现有业务步骤与产物格式保持不变，除 Act 和 Plan 外的入口只建立分类、完成契约和后续接入决策。

## Requirements

### R1: 建立覆盖全部部署入口的执行可靠性注册表 (MUST)

Core MUST 以 `VALID_COMMANDS`、`COMMANDS_CONTENT` 和 `SKILL_MANIFEST` 为权威来源，为全部 25 个部署入口生成且验证唯一的执行可靠性定义。定义至少包含入口名、入口类型、写入/外部副作用类别、恢复策略、是否需要持久化 workflow、完成验证策略和人工确认操作。新增、删除、重复或未分类入口 MUST 使完整性校验失败，adapter MUST NOT 维护独立副本。

13 个辅助 Skill 沿用 STORY-slim-146 的恢复分类。12 个 command 的最低分类如下：

| Command | 类型 | 本 Story 决策 |
|---------|------|---------------|
| project-plan | 长流程本地写入 | 完整接入 continuation workflow |
| project-act | 长流程本地写入 | 迁移到通用引擎且保持 2.20.0 行为兼容 |
| project-check | 长流程验证/产物写入 | 声明完整 workflow，后续 Story 接入 |
| project-done | Git 与归档写入 | 声明人工确认边界，后续 Story 接入 |
| project-init | 多文件初始化 | 声明 create-only/idempotent 边界，后续 Story 接入 |
| project-sprint | 多 Story 编排 | 声明子 workflow 编排边界，后续 Story 接入 |
| project-hotfix | 快速本地写入 | 声明轻量 workflow，后续 Story 接入 |
| project-design | 长流程多 Spec 写入 | 声明完整 workflow，后续 Story 接入 |
| project-clarify | 交互式分析 | 声明会话输入 checkpoint，后续 Story 接入 |
| project-release | Git/发布外部副作用 | MUST 人工确认且不得自动重放 |
| project-pr | Git push/PR 外部副作用 | MUST 远端核验且不得盲目重放 |
| project-debug | 假设驱动分析/可选写入 | 声明轻量 workflow，后续 Story 接入 |

### R2: 将 Act-only ContinuationStore 抽象为可注册 Workflow Engine (MUST)

Core MUST 将命令名、步骤顺序、阶段证据验证、完成门禁、指纹采集和 resume 决策从 `ContinuationStore` 的 Act 条件分支中移入声明式 workflow definition/registry。通用引擎负责 schema、原子写入、锁、单调状态转换、stale 检测、敏感信息净化、只读 resume 和历史归档；各 workflow 只负责自己的步骤与证据验证器。

状态主键 MUST 支持 Story 尚不存在的工作流实例，至少区分 `workflow_id`、稳定且受校验的 `run_id`、可选 `story_id` 和 `command`。Plan 在生成 Story ID 后 MUST 将同一 run 原子绑定到该 Story，不得复制出两个可竞争的活跃状态。路径构造 MUST 防止目录穿越、冲突覆盖和跨 workflow 误读。

### R3: 保持 project-act 的状态、CLI 与恢复语义向后兼容 (MUST)

现有 `pactkit continuation checkpoint|status|verify|resume STORY_ID` 调用、Act 的五个步骤、证据结构、锁语义、stale 判定、completed 不可变性和 `.pactkit/continuations/{STORY_ID}.json` 读取能力 MUST 保持兼容。旧 schema MUST 被安全读取或一次性迁移；迁移失败 MUST 保留原文件并停止，不得静默丢弃完成证据。

Act 的已有单元、CLI E2E、doctor/garden 诊断和 Classic/OpenCode/Codex/Copilot 部署语义 MUST 无回退。通用化不得放宽 STORY-slim-146 的完成门禁，也不得让 resume 执行写操作。

### R4: 为 project-plan 提供可验证的持久化阶段与恢复入口 (MUST)

`project-plan` MUST 使用以下单调 workflow，并在每个安全边界显式写入 checkpoint：

`preflight → intent_clarified → archaeology → story_identified → spec_scaffolded → requirements_written → acceptance_written → security_scoped → spec_linted → board_synced → completed`

在 `story_identified` 之前，run MUST 由明确生成的 opaque run ID 标识；用户输入只能作为经净化和指纹化的 evidence，不能直接成为路径。`story_identified` 之后，状态 MUST 绑定 `pactkit next-id` 的结果，并跟踪 Spec、Board、HLD、Git HEAD 和工作树指纹。

每一步 MUST 验证真实证据，而非相信模型文字：guard 结果、需求输入指纹、trace 摘要、Story ID 唯一性、scaffold 文件、Requirement/AC 结构、`sec-scope` 结果、`spec-lint` 零错误零警告、Board 中唯一 Story 及任务列表。只有 Spec 存在且 lint 通过、Board 精确同步、所有 MUST/AC 非空并且无 placeholder 时才可 completed。

### R5: Plan 恢复必须处理交互、漂移与幂等写入 (MUST)

新会话 MUST 能通过显式 run ID 或已绑定 Story ID 执行只读 `status|verify|resume`，返回下一安全步骤、已验证证据和精确阻塞原因。Clarify 阶段的已确认答案 MUST 被净化后持久化，恢复时不得重复询问已回答的问题；未回答的问题必须保留为 blocker。

若 Spec、Board、HLD、Git/worktree 或原始需求指纹与 checkpoint 不一致，resume MUST 停止写入并报告差异。`create_spec` 和 `add_story` 恢复时 MUST 先检查目标是否已存在且内容/身份匹配：匹配则视为幂等完成，不匹配则阻断，不得覆盖 Spec 或重复添加 Board Story。

### R6: 所有支持格式必须部署相同的可靠性语义 (MUST)

Canonical `project-plan` 和 `project-act` 模板 MUST 包含各自的 workflow 启动、边界 checkpoint、blocked handoff、只读 resume 和 completed 门禁。Classic、OpenCode、Codex、Copilot 的隔离部署 MUST 通过结构化语义与归一化 parity 测试；真实 adapter 不得删除、改写或把 CLI 参数降级为不可执行文字。版本兼容门禁 MUST 阻止不支持该 registry/schema 的 Core 与 adapter 混合部署。

### R7: 提供迁移诊断与受控后续扩展 (SHOULD)

`pactkit doctor` SHOULD 报告未知 workflow、缺失定义、损坏 schema、未绑定 Plan run、孤儿状态及入口覆盖漂移；`pactkit garden` SHOULD 报告可清理的 completed 历史。CLI SHOULD 提供机器可读的 registry audit，证明 13 个辅助 Skill 与 12 个 command 均被覆盖。

除 Act 和 Plan 外的入口在本 Story 中 SHOULD 只消费统一分类与完成契约，不引入伪 checkpoint。后续接入 MUST 复用 registry 和 engine，不得再增加 command-specific store。

## Acceptance Criteria

### AC1: 25 个部署入口全部且唯一受执行可靠性契约覆盖 (R1)

- **Given** Core 当前的 13 个 `SKILL_MANIFEST` 条目和 12 个 `VALID_COMMANDS` 条目
- **When** 运行 registry 完整性校验
- **Then** 每个入口恰有一个可验证定义，集合与两个权威清单完全相等；新增、缺失、重复或未知定义均失败

### AC2: 通用引擎不再写死 Act 的命令与步骤 (R2)

- **Given** Act 和 Plan 两个不同 workflow definition
- **When** 分别创建、推进、阻塞、恢复和完成 workflow run
- **Then** engine 使用对应定义校验证据与转换，核心存储代码不包含针对 `project-act` 或 Plan step 名的条件分支

### AC3: Plan 在 Story ID 生成前中断后可恢复 (R2, R4, R5)

- **Given** Plan 已完成 preflight、需求澄清和 archaeology，但尚未运行 `next-id`
- **When** 新会话使用 opaque run ID 执行只读 resume
- **Then** 返回 `story_identified` 为下一步，保留已确认输入与 trace 证据，不重复澄清，也不提前创建 Spec 或 Board Story

### AC4: Plan 在 Spec 创建后从准确边界恢复 (R4, R5)

- **Given** Plan run 已绑定唯一 Story ID，Spec scaffold 存在且 requirements 已写入，但 AC 尚未完成
- **When** 当前 Spec、Board、HLD 和工作树与 checkpoint 一致并执行 resume
- **Then** 返回 `acceptance_written` 为下一安全步骤，不覆盖 Spec、不重新分配 ID 且不重复添加 Board Story

### AC5: 漂移或重复写入风险会阻断 Plan (R4, R5)

- **Given** checkpoint 之后 Spec 被手工修改、Board 已存在同 ID 不同标题，或 run 绑定了冲突 Story
- **When** 执行 verify/resume 或尝试推进 checkpoint
- **Then** 命令只读失败并列出具体指纹/身份差异，不修改 Spec、Board、HLD 或 checkpoint 的可信基线

### AC6: Plan completed 由真实 Spec 和 Board 证据门禁 (R4)

- **Given** Spec 含 placeholder、lint warning、缺失 MUST/AC、Security Scope 未填或 Board 任务不一致中的任一情况
- **When** Plan 尝试写入 completed
- **Then** 完成被拒绝；仅当 Spec lint 为零错误零警告、结构完整且 Board 唯一同步时 completed 成功

### AC7: 旧 Act checkpoint 无损迁移且行为不回退 (R3)

- **Given** 2.20.0 生成的 in_progress、blocked 和 completed Act checkpoint fixture
- **When** 新引擎读取、resume 或启动 fresh cycle
- **Then** 得到与旧实现一致的决定和证据，原文件在失败时保持不变，现有 Act 测试与完成门禁全部通过

### AC8: 四种部署目标保留 Plan 与 Act 的完整语义 (R6)

- **Given** canonical command 模板和 Classic、OpenCode、Codex、Copilot 隔离目标
- **When** 从正式 Core/adapter 组合渲染并执行 manifest、完整性和归一化 parity 检查
- **Then** 两个 command 的 workflow steps、checkpoint、resume、blocked 和 completed 契约均未丢失，且临时 target 外无写入

### AC9: 未接入命令保持诚实且可扩展 (R1, R7)

- **Given** Check、Done、Init、Sprint、Hotfix、Design、Clarify、Release、PR、Debug 的 registry 定义
- **When** 查询其执行可靠性状态
- **Then** 系统明确返回分类、人工确认边界和 `not_persisted`/后续接入状态，不声称这些命令已经支持机械续跑

## Target Call Chain

    $project-plan <request>
      -> pactkit workflow start project-plan --input-fingerprint ...
      -> WorkflowRegistry.get("project-plan")
      -> ContinuationEngine.checkpoint(run_id, step, evidence)
      -> PlanEvidenceValidator validates guard/trace/spec/lint/board evidence
      -> bind_story(run_id, STORY-ID) after pactkit next-id
      -> ContinuationEngine.resume(run_id | story_id) [read-only]
      -> PlanCompletionValidator -> completed | blocked

    pactkit continuation ... STORY-ID  [2.20.0 compatibility]
      -> legacy CLI argument adapter
      -> WorkflowRegistry.get("project-act")
      -> ContinuationEngine / ActEvidenceValidator
      -> legacy-compatible checkpoint path and result

    deployer + external adapters
      -> VALID_COMMANDS + COMMANDS_CONTENT + SKILL_MANIFEST
      -> ExecutionReliabilityRegistry coverage validation
      -> canonical Plan/Act templates
      -> Classic / OpenCode / Codex / Copilot parity gates

## Technical Design

### Lateral Scan Results

- Existing call chain: `cli.main()` parses `pactkit continuation` → `ContinuationStore.checkpoint/status/resume()` → Act-specific `_validate_step_evidence()` / `_validate_completion()` → `atomic_write()`。
- Existing classification: `SKILL_RECOVERY_CONTRACTS` covers exactly 13 auxiliary Skills, while `VALID_COMMANDS` exposes 12 command Skills with no equivalent registry coverage。
- Same operation implementations: Act step order, command identity and evidence rules are coupled inside one store; Plan only emits conversational output checkpoints. Assessment: extract shared engine and workflow strategy registry, not a second Plan-specific store.

### Module boundaries

`continuation.py` retains transport-independent state, locking, atomic persistence, schema migration, sanitization and stale comparison. Workflow definitions and validators live behind a registry interface; Act and Plan validators must not import CLI or deployment modules. CLI translates legacy Act syntax and new workflow/run syntax into engine calls. Prompt templates invoke CLI only and never implement deterministic validation in prose.

### Identity and persistence

Use a generated opaque run ID before Plan has a Story ID. The persisted document contains both workflow and optional subject identity; binding a Story is a locked, validated transition. Preserve the legacy Act filename contract through path resolution or migration compatibility. All read-validate-write operations for one run use the same process lock and atomic replacement.

### Capability assessment and reuse points

| Need | Existing source | Decision |
|------|-----------------|----------|
| Atomic persistence | `utils.atomic_write()` | Reuse |
| Locking, fingerprints, sanitization | `ContinuationStore` | Extract into generic engine |
| Deployed entry inventory | `VALID_COMMANDS`, `COMMANDS_CONTENT`, `SKILL_MANIFEST` | Reuse as authoritative sets |
| Auxiliary Skill policy | `SKILL_RECOVERY_CONTRACTS` | Migrate into unified registry |
| Act evidence validation | existing continuation validators | Preserve behind Act strategy |
| Plan evidence validation | none | Implement Plan strategy |

No third-party framework provides PactKit-specific workflow evidence semantics; new implementation is limited to the registry, identity model and Plan validator while reusing existing persistence primitives.

### Error recovery and compatibility decisions

Resume remains read-only. State transitions are monotonic; stale evidence cannot become a new trusted baseline. Create-only operations use verify-before-write semantics. High-side-effect commands expose manual-confirmation policy and are never auto-replayed. Schema migration is copy/validate/swap, with the original retained on any error. Act's public CLI and old files remain supported for at least this release.

### Testing strategy

Use strict TDD. Unit tests cover registry set equality, workflow dispatch, invalid transitions, identity binding, path safety, redaction, stale detection, Plan evidence/completion and legacy Act fixtures. CLI E2E tests simulate interruption before and after Story binding, idempotent scaffold/Board recovery and drift blocking. Deployment tests render full canonical Plan and Act content for every built-in profile and run external adapter suites in isolated targets.

## Implementation Steps

| Step | File / Repository | Action | Dependencies | Risk |
|------|-------------------|--------|--------------|------|
| 1 | `tests/unit/test_story_slim147.py`, continuation tests | Write RED tests for 25-entry coverage, generic dispatch and legacy Act fixtures | None | High |
| 2 | `src/pactkit/continuation.py`, new workflow registry module | Extract generic engine, workflow/run identity, migration and strategy interfaces | Step 1 | High |
| 3 | Act workflow validator and `src/pactkit/cli.py` | Move Act rules behind registry while preserving CLI/schema behavior | Step 2 | High |
| 4 | Plan workflow validator and CLI | Add pre-Story run, Story binding, step evidence and completion gate | Step 2 | High |
| 5 | `src/pactkit/prompts/skills.py`, `config.py` | Unify 13 Skill + 12 command classifications and enforce set equality | Step 2 | Medium |
| 6 | `src/pactkit/prompts/commands.py` | Add Plan continuation boundaries and adapt Act to generic workflow interface | Steps 3-5 | High |
| 7 | doctor/garden/context and CLI E2E tests | Add migration, orphan, unbound run and honest support diagnostics | Steps 3-6 | Medium |
| 8 | Core deployer and adapter repositories | Verify Classic/OpenCode/Codex/Copilot full-template parity and version compatibility | Steps 5-7 | High |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Plan 输入、澄清答案、blocker 和命令摘要进入持久化状态，必须递归净化凭证与用户主目录 |
| SEC-2 | Yes | workflow、run ID、Story ID、step、路径和 JSON evidence 均是不可信输入，必须 allowlist/schema 校验并阻止路径穿越 |
| SEC-3 | No | 自动扫描因通用源文件文本命中 database/ORM 模式；本 Story 的状态存储为本地 JSON，不构造数据库或 SQL |
| SEC-4 | No | 不渲染浏览器不可信内容 |
| SEC-5 | No | 自动扫描因通用源文件文本命中 auth/session 模式；本 Story 不实现认证、授权或用户会话 |
| SEC-6 | No | 不新增网络服务或公共 API |
| SEC-7 | Yes | 并发写入、损坏状态、部分迁移、stale artifact 和外部 adapter 失败必须 fail closed 且保留旧证据 |
| SEC-8 | Yes | Core 与四种部署目标需要版本门禁、manifest 完整性和跨 adapter 语义兼容验证 |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | STORY-slim-139, STORY-slim-145, STORY-slim-146 |
| Provides | 25 入口执行可靠性注册表、通用 continuation engine、可恢复 project-plan workflow、Act 无损迁移 |
| Touches | `continuation.py`, CLI, prompts/config registries, Plan/Act templates, doctor/garden/context, deploy integrity, Core 与 adapter tests, system design |
| Conflict risk | HIGH |

## Out of Scope

- 一次性为除 `project-plan` 和 `project-act` 外的 10 个 command 实现持久化 checkpoint。
- 改写 13 个辅助 Skill 或 12 个 command 的业务流程、产物格式和角色职责。
- 自动重放 release、tag、publish、push、PR、archive、snapshot 或用户所有的 Draw.io 产物。
- 修复 Codex、Claude Code、OpenCode 自身的上下文、配额、网络、模型或进程终止问题。
- 云端状态同步、跨机器恢复、分布式锁或多人同时编辑同一 workflow run。
