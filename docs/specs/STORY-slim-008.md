# STORY-slim-008: Deploy Chain Parity — Align OpenCode Deployment with Classic Feature Set

| Field | Value |
|-------|-------|
| ID | STORY-slim-008 |
| Status | Draft |
| Priority | P1 |
| Release | 2.1.0 |
| Depends | STORY-slim-005 (FormatProfile) |

## Background

### 当前状态

`_deploy_classic()` 调用 10 个子函数部署完整功能集，但 `_deploy_opencode()` 只调用 6 个。缺失的 4 个功能导致 OpenCode 用户体验不完整。

### 部署链对比（代码实证）

| 函数 | classic (line 146) | opencode (line 288) | 状态 |
|------|:---:|:---:|:---:|
| `_deploy_skills(profile=)` | ✅ L197 | ✅ L319 | 对齐 |
| `_deploy_rules()` | ✅ L200 | ✅ L321 | 对齐 |
| `_deploy_agents(profile=)` | ✅ L203 | ✅ L334 | 对齐 |
| `_deploy_commands(profile=)` | ✅ L204 | ✅ L335 | 对齐 |
| `_deploy_claude_md()` / `_deploy_agents_md_inline()` | ✅ L201 | ✅ L323 | 等价 |
| `_cleanup_legacy()` | ✅ L198 | ❌ | **缺失** |
| `_deploy_hooks()` | ✅ L214 | ❌ | **缺失** |
| `_deploy_ci()` | ✅ L210 | ❌ | **缺失** |
| `_generate_config_if_missing()` | ✅ L217 | ❌ | **缺失** |
| `_generate_project_claude_md()` / 项目级 AGENTS.md | ✅ L222 | ❌ | **缺失** |
| `_print_mcp_recommendations()` | ✅ L236 | ❌ | 缺失（低优） |
| `auto_merge_config_file()` | ✅ L165 | ❌ | **缺失** |
| `_migrate_from_scafpy()` | ✅ L155 | N/A | 不需要 |

### 影响

1. **OpenCode 不读 pactkit.yaml** — `_deploy_opencode()` 不调用 `load_config()`, 硬编码部署 `all_agents/all_commands`。无法按 pactkit.yaml 做选择性部署。
2. **OpenCode 无 Hooks** — classic 支持 hooks 配置，opencode 不部署
3. **OpenCode 无 CI** — classic 支持 GitHub Actions/GitLab CI 生成，opencode 不部署
4. **OpenCode 无 auto-merge** — 新版本增加组件时，classic 自动合并配置，opencode 需要手动
5. **OpenCode 无 project-level 指令文件生成** — classic 自动生成项目级 CLAUDE.md，opencode 不生成项目级 AGENTS.md

### 非 profile 化函数

| 函数 | 应该接受 profile? | 原因 |
|------|:---:|------|
| `_deploy_rules()` | ✅ SHOULD | classic 用 `@import`，opencode 用 `instructions` glob — 两者规则文件格式不同 |
| `_deploy_hooks()` | ❌ NO | Hooks 是 claude code 专有功能 |
| `_deploy_ci()` | ❌ NO | CI 配置与 format 无关 |
| `_generate_config_if_missing()` | ✅ SHOULD | 需要知道 config 写到 `.claude/` 还是 `.opencode/` |
| `_deploy_agents_md_inline()` | ❌ NO | 只有 opencode/codex 使用 |

## Requirements

### R1: _deploy_opencode() 读取 pactkit.yaml (MUST)

当前 `_deploy_opencode()` 硬编码 `all_agents = sorted(VALID_AGENTS)`。改为：

```python
# Load config from project-level pactkit.yaml (same as classic)
config = _load_project_config(profile=oc_profile)

enabled_agents = config.get("agents", sorted(VALID_AGENTS))  # fallback: all
enabled_commands = config.get("commands", sorted(VALID_COMMANDS))
enabled_skills = config.get("skills", sorted(VALID_SKILLS))
enabled_rules = config.get("rules", sorted(VALID_RULES))
```

这使 OpenCode 部署也支持 selective deployment（选择性部署）。

### R2: _deploy_opencode() 调用 auto_merge (MUST)

在 load_config 之前，调用 `auto_merge_config_file()` 确保新版本增加的组件自动合并到 pactkit.yaml。

### R3: _deploy_opencode() 添加 _cleanup_legacy() (SHOULD)

在 skills 部署后调用 `_cleanup_legacy(skills_dir)`，清理旧版本的残留文件。

### R4: _deploy_opencode() 生成项目级 AGENTS.md (SHOULD)

等价于 classic 的 `_generate_project_claude_md()`。当 `target is None`（非 preview 模式）时，在项目根生成 `./AGENTS.md` 如果不存在。

内容模板：
```markdown
# {project_name}

@./docs/product/context.md
output MUST use Chinese
```

