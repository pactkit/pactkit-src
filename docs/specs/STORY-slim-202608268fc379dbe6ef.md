# STORY-slim-202608268fc379dbe6ef: PactKit PDCA 规则语义深化与风险驱动执行模型

| Field | Value |
|-------|-------|
| ID | STORY-slim-202608268fc379dbe6ef |
| Status | Done |
| Priority | P1 |
| Release | 2.24.0 |

## Background

STORY-slim-20260825b1c83a046b4b 已建立场景化 Rule Registry、最小 Runtime Kernel、Phase Contracts、非阻塞失败语义和无损 ownership 部署，解决了普通 coding 被 PDCA 接管、历史 workflow 状态锁死当前工作、强制拆 session、Claude Code 出现 Codex runner 术语以及用户 rules 被覆盖等主要可用性问题。

当前实现仍存在第二层结构问题：Phase Contract 只有概要句，真正的阶段不变量、执行顺序和工程要求仍集中在较长的 command playbook 中；Runtime 整体被标记为 `hard/block_action`，但其中同时包含安全边界、required completion rule、default 和 advisory；除 `spec-preflight` 外，多数 RuleDefinition 的 `trigger/evidence/override` 来自通用默认值，难以驱动精确校验；十九个 engineering guides 仍以旧 MUST/NEVER 文本为源，再通过字符串替换降级为建议；`project-sprint` 静态加载 Plan、Act、Check、Done 全部 contracts，使非当前阶段规则同时占用上下文并可能互相干扰。

同时，当前工程实践选择主要依赖 NFR 关键词，没有先形成结构化 Change Risk Profile。范围扩张、弱测试、兼容面、迁移回滚、依赖供应链、运行就绪度和 UI 状态完整性虽在部分 playbook 或 guide 中出现，但没有统一的触发、证据和跨阶段闭环。Codex 也不能假定支持 Claude Markdown `@file` import，因此动态加载必须通过 Codex 原生 Skill progressive disclosure 或明确的文件读取完成，而不是输出一个模型可能忽略的路径标记。

本 Story 在不恢复全局重规则、不引入 workflow 锁和不增加强制 session 切换的前提下，深化规则语义：Phase Contract 负责结果不变量，playbook 负责执行建议，concern guide 负责风险决策；Sprint 每次只激活当前 phase capsule；工程规则由 Change Risk Profile 选择；所有完成门都以当前证据为基础并保留安全修复路径。

## Goals

1. 让每个 PDCA Phase Contract 能独立、简洁地表达输入、输出、不变量、完成证据、失败语义和副作用边界。
2. 消除 Runtime、Phase Contract、shared module 与 command playbook 的语义重复和等级混淆。
3. 将 Rule Registry 从结构化目录提升为可校验的行为契约。
4. 让 Sprint 在当前 session 中按阶段渐进加载，而不是一次注入全部 phase contracts。
5. 以 Change Risk Profile 驱动工程 guides、验证深度和交付证据。
6. 补齐范围完整性、测试充分性、兼容迁移、运行就绪、依赖供应链和 UI 状态等工程实践，同时保持按需和非阻塞。
7. 将 Classic（Claude Code）、Codex、OpenCode 作为一等支持宿主，保持相同逻辑语义并使用宿主原生加载方式；Copilot 仅保留安全、可迁移的兼容支持，不参与主要架构取舍。

## Design Principles

- **Contract describes outcomes**：Phase Contract 只定义阶段必须成立的事实，不复制工具命令和逐步教程。
- **Playbook describes procedure**：command playbook 给出推荐顺序、工具选择和恢复路径，但不得制造新的全局规则。
- **Guide describes a risk decision**：guide 仅在风险画像命中时加载，并明确适用与不适用条件。
- **One active phase**：任一时刻只有一个 phase capsule 对当前动作具有约束力。
- **Evidence over ceremony**：复用仍然新鲜的证据，不机械重复命令。
- **Block the action, not the workflow**：hard rule 只能阻止精确风险动作；其余失败只影响完成声明。
- **Host-native loading**：不把某一宿主的 import 语法当成跨宿主能力。

## Requirements

### R1: 细粒度 Rule Semantics (MUST)

