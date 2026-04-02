# STORY-slim-005: FormatProfile Abstraction — Parameterize Environment-Specific Paths and Behaviors

| Field | Value |
|-------|-------|
| ID | STORY-slim-005 |
| Status | Draft |
| Priority | P1 |
| Release | 2.1.0 |

## Background

当前 PactKit 代码库中存在大量环境相关的 if-else 分支和硬编码路径：

**问题现状**：
- `deployer.py` 中 60+ 处 `~/.claude` 硬编码引用
- `config.py` 中 `resolve_pactkit_yaml_dir()` 使用 if-else 判断 format
- `commands.py` 中 playbook 硬编码 `~/.claude/skills/` 路径
- `scaffold.py` 中 `_PACTKIT_YAML_CANDIDATES` 列表需要手动维护
- 每次新增 format（如 codex）需要修改 10+ 个文件，极易遗漏

**根因**：缺乏统一的 Format Profile 抽象，每个环境的路径和行为分散在代码各处。

**目标**：将所有环境相关参数提取到一个 `FormatProfile` 数据结构中，代码通过查表获取参数，消除 if-else 分支。

## Requirements

### R1: FormatProfile 数据类定义 (MUST)

在 `src/pactkit/profiles.py` 中定义 `FormatProfile` dataclass：

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class FormatProfile:
    """Environment-specific configuration profile."""
    
    # Identity
    name: str                          # "classic", "opencode", "codex"
    display_name: str                  # "Claude Code", "OpenCode", "Codex CLI"
    
    # Directory Structure
    global_config_dir: str             # "~/.claude", "~/.config/opencode", "~/.codex"
    project_config_dir: str            # ".claude", ".opencode", ".codex"
    skills_dir: str                    # "~/.claude/skills", "~/.config/opencode/skills", "$HOME/.agents/skills"
    agents_dir: str                    # "~/.claude/agents", "~/.config/opencode/agents", "~/.codex/agents"
    commands_dir: str | None           # "~/.claude/commands", "~/.config/opencode/commands", None
    rules_dir: str | None              # "~/.claude/rules", "~/.config/opencode/rules", None
    
    # File Names
    project_instructions_file: str     # "CLAUDE.md", "AGENTS.md"
    global_instructions_file: str      # "CLAUDE.md", "AGENTS.md"
    pactkit_yaml_path: str             # ".claude/pactkit.yaml", ".opencode/pactkit.yaml", ".codex/pactkit.yaml"
    
    # Format & Serialization
    agent_format: Literal["md", "toml"]  # "md" for Claude/OpenCode, "toml" for Codex
    rules_import_style: Literal["@import", "instructions", "inline"]
    
    # Capabilities
    has_custom_commands: bool          # True for Claude/OpenCode, False for Codex
    supports_model_routing: bool       # False for Claude, True for OpenCode/Codex
    supports_mcp: bool                 # True for all
    
    # Playbook Variables
    skills_path_var: str               # "~/.claude/skills", "~/.config/opencode/skills", "$SKILLS_PATH"
