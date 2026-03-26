# STORY-slim-058: Extract pactkit-opencode as independent adapter package

| Field | Value |
|-------|-------|
| ID | STORY-slim-058 |
| Status | Done |
| Priority | P1 |
| Release | v2.6.0 |

## Background

PactKit 的 `deployer.py` 包含约 400 行 OpenCode 专属代码（6个函数），包括：
- `_deploy_opencode()` (line 355, 90 lines) — OpenCode 部署入口
- `_update_global_opencode_json()` (line 1624, 51 lines) — opencode.json 配置管理
- `_resolve_opencode_model_id()` (line 872, 29 lines) — 模型 ID 解析
- `_deploy_agents_md_inline()` (line 1528, 49 lines) — AGENTS.md 内联 agent 定义
- `_deploy_opencode_json()` (line 1577, 47 lines) — opencode.json 生成
- `_convert_command_frontmatter_opencode()` (line 901, 144 lines) — 命令 frontmatter 转换
- `_generate_project_agents_md()` (line 332, 23 lines) — 项目级 AGENTS.md
- `_print_mcp_recommendations_opencode()` (line 1675, 10 lines) — MCP 推荐

这些代码与 Classic/Plugin 模式完全无关，应提取到独立的 `pactkit-opencode` 包中。依赖 STORY-slim-057 提供的 `DeployerProtocol` 和 `DeployerBase`。

## Requirements

### R1: 独立仓库 pactkit-opencode (MUST)

创建独立 Git 仓库 `pactkit-opencode`，包含：
- `pyproject.toml` — 声明 `pactkit >= 2.6.0` 为依赖
- `src/pactkit_opencode/deployer.py` — `OpenCodeDeployer(DeployerBase)` 类
- `src/pactkit_opencode/__init__.py` — 自动注册 deployer（import-time side effect）
- `tests/` — OpenCode 专属部署测试

### R2: OpenCodeDeployer 类 (MUST)

`OpenCodeDeployer` MUST:
- 继承 `DeployerBase`，实现 `DeployerProtocol`
- 使用 `profile = get_profile("opencode")` 获取 FormatProfile
- 包含所有 6 个 OpenCode 专属函数（从 deployer.py 迁移）
- 调用 `register_deployer("opencode", OpenCodeDeployer)` 完成注册

### R3: Entry Point 自动注册 (MUST)

`pactkit-opencode` MUST 通过 Python entry_points 机制实现自动注册：
- `pyproject.toml` 中声明 `[project.entry-points."pactkit.deployers"]` → `opencode = "pactkit_opencode:OpenCodeDeployer"`
- `pactkit` core 在 `deploy()` 中扫描 entry_points 并自动注册
- 用户只需 `pip install pactkit-opencode`，无需手动配置

### R4: 从 core 中移除 OpenCode 代码 (MUST)

从 `deployer.py` 中删除所有 OpenCode 专属函数（~400 行）。`profiles.py` 中的 `opencode` FormatProfile 保留（它是接口定义，不是实现）。

### R5: 友好的缺失提示 (SHOULD)

当用户执行 `pactkit init --format opencode` 但未安装 `pactkit-opencode` 时：
- 报错: `"OpenCode deployer not found. Install it with: pip install pactkit-opencode"`
- 不应抛出 traceback

### R6: OpenCode 测试迁移 (MUST)

现有 `tests/` 中的 OpenCode 专属测试 MUST 迁移到 `pactkit-opencode` 仓库。Core 仓库中保留的测试 MUST 不依赖 OpenCode deployer 的存在。

## Acceptance Criteria

### AC1: pactkit-opencode 可独立安装 (R1, R3)

- **Given** 一个干净的 Python 环境，已安装 `pactkit >= 2.6.0`
- **When** 执行 `pip install pactkit-opencode`
- **Then** `pactkit init --format opencode` 成功执行，部署所有 OpenCode 文件

### AC2: OpenCodeDeployer 使用 DeployerBase (R2)

