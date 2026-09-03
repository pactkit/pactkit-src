# Sprint Board

## 📋 Backlog

### [HOTFIX-slim-127] Add codegraph sync to PDCA command source templates
> Spec: docs/specs/HOTFIX-slim-127.md

- [ ] Fix project-plan
- [ ] Fix project-act
- [ ] Fix project-done
- [ ] Fix project-hotfix

### [HOTFIX-slim-131] Fix deployer @ refs before frontmatter
> Spec: docs/specs/HOTFIX-slim-131.md

- [ ] Fix _deploy_commands prepend order

### [HOTFIX-slim-132] Add explicit board.py move_story command to project-act
> Spec: docs/specs/HOTFIX-slim-132.md

- [ ] Add move_story command template to Phase 0.6

### [STORY-slim-115] Worktree/Parallel Session Artifact Drift Prevention
> Spec: docs/specs/STORY-slim-115.md

- [ ] 实现派生 Board 视图
- [ ] 增加 Board 生成与状态命令
- [ ] 迁移 PDCA Board 操作
- [ ] 验证并行 Session 安全
- [ ] 完成兼容迁移与回归

### [STORY-slim-118] codegraph MCP Integration for Semantic Code Queries
> Spec: docs/specs/STORY-slim-118.md

- [ ] Document replacement vs augmentation decision
- [ ] Add codegraph MCP conditional note to SKILL_VISUALIZE_MD Graph Query Protocol
- [ ] Run pactkit update to redeploy

### [STORY-slim-119] Improve Python Call Graph Coverage
> Spec: docs/specs/STORY-slim-119.md

- [ ] Extend _extract_calls to capture non-self attribute method calls (R1)
- [ ] Capture function references in list/assignment contexts (R2)
- [ ] Use ast.walk to scan nested functions (R3)
- [ ] Write TDD tests for AC1-AC4
- [ ] Run pactkit update to redeploy

### [STORY-slim-2026082727cc4ab535e7] [P2-1 backlog] 生成式目录 + 漂移门
> Spec: docs/specs/STORY-slim-2026082727cc4ab535e7.md

- [ ] workflow_registry + RULE_DEFINITIONS 生成 docs/reference/ 目录页，CI 校验 diff 为零

### [STORY-slim-2026082730b5954cf538] [P2-4 backlog] 治理工具 MCP 化
> Spec: docs/specs/STORY-slim-2026082730b5954cf538.md

- [ ] board/continuation/doctor 关键子命令包成 MCP server（[mcp_servers] 配置段生成）
- [ ] Codex hook handler 可走 MCP 不必 shell out

### [STORY-slim-20260827625b870eb7da] [P2-3 backlog] 配置分层组合（企业基线→项目→用户 overlay）
> Spec: docs/specs/STORY-slim-20260827625b870eb7da.md

- [ ] pactkit.yaml 层叠 last-write-wins + pactkit config dump
- [ ] 参考 Codex config loader 与 dsh profile/bundle/patch 语义

### [STORY-slim-202608277ec1236a7b99] [P1-2 backlog] outcome_unknown 崩溃恢复中间态
> Spec: docs/specs/STORY-slim-202608277ec1236a7b99.md

- [ ] checkpoint 状态机增加 outcome_unknown（evidence 级 unknown 标记）
- [ ] 恢复时强制重跑验证步骤而非沿用旧结论（Ctrl-C 半途场景）

### [STORY-slim-20260827833e7a200f9a] [P2-2 backlog] 跨宿主 prompt snapshot 测试
> Spec: docs/specs/STORY-slim-20260827833e7a200f9a.md

- [ ] deploy 到临时目录，对 Claude/OpenCode/Codex 三 profile 产物做字节级 snapshot
- [ ] 拦截 prompt 模板静默回归（2.21/2.22 类事故）

### [STORY-slim-20260827855bf3efaec3] [P1-3 backlog] 设计决策记录（Agent Notes 治理版）
> Spec: docs/specs/STORY-slim-20260827855bf3efaec3.md

- [ ] decision note 模板 + commit-gate 规则：触及 governance/spec/architecture 文件须有对应 note
- [ ] enterprise adoption：可追溯架构决定

### [STORY-slim-2026082799fa651655be] [P2-5 backlog] 宿主版本/能力探测泛化
> Spec: docs/specs/STORY-slim-2026082799fa651655be.md

- [ ] 大部分已被 STORY-slim-20260827024e71df170f R4/R5（Codex 探测）覆盖
- [ ] 剩余：OpenCode/Copilot 的版本探测与 profiles 能力标志动态化