```

### R2: FORMAT_PROFILES Registry (MUST)

定义全局 profile 注册表：

```python
FORMAT_PROFILES: dict[str, FormatProfile] = {
    "classic": FormatProfile(
        name="classic",
        display_name="Claude Code",
        global_config_dir="~/.claude",
        project_config_dir=".claude",
        skills_dir="~/.claude/skills",
        agents_dir="~/.claude/agents",
        commands_dir="~/.claude/commands",
        rules_dir="~/.claude/rules",
        project_instructions_file="CLAUDE.md",
        global_instructions_file="CLAUDE.md",
        pactkit_yaml_path=".claude/pactkit.yaml",
        agent_format="md",
        rules_import_style="@import",
        has_custom_commands=True,
        supports_model_routing=False,
        supports_mcp=True,
        skills_path_var="~/.claude/skills",
    ),
    "opencode": FormatProfile(
        name="opencode",
        display_name="OpenCode",
        global_config_dir="~/.config/opencode",
        project_config_dir=".opencode",
        skills_dir="~/.config/opencode/skills",
        agents_dir="~/.config/opencode/agents",
        commands_dir="~/.config/opencode/commands",
        rules_dir="~/.config/opencode/rules",
        project_instructions_file="AGENTS.md",
        global_instructions_file="AGENTS.md",
        pactkit_yaml_path=".opencode/pactkit.yaml",
        agent_format="md",
        rules_import_style="instructions",
        has_custom_commands=True,
        supports_model_routing=True,
        supports_mcp=True,
        skills_path_var="~/.config/opencode/skills",
    ),
    "codex": FormatProfile(
        name="codex",
        display_name="Codex CLI",
        global_config_dir="~/.codex",
        project_config_dir=".codex",
        skills_dir="$HOME/.agents/skills",
        agents_dir="~/.codex/agents",
        commands_dir=None,  # Codex has no custom commands
        rules_dir=None,     # Codex uses inline rules in AGENTS.md
        project_instructions_file="AGENTS.md",
        global_instructions_file="AGENTS.md",
        pactkit_yaml_path=".codex/pactkit.yaml",
        agent_format="toml",
        rules_import_style="inline",
        has_custom_commands=False,
        supports_model_routing=True,
        supports_mcp=True,
        skills_path_var="$SKILLS_PATH",
    ),
}
```

### R3: get_profile() Helper (MUST)

```python
def get_profile(format: str) -> FormatProfile:
    """Get the FormatProfile for a given format name.
    
    Raises ValueError if format is not registered.
    """
    if format not in FORMAT_PROFILES:
        valid = ", ".join(FORMAT_PROFILES.keys())
        raise ValueError(f"Unknown format: {format!r}. Valid formats: {valid}")
    return FORMAT_PROFILES[format]
```

### R4: VALID_FORMATS 自动生成 (MUST)

```python
VALID_FORMATS: frozenset[str] = frozenset(FORMAT_PROFILES.keys())
```

这替代现有硬编码的 `VALID_FORMATS = frozenset(["classic", "plugin", "marketplace", "opencode"])`。

### R5: PACTKIT_YAML_CANDIDATES 自动生成 (MUST)

`config.py` 的候选路径列表从 profiles 自动生成：

```python
from pactkit.profiles import FORMAT_PROFILES

PACTKIT_YAML_CANDIDATES = [
    profile.pactkit_yaml_path 
    for profile in FORMAT_PROFILES.values()
]
```

### R6: resolve_pactkit_yaml_dir() 使用 Profile (MUST)

重写 `resolve_pactkit_yaml_dir()` 消除 if-else：

```python
def resolve_pactkit_yaml_dir(cwd: Path | None = None, format: str | None = None) -> Path:
    if cwd is None:
        cwd = Path.cwd()
    
    # Explicit format takes precedence
    if format:
        profile = get_profile(format)
        return cwd / profile.pactkit_yaml_path
    
    # Auto-detect: return first existing
    for candidate in PACTKIT_YAML_CANDIDATES:
        if (cwd / candidate).exists():
            return cwd / candidate
    
    # Default fallback
    return cwd / FORMAT_PROFILES["classic"].pactkit_yaml_path
```

### R7: deployer.py 使用 Profile (MUST)

`deploy()` 函数通过 profile 获取路径：

```python
def deploy(config=None, target=None, format="classic", ...):
    profile = get_profile(format)
    
    if format in ("plugin", "marketplace"):
        # Special deployment modes (not environment-based)
        ...
    else:
        _deploy_standard(profile, config, target)
```

`_deploy_standard()` 统一处理 classic/opencode/codex，通过 profile 参数化：

```python
def _deploy_standard(profile: FormatProfile, config, target):
    if target is not None:
        root = Path(target)
    else:
        root = Path(profile.global_config_dir).expanduser()
    
    # Use profile.skills_dir, profile.agents_dir, etc.
    _deploy_agents(root / "agents", config, profile)
    _deploy_skills(root / "skills", config, profile)
    if profile.has_custom_commands:
        _deploy_commands(root / "commands", config, profile)
    ...
