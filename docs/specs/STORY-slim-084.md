# STORY-slim-084: Adapter deploy-output validation guard

| Field | Value |
|-------|-------|
| ID | STORY-slim-084 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.13 |

## Background

v2.9.12 release 中 pactkit-copilot adapter 出现 63% fix rate（19 commits 中 12 个是 fix）。根因：部署到非 Claude Code 格式时，prompt 内容中的 CLI 引用（`pactkit visualize`）、路径引用（`~/.claude/`）、排除命令引用（`/project-sprint`）需要被替换或 strip，但没有任何自动化检查来拦截遗漏。每次发现一个遗漏就打一个补丁（mole-whacking pattern），导致 7 个版本号膨胀（v2.9.5→v2.9.12）。

同期还发现：
- `_deploy_rules()` 漏调 `_render_prompt()` — 新代码路径没复制既有模式（v2.9.11 fix）
- `load_script()` 没处理 `__future__` import 位置约束（v2.9.10 fix）
- lessons 表结构损坏修了 2 次才根治 — 最小修复 fallacy（v2.9.10 fix）

3 个 adapter 的内容适配逻辑完全独立实现，无共享验证：
- **Copilot**: `_replace_paths_for_copilot()` (20 行路径替换) + `_replace_slash_commands()` (130 行 CLI→脚本/内联)
- **Codex**: `CLAUDE_PATH_PATTERNS` + `_CLI_TO_SCRIPT` + `_replace_cli_with_scripts()`
- **OpenCode**: 路径替换通过 core `_render_prompt()` var_map，CLI 替换有限

**设计约束**：当前 3 个 adapter 都在正常运行。本 story 只加 guard（assertion + test），**不重构任何部署逻辑**，零回归风险。

## Requirements

### R1: DeployerBase 加 `validate_deployed_content()` 方法 (MUST)

在 `src/pactkit/generators/deploy_base.py` 的 `DeployerBase` 中新增 **静态方法** `validate_deployed_content(content: str, profile: FormatProfile) -> list[str]`。

逻辑：
1. 定义 `FORBIDDEN_RAW_PATTERNS` — 所有格式公共的"不应出现在最终部署内容中"的 pattern 列表
2. 排除 profile 自身的路径（例如 classic 部署内容中 `~/.claude/` 是合法的）
3. 返回违规 pattern 列表（空列表 = 通过）

Forbidden patterns（至少包含）：

| Pattern | 含义 |
|---------|------|
| `~/.claude/skills/` | Claude Code skills 路径 |
| `~/.claude/rules/` | Claude Code rules 路径 |
| `~/.claude/commands/` | Claude Code commands 路径 |
| `~/.config/opencode/skills/` | OpenCode skills 路径 |
| `~/.config/opencode/commands/` | OpenCode commands 路径 |
| `~/.codex/skills/` | Codex skills 路径 |
| `~/.codex/rules/` | Codex rules 路径 |
| `` `pactkit visualize`` | CLI 命令引用（反引号内） |
| `` `pactkit clean`` | CLI 命令引用 |
| `` `pactkit guard`` | CLI 命令引用 |
| `` `pactkit lint`` | CLI 命令引用 |
| `` `pactkit regression`` | CLI 命令引用 |
| `` `pactkit context`` | CLI 命令引用 |
| `` `pactkit doctor`` | CLI 命令引用 |
| `` `pactkit update`` | CLI 命令引用 |

**排除规则**：
- 如果 pattern 以 `profile.global_config_dir` 开头 → 跳过（自己的路径合法）
- 如果 `profile.name == "classic"` → 跳过 CLI 命令检查（classic 有 pactkit CLI）
- 如果内容包含 `pactkit init --format` → 跳过该行（安装指引是合法的）

### R2: 适配 CLI-less profile 标识 (MUST)

在 `src/pactkit/profiles.py` 的 `FormatProfile` dataclass 中新增字段 `has_pactkit_cli: bool`。

| Profile | has_pactkit_cli |
|---------|-----------------|
| classic | True |
| opencode | True（OpenCode 可通过 terminal 运行 pactkit CLI） |
| codex | False |
| copilot | False |

R1 的 CLI 命令检查仅在 `has_pactkit_cli == False` 时执行。

### R3: Core deployer 集成 validate (SHOULD)

在 `deployer.py` 的 `_deploy_commands()`, `_deploy_skills()`, `_deploy_rules()`, `_deploy_agents()` 中，当 `profile` 非 None 时，在写文件前调用 `validate_deployed_content()`。如果返回非空，打 `warnings.warn()` 日志（不 raise，不阻塞部署 — 这是 guard，不是 gate）。

### R4: pactkit-copilot 集成测试 (MUST)

在 `~/workspaces/pactkit-copilot/tests/` 中新增集成测试：

```
test_deploy_output_clean:
  1. 调用 CopilotDeployer.deploy(target=tmp_dir)
  2. 递归读取所有 .md / .prompt.md 文件内容
  3. 对每个文件调用 validate_deployed_content()
  4. assert 所有文件返回空列表（无违规）
```

### R5: pactkit-codex 集成测试 (SHOULD)

同 R4，在 `~/workspaces/pactkit-codex/tests/` 中新增对 CodexDeployer 的部署输出验证测试。