Rule Registry MUST 支持一条逻辑规则内的细粒度等级，或将混合语义拆成多个原子规则。`runtime` 不得再以单一 `hard/block_action` 代表全部内容。只有凭据暴露、未经授权的外部副作用、越权访问和重大不可逆损坏 MAY 使用 `hard/block_exact_action`；activation、current-session、language matching、evidence reuse 等分别采用 `required/default/advisory`。Registry MUST 为每条可执行规则声明专属 `trigger`、`skip_when`、`evidence`、`failure` 和 `override`，不得以“被 Skill 引用”“文件已加载”等通用描述冒充行为证据。

### R2: 完整而紧凑的 Phase Contract Schema (MUST)

Init、Plan、Clarify、Act、Check、Done、Hotfix、PR、Release、Design、Debug 和 Sprint 十二个 workflow commands MUST 使用统一 Phase Contract schema；共享 phase contract 的入口仍须有独立 command policy。Schema 至少包含：`entry`、`inputs`、`outputs`、`invariants`、`completion_evidence`、`failure_semantics`、`allowed_next` 和 `external_effects`。Contract MUST 能独立判断该 command/phase 是否完成，但 MUST NOT 包含具体 CLI 命令、固定工具、模型名、逐步教程或重复的全局安全规则。每个 contract SHOULD 保持在预算内，并由测试验证没有复制其他 phase 的专属语义。

### R3: Contract、Playbook 与 Guide 单一职责 (MUST)

构建时 MUST 检测 Runtime、Phase Contract、shared module 和 command playbook 的高价值语义重复。完成条件、阻断类别、优先级和外部副作用的单一事实源 MUST 位于 Registry/Phase Contract；playbook 只能引用或渲染这些事实并描述执行步骤；guide 不得定义 phase transition、Board 状态或 Git/Release 授权。兼容常量 MAY 保留一个 minor version，但不得成为新的编辑入口。

### R4: Sprint 动态 Phase Capsule (MUST)

`project-sprint` 初始上下文 MUST 只包含 Runtime、Sprint orchestrator、shared execution、credential safety 和当前 Story/Wave 信息，不得静态注入 Plan、Act、Check、Done 的全部完整 contracts。进入某阶段时 MUST 只激活该阶段 capsule，退出时记录结果并将下一阶段设为唯一 active phase。所有阶段继续在当前宿主 session 内执行；capsule 切换不得要求新 session、runner、WorkUnit 或后台线程。若宿主不能物理卸载已读上下文，系统 MUST 通过 active-phase 标记保证旧 capsule 只作为历史证据。

### R5: 宿主原生渐进加载 (MUST)

Classic、Codex、OpenCode MUST 从同一逻辑 capsule registry 渲染，并通过完整的渐进加载、ownership、迁移和回滚门禁。直接调用单一 phase skill 时 MAY inline 对应 contract。Sprint 的 phase reference MUST 使用宿主真实支持的显式读取或 progressive-disclosure 机制，并提供紧凑 fallback；Codex MUST NOT 依赖 Markdown `@path` 展开，且 `AGENTS.md` 不得承载全部 phase contracts 或 guides。生成产物 MUST 可静态证明初始 Sprint prompt 未包含全部 phase contract 正文。Copilot SHOULD 消费同一 registry 的兼容投影并通过 smoke、安全边界和退休术语检查，但其能力限制不得决定三个一等宿主的目录、加载机制或 prompt budget。

### R6: Change Risk Profile (MUST)

Plan MUST 为变更形成结构化风险画像，Act MAY 根据实际 diff 更新，Check MUST 复核。风险维度至少包括：data migration、public API/schema、authentication/authorization、concurrency/state、external side effect、deployment/runtime、UI/accessibility、dependency/supply-chain。每个维度使用 `none/low/medium/high`、理由和所需 evidence 表达。风险画像 MUST 驱动 0–3 个 concern guides、验证深度和 rollback 要求；关键词只可作为候选信号，不能独自决定结论。无匹配风险时不得为凑模板加载 guide。

### R7: 原生 Engineering Guide Schema (MUST)

十九个现有 guides MUST 从旧绝对规则文本原生迁移为统一 schema：`Trigger`、`Questions`、`Safe Invariants`、`Defaults`、`Alternatives`、`Evidence`、`Non-applicable`。运行时不得再通过字符串替换 `MUST/NEVER` 来改变等级。Safe Invariants MUST 是 concern-specific 的真实安全/正确性边界；固定库、固定阈值、固定文件长度、固定连接池公式、所有 awaitable timeout 等 MUST 位于可根据项目证据偏离的 Defaults/Alternatives。