```

### R8: Playbook skills_path_var 替换 (MUST)

`commands.py` 中的 playbook 使用 `{SKILLS_PATH}` 占位符，部署时根据 profile 替换：

```python
# In playbook templates
PLAYBOOK_TEMPLATE = """
1.  **Scaffold**: Run `python3 {SKILLS_PATH}/pactkit-visualize/scripts/visualize.py init_arch`.
"""

# At deploy time
def _render_playbook(template: str, profile: FormatProfile) -> str:
    return template.replace("{SKILLS_PATH}", profile.skills_path_var)
```

### R9: scaffold.py 使用 Profile (SHOULD)

`scaffold.py` 的 `_PACTKIT_YAML_CANDIDATES` 改为从 profile 导入或内联定义：

```python
_PACTKIT_YAML_CANDIDATES = [
    ".opencode/pactkit.yaml",
    ".claude/pactkit.yaml", 
    ".codex/pactkit.yaml",
]
# 或 from pactkit.profiles import PACTKIT_YAML_CANDIDATES
```

由于 scaffold.py 是独立部署的脚本，不能 import pactkit，所以保持内联定义但添加注释指向 source of truth。

### R10: plugin/marketplace 格式保持独立 (MUST)

`plugin` 和 `marketplace` 不是环境格式，而是输出模式，不纳入 FormatProfile：

```python
DEPLOYMENT_MODES = frozenset(["plugin", "marketplace"])
VALID_FORMATS = DEPLOYMENT_MODES | frozenset(FORMAT_PROFILES.keys())
```

## Acceptance Criteria

### AC1: FormatProfile Dataclass 存在

- **Given** `src/pactkit/profiles.py`
- **When** 导入 `FormatProfile`
- **Then** 是 frozen dataclass，包含所有 R1 定义的字段

### AC2: FORMAT_PROFILES 注册表完整

- **Given** `FORMAT_PROFILES`
- **When** 遍历 `["classic", "opencode", "codex"]`
- **Then** 每个 format 都有对应的 FormatProfile 实例

### AC3: VALID_FORMATS 自动生成

- **Given** `VALID_FORMATS`
- **When** 新增一个 format 到 `FORMAT_PROFILES`
- **Then** `VALID_FORMATS` 自动包含新 format，无需手动维护

### AC4: PACTKIT_YAML_CANDIDATES 自动生成

- **Given** `config.py` 的 `PACTKIT_YAML_CANDIDATES`
- **When** 新增一个 format
- **Then** 候选路径列表自动包含新 format 的 pactkit.yaml 路径

### AC5: 零 if-else format 判断

- **Given** `config.py` 的 `resolve_pactkit_yaml_dir()`
- **When** 检查函数实现
- **Then** 不包含 `if format == "opencode"` 等硬编码分支

### AC6: Deployer 通过 Profile 参数化

- **Given** `deployer.py` 的 `_deploy_standard()`
- **When** 检查路径拼接
- **Then** 所有路径来自 `profile.xxx`，无 `~/.claude` 硬编码

### AC7: Playbook Skills 路径动态替换

- **Given** 部署后的 `project-init.md`
- **When** format=classic
- **Then** 包含 `~/.claude/skills/pactkit-xxx`
- **When** format=opencode
- **Then** 包含 `~/.config/opencode/skills/pactkit-xxx`
- **When** format=codex
- **Then** 包含 `$SKILLS_PATH/pactkit-xxx`

### AC8: 新增 Format 只需修改 profiles.py

- **Given** 需要新增 `cursor` format
- **When** 只在 `profiles.py` 添加 `FormatProfile("cursor", ...)`
- **Then** CLI、deployer、config 自动支持新 format，无需修改其他文件

### AC9: Backward Compatibility

- **Given** 现有 `pactkit init --format classic/opencode` 命令
- **When** 执行部署
- **Then** 输出目录结构与重构前完全一致

## Target Call Chain

```
pactkit init --format opencode
  → cli.py: format="opencode"
    → deployer.deploy(format="opencode")
      → profile = get_profile("opencode")
      → _deploy_standard(profile, config, target)
        → root = Path(profile.global_config_dir).expanduser()  # ~/.config/opencode
        → _deploy_agents(root / "agents", config, profile)
          → profile.agent_format → "md"
        → _deploy_skills(root / "skills", config, profile)
          → profile.skills_dir → "~/.config/opencode/skills"
        → _deploy_commands(root / "commands", config, profile)
          → profile.has_custom_commands → True
        → _deploy_rules(root / "rules", config, profile)
          → profile.rules_import_style → "instructions"