### [STORY-slim-20260827c67e3add6af5] [P1-1 backlog] 授权审计事件对：authorization/asked + granted|denied 落事件流
> Spec: docs/specs/STORY-slim-20260827c67e3add6af5.md

- [ ] 依赖 P0 事件流（STORY-slim-20260827024e71df170f）落地后在 blocker 升降路径落审计事件对
- [ ] enterprise 合规刚需，实现成本低

### [STORY-slim-20260827d0ae0dfada51] [P1-5 backlog] write_scope 编译到宿主策略层
> Spec: docs/specs/STORY-slim-20260827d0ae0dfada51.md

- [ ] Spec Touches∪项目 write_scope 编译为 Codex sandbox/permission profile + Claude allowlist
- [ ] 从 prompt 劝告升级为宿主结构性拒绝

### [STORY-slim-20260827fb6291b717eb] [P1-4 backlog] Codex 插件分发形态（.codex-plugin manifest）
> Spec: docs/specs/STORY-slim-20260827fb6291b717eb.md

- [ ] 生成 .codex-plugin manifest 捆绑 skills+hooks+MCP 声明
- [ ] 依赖 P0-4 hooks.json；对称于现有 Claude plugin 发布流程

## 🔄 In Progress

## ✅ Done

### [HOTFIX-slim-20260828ee6cde3108fb] git hooks must not lock everyone out when pactkit is missing
> Spec: docs/specs/HOTFIX-slim-20260828ee6cde3108fb.md

- [x] PATH probe in generated pre-commit/pre-push scripts

### [HOTFIX-slim-20260830bbb5bc219d35] gate CLI syntax + push-gate cross-repo root
> Spec: docs/specs/HOTFIX-slim-20260830bbb5bc219d35.md

- [x] Accept authorize keyword in gate CLI
- [x] Resolve cd-target repo in hook_entry
- [x] Focused tests + golden refresh

### [HOTFIX-slim-20260901469666ef23a8] commit-gate misfires on docs/meta-only commits
> Spec: docs/specs/HOTFIX-slim-20260901469666ef23a8.md

- [x] Fix three defects: doc-only patterns miss repo meta files (.gitignore/.claude/.codex); full-suite target hard-codes tests/unit/ with no tests/ fallback and counts exit 4/5 as RED; missing pytest module (pipx fallback) reads as RED instead of GateUnavailable. From harness-backend 2026-09-01 friction.

### [STORY-slim-145] Codex 部署命令语义完整性与 Adapter 兼容门禁
> Spec: docs/specs/STORY-slim-145.md

- [x] 建立 CLI policy 与结构化操作渲染契约
- [x] 移除 pactkit-codex 有损命令前缀替换
- [x] 增加 prompt 完整性与 Classic/Codex parity 门禁
- [x] 阻止不兼容 Core/adapter 组合静默部署
- [x] 完成隔离迁移、双仓回归与 2.23.0 同版本构建验证

### [STORY-slim-147] 全 Skill 执行可靠性协议与 Plan 可恢复工作流
> Spec: docs/specs/STORY-slim-147.md

- [x] 建立 25 入口执行可靠性注册表
- [x] 抽象通用 continuation engine
- [x] 无损迁移 project-act
- [x] 接入 project-plan 可恢复 workflow
- [x] 增加迁移诊断与安全门禁
- [x] 验证四种部署目标语义一致

### [STORY-slim-148] Git 友好的分片治理事实源与无冲突投影视图
> Spec: docs/specs/STORY-slim-148.md

- [x] 定义 Story/Lesson 分片 schema 与唯一字段所有权
- [x] 实现无中心唯一 ITEM ID 与新旧解析兼容
- [x] 迁移 Board 和 Lesson 写入到单记录 repository
- [x] 将 Context 与 Board 降级为只读 projection
- [x] 实现无损迁移、回滚与禁止双写门禁
- [x] 迁移所有消费者并验证双工作树无冲突
- [x] 验证四种 Adapter 的新治理语义

### [STORY-slim-149] Codegraph-first 静态分析路由与显式降级
> Spec: docs/specs/STORY-slim-149.md

- [x] 实现统一 GraphProviderRouter 与结果模型
- [x] 实现 Codegraph 健康、新鲜度和单次 sync
- [x] 扩展 query/explore/impact CLI 与显式 fallback
- [x] 让 Plan Act Trace 统一走查询路由
- [x] 校验 continuation provider evidence
- [x] 增加 doctor 与部署完整性诊断
- [x] 验证四种 Adapter 的查询语义

