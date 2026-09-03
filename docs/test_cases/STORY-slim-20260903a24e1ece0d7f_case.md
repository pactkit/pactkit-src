# Test Cases: STORY-slim-20260903a24e1ece0d7f — Codex 嵌入副本所有权修复

> 实现位置:`tests/unit/test_accept_candidates.py`(core 4 用例)与 pactkit-codex 仓 ownership 测试(12 存量用例)。

## TC-1: 部署检查合并账本 (R1, AC1)

**Given** pactkit-codex deployer 的 deploy_codex_command_skills
**When** reference 覆盖检查取 expected_hash
**Then** 来自 {**previous_hashes, **read_command_references(skills)} 合并视图(与 _cleanup_stale_command_references 同型)——E2E 实证:真实 update 两次 codex references 零新候选
**Impl** pactkit-codex deployer.py ownership_proofs(:705-711, :876) + 该仓 12 个 ownership 存量测试

## TC-2: accept-candidates 双账本 (R2, AC2)

**Given** 临时 root 含 2 候选(references 路径 + 普通 skills 路径)及两本账
**When** accept_candidates(root)
**Then** 原文件被覆盖;references 摘要进 command manifest;普通路径摘要进 .pactkit-deployed.json;候选消失;计数=2
**Impl** `TestAcceptCandidates::test_accepts_and_updates_both_ledgers`

## TC-3: 幂等与账本保全 (R2, R3, AC3)

**Given** 无候选 root / 有既有账本条目
**When** 运行
**Then** 返回 0;既有 commands/references/files 条目不被抹除
**Impl** `test_idempotent_when_no_candidates` / `test_preserves_existing_ledger_entries`

## TC-4: CLI 注册与 prompt 引用 (R2, R3)

**Given** CLI 表面与 done playbook
**When** accept-candidates --help / 检查 doctor 步骤
**Then** 子命令存在(done playbook doctor 步骤指引 conflict 时使用——死子命令检测锚)
**Impl** `test_cli_registers_accept_candidates` + 存量 dead-subcommand 检测