```

## Implementation Steps

| Step | File | Action | Risk |
|------|------|--------|------|
| 1 | `src/pactkit/profiles.py` (NEW) | 创建 FormatProfile dataclass + FORMAT_PROFILES + helpers | Low |
| 2 | `src/pactkit/config.py` | 导入 profiles，重写 PACTKIT_YAML_CANDIDATES 和 resolve_pactkit_yaml_dir() | Medium |
| 3 | `src/pactkit/generators/deployer.py` | 导入 profiles，重写 deploy() 和 _deploy_* 函数使用 profile | High |
| 4 | `src/pactkit/prompts/commands.py` | Playbook 改为 {SKILLS_PATH} 占位符，部署时替换 | Medium |
| 5 | `src/pactkit/skills/scaffold.py` | 添加注释指向 profiles.py 作为 source of truth | Low |
| 6 | `tests/unit/test_profiles.py` | FormatProfile 单元测试 | Low |
| 7 | `tests/unit/test_deployer_profiles.py` | Deployer 使用 profile 的集成测试 | Medium |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend code |
| SEC-5 | No | No auth code |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error handling changes |
| SEC-8 | No | No dependency changes |

## Deep Analysis Findings (补充)

> 基于 ENVIRONMENT_ANALYSIS.md (702 行) 的完整代码扫描结果。

### 发现 1: 三大反模式

| 反模式 | 位置 | 影响 | FormatProfile 如何解决 |
|--------|------|------|----------------------|
| **`opencode_format` boolean** | deployer.py 6+ 处 | 默认 False，忘传时静默产生错误格式 | 废除此参数，从 `profile.agent_format` 派生 |
| **`skills_prefix` 手动路由** | deployer.py 5+ 处 | 调用者必须手动选择正确的常量，不一致性风险 | 从 `profile.skills_dir` 自动获取 |
| **Prompt 模板硬编码路径** | 40+ 处（跨 6 个文件） | 新增 format 需要搜索修改 10+ 文件 | 统一使用 `{SKILLS_PATH}` 占位符，部署时替换 |

### 发现 2: Deployer 函数签名双重参数化

当前签名（`_deploy_agents`、`_deploy_commands`）同时接受 `skills_prefix` (string) 和 `opencode_format` (bool)，这两个参数实际上都是 format 的派生值，但没有一致性校验：

```python
# 当前：可以传 skills_prefix=OPENCODE 但 opencode_format=False → 静默产生混合格式
_deploy_agents(dir, agents, skills_prefix=OPENCODE_SKILLS_PREFIX, opencode_format=False)
```

FormatProfile 解决方案：函数签名改为接受 `profile: FormatProfile`，所有派生值从 profile 获取。

### 发现 3: CLAUDE_ONLY_FIELDS 不可扩展

```python
# deployer.py line 489，嵌入函数体内
CLAUDE_ONLY_FIELDS = {"permissionMode", "memory", "skills"}
```

需提升为 `FormatProfile` 的一个字段：`excluded_agent_fields: frozenset[str]`。

### 发现 4: 25+ Playbook 硬编码路径分布

| 命令 | 硬编码路径数 | 类型 |
|------|:---:|------|
| `/project-init` | 8+ | skill 脚本调用 |
| `/project-sprint` | ~5 | skill 脚本调用 |
| `/project-design` | ~5 | skill 脚本调用 |
| `/project-plan` | 2 | visualize + impact |
| `/project-done` | 1 | board archive |
| `/project-hotfix` | ~2 | scaffold |
| `/project-release` | 2 | release skill |
| **Total** | **~25** | |

### 发现 5: 环境检测逻辑分散

| 检测方式 | 位置 | 检测手段 |
|----------|------|----------|
| Config 搜索 | config.py | `.opencode/` > `.claude/` > `.codex/` 目录存在性 |
| Playbook 检测 | commands.py project-init | `~/.config/opencode/AGENTS.md` 存在 OR `which opencode` |
| Deployer 检测 | deployer.py | N/A — 完全依赖 `--format` 参数 |

需在 FormatProfile 中增加 `detection_markers: list[str]`，统一环境检测逻辑。

### 更新后的 FormatProfile 字段（完整版）

```python
@dataclass(frozen=True)
class FormatProfile:
    # Identity
    name: str
    display_name: str
    
    # Directory Structure
    global_config_dir: str
    project_config_dir: str
    skills_dir: str
    agents_dir: str
    commands_dir: str | None
    rules_dir: str | None
    
    # File Names
    project_instructions_file: str
    global_instructions_file: str
    pactkit_yaml_path: str
    
    # Format & Serialization
    agent_format: Literal["md", "toml"]
    rules_import_style: Literal["@import", "instructions", "inline"]
    excluded_agent_fields: frozenset[str]  # NEW: 替代 CLAUDE_ONLY_FIELDS
    
    # Capabilities
    has_custom_commands: bool
    supports_model_routing: bool
    supports_mcp: bool
    
    # Playbook Variables
    skills_path_var: str
    
    # Environment Detection
    detection_markers: tuple[str, ...]  # NEW: 统一环境检测
    detection_priority: int             # NEW: 搜索优先级（越小越优先）
