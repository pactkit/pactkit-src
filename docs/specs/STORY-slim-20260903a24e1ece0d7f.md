# STORY-slim-20260903a24e1ece0d7f: Codex 嵌入副本所有权:部署检查合并 references 账本+accept-candidates 命令

| Field | Value |
|-------|-------|
| ID | STORY-slim-20260903a24e1ece0d7f |
| Status | Done |
| Priority | P1 |
| Release | 2.26.0 |

## Background

PM-20260903-codex-stale-embedded-copies.md 的根因 story（同日三次复发：5/8/20 处）。完整断点链：

1. codex 部署器把 references 摘要写入 command manifest（`.pactkit-command-manifest.json` 的 references 表，pactkit-codex deployer :865/:889）
2. 但部署时的覆盖所有权检查只读 `.pactkit-deployed.json` 的 files 映射（:849 expected_hash = previous_hashes.get(...)），该映射不含 references 路径（2026-09-03 实证：capability-design 路径在 codex manifest files 中为空集）
3. 因此即使上次部署成功记录了摘要，下次内容变更时所有权无从证明 → preserve+候选 → 手动 mv 接受后账本仍不更新（mv 不走部署器）→ 内容再变再候选。清理路径（:310）已正确合并两本账，部署检查没合并——同函数族内的不对称。

## Technical Design

### Lateral Scan Results

- Operation "references 所有权证明": 清理路径已有正确实现（proofs 合并，pactkit-codex :310）→ 部署检查复用同一合并
- Operation "候选接受": 无既有机制（preserve_or_write 只产候选）→ 新增 accept-candidates 命令
- Operation "manifest 更新": command_ownership.write_command_manifest 已支持 references 参数 → Reuse

### Capability Assessment

| Need | Source | Decision |
|------|--------|----------|
| 部署期所有权合并 | pactkit-codex 清理路径同型 | Reuse（一行合并） |
| 候选接受+账本回写 | command_ownership 读写 API | Reuse |
| CLI 命令 | cli.py 子命令模式 | Reuse |

## Requirements

### R1: 部署检查合并 references 账本 (MUST)

pactkit-codex deployer 的 deploy_codex_command_skills 中，reference 覆盖检查的 expected_hash MUST 来自 `{**previous_hashes, **read_command_references(skills_dir)}` 的合并视图（与 _cleanup_stale_command_references :310 一致）。效果：上次部署记录过摘要的 reference，内容变更时直接原地更新，不再产候选。

### R2: pactkit accept-candidates 命令 (MUST)

core 新增 `pactkit accept-candidates [--root PATH]`：扫描 deploy root（缺省扫描全部已知 root：~/.claude、~/.config/opencode、~/.codex、项目 .github）下的 `*.pactkit-new` 候选，逐个 mv 覆盖原文件，并把新内容摘要回写两本账：路径匹配 `skills/*/references/**` 的进 command manifest references 表，其余进该 root 的 `.pactkit-deployed.json` files 映射。输出接受计数。无候选时退出 0 并报告 0。

### R3: 回归测试 (MUST)

测试 MUST 覆盖：(a) 模拟两次部署——第一次写入 reference + 账本，变更内容后第二次部署不产候选（R1 的行为级验证，可在 core 侧以 preserve 逻辑单测或对 pactkit-codex 仓库跑其测试）；(b) accept-candidates 对带候选的临时 root：mv 生效、两本账更新、候选消失；(c) 候选消失后重复运行幂等。

## Acceptance Criteria

### AC1: 二次部署不产候选 (R1)

- **Given** codex root 下一个已记录摘要的 reference 文件，内容随后变更
- **When** 再次部署
- **Then** 原地更新，无 .pactkit-new 产生

### AC2: accept-candidates 全链路 (R2)

- **Given** 临时 root 含 2 个候选（1 个 references 路径、1 个普通 skills 路径）及对应账本
- **When** `pactkit accept-candidates --root <tmp>`
- **Then** 两个原文件被候选覆盖；command manifest references 表含新摘要；.pactkit-deployed.json files 映射含新摘要；候选文件消失；输出 "Accepted 2 candidate(s)"

### AC3: 幂等 (R2)

- **Given** 无候选的 root
- **When** 再次运行
- **Then** 退出 0，输出 0 计数

## Target Call Chain

- `/Users/slim/workspaces/pactkit-codex/src/pactkit_codex/deployer.py:849` — expected_hash 合并 read_command_references（R1）
- `src/pactkit/cli.py` — accept-candidates 子命令（R2）
- `src/pactkit/generators/command_ownership.py` — 复用 read/write API；新增按路径回写 entries 的辅助（R2）
- `src/pactkit/deploy_manifest.py` — 新增 files 映射单路径更新的辅助（R2）

## Implementation Inputs

| Path | Purpose |
|------|---------|
| `/Users/slim/workspaces/pactkit-codex/src/pactkit_codex/deployer.py:L287-L330` | _cleanup_stale_command_references 的合并视图——R1 的复用源 |
| `src/pactkit/generators/command_ownership.py:L66-L110` | record/read/write 账本 API——R2 的复用源 |
| `docs/architecture/governance/postmortems/PM-20260903-codex-stale-embedded-copies.md` | 三次复发的完整时间线与影响面 |

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_accept_candidates.py` | R2/R3 断言先写（RED） | None | Low |
| 2 | `src/pactkit/deploy_manifest.py` + `command_ownership.py` | 账本单路径回写辅助 | 1 | Low |
| 3 | `src/pactkit/cli.py` | accept-candidates 子命令 | 2 | Low |
| 4 | pactkit-codex `deployer.py:849` | expected_hash 合并（R1） | None | Medium（跨仓） |
| 5 | E2E: 本机 codex root | 真实 update 两次验证无候选 | 3,4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | 无 credential |
| SEC-2 | No | accept-candidates 输入为本地文件系统候选文件 |
| SEC-3 | No | 无数据库 |
| SEC-4 | No | 无前端 |
| SEC-5 | No | 无 auth |
| SEC-6 | No | 无 API |
| SEC-7 | No | 所有权检查是加强非弱化：合并账本仍要求摘要匹配才覆盖 |
| SEC-8 | No | 无依赖变化 |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | codex references 部署直通；accept-candidates 命令 |
| Touches | `src/pactkit/cli.py`, `src/pactkit/deploy_manifest.py`, `src/pactkit/generators/command_ownership.py`, `tests/unit/`（新）；**跨仓**：pactkit-codex `src/pactkit_codex/deployer.py` |
| Conflict risk | MEDIUM（跨仓改动，pactkit-codex 需独立发版跟随 core 2.26.0） |

## Out of Scope

- release 流水线排序（core 先发、adapter 跟随的既有流程，发布时另走）
- opencode 命令候选（.pactkit-new 在 opencode 的 4 个 command 候选是更早漂移，用 accept-candidates 处置即可，不单独修）
- 候选的三方审查 UI（CLI 报告足够）