### R8: Scope Integrity (MUST)

Act MUST 根据 Spec Dependency Surface 和实现计划维护预期变更范围，并在完成前比较实际 diff。出现新增模块、依赖、生成文件、公共接口或无关重构时，MUST 记录原因并判断是必要扩展、需要更新 Spec，还是应移出当前 Story。范围差异不得阻止阅读和修复，但未解释的重大扩张 MUST 使 Act completion 保持 incomplete。生成文件 MUST 追溯到其源模板，不得只修改派生产物。

### R9: Test Adequacy 与 Evidence Freshness (MUST)

Act/Check 的验证不能只证明“测试命令退出码为 0”。测试充分性 MUST 检查：行为断言、原始缺陷复现、边界/失败路径、关键集成边界、Mock 是否绕过核心行为，以及测试是否可能在删除实现后仍通过。高风险逻辑 MAY 触发 mutation/negative-control 等更强验证。测试、lint 和 review evidence MUST 绑定相关 source/test/config 输入 hash 或等价 freshness 信息；无相关改动时 Done MUST 复用证据，有输入变化时只重跑受影响证据。

### R10: Compatibility、Migration 与 Rollback Contract (MUST)

涉及 public API、CLI、配置 schema、文件布局、manifest、数据库或协议版本时，风险路由 MUST 激活兼容迁移 contract。Plan 必须列出兼容面、升级前状态、重复执行语义、失败中间态和不可逆边界；Act 必须实现或明确拒绝 legacy alias/read path；Check 必须覆盖旧调用方/旧数据和中途失败；Done 必须记录迁移说明。无法提供自动回滚不等于永久阻塞，但高风险不可逆变更在获得明确授权前不得执行。

### R11: 条件工程实践扩展 (SHOULD)

Registry SHOULD 增加三个按需 concern guides：`operational-readiness`、`dependency-supply-chain`、`ui-state-accessibility`。运行服务/任务系统关注健康信号、可观测失败、feature flag、容量和 rollback signal；新增/升级依赖关注必要性、来源、版本锁定、许可证、安装脚本、原生二进制和权限扩张；UI 关注 keyboard/focus、loading/empty/error/disabled states、screen-reader label、contrast、responsive overflow 和 optimistic rollback。它们不得在不适用的 library、docs 或纯后端变更中加载。

### R12: 可解释解析与 Doctor 输出 (SHOULD)

PactKit SHOULD 提供只读 rule resolution 视图，显示当前 command、active phase、已加载/跳过规则、触发证据、guide 选择理由、优先级冲突及最终决策。Doctor MUST 能报告默认 metadata、重复语义、非法 hard blocker、Sprint 全 phase 静态泄漏、Codex `@file` 依赖和过期 legacy source，但不得自动修改用户规则或项目文件。

### R13: 非阻塞与兼容迁移 (MUST)

升级 MUST 保留 STORY-slim-20260825b1c83a046b4b 已建立的非阻塞、ownership 和 adapter parity 保证。旧 `rules`、`rule_scopes`、`command_rules` 和 guide 文件名必须有明确 alias/migration；用户修改文件继续 side-by-side；迁移失败保留最后一个完整部署。缺失 risk profile、scope evidence 或 test adequacy evidence 只能使 phase completion incomplete，不得复活旧的 active-run 排他锁或强制新 session。

## Technical Design

### Lateral Scan Results

- Operation: PDCA 规则选择、阶段约束渲染、工程 concern 路由和跨 adapter 部署。
- Existing implementations: `RULE_DEFINITIONS` 描述规则身份，`PHASE_POLICIES` 描述阶段结果，`COMMAND_RULES_MAP` 选择静态依赖，`commands.py`/`workflows.py` 再次描述完成与失败语义，`GuideDefinition` 与 `_risk_driven_content()` 分别保存 metadata 和旧文本转换逻辑，各 adapter 另行决定 inline/reference 形式。
- Reuse assessment: 保留现有 Registry、FormatProfile、deployment manifest 和 adapter render pipeline；将 PhasePolicy 扩展为唯一 Phase Contract，将 guide 迁移为原生结构化定义，并新增 capsule/risk resolver。无需另建平行 workflow engine。
- Duplication assessment: completion、blocking、session、external side effect 等概念跨四处以上重复，已超过抽象阈值；应由结构化 contract 生成 playbook 摘要和 manifest evidence，而不是继续人工同步。
- Capability assessment: Classic 可显式读取 managed phase 文件；Codex 可通过 Skill progressive disclosure 读取 skill-local references；OpenCode/Copilot 可用 adapter-native prompt/reference 或紧凑 fallback。各宿主都不需要新增 runner 或跨 session 服务。

