# STORY-slim-006: Prompt Template Variables — Replace Hardcoded Paths with FormatProfile Placeholders

| Field | Value |
|-------|-------|
| ID | STORY-slim-006 |
| Status | Draft |
| Priority | P1 |
| Release | 2.1.0 |
| Depends | STORY-slim-005 (FormatProfile) |

## Background

### 当前状态

Prompts 源码中有 **48 处硬编码路径**，全部写死为 `~/.claude/skills/`（classic 格式）。当前通过 deployer 的 `_rewrite_skills_prefix()` 在部署时做字符串替换（`~/.claude/skills/` → `~/.config/opencode/skills/`），这个机制有以下问题：

1. **脆弱性**：依赖精确的字符串匹配，任何拼写变化都导致替换遗漏
2. **不可见性**：阅读 prompts 源码时，看到的永远是 classic 路径，其他格式的路径完全隐藏
3. **不可扩展**：新增格式时，必须知道去 deployer 加替换规则，不看代码就不知道
4. **无文档**：没有文档说明哪些变量可用、含义是什么

### 扫描结果（完整清单）

| Category | Count | Files | 当前 _rewrite 覆盖? |
|----------|:---:|-------|:---:|
| **SKILLS_PATH** — `~/.claude/skills/xxx` | 29 | skills.py(20), commands.py(2), workflows.py(6), agents.py(1) | ✅ 已覆盖 |
| **RULES_PATH** — `@~/.claude/rules/xxx` | 6 | rules.py | ⬜ 无需覆盖（classic 专有 `@import` 语法） |
| **PROJECT_CONFIG** — `.claude/pactkit.yaml` | 5 | commands.py(3), workflows.py(1), skills.py(1) | ❌ **未覆盖** |
| **DUAL_PATH_DOC** — 同时写了 classic + opencode 路径 | 8 | skills.py(6), commands.py(2) | N/A（文档性） |
| **Total** | 48 | 4 files | |

### 核心决策

**方案选择**：不再用运行时字符串替换，改为 **源码占位符 + 部署时注入**。

理由：
- 阅读源码时能清楚看到"这是一个变量"，而不是"这是 classic 的路径"
- 新增格式时，只需在 FormatProfile 里加字段，deployer 的注入逻辑自动适配
- 减少字符串替换的脆弱性，用显式的变量名替代隐式的路径匹配

## Template Variable Reference（模板变量文档）

> **这是本项目所有 prompt 模板可使用的变量定义**。
> 新增变量时必须同步更新此表和 `profiles.py` 的 `FormatProfile`。

### 变量定义表

| 变量名 | 说明 | FormatProfile 字段 | classic 值 | opencode 值 | codex 值 |
|--------|------|-------------------|-----------|------------|----------|
| `{SKILLS_ROOT}` | 全局 skills 根目录 | `skills_dir` | `~/.claude/skills` | `~/.config/opencode/skills` | `$HOME/.agents/skills` |
| `{RULES_ROOT}` | 全局 rules 根目录 | `rules_dir` | `~/.claude/rules` | `~/.config/opencode/rules` | N/A (inline) |
| `{GLOBAL_CONFIG_DIR}` | 全局配置根目录 | `global_config_dir` | `~/.claude` | `~/.config/opencode` | `~/.codex` |
| `{PROJECT_CONFIG_DIR}` | 项目配置目录名 | `project_config_dir` | `.claude` | `.opencode` | `.codex` |
| `{INSTRUCTIONS_FILE}` | 项目指令文件名 | `project_instructions_file` | `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` |
| `{PACTKIT_YAML}` | pactkit.yaml 相对路径 | `pactkit_yaml_path` | `.claude/pactkit.yaml` | `.opencode/pactkit.yaml` | `.codex/pactkit.yaml` |
| `{DISPLAY_NAME}` | 工具显示名称 | `display_name` | `Claude Code` | `OpenCode` | `Codex CLI` |

### 派生变量（由渲染器计算）

| 变量名 | 说明 | 计算方式 | 示例值 (opencode) |
|--------|------|----------|-------------------|
| `{VISUALIZE_CMD}` | visualize.py 完整调用命令 | `python3 {SKILLS_ROOT}/pactkit-visualize/scripts/visualize.py` | `python3 ~/.config/opencode/skills/pactkit-visualize/scripts/visualize.py` |
| `{BOARD_CMD}` | board.py 完整调用命令 | `python3 {SKILLS_ROOT}/pactkit-board/scripts/board.py` | `python3 ~/.config/opencode/skills/pactkit-board/scripts/board.py` |
| `{SCAFFOLD_CMD}` | scaffold.py 完整调用命令 | `python3 {SKILLS_ROOT}/pactkit-scaffold/scripts/scaffold.py` | `python3 ~/.config/opencode/skills/pactkit-scaffold/scripts/scaffold.py` |
| `{GLOBAL_INSTRUCTIONS}` | 全局指令文件完整路径 | `{GLOBAL_CONFIG_DIR}/{INSTRUCTIONS_FILE}` | `~/.config/opencode/AGENTS.md` |

