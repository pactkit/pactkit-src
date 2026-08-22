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

### [STORY-slim-145] Codex 部署命令语义完整性与 Adapter 兼容门禁
> Spec: docs/specs/STORY-slim-145.md

- [x] 建立 CLI policy 与结构化操作渲染契约
- [x] 移除 pactkit-codex 有损命令前缀替换
- [x] 增加 prompt 完整性与 Classic/Codex parity 门禁
- [x] 阻止不兼容 Core/adapter 组合静默部署
- [ ] 完成隔离迁移、双仓回归与同版本发布验证

## ✅ Done

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