### R5: _deploy_opencode() 添加 MCP 建议 (SHOULD)

调用 `_print_mcp_recommendations()` 输出 MCP 服务器建议。

### R6: 统一部署入口 — _deploy_standard() (SHOULD)

将 classic 和 opencode 的公共部分提取为 `_deploy_standard(profile, config, target)`：

```python
def _deploy_standard(profile, config, target):
    """Standard deployment for environment formats (classic, opencode, codex)."""
    root = Path(target) if target else Path(profile.global_config_dir).expanduser()
    
    # Common sub-functions
    _deploy_skills(root / "skills", config["skills"], profile=profile)
    _cleanup_legacy(root / "skills")
    _deploy_rules(root, config["rules"])
    _deploy_agents(root / "agents", config["agents"], profile=profile)
    _deploy_commands(root / "commands", config["commands"], profile=profile)
    
    # Format-specific extensions
    if profile.name == "classic":
        _deploy_claude_md(root, config["rules"])
        _deploy_hooks(root / "hooks", config.get("hooks", {}))
        _deploy_ci(config.get("ci", {}).get("provider", "none"), Path.cwd(), config)
    elif profile.name == "opencode":
        _deploy_agents_md_inline(root)
        _update_global_opencode_json(root, ...)
```

**注意**：这是一个 SHOULD — 完整统一需要更大的重构。本 Story 可以先补齐缺失功能（R1-R5），统一入口作为后续优化。

### R7: _generate_config_if_missing() 感知 format (MUST)

当前 `_generate_config_if_missing()` 只写到 `.claude/pactkit.yaml`。改为接受 format 参数，使用 `resolve_pactkit_yaml_dir(format=format)` 确定写入路径。

## Acceptance Criteria

### AC1: OpenCode selective deployment 生效

- **Given** `.opencode/pactkit.yaml` 中 `agents` 列表只包含 3 个 agent
- **When** 运行 `pactkit update --format opencode`
- **Then** 只生成 3 个 agent 文件

### AC2: OpenCode auto-merge 生效

- **Given** 旧版 `.opencode/pactkit.yaml` 缺少新组件
- **When** 运行 `pactkit update --format opencode`
- **Then** 打印 `-> Auto-added: xxx` 并更新 yaml

### AC3: OpenCode cleanup_legacy 生效

- **Given** `~/.config/opencode/skills/` 下有已弃用的 skill 目录
- **When** 运行 `pactkit update --format opencode`
- **Then** 旧 skill 目录被清理

### AC4: 部署链函数数量对等

- **Given** `_deploy_classic()` 和 `_deploy_opencode()` 的子函数调用
- **When** 对比两者
- **Then** opencode 覆盖 classic 的所有功能（CI/Hooks 除外）

### AC5: 全量测试通过

- **Given** 修改后的代码
- **When** 运行 `pytest tests/ -v`
- **Then** 2269+ 通过，0 失败

## Target Call Chain

```
pactkit update --format opencode
  → deploy(format="opencode")
    → _deploy_opencode(target)
      → profile = get_profile("opencode")
      → config = _load_project_config(profile)       ← NEW (R1)
      → auto_merge_config_file(yaml_path)             ← NEW (R2)
      → _deploy_skills(profile=opencode, config)
      → _cleanup_legacy()                              ← NEW (R3)
      → _deploy_rules()
      → _deploy_agents_md_inline()
      → _update_global_opencode_json()
      → _deploy_agents(profile=opencode, config)
      → _deploy_commands(profile=opencode, config)
      → _generate_project_agents_md()                  ← NEW (R4)
      → _print_mcp_recommendations()                   ← NEW (R5)
```

## Implementation Steps

| Step | File | Action | Risk |
|------|------|--------|------|
| 1 | `src/pactkit/generators/deployer.py` | `_deploy_opencode()` 添加 load_config + auto_merge | Medium |
| 2 | `src/pactkit/generators/deployer.py` | `_deploy_opencode()` 添加 `_cleanup_legacy()` | Low |
| 3 | `src/pactkit/generators/deployer.py` | 新增 `_generate_project_agents_md()` (等价 `_generate_project_claude_md`) | Medium |
| 4 | `src/pactkit/generators/deployer.py` | `_deploy_opencode()` 添加 `_print_mcp_recommendations()` | Low |
| 5 | `src/pactkit/config.py` | `_generate_config_if_missing()` 接受 format 参数 | Low |
| 6 | Tests | 新增 opencode selective deploy + auto-merge 测试 | Medium |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 部署链逻辑变更 |
| SEC-2~8 | No | 无用户输入处理 |

## Out of Scope

- OpenCode 的 Hooks 支持（OpenCode 无 hooks 概念）
- OpenCode 的 CI 生成（OpenCode 不管 CI）
- `_deploy_standard()` 完整统一重构（R6 标记为 SHOULD，后续 Story）
- Codex 部署链（STORY-slim-002/003/004）
