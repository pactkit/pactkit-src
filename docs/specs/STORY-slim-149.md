# STORY-slim-149: Codegraph-first 静态分析路由与显式降级

| Field | Value |
|-------|-------|
| ID | STORY-slim-149 |
| Status | Done |
| Priority | P0 |
| Release | 2.21.0 |

## Background

项目已安装 Codegraph 1.1.6，存在 `.codegraph/codegraph.db`，并在 `.codex/pactkit.yaml` 中配置 `visualize.graph_provider: codegraph`。实际执行 Plan 时仍优先调用内置 `visualize.py` 和 `rg`。现有 playbook 一方面要求先运行 Visual Scan，另一方面仅把 `pactkit query` 描述为可选路径，没有代码级 provider 路由、索引新鲜度门禁或降级审计。

当前 `pactkit query` 直接在 `cli.main()` 内读取 Codegraph SQLite；`lazy_visualize.codegraph_sync()` 只在图生成后运行。查询入口不检查 CLI 是否存在、索引是否由旧引擎生成、源码是否更新，也无法区分“合法空结果”和“索引/查询异常”。这使 Plan、Act、Trace 可以静默跳过已配置的 Codegraph。

## Requirements

### R1: 建立统一的静态分析 Provider Router (MUST)

Core MUST 提供独立于 CLI 和 prompts 的查询路由服务，读取项目 `graph_provider` 配置并返回结构化 provider decision。Plan、Act、Trace、回归影响分析和其他调用方 MUST 通过该服务选择查询路径，不得自行组合 Codegraph、SQLite、内置 Mermaid graph 或 `rg`。

路由结果 MUST 至少包含 requested provider、selected provider、availability、freshness、query kind、query target、result count、fallback status 和 machine-readable reason code。

### R2: Codegraph 配置必须产生强制优先级 (MUST)

当 `graph_provider: codegraph` 时，router MUST 优先使用 Codegraph。不得仅因为模型偏好、查询返回空集合或已有 `.mmd` 文件而跳过。运行前 MUST 验证可执行文件、数据库、索引状态及配置一致性；需要且安全时执行一次有界 `codegraph sync`，再查询。

若 Codegraph 状态命令提示索引由旧引擎构建，router MUST 返回可观测 warning；是否允许本次查询继续必须由明确策略决定，不得隐藏警告。不得自动执行破坏性 `codegraph index`。

### R3: 降级必须显式、可配置且可审计 (MUST)

Codegraph 配置模式默认 MUST fail closed：binary missing、DB missing、status failed、sync failed、schema incompatible 或 query failed 时返回失败，不得静默使用 `rg`/Mermaid。只有调用方显式传入 `--allow-fallback` 或配置允许时，才可按 `builtin_graph → text_search` 顺序降级。

每次降级 MUST 输出源 provider、目标 provider、reason code 和人类可读说明。敏感路径与命令输出必须净化。空结果不是错误；router MUST 在索引健康且查询成功时标记 `valid_empty`，不能因零结果自动 fallback。

### R4: 提供稳定的 query/explore/impact 接口 (MUST)

CLI MUST 支持统一的 callers、callees、chain、explore 和 impact 查询。现有 `pactkit query --callers|--callees|--chain` 语法 MUST 保持兼容，并增加 `--json`、`--explain` 与 `--allow-fallback`。新接口 SHOULD 封装 Codegraph CLI，而非长期依赖其私有 SQLite schema；旧 SQLite reader 可作为兼容 adapter。

结构化输出 MUST 对不同 provider 使用同一结果模型，使 prompts 和测试不依赖 Codegraph 的 ANSI 文本或版本特定格式。

### R5: Plan、Act 与 Trace 必须使用相同的 Codegraph-first 契约 (MUST)

Canonical `project-plan`、`project-act` 和 `pactkit-trace` MUST 首先调用统一 query/explore 接口，并记录 provider decision。只有 router 明确选择 fallback 后才可调用内置 visualize 或 `rg`。playbook MUST NOT 再要求无条件先生成图，也不得要求模型自行判断 provider。

Plan 的 archaeology checkpoint 和 Act 的 preflight/trace evidence MUST 包含 provider、freshness、查询目标与结果摘要；未执行配置要求的 provider 时，相应阶段不得被验证完成。

### R6: 索引生命周期必须与源码变化一致 (MUST)

Core MUST 以 Codegraph status/sync 的结果判断索引新鲜度，避免仅比较数据库 mtime。查询前至多自动 sync 一次，设置超时并返回失败原因；并发查询/同步必须避免重复竞态。`pactkit visualize --lazy` 可继续刷新派生图，但不得成为 Codegraph 查询可用性的前置条件。