### R6: Core 单元测试 (MUST)

在 `tests/unit/` 中新增 `test_story_slim084.py`：

1. `test_validate_detects_foreign_path` — 内容含 `~/.claude/skills/` + codex profile → 返回违规
2. `test_validate_allows_own_path` — 内容含 `~/.claude/skills/` + classic profile → 返回空
3. `test_validate_detects_cli_ref` — 内容含 `` `pactkit visualize` `` + copilot profile (has_pactkit_cli=False) → 返回违规
4. `test_validate_allows_cli_for_classic` — 内容含 `` `pactkit visualize` `` + classic profile (has_pactkit_cli=True) → 返回空
5. `test_validate_skips_install_instructions` — 内容含 `pactkit init --format copilot` → 不算违规
6. `test_has_pactkit_cli_field` — 验证 4 个 profile 的 `has_pactkit_cli` 值正确

## Acceptance Criteria

### AC1: validate_deployed_content 检测外部路径 (R1)

- **Given** 一段内容包含 `~/.claude/skills/pactkit-visualize`
- **When** 以 codex profile 调用 `validate_deployed_content()`
- **Then** 返回列表包含 `~/.claude/skills/`

### AC2: validate_deployed_content 放行自身路径 (R1)

- **Given** 一段内容包含 `~/.claude/skills/pactkit-visualize`
- **When** 以 classic profile 调用 `validate_deployed_content()`
- **Then** 返回空列表

### AC3: CLI 引用检测仅在无 CLI 的 profile 生效 (R1, R2)

- **Given** 一段内容包含 `` `pactkit visualize --mode class` ``
- **When** 以 copilot profile (has_pactkit_cli=False) 调用
- **Then** 返回列表包含 `` `pactkit visualize` ``
- **When** 以 classic profile (has_pactkit_cli=True) 调用
- **Then** 返回空列表

### AC4: 安装指引不算违规 (R1)

- **Given** 一段内容包含 `run pactkit init --format copilot from the terminal`
- **When** 以 copilot profile 调用
- **Then** 该行不触发 CLI 检查违规

### AC5: Copilot 部署输出零违规 (R4)

- **Given** CopilotDeployer 完整部署到临时目录
- **When** 对所有 .md/.prompt.md 文件运行 validate_deployed_content()
- **Then** 所有文件返回空列表

### AC6: Core deploy 函数调用 validate (R3)

- **Given** `_deploy_commands()` 以 copilot profile 部署一个命令
- **When** 命令内容包含未替换的 `~/.claude/` 路径
- **Then** `warnings.warn()` 被调用（验证 warning 内容包含违规 pattern）

### AC7: FormatProfile.has_pactkit_cli 值正确 (R2)

- **Given** `FORMAT_PROFILES` 中的 4 个 profile
- **When** 读取 `has_pactkit_cli` 字段
- **Then** classic=True, opencode=True, codex=False, copilot=False

### AC8: Codex 部署输出零违规 (R5)

- **Given** CodexDeployer 完整部署到临时目录
- **When** 对所有 .md 文件运行 validate_deployed_content()
- **Then** 所有文件返回空列表

### AC9: Core 单元测试覆盖 validate 函数 (R6)

- **Given** `test_story_slim084.py` 中的 6 个测试
- **When** 运行 `pytest tests/unit/test_story_slim084.py`
- **Then** 全部通过，覆盖 R1 的路径检测、CLI 检测、排除规则

## Scope 边界

### 在 scope 内
- `validate_deployed_content()` 验证函数
- `has_pactkit_cli` profile 字段
- Core deploy 函数中的 warning 级别集成
- Copilot + Codex adapter 集成测试

### 不在 scope 内
- **不重构任何 adapter 的部署逻辑**（_replace_paths_for_copilot, _replace_cli_with_scripts 等保持原样）
- **不把 adapter 的替换逻辑上移到 core**（那是未来方案 B 的事）
- **不阻塞部署**（validate 只 warn，不 raise）
- **不修改 _render_prompt()**

## Implementation Notes

1. `FORBIDDEN_RAW_PATTERNS` 应定义在 `deploy_base.py` 中，靠近 `DeployerBase` class — 让 adapter 可以 import 复用
2. `validate_deployed_content()` 是纯函数（无副作用），方便测试
3. Copilot 集成测试需要 mock pactkit core（`pactkit-copilot` 不能在测试时 import 未安装的 core adapter）— 参考 codex adapter 的 test 结构
4. `has_pactkit_cli` 字段加在 `FormatProfile.__init__` 参数末尾，default=True（向后兼容，未设置的自定义 profile 默认有 CLI）

## Security Scope

| SEC | Applies | Notes |
|-----|---------|-------|
| SEC-1 | Yes | Source code: new validation function + profile field |
| SEC-2 | No | No user input — validates internal deploy output only |
| SEC-3 | No | No database |
| SEC-4 | No | No frontend |
| SEC-5 | No | No auth/session |
| SEC-6 | No | No API/route |
| SEC-7 | No | Pure function, no error handling needed |
| SEC-8 | No | No new packages |

## Friction-Log Reference

本 story 源自 Session 19 retro 工程问题分析：pactkit-copilot 63% fix rate + mole-whacking deploy 反模式。属于质量加固，不是新功能。
