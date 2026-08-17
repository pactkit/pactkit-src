# STORY-slim-141: Deployment manifest content hash verification

| Field | Value |
|-------|-------|
| ID | STORY-slim-141 |
| Status | Done |
| Priority | P1 |
| Release | 2.18.0 |

## Background

2026-08-17 实测发现：`~/.config/opencode/` 的 `.pactkit-deployed.json` 声明 `pactkit_version: 2.17.0` 且组件清单与 registry 完全一致，但 3 个已部署文件（`rules/pactkit.md`、`skills/_rules/04-architecture-principles.md`、`skills/_rules/07-engineering-concerns.md`）内容停留在旧版 —— 占位符未渲染、已排除的 project-sprint 段落仍然存在。

根因：STORY-slim-139 的 parity check（`doctor.py:check_deploy_parity`）只比对**组件清单**（skills/commands/agents 名字列表），不校验**文件内容**。`pactkit_version` 字段记录的是部署时刻的 CLI 版本，不代表落盘内容。这造成「版本戳新、内容旧」的静默漂移。

本 Story 将 manifest 升级为携带逐文件 sha256，doctor 的 parity check 下沉到文件内容级。

## Requirements

### R1: Manifest 携带逐文件内容 hash (MUST)

`write_deploy_manifest()` 在写完组件清单后，扫描 deploy_root 内所有 **pactkit 拥有的已部署文件**，计算 sha256，写入 manifest 的 `"files"` 字段：`{"<relative/path>": "<sha256 hex>"}`。

- 覆盖范围 = manifest 声明组件对应的落盘文件：`skills/{name}/**`（含 commands-as-skills）、`agents/{name}.md`、managed rules（`rules/` 及 `skills/_rules/` 下由 VALID_RULES 部署的文件）
- **MUST NOT** 哈希用户可改/合并语义的文件：`CLAUDE.md`、`AGENTS.md`、`opencode.json`、`config.toml`、`.pactkit-version`、`.pactkit-deployed.json` 自身
- 签名保持向后兼容（adapter 包 pactkit-opencode / pactkit-codex 直接调用此函数，签名变更会导致 adapter 破坏）

### R2: doctor parity check 下沉到文件内容级 (MUST)

`check_deploy_parity()` 在组件清单比对通过后，若 manifest 含 `"files"` 字段，逐文件重新计算 sha256 并比对：

- hash 不匹配 → drift detail：`Content drift: {format} {path} — redeploy via pactkit update`
- manifest 中声明但磁盘缺失的文件 → drift detail
- 磁盘比对 MUST 在报告前完成全部文件扫描（不因首个 mismatch 短路，一次报告所有漂移文件）

### R3: 向后兼容旧 manifest (MUST)

manifest 缺少 `"files"` 字段（pre-2.18 部署）→ 降级为 warning（`re-run pactkit update to enable content verification`），**不计入 drift**、不影响 doctor 退出码语义（与现有 missing-manifest 行为一致）。

### R4: 用户追加内容不产生误报 (MUST)

用户在 `CLAUDE.md` 等合并语义文件中的追加内容 MUST NOT 触发 content drift（由 R1 的排除清单保证）。用户修改 pactkit 拥有的文件（如 `rules/pactkit.md`）SHOULD 被报告为 drift —— 这是特性而非误报（提示用户改动将在下次 update 被覆盖）。

### R5: 确定性 (MUST)

hash 计算 MUST 为纯代码实现（sha256，hex digest），禁止 LLM 判断参与比对（Code Enforces, Prompt Instructs）。文件读取使用 bytes 模式避免编码差异。

## Acceptance Criteria

### AC1: 部署后 manifest 包含逐文件 hash (R1, R5)

- **Given** 一个干净的 deploy target 目录
- **When** 执行 `pactkit init -t <dir> --format classic --no-git --no-external --non-interactive`
- **Then** `<dir>/.pactkit-deployed.json` 含 `"files"` 字段，覆盖所有 pactkit 拥有的落盘文件（skills/commands/agents/managed rules），每个值为 64 位 hex sha256，且不含 `CLAUDE.md`、`.pactkit-version`、`.pactkit-deployed.json`

### AC2: 内容漂移被 doctor 检出 (R2)