### Current Call Chain

```text
RuleDefinition / PhasePolicy / GuideDefinition
  -> COMMAND_RULES_MAP
  -> command template rendering
  -> Classic @import | Codex Skill inline | OpenCode command inline | Copilot prompt inline
  -> active project-* command
```

当前 `PhasePolicy` 只记录概要字段，`COMMAND_RULES_MAP[project-sprint]` 静态引用四个 phase contracts，guide 内容由 `_risk_driven_content()` 对旧文本进行字符串替换。新设计将三者收敛到结构化 registry。

### Proposed Model

```python
RuleClause(
    id="authorization.external-side-effect",
    level="hard",
    trigger="before push, PR, tag, publish, release, or external message",
    evidence=("current user authorization covers the exact action",),
    failure="block_exact_action",
    override="explicit authorization; platform safety is not overridable",
)

PhaseContract(
    id="act",
    entry=("explicit project-act invocation", "resolved objective"),
    inputs=("current request", "usable Spec when Spec-bound"),
    outputs=("implementation", "behavioral tests"),
    invariants=("scope integrity", "source-of-truth edits"),
    completion_evidence=("Spec alignment", "fresh targeted tests"),
    failure_semantics="incomplete_continue",
    allowed_next=("check", "done"),
    external_effects=(),
)

RiskDecision(
    concern="migration-rollback",
    level="high",
    reason="deployment manifest schema and filesystem layout change",
    evidence=("legacy fixture", "mid-write failure test", "idempotent redeploy"),
)
```

### Phase Capsule Lifecycle

```text
Sprint start
  -> load orchestrator only
  -> resolve Story/Wave
  -> activate Plan capsule
  -> verify Plan completion evidence
  -> activate Act capsule; Plan becomes historical evidence
  -> verify Act completion evidence
  -> activate Check capsule
  -> repair path returns to Act capsule without leaving the session
  -> activate Done capsule only when requested/authorized
```

Adapter rendering policy:

| Adapter | Direct phase command | Sprint capsule loading | Forbidden assumption |
|---------|----------------------|------------------------|----------------------|
| Classic | Native command/Skill plus phase reference | Explicit Read of managed phase file at transition | Stop hook or new session required |
| Codex | Contract inline in selected `SKILL.md` | Skill-local `references/phases/*.md` read on transition, compact inline fallback | Markdown `@path` expansion |
| OpenCode | Command inline or native instruction reference | Explicit phase reference read supported by adapter | Global `rules/*.md` means every phase is active |
| Copilot | Prompt inline for direct phase | Workspace-local phase references or compact generated fallback | Background runner/WorkUnit facade |

### Risk-to-Evidence Routing

| Risk | Plan decision | Act evidence | Check evidence |
|------|---------------|--------------|----------------|
| Data migration | forward/backward path, irreversibility | migration + idempotency | old data + interrupted run |
| Public API/schema | compatibility window | alias/version adapter | old caller contract tests |
| Auth/authorization | actor/action/resource matrix | deny-by-default tests | privilege-boundary review |
| Concurrency/state | ownership and ordering | race-safe implementation | contention/failure cases |
| External side effect | authorization/idempotency | controlled integration test | duplicate/partial failure |
| Deployment/runtime | rollout/rollback signal | artifact/config validation | isolated deploy/smoke |
| UI/accessibility | interaction/state matrix | component behavior tests | keyboard/focus/error states |
| Dependency/supply chain | necessity and trust | locked dependency | license/source/install review |

## Change Risk Profile