### R7: 多 Adapter 必须保留完整查询语义 (MUST)

Classic、OpenCode、Codex 和 Copilot 的隔离部署 MUST 保留 Plan/Act/Trace 的统一入口、Codegraph 优先级、禁止静默降级和 evidence 要求。Adapter 不得将 query 参数改成说明文字，Core/adapter 版本不匹配时必须由兼容门禁阻止部署。

### R8: 提供可诊断性和向后兼容 (SHOULD)

`pactkit doctor` SHOULD 报告 configured/selected provider、binary version、DB 状态、freshness、旧引擎警告和最近一次 fallback。未配置 provider 的项目 SHOULD 保持当前内置 graph 行为；未安装 Codegraph 且未配置它的项目不得报错。

## Acceptance Criteria

### AC1: 已配置 Codegraph 时不会先走内置图或 rg (R1, R2)

- **Given** `graph_provider: codegraph`、可用 binary 和健康索引
- **When** Plan、Act 或 Trace 请求 callers/callees/chain/explore
- **Then** router 选择 Codegraph，输出 provider evidence，且内置图和文本搜索未被调用

### AC2: 健康索引的空结果被诚实接受 (R2, R3)

- **Given** Codegraph 状态健康且目标符号确实不存在
- **When** 查询返回零条结果
- **Then** 结果标记 `valid_empty`，不触发 fallback，也不声称查询失败

### AC3: Codegraph 故障默认禁止静默降级 (R3)

- **Given** 已配置 Codegraph，但 binary、DB、status、sync 或 query 任一步失败
- **When** 未传 `--allow-fallback` 执行查询
- **Then** 命令非零退出并输出稳定 reason code，且不调用 Mermaid/rg fallback

### AC4: 显式降级记录完整证据 (R3, R4)

- **Given** Codegraph 查询失败且调用方显式允许 fallback
- **When** 内置 graph 或文本搜索成功
- **Then** 统一结果包含原 provider、最终 provider、失败原因、fallback chain 和查询结果

### AC5: 旧 query CLI 保持兼容 (R4)

- **Given** 现有脚本调用 `pactkit query --callers foo`、`--callees foo` 或 `--chain foo --down`
- **When** 升级到新版本
- **Then** 输出的符号语义和退出码保持兼容，同时 `--json`/`--explain` 提供结构化路由证据

### AC6: 索引过期时只同步一次再查询 (R6)

- **Given** Codegraph status 报告源码变更且索引需要 sync
- **When** 发起一次查询
- **Then** router 在超时内执行一次 sync、重新检查状态并查询；同步失败时按 R3 处理，不无限重试

### AC7: 旧引擎索引警告可见且不触发破坏性重建 (R2, R6)

- **Given** Codegraph status 报告 index built by earlier version
- **When** 执行查询
- **Then** 输出 warning/evidence，不自动运行 full index；健康查询仍可按策略继续

### AC8: Plan/Act checkpoint 验证 provider evidence (R5)

- **Given** 项目配置 Codegraph
- **When** Plan archaeology 或 Act trace 尝试完成但 evidence 显示 `builtin_graph`/缺少 provider
- **Then** checkpoint 被拒绝；Codegraph 查询成功或显式获准降级后才可推进

### AC9: 四个目标平台部署语义一致 (R7)

- **Given** canonical Plan、Act、Trace 模板
- **When** 隔离部署到 Classic、OpenCode、Codex、Copilot 并运行语义 parity 检查
- **Then** provider 路由、freshness、fallback 和 evidence 关键操作全部保留，目标目录外无写入

### AC10: 未配置 Codegraph 的项目保持兼容 (R8)

- **Given** 项目未设置 graph provider 且没有 `.codegraph`
- **When** 执行 Plan/Act/Trace 查询
- **Then** router 选择内置 provider 并解释默认决策，不要求安装 Codegraph且不产生错误

## Target Call Chain

    project-plan / project-act / pactkit-trace
      -> pactkit query|explore --json --explain
      -> GraphProviderRouter.resolve(project config, query request)
      -> CodegraphProvider.health()
      -> optional bounded CodegraphProvider.sync()
      -> CodegraphProvider.query()
      -> UnifiedGraphResult + ProviderDecision evidence
      -> explicit BuiltinGraphProvider/TextSearchProvider fallback only when allowed

    Plan/Act continuation checkpoint
      -> workflow evidence validator
      -> verify provider == configured provider OR authorized fallback evidence

    pactkit doctor
      -> GraphProviderRouter.diagnostics()
      -> configured/selected/version/freshness/fallback report

## Technical Design

### Lateral Scan Results

