# STORY-slim-142: deploy format=all with target must skip adapters + adapter skew guard

| Field | Value |
|-------|-------|
| ID | STORY-slim-142 |
| Status | Done |
| Priority | P1 |
| Release | 2.18.0 |

## Background

2026-08-17，STORY-slim-141 的内容级 parity check 在 commit gate 实战中检出真实漂移，二分定位出完整污染链：

1. `tests/unit/test_story_slim056.py` 中 `test_unicode_project_path` 等测试调用 `pactkit init -t <tmp>`（默认 `format=all`）
2. `deploy(format="all")` 遍历 `_DEPLOYER_REGISTRY`，其中 `fmt_target = target if fmt_name == "classic" else None`（`deployer.py:~285`）—— **adapter 格式无视 `-t`，永远部署到真实 home**（`~/.config/opencode`）
3. 本机安装的 `pactkit-opencode` 是 **2.9.1**（repo 源已 2.17.0）：渲染逻辑陈旧（占位符未解析、project-sprint 未排除），且不调用 `write_deploy_manifest`（slim-139 时还未发布）
4. 结果：每次全量测试跑完，真实 opencode 部署被 2.9.1 陈旧内容覆盖且 manifest 不更新 → 下一次 `doctor` 必报 content drift → `test_doctor_runs` 对同文件内执行顺序产生隐式依赖（pass 留给别人，fail 留给自己）

这同时解释了 2026-08-13 发布日后的首次漂移事件（同签名：占位符 + sprint 段落）。

## Requirements

### R1: format=all + 显式 target 时跳过 adapter 部署 (MUST)

`deploy(format="all", target=<非None>)` 时，MUST 跳过所有 adapter 格式（opencode/codex/copilot 等非 classic），并打印一行说明：`Skipping adapter formats (…): -t target only applies to classic`。

理由：adapter deployer 不接受 target（永远写各自默认 home 目录），带 target 的调用语义是"预览/测试"，把内容写进用户真实 home 在任何场景下都是错的。此改动从污染源头根治——**不需要修改任何现有测试**（遵守 Pre-existing Test Protocol），`test_unicode_project_path` 等自动获得隔离。

`target=None` 的真实 init/update 行为 MUST 保持不变（adapter 正常部署到各自 home）。

### R2: 回归测试——target 模式零 home 副作用 (MUST)

新增测试验证：注册一个 spy adapter deployer 后调用 `deploy(format="all", target=tmp_path)`：

- spy adapter 的 `deploy()` MUST NOT 被调用
- classic 内容正确部署到 tmp_path
- 输出含跳过说明

### R3: doctor 报告 adapter 与 core 的版本偏斜 (SHOULD)

`pactkit doctor` 增加 adapter 包版本检查：通过 `importlib.metadata.version("pactkit-opencode")` 等读取已装 adapter 版本，major.minor 落后于 core `pactkit.__version__` 时输出 warning（含升级提示 `pipx inject pactkit pactkit-opencode==X`）。warning 不计入 drift、不影响退出码。

理由：本次事故的 root cause 是 adapter 2.9.1 配 core 2.17.0；manifest 的 `pactkit_version` 字段由 core 生成，无法反映 adapter 自身版本，必须直接读包元数据。

### R4: 向后兼容 (MUST)

- `deploy()` 签名不变；`format="all", target=None` 行为完全不变
- 现有测试（含 slim056 全套）MUST NOT 修改，且修复后全量套件通过

## Acceptance Criteria

### AC1: target 模式跳过 adapter (R1)

- **Given** 已安装 pactkit-opencode adapter（registry 含 opencode）
- **When** 调用 `deploy(format="all", target=tmp_path)`（或 CLI `pactkit init -t <dir>` 默认 format=all）
- **Then** adapter 的 deploy() 不被调用，`~/.config/opencode` 内容零变化，输出含跳过说明，classic 正常部署到 tmp_path

### AC2: 真实 init 行为不变 (R1, R4)

- **Given** 同上环境
- **When** 调用 `deploy(format="all")`（target=None）
- **Then** classic + 所有已注册 adapter 均正常部署到各自默认目录

### AC3: 全量套件自洁 (R1, R2, R4)

- **Given** opencode 部署处于干净状态（doctor 无 content drift）
- **When** 连续运行两次全量 `pytest tests/unit/`
- **Then** 两次均全绿（含 `test_story_slim056.py::TestDoctorCommand::test_doctor_runs` 单测独立运行也通过）

### AC4: adapter 版本偏斜 warning (R3)

- **Given** 安装的 pactkit-opencode 版本落后于 core（如 2.9.1 vs 2.17.0）
- **When** 运行 `pactkit doctor`
- **Then** 输出含版本偏斜 warning 与升级提示，且退出码语义不变（不计入 drift）

## Target Call Chain

```
pactkit init -t <dir>          (CLI 默认 format=all)
  └─ cli.py → deployer.py:deploy(format="all", target=<dir>)
       └─ for fmt in _DEPLOYER_REGISTRY:                    ← R1 修改点
            fmt_target = target if fmt == "classic" else None   ← BUG: adapter 无视 target
            → R1: target 非 None 且 fmt != classic → skip + 提示

pactkit doctor
  └─ doctor.py:check_deps() 附近                              ← R3 新增点
       └─ importlib.metadata.version("pactkit-opencode") vs pactkit.__version__
```

污染链实证（2026-08-17）：`test_unicode_project_path` → `run_pactkit("init", "-t", tmp)` → format=all → adapter 2.9.1 写 `~/.config/opencode`（陈旧渲染、不写 manifest）→ slim-141 parity 检出 drift。

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim142_all_target_isolation.py` | 新建：AC1/AC2 spy deployer 测试（RED） | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | `deploy(format="all")` 分支：target 非 None 时跳过 adapter + 提示 | Step 1 | Medium — 勿影响 target=None 主路径 |
| 3 | `src/pactkit/doctor.py` | adapter 版本偏斜检查（importlib.metadata） | None | Low |
| 4 | 运维（非代码） | 本机升级 adapter：`pipx inject pactkit <path-to-pactkit-opencode>` + `.venv` 同步升级，验证 doctor 无 drift | Step 2 合并后 | Low |
| 5 | 回归 | 连续两次全量套件 + slim056 单测独立运行（AC3） | Step 2, 4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 修改 source code（deployer.py, doctor.py） |
| SEC-2 | No | 无外部输入解析（target 为既有参数） |
| SEC-3 | No | 无数据库 |
| SEC-4 | No | 无前端 |
| SEC-5 | Yes | sec-scope 命中 auth/session 模式（deployer 含 token 相关字串）——本次改动不触碰凭据逻辑，仅需确认跳过逻辑不影响 MCP/凭据部署提示 |
| SEC-6 | No | 无 API/路由 |
| SEC-7 | Yes | importlib.metadata.PackageNotFoundError（adapter 未安装）必须静默跳过，不得 crash doctor |
| SEC-8 | No | 无新依赖（importlib.metadata 为标准库） |

## Out of Scope

- adapter 包（pactkit-opencode 2.9.1 → 2.17.0）的版本升级本身 —— 属运维动作（Step 4），不改 adapter 仓库代码
- adapter deployer 支持自定义 target 的能力（如需 preview adapter 部署，另立 story）
- 测试套件的全面 HOME 隔离改造（R1 从源头消除污染向量后，slim056 无需修改；其余测试若有个案另议）
- `test_doctor_runs` 对真实机器状态的隐性依赖重构 —— R1 修复后该测试恢复确定性，不追求完美隔离
