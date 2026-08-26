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

## 🔄 In Progress

## ✅ Done

### [STORY-slim-202608268fc379dbe6ef] PactKit PDCA 规则语义深化与风险驱动执行模型
> Spec: docs/specs/STORY-slim-202608268fc379dbe6ef.md

- [x] 细化 RuleClause 与 PhaseContract schema
- [x] 实现 Sprint 动态 phase capsule
- [x] 建立 Change Risk Profile 与风险路由
- [x] 原生重写 engineering guides 并补三类实践
- [x] 实现 scope integrity 与 test adequacy evidence
- [x] 完善兼容迁移、doctor 与四 Adapter parity

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
