# Test Cases: STORY-slim-147 — 全 Skill 执行可靠性协议与 Plan 可恢复工作流

| Field | Value |
|---|---|
| Spec | STORY-slim-147 |

## TC-1: 全部部署入口具有唯一可靠性定义（AC1）

- **Given** canonical command 与 skill manifest
- **When** 校验执行可靠性注册表
- **Then** 25 个入口全部且仅出现一次，缺失、重复或未知入口会使校验失败

## TC-2: 通用引擎通过注册表分派 workflow（AC2）

- **Given** Act 与 Plan 的 workflow definition
- **When** 通用 continuation engine 启动并推进 workflow
- **Then** 命令、步骤和 validator 来自注册表，通用引擎不写死 Act 步骤

## TC-3: Plan 在 Story ID 生成前可恢复（AC3）

- **Given** Plan 已完成 preflight、intent_clarified 与 archaeology，但尚无 Story ID
- **When** 通过 opaque run ID 执行 resume
- **Then** 返回 story_identified 作为下一步，resume 不修改 checkpoint

## TC-4: Plan 在 Spec 创建后从准确边界恢复（AC4）

- **Given** Plan run 已绑定唯一 Story 且 Spec scaffold evidence 有效
- **When** workflow 被中断后恢复
- **Then** 从首个未完成步骤继续，不重复创建 Spec 或 Story record

## TC-5: 漂移和重复写入风险阻断 Plan（AC5）

- **Given** checkpoint 后 Spec、Story fact、Git HEAD 或工作树发生未确认变化
- **When** 请求 resume 或重复绑定
- **Then** workflow fail closed，并报告稳定的漂移或冲突原因

## TC-6: Plan completion 由真实证据门禁（AC6）

- **Given** Plan 到达最终 checkpoint
- **When** Spec、Requirement、AC、Security Scope、spec-lint 或 Story tasks 任一证据缺失
- **Then** completed 写入被拒绝；全部真实证据有效时才允许 completed

## TC-7: 旧 Act checkpoint 无损兼容（AC7）

- **Given** 2.20.0 格式的 Act checkpoint 和 legacy continuation CLI
- **When** 新引擎读取、验证、恢复或开启 fresh cycle
- **Then** 原步骤、锁、stale、completed 不可变及归档语义保持不变，迁移失败不覆盖原文件

## TC-8: 四种部署目标保持 Plan/Act 语义（AC8）

- **Given** canonical Plan 与 Act 模板
- **When** 隔离部署到 Classic、OpenCode、Codex 和 Copilot
- **Then** continuation、checkpoint、resume、证据门禁及参数均保留，目标目录外无写入

## TC-9: 未接入入口诚实声明能力（AC9）

- **Given** 尚未接入持久化 workflow 的 command 或 skill
- **When** 查询可靠性注册表
- **Then** 返回明确恢复策略、完成契约和人工确认边界，不伪装为已支持自动续跑