| Dimension | Level | Reason | Required evidence |
|-----------|-------|--------|-------------------|
| Data migration | Low | 不迁移业务数据，但会迁移 rule/guide manifest schema 和生成布局 | 2.23.x fixtures、双次升级、失败后旧 manifest 可用 |
| Public API/schema | High | RuleDefinition、PhasePolicy、GuideDefinition 和 adapter manifest 是跨仓消费接口 | compatibility projection、schema tests、adapter version gate |
| Authentication/authorization | Medium | hard rule 和 external-effect authorization 将被重新建模 | exact-action blocker tests、credential regression |
| Concurrency/state | Medium | Sprint active-phase transition 和 evidence freshness 涉及状态顺序 | 单一 active phase、Check→Act 返回、无历史状态排他锁测试 |
| External side effect | High | deploy/update 可写宿主配置，PR/Release 等动作需要授权 | 临时 target 测试、真实 HOME 零写入、授权边界测试 |
| Deployment/runtime | High | Classic 与三个 adapter 的生成策略和 manifest 都会变化 | 四 adapter 隔离部署、normalized parity、rollback injection |
| UI/accessibility | Low | 只新增 UI concern guide，不修改业务 UI | guide routing fixture、纯后端/文档不泄漏测试 |
| Dependency/supply-chain | Low | 计划不新增运行依赖，但会新增对应 concern guide | dependency diff 检查、无新增依赖或给出必要性证据 |

Selected implementation guides: `backwards-compatibility`、`testing-strategy`、`error-recovery`。选择理由是本 Story 的主要风险位于跨版本 schema、证据质量和中途部署失败；其余 concern 作为路由测试 fixture，不在实现上下文中全量加载。

## Acceptance Criteria

### AC1: Runtime 不再是单一 hard rule (R1)

- **Given** 新 Rule Registry 和 Runtime Kernel
- **When** validator 枚举其中的规则条款
- **Then** 只有允许的安全/授权/不可逆风险条款为 `hard/block_exact_action`，current-session、language、activation 和 evidence reuse 使用更低等级且拥有专属 trigger/evidence/override

### AC2: 每个 Phase Contract 可独立判定完成 (R2, R3)

- **Given** 十二个 `project-*` workflow commands
- **When** 对其 Phase Contract 执行 schema 和内容校验
- **Then** 每个 contract 都声明完整字段、能判定本 phase 完成，并且不包含 CLI 命令、固定工具、模型名或其他 phase 的专属步骤

### AC3: Playbook 不复制权威语义 (R3)

- **Given** Runtime、contracts、shared modules 和 command playbooks
- **When** 运行语义重复与 source-of-truth 测试
- **Then** completion、blocking、priority 和 external-effect 语义来自 registry/contract，playbook 只渲染引用和步骤，兼容文本不再作为新编辑入口

### AC4: Sprint 初始只加载 orchestrator (R4)

- **Given** 用户在任一支持的 adapter 调用 `project-sprint`
- **When** 检查初始 prompt 和 Plan→Act→Check→Done 转换
- **Then** 初始 prompt 不含四个完整 contracts；任一时刻只有一个 active phase；失败可在当前 session 回到修复阶段，且不产生 runner、WorkUnit 或强制新 session

### AC5: Codex 使用原生 progressive disclosure (R5)

- **Given** Codex 隔离部署
- **When** 检查 `AGENTS.md`、`project-sprint/SKILL.md` 和其 references
- **Then** Runtime 保持最小，Sprint 按阶段显式读取 skill-local reference 或使用紧凑 fallback，不包含 `@~/.codex/...`，也不把全部 guides/contracts 常驻注入

### AC6: 风险画像决定 guides 与验证深度 (R6)

- **Given** 分别包含数据库迁移、UI 状态、依赖升级和无特殊风险的四个 Spec fixture
- **When** Plan/Act concern router 生成 Change Risk Profile
- **Then** 每个风险有等级、理由和 evidence；只选择 0–3 个最相关 guides；纯关键词误命中不会独自激活规则

### AC7: Guides 不再依赖字符串降级 (R7)

- **Given** 全部现有及新增 engineering guides
- **When** 构建最终 guide 内容
- **Then** 每个源定义原生包含七段 schema，构建不执行 MUST/NEVER 文本替换，固定技术选择和阈值位于 Defaults/Alternatives，Safe Invariants 仅保留 concern-specific 安全或正确性边界

### AC8: 未解释的范围扩张只阻止完成声明 (R8)

- **Given** 实际 diff 新增了 Spec Dependency Surface 外的模块、依赖或公共接口
- **When** Act 执行 scope-integrity check
- **Then** 系统报告差异和建议处置；安全修复仍可继续，但在解释或同步 Spec 前不得声称 Act 完成；生成文件可追溯到源模板

### AC9: 测试证据证明行为且保持新鲜 (R9)

- **Given** 一个只断言退出码的弱测试、一个删除实现仍会通过的测试，以及一组先前通过但输入已变化的 evidence
- **When** Act/Check/Done 评估 test adequacy 与 freshness
- **Then** 弱证据被指出并要求补充行为断言，过期证据只重跑受影响部分；未变化输入的有效证据可被 Done 复用