### [STORY-slim-2026082381e832771d4e] Codex 未完成 Workflow 终止门禁与宿主续跑协议
> Spec: docs/specs/STORY-slim-2026082381e832771d4e.md

- [x] 实现 workflow finish-guard 与稳定终止决策
- [x] 为关键写操作增加 managed active-run ownership
- [x] 定义宿主 capability handshake 与 bounded resume runner
- [x] 加入 lease、无进展检测与人工副作用边界
- [x] 在四平台模板中部署 Pre-Final Protocol
- [x] 建立 transcript-level agent-loop 与 adapter 验收
- [x] 补充 doctor、manifest 与保证等级文档
- [x] 为十个通用 Project Workflow 增加命令级完成证据
- [x] 在 Codex、OpenCode 与 Copilot 部署 Sprint 串行降级入口

### [STORY-slim-20260823d854b0cf1875] Portable Methods 与宿主能力分层工作流架构
> Spec: docs/specs/STORY-slim-20260823d854b0cf1875.md

- [x] 定义三层产品边界与单一事实源
- [x] 实现 Work Unit 与租约状态机
- [x] 实现 ExecutionAttempt 与 EvidenceReceipt 复验
- [x] 建立 Host Capability Contract 与诚实降级
- [x] 提取 Portable Methods 单一内容源
- [x] 迁移 project-plan 与原子 finalize
- [x] 移除 Stop hook 正确性依赖
- [x] 完成兼容迁移、doctor 与真实宿主验证

### [STORY-slim-20260823de7e85d6042a] Codex Stop Hook 强制续跑与真实宿主完成门禁
> Spec: docs/specs/STORY-slim-20260823de7e85d6042a.md

- [x] 实现 Core session/turn 绑定与 hook-facing decision 接口
- [x] 实现 Codex Stop handler 与 finish-guard 映射
- [x] 部署并无损管理 Codex hooks 配置
- [x] 增加 trust/capability/doctor 与 manifest 诊断
- [x] 覆盖 handler、部署和防循环测试
- [x] 完成真实 Codex Plan/Done 提前终止 E2E
- [x] pip 更新并验证真实本机 Codex 部署

### [STORY-slim-20260825b1c83a046b4b] PactKit 场景化规则架构与非阻塞执行契约
> Spec: docs/specs/STORY-slim-20260825b1c83a046b4b.md

- [x] 建立规则注册表与最小 Runtime Kernel
- [x] 拆分 Phase Contracts 与共享能力模块
- [x] 统一非阻塞失败和完成语义
- [x] 重写风险驱动 Engineering Guides
- [x] 实现 ownership 安全迁移与回滚
- [x] 验证四种 Adapter 语义一致性

### [STORY-slim-202608264cf429c75e22] Unify deployment ownership safety across skills, agents, CLAUDE.md and rollback
> Spec: docs/specs/STORY-slim-202608264cf429c75e22.md

- [x] Extract shared ownership helper (load_previous_hashes + preserve_or_write) in deploy_manifest.py; narrow manifest skill ownership to registered artifacts
- [x] Write RED tests for skill/agent ownership preservation (AC1-AC4, AC9)
- [x] Refactor _deploy_rules/_deploy_guides to shared helper; add ownership checks to _deploy_skills/_deploy_agents; fix _deploy_claude_md unreadable+appended-content paths; retire disabled skills with proof
- [x] Write RED tests for CLAUDE.md preservation and skill retirement (AC5, AC8)
- [x] Fix rollback_paths: catch BaseException + per-restore isolation
- [x] Write RED tests for KeyboardInterrupt rollback and restore isolation (AC7, AC10)
- [x] Full regression + update spec status
- [x] QA fix iteration — command-skill ownership, CLAUDE.md boundary tightening, gate unification, retirement hardening, count honesty

### [STORY-slim-2026082672b57c78fd67] Subtraction pass: dead code removal, completion-rule dedup, CLI decomposition
> Spec: docs/specs/STORY-slim-2026082672b57c78fd67.md

- [x] RED: taxonomy-consistency + help-surface snapshot tests
- [x] Completion-rule delegation to workflow_validators (R1)
- [x] Shared step taxonomy (R2)
- [x] cli.py decomposition (R3)
- [x] Dead code removal with adapter-package grep proof (R4)
- [x] Doctor FORMAT_PROFILES root helper (R5)
- [x] Full regression + CHANGELOG
- [x] Delivered scope: R3 bounded + R4 partial + R5 project-level (R1/R2 dropped per legacy freeze)

