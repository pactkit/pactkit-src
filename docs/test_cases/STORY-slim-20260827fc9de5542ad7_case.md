# Test Cases: STORY-slim-20260827fc9de5542ad7 — Codex command references 所有权契约修复

## TC-1: v2 schema 写入与读取回路 (R1)

**Given** 一个已部署的 skill 与 reference 文件
**When** `record_deployed_reference` 记录摘要后调用 `write_command_manifest`（含 references 参数）
**Then** manifest 为 `version: 2`，`commands` 与 `references` 两表均可由 `read_command_references` 读回
**And** 同输入重复写入输出字节一致（确定性）

## TC-2: v1 manifest 兼容读取 (R1, AC4)

**Given** 磁盘上存在 `version: 1` 的 command manifest（无 references 段）
**When** 读取
**Then** `read_command_references` 返回空表（降级不抛错），commands 表仍可用于禁用命令退役

## TC-3: 损坏 manifest 降级 (R4, AC6)

**Given** `.pactkit-command-manifest.json` 为非法 JSON / 非对象 / 非 dict references / 非法摘要值
**When** 读取
**Then** 一律降级为空证明表，不抛异常；非法摘要行被逐条过滤

## TC-4: 陈旧 reference 清理恢复 (R2, AC1)

**Given** 以 `commands=["project-act"]` 部署后再以 `commands=["project-plan"]` 部署
**When** 第二次部署的 `_cleanup_stale_command_references` 运行
**Then** `skills/project-act/references/guides/caching.md` 凭 command manifest v2 摘要证明被删除

## TC-5: 禁用命令整目录退役 (R3, AC2)

**Given** 以 `commands=["project-act", "project-plan"]` 部署后再以 `commands=["project-plan"]` 部署
**When** 清理完成
**Then** `skills/project-act/` 整目录不存在（references 先清 → `cleanup_disabled_command_skills` 的整删条件重新成立）

## TC-6: 用户修改的 reference 保留 (R2, AC3)

**Given** 部署后手工修改某个 reference 内容
**When** 以禁用该命令的配置再次部署
**Then** 该文件原样保留（`.pactkit-new` 分支不记录摘要，哈希不匹配即无所有权）

## TC-7: 渲染失败不污染 manifest (R4, AC5)

**Given** 部署中某 reference 的 integrity 检查抛错
**When** 部署失败回滚
**Then** command manifest 保持部署前字节不变（manifest 写入位于 try 块末尾）

## TC-8: sprint phase capsules 重部署守卫

**Given** 以 `commands=["project-sprint"]` 部署两次
**When** 第二次部署完成
**Then** 四个 phase capsules 的摘要都在 manifest references 表中（desired-set 含 phases，防止可用证明误删活跃文件）

## TC-9: 既有回归

**Given** 本 Story 的 core 变更
**When** 运行 `pytest tests/unit/ tests/e2e/ tests/integration/ -q`
**Then** 全量通过（4673 passed）；`tests/unit/test_selective_deploy.py` 的版本断言更新为 v2（过时契约分类）
