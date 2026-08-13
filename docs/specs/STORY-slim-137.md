# STORY-slim-137: pactkit deps: external dependency check and guided install

| Field | Value |
|-------|-------|
| ID | STORY-slim-137 |
| Status | Done |
| Priority | P1 |
| Release | 2.17.0 |

## Background

PactKit 的运行依赖两类外部工具，pip 管不到、只能文档提示：`codegraph`（npm 全局包，call graph 数据源）、`gh` CLI（issue-sync / PR / release / CI 检查）、`node` 本身（codegraph 前置）。pip 生态内的依赖已被 extras 覆盖（`pactkit[all]`），缺口全在 npm/系统层。新用户 onboarding 的最大痛点是"不知道要装什么"。

设计共识（2026-08-13 讨论确认）：安装时机 MUST 在 `/project-init`（交互式 playbook，人一定在场），而 `pactkit init` CLI 可能在 CI/CD、`--non-interactive`、气隙环境运行，MUST 只做只读检测、绝不自动安装。"怎么装"是确定性逻辑，MUST 由 CLI 子命令实现（可测试）；"/project-init 什么时候问"才是 playbook 编排。

## Requirements

### R1: 依赖注册表 + `pactkit deps check` (MUST)

新增 `src/pactkit/deps.py`，以模块级注册表常量声明外部依赖清单（每项：`name`、检测方式 `which` 命令、最低版本、各平台安装命令、用途说明）。`pactkit deps check` 逐项检测并输出状态表（✅ 已装 / ❌ 缺失 + 对应平台安装命令），支持 `--json`。退出码：全部就绪 0，有缺失 1（调用方按 informational 处理）。

### R2: `pactkit deps install` (MUST)

按平台执行安装：darwin → `brew install`（gh、node）；codegraph → `npm i -g @colbymchenry/codegraph`（前置检测 node，缺失则先装 node）。逐项执行前打印将运行的命令；默认逐项询问确认，`--yes` 跳过。单项失败不中断其余项，结束后输出汇总（成功/失败/跳过）。`enterprise.no_external: true` 时 MUST 拒绝执行并说明原因。平台无映射（如 linux 非 apt 系）→ 打印手动安装指引，不猜测。

### R3: /project-init Phase 1.5 接线 (MUST)

修改 `prompts/commands.py` 的 `project-init.md`，在 Phase 1 之后插入 "Phase 1.5: External Dependencies"：运行 `pactkit deps check`；有缺失 → 列出清单询问用户是否安装；同意 → 运行 `pactkit deps install`；拒绝 → 打印手动命令继续。位置必须在 Phase 3（Discovery 依赖 codegraph）之前。同步重新生成 plugin artifact。

### R4: CLI init/update 只读检测 + doctor 纳入 (MUST)

`pactkit init` / `pactkit update` 末尾输出 deps 检测摘要（只读，缺失时给出 `pactkit deps install` 指引，绝不自动安装）。`pactkit doctor` 新增 deps 健康项（复用 R1 注册表）。

### R5: 无静默系统变更 (MUST NOT)

任何代码路径 MUST NOT 在非交互场景（CI、`--non-interactive`、`--no-external`）自动执行系统级安装命令。依赖清单、平台映射、版本号 MUST 全部来自 R1 注册表，禁止散落在函数体内的 hardcode。

## Acceptance Criteria

### AC1: 检测状态表 (R1)

- **Given** 一台已装 codegraph、未装 gh 的环境
- **When** 执行 `pactkit deps check`
- **Then** 输出逐项状态表：codegraph ✅（含版本）、gh ❌（含 macOS 安装命令 `brew install gh`）；退出码为 1

### AC2: 引导安装 (R2)

- **Given** 缺失 gh 的 macOS 环境
- **When** 执行 `pactkit deps install --yes`
- **Then** 执行 `brew install gh` 前打印该命令；结束后输出汇总；再次 `pactkit deps check` 时 gh 为 ✅

### AC3: 企业环境拒绝执行 (R2, R5)

