# STORY-slim-146: 全 Skill 可恢复执行契约与 Act 断点续作

| Field | Value |
|-------|-------|
| ID | STORY-slim-146 |
| Status | Done |
| Priority | P0 |
| Release | 2.20.0 |

## Background

STORY-slim-145 已修复 Codex 部署时对 $project-act 指令的有损转换，避免 Run run、游离 continuation 参数和关键步骤丢失。然而，它只保证部署后的指令语义完整，不能处理 Codex 在执行期间因上下文耗尽、工具错误、用户中断或运行时停止而半途退出的情形。

现有 STORY-slim-071 的 context.md continuation 只保存 Last Command、Phase Reached、可选 blocker 和 AC 标题；它不是机器可验证的断点，且 Act 仅在 Phase 4 正常抵达时更新。新会话因此无法安全判断已完成或待执行工作，容易重复有副作用的操作，或错误宣称任务已经完成。

本 Story 为 PactKit 的全部 runtime skill 建立恢复影响矩阵，并为可恢复的 PDCA 工作引入原子、可校验、按 Story 隔离的 continuation 状态。恢复机制只会建议或执行经过验证的下一个安全步骤；不会自动重放发布、归档、GitHub 写入或其他外部副作用。

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | STORY-slim-071, STORY-slim-099, STORY-slim-139, STORY-slim-145 |
| Provides | 全 Skill 恢复契约、持久化 checkpoint、可验证的 Act resume 流程与安全恢复门禁 |
| Touches | cli.py, context_gen.py, schemas.py, prompts/commands.py, prompts/skills.py, generators/deployer.py, runtime skill manifest、单元/E2E 测试与 system design |
| Conflict risk | HIGH |

## Requirements

### R1: 建立覆盖全部 Runtime Skill 的恢复影响矩阵 (MUST)

实现 MUST 以 get_skill_manifest()/SKILL_MANIFEST 为唯一技能清单来源，对每个已部署 runtime skill 产出且测试一份恢复契约。新增 skill 未声明恢复类别时，校验 MUST 失败，防止新增能力绕过恢复安全边界。

| Skill | 类别 | Resume 行为 |
|-------|------|-------------|
| pactkit-visualize | 可重跑、派生输出 | 可在 checkpoint 后重跑；图文件必须标为派生物 |
| pactkit-board | 本地状态写入 | 仅允许幂等 move_story/update_task；add_story、archive、snapshot 必须显式确认或记录已完成证据 |
| pactkit-scaffold | 创建写入 | 不自动重放；恢复时验证目标是否已存在及内容是否匹配预期 |
| pactkit-report | 可重跑、派生输出 | 可重跑；不得把 HTML 报告当作完成证据 |
| pactkit-trace | 只读分析 | 可自由重跑；其结论不得单独推进 checkpoint |
| pactkit-draw | 用户产物写入 | 不自动重放；只可提示重新打开或由用户确认 |
| pactkit-status | 只读分析 | 可自由重跑；用于恢复前环境摘要 |
| pactkit-doctor | 只读诊断 | 恢复前 MUST 运行或等价验证；WARN/ERROR 按策略阻断或要求确认 |
| pactkit-garden | 只读诊断 | 可自由重跑；不得自动删除或修改文件 |
| pactkit-review | 外部读取 | 可重跑；不得自动提交 PR review 或改变远端状态 |
| pactkit-release | 高副作用发布 | MUST NOT 自动恢复或重放；只生成明确的人工恢复清单 |
| pactkit-analyze | 只读一致性检查 | 可重跑；用于确认 Spec/Board/Test Case 对齐 |
| pactkit-audit | 派生治理输出 | 可重跑；--append 只在 Done 流程经验证后执行 |

此矩阵 MUST 与部署的每个格式（Classic、OpenCode、Codex、Copilot）共享同一语义；adapter 不得维护本地、漂移的恢复策略副本。

### R2: 引入按 Story 隔离、原子持久化的 Continuation Checkpoint (MUST)

Core MUST 在项目目录内保存机器可读的 continuation 状态，推荐路径为 .pactkit/continuations/{STORY_ID}.json。状态 MUST 至少包含：schema version、Story ID、命令、phase、step ID、状态（in_progress / blocked / completed）、当前需求/AC 覆盖、已验证命令摘要、输入/输出 artifact 指纹、git HEAD 或工作树摘要、时间戳和经过净化的 blocker。