### AC10: 兼容迁移覆盖旧数据与中途失败 (R10, R13)

- **Given** public/config/manifest migration 风险和 2.23.x legacy fixtures
- **When** 连续升级两次并模拟中途写入失败
- **Then** 旧调用方/旧数据仍按声明兼容，部署幂等，失败保留最后完整版本，用户修改文件不被覆盖，不可逆操作仅阻断其自身直到获得授权

### AC11: 条件工程实践不泄漏 (R11)

- **Given** service、dependency、UI 和纯文档四类变更
- **When** risk router 选择 operational、supply-chain 和 UI guides
- **Then** 前三类各获得对应决策问题和证据要求，纯文档变更不加载这些 guides，任何未命中 guide 都不形成完成门

### AC12: Rule resolution 可解释且只读 (R12)

- **Given** 一个 command、项目规则、用户规则、旧 Spec 和 advisory guide 存在优先级冲突
- **When** 执行 doctor/rule-resolution audit
- **Then** 输出 active phase、加载与跳过理由、证据、最终优先级和潜在问题，不修改任何规则、Spec 或源码

### AC13: 三主宿主语义一致，Copilot 保持兼容 (R4, R5, R13)

- **Given** 同一 registry、phase contracts、risk profiles 和 guides
- **When** 隔离部署 Classic、Codex、OpenCode，并对 Copilot 执行兼容性 smoke
- **Then** 三主宿主的 activation、active-phase、rule level、failure、evidence 和 ownership 语义一致，格式差异只体现在宿主原生加载方式；Copilot 保持安全兼容且不反向约束主宿主；所有产物均无退休编排术语、全 phase 静态泄漏或 maintainer 泄漏

## Target Call Chain

```text
src/pactkit/prompts/rules.py
  RuleDefinition / PhasePolicy / COMMAND_RULES_MAP
    -> src/pactkit/prompts/commands.py + workflows.py
    -> src/pactkit/generators/deployer.py
    -> src/pactkit/deploy_manifest.py
    -> Classic deployment

src/pactkit/prompts/guides.py
  GuideDefinition / guide registry / concern router
    -> Plan risk profile
    -> Act guide selection
    -> Check evidence matrix

Core registry
    -> pactkit-codex/src/pactkit_codex/deployer.py
    -> pactkit-opencode/src/pactkit_opencode/deployer.py
    -> pactkit-copilot/src/pactkit_copilot/deployer.py
    -> adapter-native phase capsules and parity manifests

src/pactkit/doctor.py + src/pactkit/cli.py
    -> read-only rule resolution and conflict report
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_rule_registry_architecture.py`, new focused tests | Add RED tests for atomic levels, Phase schema, source-of-truth and non-blocking semantics | None | Medium |
| 2 | `src/pactkit/prompts/rules.py` or dedicated registry modules | Introduce RuleClause, full PhaseContract and active-phase capsule registry; migrate compatibility projections | 1 | High |
| 3 | `src/pactkit/prompts/commands.py`, `src/pactkit/prompts/workflows.py` | Slim playbooks, remove duplicated authority, implement Sprint phase transitions and capsule references | 2 | High |
| 4 | `src/pactkit/prompts/guides.py` | Replace transformed legacy prose with native guide schema and add three conditional guides | 2 | High |
| 5 | concern/risk routing module and Spec templates | Add Change Risk Profile, scope-integrity, test-adequacy and compatibility evidence model | 2–4 | High |
| 6 | `src/pactkit/generators/deployer.py`, `src/pactkit/deploy_manifest.py` | Render host-native capsules and record normalized rule/phase/guide semantics | 2–5 | High |
| 7 | `src/pactkit/doctor.py`, `src/pactkit/cli.py` | Add read-only rule resolution, duplication and leakage diagnostics | 2–6 | Medium |
| 8 | `pactkit-codex`, `pactkit-opencode` deployers；`pactkit-copilot` compatibility adapter | Implement native progressive disclosure for primary hosts and a safe compatibility projection for Copilot | 6 | High |
| 9 | Core and adapter tests | Fully cover three primary hosts; smoke-test Copilot compatibility; cover direct phase, Sprint transitions, Codex no-@, risk fixtures, rollback and user-file preservation | 1–8 | High |
| 10 | architecture/migration documentation | Document layer ownership, phase lifecycle, compatibility aliases and upgrade behavior | 2–9 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Runtime、guides 和 doctor 涉及 credential safety；重构不得降低秘密保护 |
| SEC-2 | Yes | Registry、risk profile、Spec、config 和用户 rules 都是输入，必须校验 schema、路径和枚举 |
| SEC-3 | N/A | 本 Story 不引入数据库查询；数据库仅作为风险路由 fixture |
| SEC-4 | Yes | UI guide 涉及输出与可访问状态，但本 Story 不直接渲染业务 HTML；prompt 内容仍需防不可信指令提升权限 |
| SEC-5 | Yes | active phase、用户授权和外部副作用属于执行边界 |
| SEC-6 | Yes | 规则优先级、override、guide loading 和工具调用必须遵循最小权限 |
| SEC-7 | Yes | 跨 adapter 部署、迁移和中途失败必须原子降级并保留可用版本 |
| SEC-8 | Yes | 新增 dependency/supply-chain guide；实现本身不得无必要新增运行依赖 |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | STORY-slim-20260825b1c83a046b4b, STORY-slim-145, STORY-slim-147 |
| Provides | 原子规则语义、完整 Phase Contract、Sprint 动态 capsule、Change Risk Profile、原生 guides、scope/test/compatibility evidence |
| Touches | `src/pactkit/prompts/rules.py`, `src/pactkit/prompts/commands.py`, `src/pactkit/prompts/workflows.py`, `src/pactkit/prompts/guides.py`, `src/pactkit/generators/deployer.py`, `src/pactkit/deploy_manifest.py`, `src/pactkit/doctor.py`, `src/pactkit/cli.py`, three adapter deployers and their tests |
| Conflict risk | HIGH |