### 变量使用规则

1. **Prompt 源码**中使用 `{VAR_NAME}` 占位符（Python str.format 语法）
2. **Deployer** 在写入文件前调用 `_render_prompt(template, profile)` 注入实际值
3. **双路径文档**（如 "Classic: xxx, OpenCode: yyy"）使用 `{DISPLAY_NAME}` + 实际路径
4. **`@import` 语法**的 rules.py CLAUDE_MD_TEMPLATE 不使用占位符（classic 专有功能）
5. **新增变量时**：(a) 加到 FormatProfile (b) 加到 `_render_prompt()` 的变量字典 (c) 更新本文档

## Requirements

### R1: 渲染器函数 `_render_prompt()` (MUST)

在 deployer.py 新增统一的 prompt 渲染函数：

```python
def _render_prompt(template: str, profile: FormatProfile) -> str:
    """Render a prompt template by replacing {VAR} placeholders with profile values.
    
    All available template variables are defined in FormatProfile fields.
    See docs/specs/STORY-slim-006.md 'Template Variable Reference' for the full list.
    """
    skills_root = profile.skills_dir
    vars = {
        "SKILLS_ROOT": skills_root,
        "RULES_ROOT": profile.rules_dir or "",
        "GLOBAL_CONFIG_DIR": profile.global_config_dir,
        "PROJECT_CONFIG_DIR": profile.project_config_dir,
        "INSTRUCTIONS_FILE": profile.project_instructions_file,
        "PACTKIT_YAML": profile.pactkit_yaml_path,
        "DISPLAY_NAME": profile.display_name,
        # Derived
        "VISUALIZE_CMD": f"python3 {skills_root}/pactkit-visualize/scripts/visualize.py",
        "BOARD_CMD": f"python3 {skills_root}/pactkit-board/scripts/board.py",
        "SCAFFOLD_CMD": f"python3 {skills_root}/pactkit-scaffold/scripts/scaffold.py",
        "GLOBAL_INSTRUCTIONS": f"{profile.global_config_dir}/{profile.global_instructions_file}",
    }
    return template.format_map(vars)
```

**关键点**：
- 使用 `str.format_map()` 而非 `str.format()` — 前者在遇到未知变量时不报错
- Prompt 模板中的非变量花括号（如 JSON 示例）需要用 `{{` `}}` 转义

### R2: skills.py — 29 处 SKILLS_PATH 替换 (MUST)

将所有 `~/.claude/skills/pactkit-xxx/scripts/xxx.py` 替换为占位符：

**Before**:
```python
SKILL_VISUALIZE_MD = """
> **Script location**: Classic: `~/.claude/skills/pactkit-visualize/scripts/visualize.py`, OpenCode: `~/.config/opencode/skills/pactkit-visualize/scripts/visualize.py`

## Command Reference
```bash
python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize
```
"""
```

**After**:
```python
SKILL_VISUALIZE_MD = """
> **Script location**: Use the base directory from the skill invocation header to resolve script paths.

## Command Reference
```bash
{VISUALIZE_CMD} visualize
```
"""
```

**规则**：
- 双路径文档行（"Classic: xxx, OpenCode: yyy"）替换为通用说明
- 命令调用直接用 `{VISUALIZE_CMD}`、`{BOARD_CMD}`、`{SCAFFOLD_CMD}` 派生变量
- 保留不含路径的内容不变

### R3: commands.py — 2 处 SKILLS_PATH + 3 处 PROJECT_CONFIG 替换 (MUST)

**SKILLS_PATH** (commands.py 中的 playbook)：
- `project-done.md` Phase 1.7: `python3 ~/.claude/skills/...` → `{VISUALIZE_CMD} impact`
- `project-done.md` Phase 3.5: `python3 ~/.claude/skills/...` → `{BOARD_CMD} archive`

