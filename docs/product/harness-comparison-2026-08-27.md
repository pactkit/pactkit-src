# PactKit vs DeepSeek Harness / Codex CLI — 对比分析与提升清单

> 日期：2026-08-27
> 对比对象：
> - [deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)（本地 checkout：`/Users/slim/workspaces/deepseek-harness`，版本 0.1.1-rc.2，developer preview）— 全功能 agent 运行时（**机制思想参照系**）
> - [Codex CLI](https://github.com/openai/codex)（本地 checkout：`/Users/slim/workspaces/codex`，Rust workspace ~120 crates）— **PactKit 的部署宿主之一**（宿主对齐参照系）
>
> 结论用途：PactKit 后续版本改进候选清单（非承诺排期）

---

## 0. 一句话结论

**对比 dsh（运行时参照系）**：PactKit 在证据治理和 fail-closed 设计上领先（dsh 完全没有 PDCA / Spec / Board 对应物）；dsh 值得抄的不是功能，而是三个机制思想：

1. **事件溯源的会话模型**（append-only 事件流替代覆盖式 checkpoint）
2. **自报降级状态的诚实门**（gate 必须声明自己的 enforcement completeness）
3. **"文档由代码生成且 CI 防漂移"的工程纪律**（生成式目录 + 漂移门）

**对比 Codex（宿主参照系）**：宿主的扩展面进化速度超过了 pactkit-codex adapter 的利用程度 —— Codex 现已拥有**12 事件生命周期 hooks 引擎、插件+marketplace 系统、Starlark 确定性策略引擎**，而 adapter 目前只部署 skills/rules/prompts 静态文件，`commit-gate` 的 hook 通道只接了 Claude 侧。宿主已经把"确定性拦截"的原生机制造好了，PactKit 没用上。

其中 dsh 线的前两条（事件流 + 诚实门）正好是 PactKit 当前"collecting friction data"阶段缺的那双眼睛；Codex 线则是**不新增语义、只接通既有机制**就能拿到的拦截力升级。

---

## 1. 定位差异（为什么不是逐功能对比）

三个项目不在同一层：

- **dsh** 是完整的 agent **运行时**：基于 Cordis（vendored）的"一切皆插件"架构，自己驱动模型、执行工具、管理会话，含 Web UI、沙箱、subagent、工作流引擎。
- **Codex CLI** 是 PactKit 的**宿主**之一：OpenAI 的 Rust 实现 coding agent，拥有 OS 级沙箱、12 事件 hooks 引擎、插件系统。它既是"可借鉴机制的来源"，也是"必须对齐的部署目标"。
- **PactKit** 是骑在宿主 CLI（Claude Code / OpenCode / Codex）之上的**治理层**：不驱动模型，只做确定性验证（evidence-typed workflow registry、fail-closed gates、部署完整性）。

因此对比有两条线：
- **dsh 线**：哪些机制性思想可以移植到 PactKit 的治理定位内。两家是互补关系——dsh 甚至把 Claude Code 和 Codex 当作 subagent 后端（`packages/subagent/subagent-claude-code` / `subagent-codex`），它缺的 PDCA/证据层正是 PactKit 的主场。
- **Codex 线**：宿主的原生扩展面（hooks / 插件 / 策略层）与 pactkit-codex adapter 当前利用度之间的**已查证差距**（见第 4 节）。

---

## 2. 能力对比总览（dsh 线）

| 维度 | deepseek-harness | PactKit | 差距性质 |
|---|---|---|---|
| 运行时 | 完整 agent loop（Cordis 插件化，一切可插拔） | 无（寄生于宿主） | 定位使然，不补 |
| 会话模型 | **append-only 事件流**，"model-visible ⟺ logged" 不变量；fork/resume/compaction/telemetry 全部从同一条流推导 | 扁平 JSON checkpoint（`continuation.py`），覆盖式写入 | **可移植，价值高** |
| 崩溃恢复 | 持久化屏障（模型请求/副作用前先落盘）+ `TOOL_OUTCOME_UNKNOWN` 恢复语义 | 按 step checkpoint；artifact 消失会 fail 而非 brick，但无"结果未知"中间态 | **可移植** |
| 工具安全 | 单调 guard（只能拒绝不能放行）+ fail-closed 审批 + **每次审批落一对 `asked/decided` 审计事件** | 授权门控 Story 写入（结构性防篡改），但授权决策本身无审计流 | **可移植** |
| 证据/治理 | 无 PDCA 对应物（仅 Agent Notes 设计决策记录 + 运行时不变量注册表） | **PactKit 主场**：workflow registry、fail-closed gates、delivery evidence、commit/coverage gate | PactKit 领先 |
| 可观测性 | OTel、token meter、session query 工具、事件回放 | doctor stdout + H1-H7 静态审计 + observe.py（web 指标）；无 agent 行为级追踪 | **可移植，价值高** |
| 文档工程 | 生成式目录（工具/配置/事件 catalog）+ type-equiv 漂移门 + 双语 blob-hash 配对 + 自定义 merge driver | prompt↔CLI 一致性 CI + golden CLI snapshot | 部分可移植 |
| 测试纪律 | 逐文件 100% 覆盖率门 + **任何 model-visible 变更必须同 PR 带真实组合 snapshot 测试**（ACP + headless + Chromium 双 SDK） | 288 单测 + 部署完整性检查 + golden help snapshot | **可移植** |
| 沙箱/并行/模型路由 | Landlock/Seatbelt 沙箱、continuable 后台 subagent、LLM 适配层 | 均无 | 定位使然，不补 |

---

## 3. 可移植提升点 — dsh 线（按优先级）

### P0 — 直接服务当前阶段（collecting friction data + enterprise adoption）

#### P0-1. Checkpoint 升级为 append-only 事件流

**dsh 机制**：`packages/core/session` —— Session 是类型化事件的只追加日志；不变量 "model-visible ⟺ logged"（凡是到达模型请求的内容必须可从日志重建，由运行时不变量强制）。fork、resume、compaction、telemetry、UI 全是这条流的投影。

**PactKit 现状**：`continuation.py` 是覆盖式 JSON —— 只知道 run 的*当前状态*，丢失*历史*（evidence 被推翻过几次、blocker 挂了多久、重试了几次）。

**落地做法**：
- `.pactkit/continuations/runs/<id>/` 下新增 `events.jsonl`；step 进入、evidence 记录/失效、blocker 升降各追加一条带时间戳事件
- 现有 JSON checkpoint 保留，作为事件的投影物化视图（兼容既有 `finish_guard` 读取路径）
- 改动面集中在 `ContinuationEngine` 内部，是 P0-2 的前提

#### P0-2. Friction 数据管道（run 指标采集与导出）

**背景**：项目记忆里写着 "Feature-complete, collecting friction points. No new features until friction data" —— 但 PactKit 目前**没有任何结构化的 run 指标出口**，friction data 实际上收不上来。

**落地做法**：基于 P0-1 的事件流，新增 `pactkit stats`（或 `pactkit runs`）命令，输出：
- 每 run 时长、evidence 重试次数、blocker 停留时长（按 blocker kind 分桶）
- gate 通过 / 降级 / 拦截比例
- 哪条 rule 被触发、哪个 workflow step 最常返工
- JSON 导出（`--format json`），将来接任何 dashboard 都有数据源

这是 dsh token-meter + session stats 的治理版对应物，也是 enterprise 客户的必问项（"你们的流程到底省了多少返工"）。

#### P0-3. Gate 执行完整度上报（"honest sandbox" 思想）

**dsh 机制**：沙箱后端必须自报 enforcement completeness（`full|partial`），调用方被迫正视缺口，不许假装全覆盖。

**PactKit 现状**：已有雏形——commit-gate 自锁保护是 fail-open + WARN（`commit_gate.py`），但这属于"悄悄降级"。

**落地做法**：
- 统一约定：每个 gate 输出机器可读的 enforcement 状态（`full / degraded / unavailable`）
- `doctor` 汇总所有 gate 的当前降级状态
- 企业客户审计时，"你们的门什么时候是虚掩的"是必答题；答案应该在 `pactkit doctor --json` 里

### P1 — 机制强度提升

#### P1-1. 授权审计事件对

**dsh 机制**：每次审批落一对 `approval/asked` + `approval/decided` 审计事件到不可变日志，不可抵赖。

**PactKit 现状**：`user_input / authorization` blocker 只是暂停等待，人来解除，但**决策本身没有留痕**。

**落地做法**：在 P0-1 事件流里落 `authorization/asked` + `authorization/granted|denied` 事件对。enterprise 场景的合规刚需，且实现几乎免费（依赖 P0-1）。

#### P1-2. 崩溃恢复语义补全：`outcome_unknown` 中间态

**dsh 机制**：`packages/session/session-checkpoint-policy` 在每个模型请求和副作用工具体之前落持久化屏障；崩溃恢复时注入模型可见的 `TOOL_OUTCOME_UNKNOWN` 结果，专门设计成不破坏 KV-cache 前缀，避免 agent 假设成功或失败。

**PactKit 现状**：`revalidate_artifacts` 只处理"artifact 消失"一种情况。commit-gate 跑到一半被 Ctrl-C 时，run 没有明确表达"验证结果未知"。

**落地做法**：checkpoint 状态机增加 `outcome_unknown`（或 evidence 级别的 unknown 标记），恢复时强制重跑该验证步骤而非沿用旧结论。

#### P1-3. 设计决策记录（Agent Notes 的治理版）

**dsh 机制**：`.agents/notes/` 强制每个非平凡 PR 附带一份带生命周期的决策记录（`proposed/implemented/rejected` × 类型分类，路径编码生命周期），pre-commit 门检查"同一 PR 必须有 note"。

**PactKit 现状**：有 lessons.md（教训）和 stories（任务），但缺**"为什么这么做"的决策层**。

**落地做法**：与现有 `pactkit scaffold` / commit-gate 基础设施契合——加一个 note 模板 + commit-gate 规则："本 commit 触及 governance/spec/architecture 文件时须有对应 decision note"。对 enterprise adoption 价值极高（他们最怕不可追溯的架构决定）。

### P2 — 工程纪律（低成本，防漂移）

#### P2-1. 生成式目录 + 漂移门

**dsh 机制**：从源码生成工具/配置/事件目录进文档（`scripts/gen-cordis-catalog.ts` 等），CI 检查再生成是否 diff 为零；`type-equiv` 门抽取源码声明+JSDoc，文档粘贴漂移即 fail。

**PactKit 落地**：`workflow_registry.py`（所有 workflow 的 evidence 要求表）和 `RULE_DEFINITIONS`（16 条规则）目前只存在于代码里——生成 `docs/reference/` 目录页并 CI 校验，规则和证据要求永不与文档漂移。是现有 prompt↔CLI 一致性 CI 的同一思想延伸。

#### P2-2. 组装后 prompt 的跨宿主 snapshot 测试

**dsh 机制**：任何 model-visible 变更必须同 PR 带真实组合的 snapshot 测试（无 key、真实组装、多表面）。

**PactKit 落地**：已有 golden CLI help snapshot 与部署完整性检查，但**没有三个宿主渲染出的最终 prompt 的字节级快照**。加一个 e2e：deploy 到临时目录，对 Claude / OpenCode / Codex 三个 profile 的产物做 snapshot。prompt 模板改动导致的静默回归（2.21/2.22 withdrawn 这类事故）会被直接拦住。

#### P2-3. 配置分层组合（profile → 项目 → 用户 overlay）

**dsh 机制**：profile / bundle / patch 三层 last-write-wins + `--dump-config` 打印最终组合树。

**PactKit 落地**：`pactkit.yaml` + `FormatProfile` 目前是平面的。做成层叠 + `pactkit config dump`；多团队 enterprise 场景"公司基线覆盖项目覆盖个人"是常见诉求。

---

## 4. Codex CLI 对比（宿主视角）

Codex 与 dsh 的角色不同：它不是"抄思想"的对象，而是 PactKit 的部署目标。本节回答两个问题：**(a) Codex harness 有哪些机制 PactKit 可以借力或借鉴；(b) pactkit-codex adapter 相对 Codex 现有扩展面的真实差距在哪**（差距部分已逐一查证 PactKit 源码）。

### 4.1 Codex 值得关注的 harness 机制

| 机制 | 位置 | 与 PactKit 的关系 |
|---|---|---|
| **12 事件 hooks 引擎**：PreToolUse（可 block + 改写输入 + 附加上下文）、PermissionRequest（可裁决）、PostToolUse、Pre/PostCompact、SessionStart/End、SubagentStart/Stop、Stop、Interrupt；支持 shell 命令和 **MCP 调用**两种 handler | `codex-rs/hooks/src/lib.rs`，schema 在 `hooks/schema/generated/` | commit-gate 可增加 Codex 原生通道（现在只有 Claude hook + git pre-commit） |
| **Hook 信任机制**：第三方 hook 需 content-hash 信任确认才启用；企业 `allow_managed_hooks_only=true` 可全锁 | `hooks/src/registry.rs` | adapter 部署 hook 的安全前提（对应 feedback: 绝不静默改用户工具配置） |
| **插件 + marketplace 系统**：一个 `.codex-plugin` manifest 捆绑 skills + hooks + MCP servers + apps | `codex-rs/plugin/src/manifest.rs`, `core-plugins/` | PactKit 已有 Claude plugin（`pactkit-plugin/`），Codex 有等价分发形态 |
| **Anthropic 兼容 SKILL.md + 隐式调用检测**：命令匹配 skill 脚本时触发审批 | `codex-rs/skills/` | PactKit skills 天然可迁移；隐式调用 = 免提示词的确定性触发点 |
| **Starlark execpolicy**：命令前缀规则 `allow/prompt/forbidden` + justification + 加载时自测试 | `codex-rs/execpolicy/` | "策略即数据"——PactKit 规则的宿主原生执行版 |
| **沙箱策略 + permission profiles 作为配置数据**：read-only / workspace-write / danger-full-access，分域文件系统策略 | `protocol/src/config_types.rs` | PactKit 的 write_scope 治理可编译到这一层 |
| **分层配置栈**：enterprise `requirements.toml` → managed → project `.codex/config.toml` → profile | `codex-rs/config/src/loader/` | 与 P2-3 配置分层的诉求完全同构，可参考其合并语义 |
| **Guardian auto-review**：`approvals_reviewer=auto_review` 让一个专门 subagent 顶在审批环里 | `codex-rs/core/src/guardian/` | PactKit Check 阶段自动化评审的宿主内对应物 |
| **不可变 rollout JSONL + SQLite 状态库**：追加式会话记录，fork/revert 保 thread id | `codex-rs/rollout/` | 佐证 P0-1 方向：三家（dsh/Codex/Claude）都是事件流模式 |
| **app-server JSON-RPC**：VS Code 同款协议，可编程 approve/steer turn | `codex-rs/app-server/` | PactKit 未来做监督面板的免费通道（`pactkit supervise`） |

### 4.2 已查证的 adapter 差距（最 actionable 的部分）

以下四条均已在 PactKit 源码中逐一定位确认：

1. **commit-gate 只接了 Claude hook 通道**
   `commit_gate.py:274`（`install_hook`）只 merge `.claude/settings.json`；Codex 宿主上仅有 git pre-commit 兜底（退出码语义也不同：Claude exit 2 / git exit 1）。而 Codex 现在有原生 PreToolUse（可 block + `updated_input` 改写）和 Stop 事件——拦截时点可以从"提交时"提前到"工具调用时"，且能把修正反馈直接注入对话。

2. **Codex profile 的能力模型已过时**
   `profiles.py:212` 的 codex `FormatProfile` 把 `"hooks"` 列入 `excluded_agent_fields`（基于"Codex 没有 hooks"的旧假设，现在 Codex 有 SubagentStart/Stop 等 hooks）；`supports_model_routing=False` 也与 Codex 现有的 `model_providers`/profiles 机制不符。能力标志目前是**硬编码快照**，而 Codex 的 wire 格式（hook schema、app-server）与二进制版本钉死。

3. **MCP 只是声明，没有部署动作**
   `supports_mcp=True`，但 `deployer.py:305` 仅打印一句 "Configure in Claude Code settings.json → mcpServers" 的手动提示；没有生成 Codex `[mcp_servers]` 配置段，也没有 Claude 侧的自动注册。PactKit 的治理工具（board / continuation / doctor）本可以作为 MCP server 原生暴露给宿主调用。

4. **没有 Codex 插件分发形态**
   PactKit 为 Claude 打了 `pactkit-plugin/` 插件包，Codex 现在有完全对等的机制（一个包捆绑 skills+hooks+MCP，marketplace 可发现），但 adapter 没有 `.codex-plugin` manifest 输出。发布流程第 6 步天然可以扩展出 Codex 目标。

### 4.3 Codex 线新增提升项

#### P0-4. pactkit-codex adapter 接入 Codex hooks 引擎

**落地做法**：
- commit-gate 增加 Codex 通道：生成 `.codex/hooks.json`（PreToolUse 拦截 Bash git commit / Stop 事件检查 run 状态），handler 复用现有 `pactkit commit-gate --hook` 入口（Codex hook 事件名与 Claude Code 风格对齐，输入/输出 schema 需按 `hooks/schema/generated/` 适配）
- **信任机制红线**：Codex hook 需要 content-hash 信任确认才生效，企业环境可能 `allow_managed_hooks_only`。部署绝不能静默写入（对应 codex config.toml 两次被清空的事故教训）——部署时显式告知用户需要信任确认，`doctor` 增加 Codex hook 信任状态检测
- 同步修正 `profiles.py` 的 codex 能力标志（hooks 不再排除）

#### P1-4. Codex 插件分发形态

生成 `.codex-plugin/` manifest（捆绑 skills + hooks.json + MCP server 声明），对称于现有 Claude plugin 发布流程。发布 checklist 第 6 步扩展为双目标。

#### P1-5. write_scope 编译到宿主策略层

PactKit 的 write_scope（Spec `Touches` ∪ 项目配置）目前只存在于 prompt 规则层。编译为：
- Codex：`sandbox_workspace_write` 边界 / permission profile / execpolicy 前缀规则
- Claude：permissions allowlist

从"模型被提示不要越界"升级为"宿主结构性拒绝越界"。这是 PactKit"确定性核心"哲学在宿主侧的自然延伸。

#### P2-4. 治理工具 MCP 化

把 board / continuation / doctor 的关键子命令包成 MCP server：宿主可以原生调用（不再依赖 CLI 可用性探针），Codex 的 hook handler 甚至可以直接是 MCP 调用而不必 shell out。

#### P2-5. doctor 增加 Codex 版本/能力探测

Codex 的 hook schema 与 wire 格式和二进制版本钉死。`pactkit doctor` 探测本机 Codex 版本，按版本动态判定能力标志（替代 `profiles.py` 的硬编码快照），避免 adapter 对着旧能力模型部署。

---

## 5. 明确不抄的部分（及理由）

| 不抄 | 理由 |
|---|---|
| 运行时 / LLM 适配层 / token meter / compaction / Code Mode / 沙箱 | 这是宿主的职责。抄了就变成第二个 harness，与"治理层"定位冲突。dsh 与 PactKit 是互补关系 |
| Web UI | 宿主有 UI。P0-2 的 stats 做 JSON 导出即可，将来任何 dashboard 都有数据源；Codex 的 app-server JSON-RPC 已提供监督通道 |
| Cordis 插件运行时 / DI 容器 | PactKit 的 entry-point deployer 机制已覆盖"第三方扩展部署器"这个真实需求 |
| 双语 blob-hash 配对 + 自定义 merge driver | PactKit 双语内容量小（仅站点），收益配不上复杂度 |
| 逐文件 100% 覆盖率门 | PactKit 已有自己的覆盖率门治理宿主项目；对自身可参考但不强制 |
| Guardian auto-review 的完整实现 | 思路值得借鉴（Check 阶段自动评审），但审批环自动化是宿主职责；PactKit 只需保证自己的 review 工具产出结构化证据供其消费 |

---

## 6. 依赖关系与建议顺序

```
dsh 线：
P0-1 事件流 ──┬──> P0-2 friction 管道
              └──> P1-1 授权审计对
P0-3 gate 完整度上报（独立）
P1-2 outcome_unknown（依赖 checkpoint 状态机改动，可与 P0-1 同期）
P1-3 决策记录（独立，靠 commit-gate）
P2-1/P2-2/P2-3（独立，纯工程纪律）

Codex 线：
P0-4 Codex hooks 接入（独立；先于 P1-4，是插件包的内容物之一）
P1-4 Codex 插件形态（依赖 P0-4 的 hooks.json + P2-4 的 MCP 声明更佳）
P1-5 write_scope → 宿主策略层（独立）
P2-4 治理工具 MCP 化（独立）
P2-5 doctor 版本探测（独立，小改动）
```

若只做一件事：**做 P0-1 + P0-2**。它不改变治理语义、改动面可控，且直接解决"friction data 收不上来"这个当前阶段的卡点。

若做两件事：加 **P0-4（Codex hooks 接入）**。它不新增任何治理语义——只是把已有的 commit-gate 接到宿主已造好的原生拦截机制上，投入最小、拦截时点提升最大，且 2.23.0 发布尾巴里的 codex ownership 契约缺口正好在这次 adapter 升级中一并补齐。