checkpoint 写入 MUST 使用原子写入；自由文本 MUST 使用现有净化规则，且不得持久化环境变量、凭证、命令输出中的 secrets 或绝对用户主目录。写入失败 MUST 保留旧 checkpoint 并明确报错，不能把工作错误地标为完成。

context.md 保持人类可读的摘要，但 MUST 从 checkpoint 派生或交叉校验；它不能再是唯一恢复事实来源。

### R3: 为 project-act 定义显式安全检查点与完成门禁 (MUST)

Core MUST 提供显式 checkpoint CLI，例如 pactkit continuation checkpoint STORY_ID --step <preflight|red|green|regression_lint|sync_coverage> --evidence <JSON 或文件>。只有此命令可写入安全边界；它 MUST 校验状态转换、证据结构、Spec/Board/工作树指纹和敏感信息过滤后再原子写入。

project-act MUST 在 Spec/输入预检完成、测试 RED 已确认、实现 GREEN 已确认、回归与 lint 已确认、文档/Board/coverage 输出完成的每个边界调用该 CLI。任何阻塞（RFC、前置测试失败、环境不可恢复、用户决策缺失）MUST 通过显式 checkpoint 写为 blocked，并保存下一个需要人工处理的动作。Core MUST NOT 从自然语言回复、上下文长度或未验证的模型声明推断阶段完成。

任务只有在以下条件全部满足时才可写为 completed：

- Story Spec 通过结构校验；
- Requirement/AC coverage 表完整且每个 MUST 有可追溯证据；
- 本 Story 的测试和所需回归、lint 门禁已成功；
- Board 任务与 checkpoint 状态一致；
- 必要的派生文档同步已完成。

模型不得仅因回复末尾出现“完成”或 context window 即将结束而写 completed。

### R4: 提供验证优先的恢复入口 (MUST)

Core MUST 提供稳定的 CLI 恢复/检查入口，例如 pactkit continuation status|resume|verify。resume 默认 MUST 仅做读取和验证：加载 Spec、Board、checkpoint 和当前工作树；校验 schema、Story ID、artifact 指纹、不可重放副作用与 blocker；运行 R1 矩阵要求的只读诊断，并输出下一安全步骤和恢复依据。

若状态过期、分支/HEAD 明显变化、artifact 被手动改写、多个 Story checkpoint 竞争，或验证不足以判定安全下一步，命令 MUST 不自动执行写操作，并输出精确的人工恢复步骤。对非破坏性的只读调查和幂等验证，可自动继续。

project-act 启动时 MUST 检测对应未完成 checkpoint，并优先提示执行只读 resume 验证；显式 $project-act STORY_ID --resume 仅加载已验证的下一步计划，不得隐式写 checkpoint 或重放副作用。新 Story、显式 --fresh 或已完成 checkpoint 必须有明确且可测试的行为。

### R5: 将完整性契约部署到所有目标格式 (MUST)

所有 format 的 project-act 生成物 MUST 包含同一恢复语义：启动时检测 continuation、在每个安全点写 checkpoint、遇到 blocker 记录而非虚假完成、输出最终 Requirement coverage。Codex 生成物还 MUST 保持 STORY-slim-145 的命令完整性门禁；adapter/Core 版本错配时不得部署混合恢复契约。

测试 MUST 将完整 canonical project-act（不是手工缩短模板）渲染到每个已支持 profile 并归一化格式差异，确认恢复步骤、完成门禁及禁止自动重放高副作用操作均未丢失。

### R6: 可观测性、迁移和向后兼容 (SHOULD)

旧项目没有 .pactkit/continuations/ 时，命令 SHOULD 安全初始化为空状态并保留现有 context.md 工作流。旧 continuation 仅含文本摘要时 SHOULD 显示“不可验证的 legacy handoff”，要求从预检建立新 checkpoint，不得伪造进度。

pactkit doctor SHOULD 报告损坏、孤儿、过期或与 Board/Spec 不一致的 checkpoint；pactkit garden SHOULD 可识别已完成 Story 的残留 checkpoint。所有状态与诊断输出 MUST 避免敏感信息。

## Acceptance Criteria

### AC1: 13 个 Runtime Skill 都有受测恢复契约 (R1)

- **Given** 当前 SKILL_MANIFEST 的完整列表
- **When** 运行恢复契约校验
- **Then** 13 个技能各自恰有一个类别与明确的自动重跑/人工确认策略；缺少或新增未分类 skill 时校验失败