**PROJECT_CONFIG** (commands.py 中的 playbook)：
- `project-plan.md` Phase 0 Init Guard: `.claude/pactkit.yaml` or `.opencode/pactkit.yaml` → `{PACTKIT_YAML}`
- `project-plan.md` Phase 3: "check `.claude/pactkit.yaml` then `.opencode/pactkit.yaml`" → `{PACTKIT_YAML}`
- `project-plan.md` R5: "read version from `pactkit.yaml` (in `.claude/` or `.opencode/`)" → `{PACTKIT_YAML}`

### R4: workflows.py — 6 处 SKILLS_PATH + 1 处 PROJECT_CONFIG 替换 (MUST)

**SKILLS_PATH** (workflows.py 中的 prompt 常量)：
- `TRACE_PROMPT`: `python3 ~/.claude/skills/...` → `{VISUALIZE_CMD}`
- `SPRINT_PROMPT`: 5 处 skill 调用 → `{VISUALIZE_CMD}`, `{SCAFFOLD_CMD}`, `{BOARD_CMD}`
- `HOTFIX_PROMPT`: 1 处 board 调用 → `{BOARD_CMD}`
- `DESIGN_PROMPT`: 2 处 visualize + scaffold 调用

**PROJECT_CONFIG**:
- `SPRINT_PROMPT`: "Read `pactkit.yaml` (check `.claude/pactkit.yaml` then `.opencode/pactkit.yaml`)" → `{PACTKIT_YAML}`

### R5: agents.py — 1 处 SKILLS_PATH 替换 (MUST)

- `system-medic` agent prompt: `~/.claude/skills/` directory reference → `{SKILLS_ROOT}/`

### R6: deployer 调用链更新 (MUST)

`_deploy_skills()`, `_deploy_agents()`, `_deploy_commands()` 中调用 `_rewrite_skills_prefix()` 替换为 `_render_prompt()`：

```python
# Before
skill_md = _rewrite_skills_prefix(sd["skill_md"], _prefix)

# After  
skill_md = _render_prompt(sd["skill_md"], profile)
```

`_rewrite_skills_prefix()` 保留但标记为 `@deprecated`，仅供 plugin/marketplace 的 `_legacy_prefix` 模式使用。

### R7: JSON 花括号转义 (MUST)

`project-init.md` playbook 包含 `opencode.json` 的 JSON 示例：
```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md"]
}
```

`str.format_map()` 会把 `{` 当做变量引用。MUST 将所有 JSON 示例中的 `{` → `{{`、`}` → `}}` 转义。

### R8: 测试覆盖 (MUST)

- `_render_prompt()` 单元测试：验证所有变量正确注入
- 回归测试：classic 格式部署后不包含 `{SKILLS_ROOT}` 未替换残留
- 回归测试：opencode 格式部署后不包含 `~/.claude/` 残留
- 回归测试：JSON 示例中的花括号不被替换

### R9: profiles.py 文档更新 (MUST)

在 `FormatProfile` 的 docstring 中添加 Template Variable Reference 表，确保开发者在修改 profiles.py 时能看到所有变量的定义和用途。

```python
@dataclass(frozen=True)
class FormatProfile:
    """Immutable environment-specific configuration profile.

    Template Variable Reference (used in prompt templates):
    ┌────────────────────┬──────────────────────┬───────────────────────────┐
    │ Variable           │ FormatProfile Field   │ Example (opencode)        │
    ├────────────────────┼──────────────────────┼───────────────────────────┤
    │ {SKILLS_ROOT}      │ skills_dir            │ ~/.config/opencode/skills │
    │ {RULES_ROOT}       │ rules_dir             │ ~/.config/opencode/rules  │
    │ {GLOBAL_CONFIG_DIR}│ global_config_dir     │ ~/.config/opencode        │
    │ {PROJECT_CONFIG_DIR│ project_config_dir    │ .opencode                 │
    │ {INSTRUCTIONS_FILE}│ project_instructions  │ AGENTS.md                 │
    │ {PACTKIT_YAML}     │ pactkit_yaml_path     │ .opencode/pactkit.yaml    │
    │ {DISPLAY_NAME}     │ display_name          │ OpenCode                  │
    ├────────────────────┼──────────────────────┼───────────────────────────┤
    │ {VISUALIZE_CMD}    │ (derived)             │ python3 {SKILLS_ROOT}/... │
    │ {BOARD_CMD}        │ (derived)             │ python3 {SKILLS_ROOT}/... │
    │ {SCAFFOLD_CMD}     │ (derived)             │ python3 {SKILLS_ROOT}/... │
    │ {GLOBAL_INSTRUCTIONS│(derived)             │ {GLOBAL_CONFIG_DIR}/...   │
    └────────────────────┴──────────────────────┴───────────────────────────┘

    Adding a new format:
        1. Add FormatProfile entry to FORMAT_PROFILES
        2. All template variables auto-derive from profile fields
        3. No prompt files need modification
    """
```