## Migration Strategy

1. 先扩展 registry/schema 与测试，保留当前 RuleDefinition、PhasePolicy 和 guide filenames 的兼容投影。
2. 将 Runtime 混合语义拆成原子 clauses，但维持现有最小渲染结果，避免部署升级时同时改变所有行为。
3. 逐个迁移 Phase Contract；直接 phase commands 先切换，Sprint 最后切换为动态 capsules。
4. 将 guides 改为结构化源定义；旧文件名继续解析到新 ID，用户修改文件继续 side-by-side。
5. adapter 以 normalized manifest 做 parity；任何 adapter 不支持目标加载方式时显式使用 compact fallback，不伪造动态能力。
6. 在临时 HOME/target 中执行 2.23.x → 2.24.0 双次升级和中途失败测试；失败不得改变最后完整 manifest。
7. 一个 minor version 后，在 telemetry-free doctor 报告证明无活动 legacy config 引用时，才考虑移除旧兼容源。

## Out of Scope

- 不把所有工程实践提升为全局 hard rules。
- 不要求普通 coding 创建 Spec、Risk Profile、Board 或 Test Case。
- 不引入新的跨 session runner、WorkUnit 调度器、Stop hook 或后台 agent runtime。
- 不要求宿主真正从模型上下文中删除已读取文本；只保证唯一 active phase 和渐进读取。
- 不自动修改 user-owned 或 project-owned rules。
- 不强制 mutation testing、完整 E2E、可观测平台、feature flag 或 rollback automation；它们由风险等级决定。
- 不在本 Story 中发布 PyPI、Git tag、GitHub Release，或写入真实用户 HOME。

## Verification Evidence

- Core regression: `4598 passed, 1 warning`。
- Codex adapter: `169 passed`；OpenCode adapter: `103 passed`；Copilot compatibility smoke: `41 passed`。
- Ruff: Core、Codex、OpenCode、Copilot 均通过。
- 隔离部署：三个一等宿主 Claude Code、Codex、OpenCode 均成功生成；manifest schema v2、22 个 guides、单一 active phase 和 phase capsule 顺序校验通过。Copilot 保持兼容性 smoke 覆盖。
- Codex Sprint 使用 skill-local `references/phases/*.md`，不依赖 Markdown `@file` 展开。
- 三主宿主 Sprint 产物均不含 Team API、WorkUnit、runner 或固定模型路由；Copilot 兼容产物通过相同退休术语检查。
- 真实 Story 的 `spec-preflight` 通过；正文中的歧义 basename 不再误触发阻塞。
- 未写入真实用户 HOME，未 commit、push 或 release。