### [STORY-slim-202608267c3989223b4d] Workflow engine robustness: no bricked runs, corrupt-file isolation, Windows locks
> Spec: docs/specs/STORY-slim-202608267c3989223b4d.md

- [x] RED tests AC1-AC6
- [x] workflow_engine: fingerprint consistency + scan isolation
- [x] continuation: platform-split lock + story lock + stale tolerance + typed guards
- [x] host_continuation typed access
- [x] Full regression

### [STORY-slim-202608268fc379dbe6ef] PactKit PDCA 规则语义深化与风险驱动执行模型
> Spec: docs/specs/STORY-slim-202608268fc379dbe6ef.md

- [x] 细化 RuleClause 与 PhaseContract schema
- [x] 实现 Sprint 动态 phase capsule
- [x] 建立 Change Risk Profile 与风险路由
- [x] 原生重写 engineering guides 并补三类实践
- [x] 实现 scope integrity 与 test adequacy evidence
- [x] 完善兼容迁移、doctor 与四 Adapter parity

### [STORY-slim-20260826ac1f0bfe4148] Prompt-to-CLI contract consistency: machine-checked and gap-closed
> Spec: docs/specs/STORY-slim-20260826ac1f0bfe4148.md

- [x] RED contract test AC1/AC2
- [x] board.py add_task subcommand + AC3 round-trip test
- [x] spec_preflight dedup + oversized-reference WARN + AC4/AC5 tests
- [x] Playbook interface inventory (R4)
- [x] Full regression

### [STORY-slim-20260826cb37edfdd4da] Freeze and isolate the legacy workflow engine with a data-driven deletion track
> Spec: docs/specs/STORY-slim-20260826cb37edfdd4da.md

- [x] RED tests AC1-AC8
- [x] Create protocols.py neutral constants module
- [x] Move workflow_engine + host_continuation to frozen legacy package with compat shims
- [x] Re-point cli/doctor/deploy_manifest imports + usage instrumentation + doctor usage line
- [x] Test import migration + full regression
- [x] CHANGELOG deprecation notice

### [STORY-slim-20260826ce35b77ce005] Gate subsystem fails closed: fix inverted and fail-open gates
> Spec: docs/specs/STORY-slim-20260826ce35b77ce005.md