### AC2: 显式边界命令原子保存中断前的 Act 状态 (R2, R3)

- **Given** STORY-slim-146 的 Act 已完成 RED 和部分 GREEN 阶段
- **When** Act 在每个完成边界显式调用 continuation checkpoint，随后在继续回归前模拟进程中断
- **Then** 每个已完成边界都存在有效 checkpoint，包含 Story、精确 step、证据摘要和 in_progress 状态；旧 checkpoint 不会被半写覆盖

### AC3: 新会话从安全的下一步恢复而不是从头猜测 (R3, R4)

- **Given** 有效 checkpoint、未变更的 Spec/Board/工作树和已通过的 RED/GREEN 证据
- **When** 运行 continuation resume 或重新启动 $project-act STORY-slim-146 --resume
- **Then** 系统仅验证并输出从回归/lint 开始的下一安全步骤与恢复依据；后续 checkpoint 仍必须由 Act 在完成边界显式写入，且不重复已经确认的实现或 Board 写入

### AC4: 失效状态不会触发不安全自动写入 (R2, R4)

- **Given** checkpoint 对应的 Spec、git HEAD、artifact 指纹或 Board 已发生不一致变更，或状态为 blocked
- **When** 请求恢复
- **Then** 命令停止在只读诊断，指出具体差异和人工动作；不会覆盖文件、标记 Board 任务、提交、归档或发布

### AC5: Act 只有在可证明覆盖完整时结束 (R3)

- **Given** 一个 MUST requirement、AC、测试、lint 或 Board task 尚无证据
- **When** Act 尝试写 completed
- **Then** 完成门禁拒绝该状态，并把 checkpoint 保持为 in_progress 或 blocked，同时列出缺失证据

### AC6: 高副作用 Skill 永不自动重放 (R1, R4)

- **Given** 中断发生在 pactkit-release、pactkit-board archive、snapshot、GitHub 写入或用户产物 draw 的前后
- **When** 新会话请求恢复
- **Then** 系统只展示已验证证据和下一个人工确认命令，不自动执行任何发布、远端写入、归档、tag 或用户产物覆盖

### AC7: 真实 project-act 在所有格式中保留恢复语义 (R5)

- **Given** Classic、OpenCode、Codex 和 Copilot 的临时隔离部署
- **When** 从 canonical project-act 模板渲染并执行内容完整性/归一化语义测试
- **Then** 每份生成物都有 continuation 检测、checkpoint、blocker 和 coverage 门禁；Codex 不含 STORY-slim-145 已知损坏签名；临时 target 外无写入

### AC8: 旧项目与诊断工具安全兼容 (R6)

- **Given** 没有 checkpoint 目录或只存在旧 context.md continuation 的项目
- **When** 运行 status、doctor、garden 与 Act preflight
- **Then** 不崩溃、不丢失已有 context，doctor/garden 正确报告 legacy 或 stale 状态，且可安全建立新的 checkpoint

## Target Call Chain

    $project-act STORY-XXX
      -> continuation preflight (Spec + Board + checkpoint + worktree verification)
      -> pactkit continuation resume (read-only decision)
      -> ContinuationStore.atomic_write(checkpoint)
      -> Act safe boundary: preflight / RED / GREEN / regression-lint / sync-coverage
      -> SkillRecoveryContract validates invoked runtime skill category
      -> context_gen renders human-readable continuation summary from checkpoint
      -> final coverage gate
      -> checkpoint completed OR blocked with explicit handoff

    pactkit doctor / pactkit garden / pactkit-status
      -> ContinuationStore.read_only_status()
      -> stale/orphan/schema/board consistency diagnostics

    deployer + external adapters
      -> canonical project-act template + SkillRecoveryContract
      -> prompt integrity / normalized parity validation
      -> format-specific SKILL.md output

## Technical Design

### Lateral Scan Results

- Operation: 跨会话工作恢复与进度持久化
- Existing implementations: 3（context_gen.py 的 Agent Continuation 文本摘要、cli.py 的 context 参数分发、commands.py 的 Act Phase 4 单点 context 更新）
- Assessment: Extract shared abstraction。三处现有逻辑都只能保存或提示 Markdown 摘要，无法验证 step、artifact、工作树或副作用；应抽取 Core-owned continuation state/contract，而不是在各 command 或 adapter 继续复制 resume 判断。

### State model and write boundary

