# Test Cases: STORY-slim-202608268fc379dbe6ef — PDCA 规则语义深化与风险驱动执行

| Field | Value |
|---|---|
| Spec | STORY-slim-202608268fc379dbe6ef |

## TC-01: Runtime 按条款区分规则等级（AC1）

- **Given** Runtime Kernel 同时包含安全边界和执行偏好
- **When** Rule Registry validator 枚举原子条款
- **Then** 仅安全、授权和不可逆风险条款为 hard；其他条款拥有准确 level、trigger、evidence、failure 和 override

## TC-02: Phase Contract 独立且紧凑（AC2）

- **Given** Init、Plan、Clarify、Act、Check、Done、Hotfix、PR、Release、Design、Debug、Sprint 十二个 command policies/contracts
- **When** 执行 schema、预算和禁止内容检查
- **Then** 每个 contract 字段完整、可判定完成，且不含 CLI 步骤、固定工具、模型名或其他 phase 专属操作

## TC-03: 权威语义只有一个来源（AC3）

- **Given** registry、contracts、shared modules、playbooks 和 legacy compatibility projections
- **When** 执行重复与 provenance 检查
- **Then** completion、blocking、priority、external effects 仅由 registry/contracts 定义，playbook 和兼容层不能独立漂移

## TC-04: Sprint 按当前阶段加载 capsule（AC4）

- **Given** 一个包含 Plan、Act、Check、Done 的 Sprint
- **When** 依次进入各阶段并模拟 Check 失败后返回 Act
- **Then** 初始只含 orchestrator；每次只有一个 active phase；修复在当前 session 继续且不创建 runner、WorkUnit 或 session 切换要求

## TC-05: Codex 不依赖 Markdown @ import（AC5）

- **Given** 隔离生成的 Codex deployment
- **When** 检查 AGENTS、Sprint Skill、phase references 和 guide references
- **Then** 没有 `@~/.codex/...`，Runtime 未膨胀，phase capsule 由 Skill progressive disclosure 或紧凑 fallback 提供

## TC-06: Change Risk Profile 基于证据路由（AC6）

- **Given** database migration、UI、dependency upgrade、纯文档和关键词误命中 fixtures
- **When** Plan 生成且 Act/Check 复核风险画像
- **Then** 风险含 level、reason、evidence，只选 0–3 个相关 guides，纯关键词和纯文档不会触发无关规则

## TC-07: Guide 使用原生七段 schema（AC7）

- **Given** 现有十九个 guides 和三个新增 guides
- **When** 比较源定义与最终部署内容
- **Then** 二者均含 Trigger、Questions、Safe Invariants、Defaults、Alternatives、Evidence、Non-applicable，且不存在运行时 MUST/NEVER 降级替换

## TC-08: Scope Integrity 发现并分类范围扩张（AC8）

- **Given** 实际 diff 含 Dependency Surface 外模块、新依赖、公共接口和派生文件改动
- **When** Act completion verifier 比较预期与实际范围
- **Then** 每项差异被分类并追溯源文件；未解释的重大扩张只令 completion incomplete，不阻断安全修复

## TC-09: Test Adequacy 与 Evidence Freshness（AC9）

- **Given** 弱断言、删除实现仍通过、Mock 绕过核心边界及输入 hash 已变化的测试证据
- **When** Act、Check、Done 评估验证结果
- **Then** 弱或过期证据不能证明完成；输入未变化的有效证据可复用，仅受影响验证需要重跑

## TC-10: 兼容迁移和中途失败可恢复（AC10）

- **Given** 2.23.x legacy config、rules、guides、用户修改文件和旧调用方数据
- **When** 连续升级两次并注入中途写入失败
- **Then** 升级幂等、旧入口按声明兼容、用户文件不变，失败后最后完整 manifest 和部署仍可用

## TC-11: 新增工程实践严格按场景加载（AC11）

- **Given** service、dependency、UI 和纯文档四类变更
- **When** risk router 选择 concern guides
- **Then** operational-readiness、dependency-supply-chain、ui-state-accessibility 只在对应场景加载，未加载 guide 不形成完成门

## TC-12: Rule resolution 诊断只读可解释（AC12）

- **Given** phase、项目规则、用户规则、旧 Spec 和 advisory 冲突
- **When** 执行 doctor/rule-resolution audit
- **Then** 输出 active phase、loaded/skipped reason、evidence 和 precedence decision，所有输入文件 byte-for-byte 不变

## TC-13: 三主宿主语义一致，Copilot 保持兼容（AC13）

- **Given** 同一 Core registry、三个一等宿主 target 和一个 Copilot 兼容 target
- **When** 完整验证 Classic、Codex、OpenCode，并对 Copilot 运行 compatibility smoke
- **Then** 三主宿主的 phase、level、failure、evidence、ownership 语义一致；Copilot 保持安全兼容但不决定主宿主架构；所有产物均无全 phase 泄漏、退休编排术语、强制新 session 或 maintainer 泄漏