- Provider selection appears independently in `cli.py` query handling, `lazy_visualize.py`, Plan/Act prompts and `pactkit-trace`.
- Codegraph index refresh is implemented by `codegraph_sync()`, while query execution directly reads SQLite in `cli.main()`; there is no common health or fallback contract.
- Assessment: extract a shared provider router and adapters; CLI, workflows and diagnostics consume it instead of adding another prompt instruction.

### Provider model

Define `GraphQueryRequest`, `GraphQueryResult`, `ProviderDecision` and a provider protocol. `CodegraphProvider` owns binary/status/sync/query integration; `BuiltinGraphProvider` owns generated graph queries; `TextSearchProvider` is the final explicit fallback. Router policy is deterministic and testable without invoking prompts.

### Freshness and failure policy

Codegraph status output is the authoritative freshness signal. The adapter normalizes version-dependent output to stable reason codes. Query execution uses bounded subprocess timeouts, strips ANSI sequences and never logs secrets. A successful empty result is distinct from process/schema failure. Full re-index remains an explicit user operation.

### Capability Assessment

| Need | Source | Decision |
|------|--------|----------|
| Symbol graph/query | installed Codegraph CLI | Reuse through public CLI adapter |
| Existing callers/callees/chain compatibility | `pactkit query` SQLite implementation | Preserve CLI contract, migrate behind provider adapter |
| Index refresh | `lazy_visualize.codegraph_sync()` | Reuse logic through centralized provider |
| Fallback graph | PactKit visualize/call graph | Reuse only through explicit router decision |
| Routing/evidence | none | Implement new Core service |

### Engineering concern decisions

- Module design: providers implement a narrow protocol; router owns policy; CLI owns presentation.
- Error recovery: one sync attempt, fixed timeout, stable reason codes, explicit fallback only.
- Backwards compatibility: preserve existing query flags/output and default behavior when Codegraph is not configured.
- Observability: every query can emit structured provider, health, freshness and fallback evidence.
- Testing strategy: fake subprocess/provider tests, real local Codegraph smoke test, empty/failure/stale fixtures and four-adapter prompt parity.

## Implementation Steps

| Step | File / Repository | Action | Dependencies | Risk |
|------|-------------------|--------|--------------|------|
| 1 | new graph routing unit tests | RED tests for selection, empty results, failures, sync, fallback and output model | None | High |
| 2 | new graph provider module, `lazy_visualize.py` | Implement provider protocol, health/sync/query and router | Step 1 | High |
| 3 | `cli.py` | Move query logic behind router; add JSON/explain/fallback and explore/impact | Step 2 | High |
| 4 | continuation workflow validators | Require provider evidence for Plan archaeology and Act trace | Steps 2-3, STORY-slim-147 | High |
| 5 | `prompts/commands.py`, `prompts/skills.py`, rules | Route Plan/Act/Trace through unified CLI and remove manual selection | Steps 2-4 | Medium |
| 6 | doctor and deployment integrity | Add diagnostics and canonical semantic checks | Steps 2-5 | Medium |
| 7 | Core and adapter suites | Verify real Codegraph smoke path and four isolated deployments | Steps 1-6 | High |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 查询目标、subprocess 输出和诊断可能包含本机路径或敏感文本，必须净化 |
| SEC-2 | Yes | query target、provider、DB override 和 CLI 参数均不可信，必须严格校验并限制路径 |
| SEC-3 | Yes | 兼容 adapter 以只读方式访问 SQLite，必须参数化查询并禁止任意 SQL |
| SEC-4 | No | 不涉及浏览器或前端渲染 |
| SEC-5 | No | 不涉及认证或授权 |
| SEC-6 | No | 不新增网络服务或远端 API |
| SEC-7 | Yes | binary/status/sync/query 超时、损坏索引和并发 sync 必须显式失败或受控降级 |
| SEC-8 | Yes | Codegraph 版本差异、Core/adapter 版本及四平台命令渲染需要兼容验证 |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | STORY-slim-121, STORY-slim-124, STORY-slim-126, STORY-slim-145, STORY-slim-147 |
| Provides | Codegraph-first provider router、索引新鲜度门禁、显式 fallback 与 Plan/Act/Trace evidence |
| Touches | graph query/provider modules, CLI, lazy visualize, continuation validators, Plan/Act/Trace prompts, doctor, deploy integrity and adapter tests |
| Conflict risk | HIGH |

## Out of Scope

- 修改 Codegraph 自身的索引格式、解析器或 MCP server。
- 在未授权时自动安装、升级或执行完整 `codegraph index`。
- 保证 Codegraph 能解析所有语言或动态调用。
- 用 Codegraph 替代 Spec、测试、人工代码阅读或所有文本搜索。
- 实现 STORY-slim-147/148 中与查询路由无关的能力。