Introduce a small Core-owned continuation module rather than parsing Markdown as state. Persist JSON with a versioned schema through atomic_write; validate it before every read-driven decision. context_gen only renders the compact human handoff and preserves the existing context.md public format.

Checkpoint transitions are monotonic: in_progress -> blocked|completed; only the explicit checkpoint CLI may create a new in_progress revision after validating evidence. resume never writes state. Each safe boundary names a deterministic step_id, so a new session never infers progress from prose alone.

### Skill contract registry

Create a Core registry keyed by the manifest skill name. It declares read_only, derived_replayable, idempotent_local_write, create_only, or manual_confirmation. A manifest coverage validator rejects missing, duplicate, or unknown records. The registry belongs in Core and adapters consume deployed prompt content rather than duplicating policy.

### Resume decision

The resume command is a verifier: it compares Story/Spec/Board, selected git/worktree fingerprint, expected artifacts and blocker state. Its only automatic actions are read-only checks and replayable derived outputs. It never writes state or executes an Act phase. It returns a structured decision: resume_at(step_id), start_fresh, blocked(reason), or manual_confirmation(actions).

### Skill-by-skill impact decision

R1 is the implementation contract and represents the required audit of all 13 manifest skills. No new resume-specific behavior should be invented for read-only skills; their role is evidence collection. Board, scaffold, draw, and release require special treatment because their writes are either user-owned, create-only, history-changing, or external. This prevents finish-task pressure from turning an interrupted workflow into an unsafe replay engine.

### Testing strategy

Use TDD with unit tests for schema, atomic overwrite behavior, transition validation, registry completeness, stale detection and completion gate. Use CLI E2E tests in a temporary project/home for resume success, stale block, legacy migration and zero-outside-target writes. Add full deployment parity tests against actual canonical project-act output across all profiles and external adapters, plus targeted tests for every skill category.

## Implementation Steps

| Step | File / Repository | Action | Dependencies | Risk |
|------|-------------------|--------|--------------|------|
| 1 | tests/unit/test_continuation*.py, tests/e2e/cli/ | RED tests for state schema, transitions, atomicity, contract coverage, complete gate and resume decisions | None | Medium |
| 2 | src/pactkit/continuation.py, schemas.py, utils.py | Add versioned state model, validation and atomic store | Step 1 | High |
| 3 | src/pactkit/cli.py, context_gen.py | Add explicit checkpoint plus read-only status/verify/resume entry points and derived human summary | Step 2 | High |
| 4 | src/pactkit/prompts/skills.py | Add 13-skill recovery contract registry and validate it against SKILL_MANIFEST | Step 1 | Medium |
| 5 | src/pactkit/prompts/commands.py, workflows.py, rules.py | Add Act safe-boundary writes, resume preflight, blocker handling and complete gate | Steps 2-4 | High |
| 6 | doctor.py, garden.py, status prompts | Add read-only stale/orphan/legacy continuation diagnostics | Steps 2-4 | Medium |
| 7 | generators/deployer.py, deploy_base.py, external adapters | Deploy canonical recovery semantics and test real full project-act parity | Steps 4-5 | High |
| 8 | all affected tests and temporary targets | Run unit, E2E, full regression, lint, external adapter suites and no-real-home migration checks | Steps 1-7 | Medium |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Checkpoints and diagnostic output MUST exclude credentials, environment secrets and unsafe command output |
| SEC-2 | Yes | CLI arguments, JSON checkpoint data, Story IDs and step IDs require strict schema/allowlist validation |
| SEC-3 | No | No database access or SQL query construction |
| SEC-4 | No | No browser rendering of untrusted content |
| SEC-5 | No | No authentication or session implementation |
| SEC-6 | No | No public network endpoint or rate-limited API |
| SEC-7 | Yes | Corrupt/missing state, filesystem errors and adapter failures must safely block resume without data loss |
| SEC-8 | Yes | Multi-package adapter compatibility and dependency bounds are required for identical deployed semantics |

## Out of Scope

- 修复 Codex Runtime 自身的 tool-call、配额、网络或模型停止问题。
- 在没有 checkpoint 的情况下猜测历史进度，或从自然语言回复推断完成状态。
- 自动重放 release、tag、GitHub 写入、archive、snapshot、用户-owned Draw.io 文件或其他外部副作用。
- 跨项目共享 continuation、云端同步、多人并发锁服务。
- 用本 Story 改变现有 Story 的业务需求或绕过 TDD、regression、lint 门禁。
