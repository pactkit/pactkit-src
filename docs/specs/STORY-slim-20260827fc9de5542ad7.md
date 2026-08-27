# STORY-slim-20260827fc9de5542ad7: Codex command references 所有权契约修复：command manifest v2 记录 reference 摘要

| Field | Value |
|-------|-------|
| ID | STORY-slim-20260827fc9de5542ad7 |
| Status | Done |
| Priority | P1 |
| Release | 2.24.0 |

## Background

**问题**：2.23.0 `pactkit-codex` 因两个测试红而延后发布（见项目记忆 project_230_release_followups）。`pip install pactkit[codex]` 至今解析不到 2.23.0。

**根因（已查证）**：core commit `5311c56` 把 `pactkit_owned_files`（`src/pactkit/deploy_manifest.py:245`）从 rglob 全量枚举收窄为"只记 SKILL.md + 注册脚本"——这是正确防过度声明的修复（枚举整个目录会把用户放进 skill 目录的文件也声明为 PactKit 所有，授权后续覆盖）。副作用：`skills/*/references/**`（pactkit 自己部署的 command-local rule/guide 引用文件）不再进入 `.pactkit-deployed.json` 的 `files` 表。

消费方 `CodexDeployer._cleanup_stale_command_references`（pactkit-codex `deployer.py:285`）用该表做删除前的所有权证明（sha256 相等才删）→ 证明拿不到 → 保守保留 → 陈旧文件清不掉：

- `test_codex_selective_redeploy_removes_owned_stale_references`：禁用 project-act 后 `skills/project-act/references/guides/caching.md` 残留
- `test_codex_command_selection_removes_only_owned_disabled_command`：references 残留导致 `cleanup_disabled_command_skills` 的整目录删除条件（`files == [SKILL.md]`，core `command_ownership.py:57`）不成立 → `skills/project-act/` 整目录残留

**设计决策（本 Spec 拍板，替代记忆中的两个候选方向）**：

- ~~方向 B：渲染内容比对作为所有权证明~~（core 对 guides 的既有做法）——**否决**。codex reference 渲染管线（`deployer.py:583-587`：brand 剥离 + 路径替换 + `_filter_codex_command_reference_sections(content, enabled_commands)`）依赖**部署时**的 enabled_commands/rules 配置。陈旧文件正是"用旧配置渲染的"，用当前配置重放内容必然不等——恰是两个测试覆盖的场景。该方向对配置无关的静态文件可行，但对 command references 结构性不可行。
- **方向 A（采纳）：部署时自记哈希**。参照 `record_deployed_command` 的既有先例（部署器记录自己刚写入内容的摘要），把 command references 的 sha256 记入 `.pactkit-command-manifest.json`（v2 schema 增设 `references` 段），cleanup 时以该表为所有权证明。部署时记录的哈希与文件内容天然匹配，且对后续版本变化鲁棒（记录的是写入时刻的摘要，非重放）。

**为什么记入 command manifest 而非 deployed manifest**：`.pactkit-deployed.json` 的 `files` 表由 core 的 `pactkit_owned_files` 生成，core 不渲染 references（adapter 私有管线），强行加入需要 core 复刻 adapter 的渲染管线。`.pactkit-command-manifest.json` 的读写函数（`command_ownership.py`）本来就在 core，由 adapter 传入部署器实际写入的摘要——账本单一、无渲染复刻、无第三套所有权机制。

**时序正确性**：`_cleanup_stale_command_references`（deployer.py:173）在 `deploy_codex_command_skills`（:187）之前运行，读到的 command manifest 是**上一次**部署写的——恰好包含当时部署的 references 摘要 → 证明可用。随后本次部署重写 manifest 为当前集合。

## Requirements

### R1: Command manifest v2 schema 记录 reference 摘要 (MUST)

`.pactkit-command-manifest.json` 升级为 v2：`{"version": 2, "commands": {...}, "references": {"<相对路径>": "<sha256>"}}`。

- v2 写入：`record_deployed_reference(entries, relative_path, digest)` 累积；`write_command_manifest` 写出 `references` 段
- v1 兼容读取：`version: 1` 无 `references` 段时按空表处理，不报错（升级路径中旧 manifest 必须可读）
- manifest 原子写（复用 `atomic_write`），排序稳定（确定性输出）

### R2: Adapter 部署时记录、清理时消费 (MUST)

pactkit-codex：

- `deploy_codex_command_skills` 渲染每个 reference 后将其 sha256 记入 manifest entries（与 `record_deployed_command` 同批落盘，在 rollback snapshot 保护范围内）
- `_cleanup_stale_command_references` 的所有权证明来源扩展为：`.pactkit-deployed.json` files 表 ∪ command manifest v2 references 表；两处都拿不到证明 → 保守保留（既有语义不变）
- 用户修改过的 reference（哈希不匹配）MUST 保留——`test_codex_selective_redeploy_preserves_user_modified_stale_reference` 的语义不得回退

### R3: 整目录退役链路恢复 (MUST)

references 清理恢复后，`cleanup_disabled_command_skills` 的整目录删除条件（目录内仅剩 SKILL.md）自然重新成立；R2 生效时禁用命令的 skill 目录 MUST 整体移除（AC2 断言）。

### R4: 回滚与失败安全 (MUST)

