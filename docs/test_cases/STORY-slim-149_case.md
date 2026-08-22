# Test Cases: STORY-slim-149 — Codegraph-first 静态分析 Provider Router

| Field | Value |
|---|---|
| Spec | STORY-slim-149 |

## TC-1: 配置 Codegraph 时优先使用它（AC1）

- **Given** graph_provider 为 codegraph 且 binary 与索引健康
- **When** Plan、Act 或 Trace 发起图查询
- **Then** router 选择 codegraph 并记录 provider evidence，builtin graph 与 text search 不被调用

## TC-2: 健康索引空结果有效（AC2）

- **Given** Codegraph 健康且查询目标不存在
- **When** 查询返回零条结果
- **Then** 状态为 valid_empty，不触发 fallback

## TC-3: Codegraph 故障默认 fail closed（AC3）

- **Given** 配置了 Codegraph，但 binary、DB、status、sync 或 query 失败
- **When** 未显式允许 fallback
- **Then** 命令非零退出并返回稳定 reason code，不调用其他 provider

## TC-4: 显式 fallback 记录完整证据（AC4）

- **Given** Codegraph 失败且调用方显式允许 fallback
- **When** builtin graph 或 text search 成功
- **Then** 结果包含原 provider、最终 provider、失败原因、fallback chain 和统一查询结果

## TC-5: 旧 query CLI 与受限只读 DB 兼容（AC5）

- **Given** 旧 callers、callees 或 chain CLI 调用及项目 .codegraph 内的兼容数据库
- **When** 执行查询
- **Then** 符号语义和退出码兼容，SQLite 查询只读且参数化；项目外 DB override 被拒绝

## TC-6: 过期索引只同步一次（AC6）

- **Given** Codegraph status 报告索引过期
- **When** 发起查询
- **Then** router 在锁和超时边界内最多 sync 一次并重新检查 freshness，仍过期则 fail closed

## TC-7: 旧引擎警告可见且不破坏性重建（AC7）

- **Given** 索引由旧版引擎构建但仍可健康查询
- **When** 执行查询
- **Then** evidence 包含 index_old_engine，且不自动执行 full index

## TC-8: Plan 与 Act 验证 provider evidence（AC8）

- **Given** 项目要求 Codegraph
- **When** checkpoint 缺少 provider evidence 或提交未经授权的 fallback evidence
- **Then** checkpoint 被拒绝；Codegraph 成功或显式授权 fallback 后才可推进

## TC-9: 四个平台查询语义一致（AC9）

- **Given** canonical Plan、Act 与 Trace 模板
- **When** 隔离部署到 Classic、OpenCode、Codex 和 Copilot
- **Then** provider routing、freshness、fallback、参数与 evidence 语义全部保留，目标目录外无写入

## TC-10: 未配置 Codegraph 时兼容 builtin provider（AC10）

- **Given** 项目未配置 graph provider 且没有 .codegraph
- **When** 执行统一图查询
- **Then** router 选择 builtin_graph 并解释默认决策，不要求安装 Codegraph