## Acceptance Criteria

### AC1: 零 `~/.claude/skills/` 残留

- **Given** `skills.py`, `commands.py`, `workflows.py`, `agents.py` 源码
- **When** 搜索 `~/.claude/skills/`
- **Then** 结果为 0（所有路径已替换为 `{VAR}` 占位符）

### AC2: Classic 部署正确渲染

- **Given** 运行 `pactkit init --format classic -t /tmp/test`
- **When** 检查部署产物
- **Then** 所有文件包含 `~/.claude/skills/` 实际路径，不包含 `{SKILLS_ROOT}` 等占位符

### AC3: OpenCode 部署正确渲染

- **Given** 运行 `pactkit update --format opencode`
- **When** 检查部署产物
- **Then** 所有文件包含 `~/.config/opencode/skills/` 实际路径，不包含 `~/.claude/` 路径

### AC4: JSON 花括号不被替换

- **Given** `project-init.md` 包含 JSON 示例 `{{"$schema": ...}}`
- **When** 渲染模板
- **Then** 输出为 `{"$schema": ...}`（单花括号）

### AC5: PROJECT_CONFIG 路径正确

- **Given** OpenCode 格式部署
- **When** 检查 playbook 中的 pactkit.yaml 引用
- **Then** 包含 `.opencode/pactkit.yaml` 而非 `.claude/pactkit.yaml`

### AC6: profiles.py 包含变量文档

- **Given** `src/pactkit/profiles.py`
- **When** 阅读 `FormatProfile` 的 docstring
- **Then** 包含完整的 Template Variable Reference 表

### AC7: 全量测试通过

- **Given** 修改后的代码
- **When** 运行 `pytest tests/ -v`
- **Then** 2239+ 通过，0 失败

## Target Call Chain

```
pactkit init --format opencode
  → deploy(format="opencode")
    → profile = get_profile("opencode")
    → _deploy_skills(skills_dir, ..., profile=profile)
      → _render_prompt(SKILL_VISUALIZE_MD, profile)
        → "{VISUALIZE_CMD} visualize" → "python3 ~/.config/opencode/skills/pactkit-visualize/scripts/visualize.py visualize"
    → _deploy_commands(commands_dir, ..., profile=profile)
      → _render_prompt(CMD_DONE_MD, profile)
        → "{BOARD_CMD} archive" → "python3 ~/.config/opencode/skills/pactkit-board/scripts/board.py archive"
    → _deploy_agents(agents_dir, ..., profile=profile)
      → _render_prompt(agent["prompt"], profile)
        → "{SKILLS_ROOT}/" → "~/.config/opencode/skills/"
```

## Implementation Steps

| Step | File | Action | Risk |
|------|------|--------|------|
| 1 | `src/pactkit/profiles.py` | 更新 FormatProfile docstring：添加 Template Variable Reference 表 | Low |
| 2 | `src/pactkit/generators/deployer.py` | 新增 `_render_prompt(template, profile)` 函数 | Low |
| 3 | `src/pactkit/prompts/skills.py` | 29 处 `~/.claude/skills/` → `{SKILLS_ROOT}` / `{VISUALIZE_CMD}` / `{BOARD_CMD}` / `{SCAFFOLD_CMD}` | Medium |
| 4 | `src/pactkit/prompts/workflows.py` | 7 处替换 + JSON 花括号转义 | Medium |
| 5 | `src/pactkit/prompts/commands.py` | 5 处替换 + JSON 花括号转义 | Medium |
| 6 | `src/pactkit/prompts/agents.py` | 1 处替换 | Low |
| 7 | `src/pactkit/generators/deployer.py` | `_deploy_skills/agents/commands` 调用 `_render_prompt()` 替代 `_rewrite_skills_prefix()` | Medium |
| 8 | `tests/unit/test_render_prompt.py` | 新增测试覆盖 AC1-AC7 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | str.format_map 需验证不会注入恶意变量 |
| SEC-2~8 | No | Prompt 文本变更 only |

## Out of Scope

- rules.py 的 `@~/.claude/rules/` 路径（classic 专有 `@import` 语法，不需要模板化）
- `_deploy_claude_md_inline()` 的 plugin 模式路径替换（保持 `_rewrite_skills_prefix` legacy）
- Codex 格式的 prompt 内容适配（那是 STORY-slim-002/003）