- reference 摘要记录与 reference 写入同处一个 snapshot 事务：渲染失败回滚时，manifest 不得留下未实际落盘文件的摘要（`test_failed_command_selection_keeps_old_command_and_manifest` 的既有语义扩展到 references）
- manifest 读取损坏（JSON 解析失败/结构异常）时降级为"无证明"，不抛异常、不清删任何文件

## Acceptance Criteria

### AC1: 陈旧 reference 被清理 (R1, R2)

- **Given** 以 `commands=["project-act"]` 完成一次部署（command manifest v2 含 guides 摘要）
- **When** 以 `commands=["project-plan"]` 再次部署
- **Then** `skills/project-act/references/guides/caching.md` 被删除；`skills/project-plan/SKILL.md` 正常存在

### AC2: 禁用命令整目录退役 (R2, R3)

- **Given** 以 `commands=["project-act", "project-plan"]` 完成一次部署
- **When** 以 `commands=["project-plan"]` 再次部署
- **Then** `skills/project-act/` 目录整体不存在

### AC3: 用户修改过的 reference 被保留 (R2)

- **Given** 一次部署后手工修改 `skills/project-act/references/guides/caching.md` 的内容
- **When** 以不含 project-act 的配置再次部署
- **Then** 该文件原样保留（哈希不匹配 = 非 PactKit 当前所有 = 不删）

### AC4: v1 manifest 兼容 (R1)

- **Given** 磁盘上存在 v1 schema 的 command manifest（无 references 段）
- **When** 执行部署
- **Then** 不抛异常；cleanup 按空证明表处理（保守保留）；部署后 manifest 升级为 v2

### AC5: 渲染失败不污染 manifest (R4)

- **Given** 部署过程中某 command reference 的 integrity 检查抛错
- **When** 部署失败回滚
- **Then** command manifest 不含该次未落盘文件的摘要；再次部署仍可正常完成

### AC6: 损坏 manifest 降级 (R4)

- **Given** `.pactkit-command-manifest.json` 内容为非法 JSON
- **When** 执行部署
- **Then** 部署正常完成，cleanup 不删除任何 reference 文件，manifest 被重写为合法 v2

## Target Call Chain

- **core**：`generators/command_ownership.py` — `record_deployed_command` / `write_command_manifest` / `cleanup_disabled_command_skills`（新增 `record_deployed_reference`，manifest schema v1→v2）
- **adapter（pactkit-codex repo）**：`deployer.py:173` `_cleanup_stale_command_references`（证明来源扩展）→ `deployer.py:187` `deploy_codex_command_skills`（渲染时记录摘要，deployer.py:820-850 reference 写入点）→ `deployer.py:857` `write_command_manifest`（v2 落盘）→ `deployer.py:874` `cleanup_disabled_command_skills`（整目录退役）

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | core `src/pactkit/generators/command_ownership.py` | v2 schema + `record_deployed_reference` + v1 兼容读取 + 单测（AC4/AC6） | None | Low |
| 2 | adapter `src/pactkit_codex/deployer.py` | 渲染时记录 reference 摘要（snapshot 事务内） | Step 1（core 先发） | Medium（触碰部署事务区） |
| 3 | adapter `src/pactkit_codex/deployer.py` | `_cleanup_stale_command_references` 证明来源 ∪ command manifest | Step 2 | Medium |
| 4 | adapter tests | 修复两个红测试 + 新增 AC3/AC5/AC6 覆盖 | Step 2-3 | Low |
| 5 | core tests | command_ownership v2 单测 + 全量回归（core 侧无行为变化面：仅新增函数与 schema 扩展） | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 所有权证明是删除授权的安全边界——哈希证明 MUST 保持不可绕过（name-based unlink 禁止） |
| SEC-2 | Yes | manifest JSON 解析外部输入，损坏输入必须降级不抛错（R4/AC6） |
| SEC-3 | No | 无数据库模式 |
| SEC-4 | No | 无前端文件 |
| SEC-5 | No | 无认证模式 |
| SEC-6 | No | 无 API/route 文件 |
| SEC-7 | Yes | 回滚/失败路径的健壮性即 R4 主题；事务边界错误处理 MUST 显式测试 |
| SEC-8 | No | 无依赖清单变更 |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None（core 与 adapter 变更同船 2.24.0；发布顺序沿用既有 core 先发 → adapter 紧随） |
| Provides | command manifest v2 schema（references 段）；`record_deployed_reference` 公共 API —— STORY-slim-20260827024e71df170f 的 R4（Codex hooks 部署）可将 hooks.json 摘要记入同一账本 |
| Touches | core `src/pactkit/generators/command_ownership.py`；pactkit-codex `src/pactkit_codex/deployer.py`；两侧 tests |
| Conflict risk | MEDIUM（跨 repo 变更；adapter deploy() 事务区历史敏感——config.toml 清空事故、2.21 事故都在此区域） |

## Out of Scope

- 不改 `.pactkit-deployed.json` 的 `files` 表生成逻辑（`pactkit_owned_files` 的收窄是正确行为，保持）
- 不为 2.23.0 补发 pactkit-codex（该版本从未发布，无回退用户；修复随 2.24.0 双包同船）
- OpenCode/Copilot adapter 无 command-local references 机制，不在本 Story 范围
- Codex hooks 部署（STORY-slim-20260827024e71df170f R4）另行实施，仅复用本 Story 提供的 v2 账本