- **Given** pactkit.yaml 含 `enterprise.no_external: true`
- **When** 执行 `pactkit deps install`
- **Then** 拒绝执行任何安装命令，打印原因与手动指引；退出码非 0

### AC4: init 接线位置正确 (R3)

- **Given** 修改后的 `project-init.md`（source 与 plugin artifact）
- **When** 检查 Phase 顺序
- **Then** Phase 1.5 位于 Phase 1 与 Phase 3 之间；含"询问→同意才安装"的明确指令；`pactkit-plugin/commands/project-init.md` 与 source 一致

### AC5: CLI init 只读摘要 (R4)

- **Given** 缺失 codegraph 的环境
- **When** 执行 `pactkit init --format classic --non-interactive`
- **Then** 末尾输出缺失项与手动安装指引；全程无任何安装命令被执行

### AC6: doctor 报告 deps 健康 (R4)

- **Given** 缺失任一外部依赖
- **When** 执行 `pactkit doctor`
- **Then** 输出缺失依赖项及安装指引；退出码为 1

### AC7: 测试套件全通过 (R1-R5)

- **Given** 全部修改完成
- **When** 运行 `.venv/bin/pytest tests/ -v`
- **Then** 所有测试通过，无新失败（install 逻辑以 mock subprocess 单测覆盖，不在 CI 真实执行安装）

## Target Call Chain

```
/project-init Phase 1.5 (playbook 编排：询问→同意)
  → pactkit deps check                    [cli.py → deps.py: DEP_REGISTRY 注册表 + shutil.which 检测]
  → pactkit deps install [--yes]          [deps.py: 平台映射 darwin→brew / npm -g；逐项确认；no_external 拒绝]
pactkit init/update 末尾 → deps.check(report_only=True)   [只读摘要]
pactkit doctor → deps 健康项              [复用同一注册表]
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/deps.py` | 新模块：DEP_REGISTRY 注册表 + check/install 逻辑 | None | Medium（install 须全 mock 测试） |
| 2 | `src/pactkit/cli.py` | 注册 deps 子命令（check/install/--json/--yes） | Step 1 | Low |
| 3 | `src/pactkit/generators/deployer.py` | init/update 末尾只读检测摘要 | Step 1 | Low |
| 4 | `src/pactkit/doctor.py` | 新增 deps 健康项 | Step 1 | Low |
| 5 | `src/pactkit/prompts/commands.py` | project-init 插入 Phase 1.5 | Step 2 | Low |
| 6 | `pactkit-plugin/commands/project-init.md` | 重新生成 plugin artifact | Step 5 | Low |
| 7 | `tests/unit/test_deps.py` | 注册表/check/install（mock）单测 | Step 1-2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | install 执行系统命令——安装命令 MUST 全部来自注册表常量，禁止任何用户输入拼接进 shell；使用列表参数 subprocess，禁用 shell=True |
| SEC-2 | Yes | 检测外部命令输出版本号，解析须容错（格式不符按"未知版本"处理，不崩溃） |
| SEC-3 | N/A | 无数据库相关（sec-scope 命中为关键词误报） |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无认证/会话逻辑（sec-scope 命中为关键词误报） |
| SEC-6 | N/A | 无 API/路由变更 |
| SEC-7 | Yes | 安装命令失败/命令不存在/无权限等路径必须捕获并进入汇总报告，不得抛栈中断 |
| SEC-8 | N/A | 无 Python 依赖清单变更（本故事安装的正是"依赖清单外"的工具） |

## Out of Scope

- pip 生态内依赖（已由 `pactkit[all]` extras 覆盖，不在本故事重复）
- Windows 平台安装映射（本期覆盖 darwin + linux-apt；Windows 打印手动指引）
- MCP server（context7/memory）的安装——属用户 Claude Code 配置，非 pactkit 依赖
- install.sh 一站式分发脚本（`curl | sh` 形态）——分发渠道决策，另行评估
- 版本锁定/自动升级已装依赖（只检测最低版本，不主动升级）
