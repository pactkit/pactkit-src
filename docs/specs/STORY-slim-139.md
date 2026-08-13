# STORY-slim-139: Skill manifest single source + adapter parity check

| Field | Value |
|-------|-------|
| ID | STORY-slim-139 |
| Status | Done |
| Priority | P1 |
| Release | 2.17.0 |

## Background

实锤的"更新丢失"：codex adapter（独立仓库 `~/workspaces/pactkit-codex`，v0.2.3）的 `deploy_codex_skills` 里硬编码了 10 个 skill 的清单，而 core 已新增 `pactkit-garden`（slim-070）、`pactkit-audit`（slim-091）、`pactkit-report`（slim-094）——codex 用户静默丢失这 3 个 skill，部署摘要显示 "10 Skills" 无任何告警。

根因不在 adapter 一家：core 自己的 `_deploy_skills` 同样用硬编码清单（13 项，当前碰巧是新的）。adapter 只是复制了 core 的模式后停在旧快照。同一操作（skill 部署清单）存在 2 份独立实现，违反 Open-Closed 与 Single Source of Truth。Commands 无此问题（`COMMANDS_CONTENT` dict 天然是注册表）。

另一缺口：各格式的部署数量漂移（部署物漂移）目前无任何机制盯着——需要一个 parity 检查把"静默丢失"变成"显式告警"。

## Requirements

### R1: SKILL_MANIFEST 单一注册表 (MUST)

在 core 定义唯一声明式 skill 清单（每项：`name`、`skill_md` 引用、可选 `script_name`/`script_source`）。`_deploy_skills` MUST 改为迭代该清单——新增 skill 只需一处注册。提供公开 API `get_skill_manifest()` 供 adapter 消费（稳定契约：返回 list[dict]，含 name/script 字段）。core 的 `_deploy_skills` 与 adapter MUST 共用同一份数据。

### R2: 部署清单落盘 (MUST)

每次 `deploy()` 在目标目录写 `.pactkit-deployed.json`：`format`、pactkit 版本、实际部署的 skills/commands/agents 名称列表。所有内置格式（classic/codex/copilot/opencode/plugin）与 adapter 格式 MUST 都写。

### R3: doctor parity 检查 (MUST)

`pactkit doctor` 新增部署漂移检测：读取本机各格式的 `.pactkit-deployed.json`，对照 core 注册表 + 格式能力矩阵（FormatProfile 的排除项，如 `project-sprint` 为 claude-only）计算**期望集合**，实际集合缺项即报告 `Deployed drift: {format} missing {component}` 并给出修复指引（升级 adapter / 重新 deploy）。能力矩阵内的合法差异 MUST NOT 误报。

### R4: codex + copilot adapter 消费契约（跨仓步骤）(MUST)

在 `~/workspaces/pactkit-codex` 与 copilot adapter（Act 阶段确认仓库位置）：删除各自的硬编码 skill 清单（两处均为 10 项旧快照），改为消费 `get_skill_manifest()`；adapter 版本 bump 并在本仓 Spec 记录。adapter 侧改动以其自身测试套件验证。

### R5: 能力矩阵语义不变 (MUST NOT)

不得借"对齐"之名把 claude-only 组件（如 project-sprint）强推到不支持工作流编排的格式。parity 判定 MUST 按格式期望集合，不是格式间全等。

## Acceptance Criteria

### AC1: 清单单一事实源 (R1)

- **Given** 重构后的 core
- **When** 检查 `_deploy_skills` 实现
- **Then** 其迭代 `SKILL_MANIFEST`；代码中不存在第二份逐 skill 硬编码清单

### AC2: 部署清单可机器读 (R2)

- **Given** 任意格式执行 deploy
- **When** 读取目标目录 `.pactkit-deployed.json`
- **Then** 含 format/version/三组件列表，且与实际落盘文件一致

### AC3: 漂移被显式报告 (R3)

- **Given** 人为构造 codex 部署清单缺少 `pactkit-garden`
- **When** 执行 `pactkit doctor`
- **Then** 输出 `Deployed drift: codex missing pactkit-garden` 并退出码为 1

### AC4: 合法差异不误报 (R3, R5)

- **Given** codex 部署缺 `project-sprint`（能力矩阵内）
- **When** 执行 `pactkit doctor`
- **Then** 不产生 sprint 相关 drift 报告

### AC5: adapter 消费后补齐 (R4)

- **Given** 改造后的 pactkit-codex
- **When** 对 codex 格式执行 deploy
- **Then** 部署 13 个 skill（与 core 清单一致），含 garden/audit/report

### AC6: 测试套件全通过 (R1-R5)

- **Given** 全部修改完成
- **When** 本仓与 adapter 仓各自运行测试
- **Then** 全部通过，无新失败

## Target Call Chain

```
core: prompts/skills.py SKILL_*_MD 常量
  → SKILL_MANIFEST（新，单一注册表）
    → deployer._deploy_skills() 迭代部署（classic/copilot/opencode/plugin 复用）
    → get_skill_manifest() 公开 API
      → pactkit-codex deploy_codex_skills() 消费（跨仓，删硬编码清单）
每次 deploy → 目标目录 .pactkit-deployed.json（R2）
pactkit doctor → 读各格式清单 × 注册表×能力矩阵 → drift 报告（R3）
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/skills.py` 或新模块 | SKILL_MANIFEST 注册表 + get_skill_manifest() | None | Medium |
| 2 | `src/pactkit/generators/deployer.py` | _deploy_skills 改迭代清单；deploy 末尾写 .pactkit-deployed.json | Step 1 | Medium（deployer 行数守卫<1660，需紧凑或外置） |
| 3 | `src/pactkit/doctor.py` + `cli.py` | parity 检查（期望集合 = registry − profile 排除项） | Step 2 | Medium |
| 4 | `~/workspaces/pactkit-codex/src/pactkit_codex/deployer.py` | 删硬编码清单，消费 get_skill_manifest()；版本 bump | Step 1 | Medium（跨仓，注意该仓工作区已有未提交改动） |
| 5 | `tests/unit/` | 清单单一源/部署清单/parity 检查单测 | Step 1-3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 部署清单文件读写须处理损坏 JSON（降级为 WARN 不崩溃） |
| SEC-2 | Yes | 读取 adapter/用户目录的 .pactkit-deployed.json 是不可信输入，解析须容错 |
| SEC-3 | N/A | 无数据库相关 |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无认证/会话逻辑 |
| SEC-6 | N/A | 无 API/路由变更 |
| SEC-7 | Yes | 清单缺失/格式不符时 doctor 降级为 WARN，不影响其他检查项 |
| SEC-8 | N/A | core 无新依赖；adapter  bump 其自身版本 |

## Out of Scope

- opencode adapter（pactkit-opencode 独立包）的同款检查——opencode 格式当前在 core 内部署无漂移，但 R2/R3 的机制天然覆盖它
- 能力矩阵本身的重新设计（只消费现有 FormatProfile 排除项）
- marketplace 格式的 parity（部署形态不同，暂不纳入）
- adapter 仓库的 CI/发布流程调整（跟随既有 release 流程）