```

### 更新后的实施步骤（含新发现）

| Step | File | Action | Risk | 发现来源 |
|------|------|--------|------|----------|
| 1 | `src/pactkit/profiles.py` (NEW) | 创建 FormatProfile + FORMAT_PROFILES + helpers | Low | — |
| 2 | `src/pactkit/config.py` | 从 profiles 自动生成 PACTKIT_YAML_CANDIDATES；重写 resolve 函数 | Medium | 发现 5 |
| 3 | `src/pactkit/generators/deployer.py` | 消除 `opencode_format` bool + `skills_prefix` 手动路由；函数签名改为 `profile` | **High** | 发现 1+2 |
| 4 | `src/pactkit/generators/deployer.py` | 提升 CLAUDE_ONLY_FIELDS 到 profile.excluded_agent_fields | Medium | 发现 3 |
| 5 | `src/pactkit/prompts/commands.py` | 所有 playbook 的 `~/.claude/skills/` 改为 `{SKILLS_PATH}` 占位符 | Medium | 发现 4 |
| 6 | `src/pactkit/prompts/skills.py` | 12+ 硬编码路径改为占位符 | Medium | 发现 4 |
| 7 | `src/pactkit/prompts/workflows.py` | 8+ 硬编码路径改为占位符 | Medium | 发现 4 |
| 8 | `src/pactkit/prompts/rules.py` | 7+ `@~/.claude/rules/` 改为动态引用 | Medium | 发现 4 |
| 9 | `src/pactkit/skills/scaffold.py` | 添加注释指向 profiles.py 作为 source of truth | Low | — |
| 10 | Tests | FormatProfile + deployer + playbook rewrite 测试（30-40 个新测试） | Medium | — |

## Out of Scope

- Codex CLI 的具体实现（那是 STORY-slim-002/003/004）
- plugin/marketplace 格式改造（保持现有实现）
- Playbook 内容优化（只做路径占位符替换，不改流程逻辑）
- 环境自动检测命令（如 `pactkit detect-env`）