- **Given** `pactkit-opencode` 已安装
- **When** `deploy(format="opencode")` 被调用
- **Then** 调用链为: `OpenCodeDeployer.deploy()` → `DeployerBase._deploy_skills()` → ... → `OpenCodeDeployer._update_global_opencode_json()`

### AC3: Core 不包含 OpenCode 代码 (R4)

- **Given** `pactkit` core 包
- **When** `grep -r "opencode" src/pactkit/generators/deployer.py` 执行
- **Then** 无 OpenCode 专属函数匹配（FormatProfile 引用除外）

### AC4: 缺失包时友好报错 (R5)

- **Given** 未安装 `pactkit-opencode`
- **When** 执行 `pactkit init --format opencode`
- **Then** 输出 `"OpenCode deployer not found. Install it with: pip install pactkit-opencode"` 并退出码 1

### AC5: OpenCode 测试独立运行 (R6)

- **Given** `pactkit-opencode` 仓库的测试目录
- **When** 在该仓库中执行 `pytest tests/ -v`
- **Then** 所有 OpenCode 专属测试通过，不依赖 core 仓库的测试

### AC6: 部署产物一致 (R2)

- **Given** 安装 pactkit + pactkit-opencode
- **When** 对同一项目执行 `pactkit init --format opencode`
- **Then** 所有部署文件（skills, rules, agents, commands, opencode.json, AGENTS.md）与拆分前版本 byte-identical

## Target Call Chain

```
cli.py: main()
  → deployer.py: deploy(format="opencode")
    → _load_entry_point_deployers()  # scans pactkit.deployers entry_points
    → _DEPLOYER_REGISTRY["opencode"]  →  OpenCodeDeployer.deploy(config, target)
      → DeployerBase._deploy_skills(...)
      → DeployerBase._deploy_rules(...)
      → DeployerBase._deploy_agents(...)
      → DeployerBase._deploy_commands(...)
      → OpenCodeDeployer._deploy_opencode_json(...)
      → OpenCodeDeployer._update_global_opencode_json(...)
      → OpenCodeDeployer._deploy_agents_md_inline(...)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | (new repo) `pactkit-opencode/pyproject.toml` | Create package with `pactkit >= 2.6.0` dependency and entry_point declaration | STORY-slim-057 | Low |
| 2 | `pactkit-opencode/src/pactkit_opencode/deployer.py` | Move 6 OpenCode functions from deployer.py into `OpenCodeDeployer(DeployerBase)` | Step 1 | Medium — must preserve all logic |
| 3 | `pactkit-opencode/src/pactkit_opencode/__init__.py` | Import `OpenCodeDeployer`, call `register_deployer("opencode", OpenCodeDeployer)` | Step 2 | Low |
| 4 | `src/pactkit/generators/deployer.py` | Add `_load_entry_point_deployers()` using `importlib.metadata.entry_points` | STORY-slim-057 | Medium — entry_point API varies by Python version |
| 5 | `src/pactkit/generators/deployer.py` | Delete 6 OpenCode-specific functions (~400 lines) | Steps 2-4 | High — must verify no remaining references |
| 6 | `pactkit-opencode/tests/` | Migrate OpenCode-specific tests from core repo | Step 5 | Medium |
| 7 | Both repos | Run full test suites | Steps 5-6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | No new user input paths |
| SEC-2 Authentication | N/A | No auth changes |
| SEC-3 Path Traversal | N/A | File paths remain profile-driven via `atomic_write()` |
| SEC-4 Injection | N/A | No new template rendering |
| SEC-5 Secrets | Low | `_update_global_opencode_json` handles opencode.json which MAY contain API keys — existing behavior preserved, no new exposure |
| SEC-6 Dependencies | Low | New package depends on `pactkit` — circular dependency risk if not carefully scoped |
| SEC-7 Config Safety | Low | Entry_point scanning: only loads classes from installed packages (pip trust boundary) |
| SEC-8 Data Exposure | N/A | No new data flows |

## Out of Scope

- Trae adapter package (future, separate project)
- Changes to FormatProfile definitions
- Changes to prompt templates
- OpenCode model routing logic changes
- PyPI publishing automation for pactkit-opencode (manual first release)