- **Given** 已完成部署且 manifest 含 `"files"`
- **When** 手工篡改一个 pactkit 拥有的已部署文件（如 `rules/pactkit.md` 追加一行）后运行 `pactkit doctor`
- **Then** 输出包含该文件路径的 `Content drift` detail，doctor 退出码为 1（NEEDS ATTENTION）

### AC3: 未漂移时 doctor 不误报 (R2, R4)

- **Given** 部署后未改动任何 pactkit 文件，仅在 `CLAUDE.md` 末尾追加用户内容
- **When** 运行 `pactkit doctor`
- **Then** 无 `Content drift` 输出（parity 部分不产生 issue）

### AC4: 旧版 manifest 降级为 warning (R3)

- **Given** 一个不含 `"files"` 字段的 `.pactkit-deployed.json`（模拟 pre-2.18 部署）
- **When** 运行 `pactkit doctor`
- **Then** 输出 warning 提示重新部署以启用内容校验，且不计入 drift、不影响退出码

### AC5: 声明文件在磁盘缺失被检出 (R2)

- **Given** 部署完成后删除一个 manifest 声明的文件（如 `skills/pactkit-board/SKILL.md`）
- **When** 运行 `pactkit doctor`
- **Then** 输出该文件缺失的 drift detail，退出码为 1

### AC6: adapter 签名兼容 (R1)

- **Given** 现有 `write_deploy_manifest(deploy_root, format_name, config)` 调用方（core deployer + 外部 adapter 包）
- **When** 本 Story 完成后
- **Then** 函数签名不变，adapter 无需修改即可获得 hash 能力（纯内部行为增强）

## Target Call Chain

```
pactkit init/update
  └─ cli.py → generators/deployer.py:_deploy_classic() (及各 format deployer)
       └─ deploy_manifest.py:write_deploy_manifest(deploy_root, format, config)   ← R1 修改点
            └─ NEW: _hash_deployed_files(deploy_root, components) → {"files": {...}}

pactkit doctor
  └─ cli.py:767 → doctor.py:check_deploy_parity(project_root)                     ← R2 修改点
       ├─ 现有: expected_components() 清单比对
       └─ NEW: manifest["files"] 逐文件 sha256 比对                               ← R3 兼容分支
```

Adapter 调用链（外部 repo，签名兼容由 R1 保证）：`pactkit-opencode/pactkit-codex → write_deploy_manifest()`

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim141_manifest_hash.py` | 新建：AC1-AC6 的 TDD 测试（RED） | None | Low |
| 2 | `src/pactkit/deploy_manifest.py` | 新增 `_hash_deployed_files()` + 排除清单常量；`write_deploy_manifest` 写入 `files` 字段 | Step 1 | Low |
| 3 | `src/pactkit/doctor.py` | `check_deploy_parity` 增加 files 比对分支 + 旧 manifest warning 分支 | Step 2 | Medium — 勿破坏现有清单比对与 SEC-2/SEC-7 降级行为 |
| 4 | `tests/unit/test_story_slim139_skill_manifest.py` | 回归：现有 parity 测试不受影响 | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 修改 source code（deploy_manifest.py, doctor.py） |
| SEC-2 | No | 无用户输入处理（hash 对象为部署器自身产物） |
| SEC-3 | No | 无数据库 |
| SEC-4 | No | 无前端 |
| SEC-5 | No | 无认证逻辑 |
| SEC-6 | No | 无 API/路由 |
| SEC-7 | Yes | manifest JSON 损坏/文件不可读时必须降级为 warning（沿用现有 SEC-7 try/except 模式），禁止 crash doctor |
| SEC-8 | No | 无依赖变更（hashlib 为标准库） |

## Out of Scope

- adapter 包（pactkit-opencode / pactkit-codex / pactkit-copilot）的发布与重部署 —— 它们自动继承 core 的新 manifest 行为
- 对历史已部署目录的批量修复（由用户在下次 `pactkit update` 时自然获得）
- `CLAUDE.md` / `AGENTS.md` 等合并语义文件的内容校验（结构上无法区分 pactkit 段与用户追加段）
- 部署性能优化（hash 扫描为 O(文件数)，pactkit 文件约 100 个，无需优化）