- [x] RED tests AC1-AC9 with mocked subprocesses
- [x] Fix audit.py: pip-audit exit contract, exception surfacing, no_secrets pathspec, single-layer scorecard guard, load_config path
- [x] Fix done_verify.py word-boundary matching
- [x] Extract shared venv-aware pytest helper; coverage_gate fail-closed + CLI exit code
- [x] Fix commit_gate collection-failure transparency + tests/** classification
- [x] Fix doctor.py stale-graph config loading
- [x] Full regression

### [STORY-slim-20260826f9492ab32c3d] Unify pactkit.yaml read and sync precedence into one canonical order
> Spec: docs/specs/STORY-slim-20260826f9492ab32c3d.md

- [x] RED tests AC1-AC4 fixture matrix
- [x] Expose single candidate-order constant in profiles.py
- [x] sync_config_copies: sync-from-effective + atomic write + divergence warning
- [x] Full regression + pre-existing sync test migration

### [STORY-slim-20260827024e71df170f] P0 可观测性与拦截力升级：run 事件流、friction 统计、gate 完整度上报、Codex 原生 hooks 接入
> Spec: docs/specs/STORY-slim-20260827024e71df170f.md

- [x] R1 事件流写入：continuation.py 锁内追加 events/*.jsonl + 归档随行
- [x] R2 pactkit stats 聚合命令 + golden CLI snapshot 更新
- [x] R3 enforcement 状态模型（full/degraded/unavailable）+ doctor 聚合
- [x] R4 Codex hooks.json 薄注册（create-if-absent，依赖 ownership 契约修复）
- [x] R4b Codex hook schema 适配 + doctor 真实能力检测 + profiles 能力标志修正
- [x] 单测：AC1-AC3 事件流（投影一致/blocker 对/崩溃安全）
- [x] e2e：AC7-AC9 config.toml 字节不变 + hooks 幂等 + doctor 检测

### [STORY-slim-20260827eddbe9669c87] Continuation 状态机补强：授权审计事件对与 outcome_unknown 恢复语义
> Spec: docs/specs/STORY-slim-20260827eddbe9669c87.md

- [x] R1 授权审计事件对（asked/granted 自动 + denied 显式，双路径发射）
- [x] R2 pactkit continuation deny 命令（锁内、前置校验、blocked 重写）
- [x] R3 验证尝试围栏 record_attempt + commit-gate 接入
- [x] R4 resume/finish_guard outcome_unknown 交叉检查（阻塞与解除）
- [x] R5 stats 授权决策计数 + golden CLI 更新

### [STORY-slim-20260827fc9de5542ad7] Codex command references 所有权契约修复：command manifest v2 记录 reference 摘要
> Spec: docs/specs/STORY-slim-20260827fc9de5542ad7.md

- [x] core: command_ownership.py v2 schema + record_deployed_reference + v1 兼容读取 + 单测
- [x] adapter: deploy_codex_command_skills 渲染时记录 reference 摘要（snapshot 事务内）
- [x] adapter: _cleanup_stale_command_references 证明来源 ∪ command manifest v2
- [x] adapter tests: 修复两个红测试 + AC3/AC5/AC6 覆盖
- [x] core tests: v2 单测 + 全量回归

### [STORY-slim-20260828897396a935ab] Hook coverage expansion: session context, spec/auth/secrets gates
> Spec: docs/specs/STORY-slim-20260828897396a935ab.md

- [x] auth_gate module + TTL token
- [x] secrets_gate credential patterns
- [x] session_gate SessionStart/PreCompact
- [x] spec_guard in tamper_guard
- [x] dispatch wiring + install registration
- [x] config/enforcement/cli extensions
- [x] unit tests AC1-AC6

### [STORY-slim-202608289e83eeb30df4] Protected-branch push gate + L1 hard-rule override protocol
> Spec: docs/specs/STORY-slim-202608289e83eeb30df4.md

- [x] Extend hook_entry with git push matching + branch resolution + block/bypass
- [x] Add enforcement config section to config.py
- [x] Install pre-push hook + tamper guard registration + ensure_gate_channel
- [x] Extend GATES + probe_push_gate + doctor output
- [x] Upgrade prompts/rules.py: L1 entries + Override Protocol
- [x] Write unit tests for AC1-AC8
- [x] Set pactkit self-config allow_direct_push/tamper_guard

### [STORY-slim-20260828d43fae4edbb6] Stack-aware commit-gate test commands (node/go/java)
> Spec: docs/specs/STORY-slim-20260828d43fae4edbb6.md

- [x] utils.stack_test_command marker resolution
- [x] run_pytest stack dispatch + GateUnavailable
- [x] probe_commit_gate stack-aware
- [x] unit tests AC1-AC5

### [STORY-slim-20260830c65491123af1] Gate telemetry truthfulness + audit-record redaction
> Spec: docs/specs/STORY-slim-20260830c65491123af1.md

- [x] redact_command helper + persisted reason redaction
- [x] EVENT_TYPES extension + gate event emission
- [x] Skill matcher telemetry branch
- [x] run_stats gate/command counters
- [x] clean-time legacy record scrub
- [x] unit tests AC1-AC5

### [STORY-slim-202609025bc9246b6a54] commit-gate 计数解析鲁棒性:中和 repo addopts 干扰 + 真实失败文案
> Spec: docs/specs/STORY-slim-202609025bc9246b6a54.md

- [x] R1 计数可得性——gate 的 pytest 调用不受 repo addopts 干扰(2026-09-02 harness-backend 事故:addopts=-q 与 gate -q 叠加成 -qq,pytest 9 在 -qq 下不打印 summary 行→解析永远全 0);候选 -o addopts= 清空 / --junitxml 机器可读计数,需权衡 addopts 中必要运行参数(如 --asyncio-mode=auto)不可被清空
- [x] R2 文案真实化——rc≠0 且计数全 0 时按 exit code 报因:5=没跑、4=usage/collection、其余=跑了但 summary 不可解析(附 addopts 干扰提示),不再一律报 no tests collected
- [x] R3 回归测试——fixture repo 带 pyproject addopts=-q 复现事故场景,断言修复后计数解析正确、文案与事实一致
- [x] R4 全量套件绿 + CHANGELOG/README 更新

### [STORY-slim-2026090301691dea72e8] 规则遵循率实证修复:Capability lint 门+域材料声明+验证语义补强
> Spec: docs/specs/STORY-slim-2026090301691dea72e8.md

- [x] spec-lint W012 Capability Assessment 门
- [x] Plan 阶段域材料声明步骤
- [x] Check 契约 setup 对齐+环境同源语义
- [x] Defect-class sweep 步骤
- [x] Adapter parity 验证
