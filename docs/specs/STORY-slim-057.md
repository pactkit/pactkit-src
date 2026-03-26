# STORY-slim-057: Refactor deployer.py: extract DeployerProtocol and DeployerBase

| Field | Value |
|-------|-------|
| ID | STORY-slim-057 |
| Status | Done |
| Priority | P1 |
| Release | v2.6.0 |

## Background

`deployer.py` (1685 lines) is the deployment orchestrator for PactKit. It currently uses a monolithic if-elif dispatch in `deploy()` (line 160) to route to format-specific deployers: `_deploy_classic()`, `_deploy_opencode()`, `_deploy_plugin()`. Each format-specific deployer duplicates ~80% of its logic (calling `_deploy_skills`, `_deploy_rules`, `_deploy_agents`, `_deploy_commands`, `_deploy_ci` in sequence). OpenCode has 6 additional functions that are irrelevant to Classic/Plugin modes.

This monolithic structure creates two problems:
1. **Cannot extract adapters**: pactkit-opencode cannot be a separate package because shared deployment logic is tangled with format-specific logic in a single file
2. **Dead code accumulation**: The codex profile (profiles.py line 149-168) and its branches in deployer.py are dead code since Codex was moved to a separate project

This story extracts a `DeployerProtocol` (interface) and `DeployerBase` (shared logic) so that format-specific deployers can be implemented as standalone classes — enabling STORY-slim-058 (extract pactkit-opencode) and STORY-slim-059 (remove dead codex code).

## Requirements

### R1: DeployerProtocol Interface (MUST)

Define a `DeployerProtocol` (typing.Protocol) in a new `src/pactkit/generators/deploy_base.py` with the following contract:
- `deploy(config, target) -> None` — top-level entry point
- `profile: FormatProfile` — the format profile this deployer handles
Each concrete deployer class MUST implement this protocol.

### R2: DeployerBase (MUST)

Extract the following shared functions from `deployer.py` into `DeployerBase` in `deploy_base.py`:
- `_deploy_skills()` (line 445, 110 lines)
- `_deploy_rules()` (line 555, 58 lines)
- `_deploy_agents()` (line 613, 192 lines)
- `_deploy_commands()` (line 805, 67 lines)
- `_deploy_ci()` (line 1045, 243 lines)
- `_render_prompt()` (line 40, 112 lines)
- `_generate_project_instructions()` — consolidated from `_generate_project_claude_md()` (line 1288) and `_generate_project_agents_md()` (line 332)

All shared methods MUST accept a `profile: FormatProfile` parameter (already the case for most).

### R3: ClassicDeployer (MUST)

Refactor `_deploy_classic()` (line 190, 93 lines) into a `ClassicDeployer` class that:
- Inherits `DeployerBase`
- Implements `DeployerProtocol`
- Lives in `deployer.py` (stays in core package)
- Preserves all current Classic behavior (MCP recommendations, plugin JSON, etc.)

### R4: deploy() Dispatch Refactored (MUST)

The top-level `deploy()` function (line 160) MUST use a registry pattern instead of if-elif:
- `_DEPLOYER_REGISTRY: dict[str, type[DeployerProtocol]]` mapping format names to deployer classes
- External packages (pactkit-opencode) can register their deployer via `register_deployer(format, cls)`
- Fallback: if format not in registry, raise `ValueError` with helpful message

### R5: Backward Compatibility (MUST)

All existing tests in `tests/` MUST pass without modification. The public API (`deploy(format=, config=, target=)`) MUST remain identical. No changes to CLI entry points.

### R6: PluginDeployer (SHOULD)

Refactor `_deploy_plugin()` (line 283, 49 lines) into a `PluginDeployer` class. Lower priority since plugin mode is simpler.

## Acceptance Criteria

### AC1: DeployerProtocol is importable and type-checkable (R1)

- **Given** `deploy_base.py` exists in `src/pactkit/generators/`
- **When** `from pactkit.generators.deploy_base import DeployerProtocol, DeployerBase` is executed
- **Then** both symbols import successfully; `ClassicDeployer` satisfies `isinstance` check against Protocol

### AC2: DeployerBase methods produce identical output (R2)

- **Given** a test project with `pactkit.yaml` configured for `classic` format
- **When** `pactkit init --format classic` is run using the refactored deployer
- **Then** all deployed files (skills, rules, agents, commands, CI, CLAUDE.md) are byte-identical to pre-refactor output

### AC3: ClassicDeployer handles all Classic-specific logic (R3)

- **Given** `ClassicDeployer` is registered for format `classic`
- **When** `deploy(format="classic")` is called
- **Then** Classic-specific functions execute: `_generate_project_claude_md`, `_deploy_plugin_json`, `_print_mcp_recommendations`

### AC4: Registry dispatch replaces if-elif (R4)

- **Given** `_DEPLOYER_REGISTRY` contains `{"classic": ClassicDeployer}`
- **When** `deploy(format="opencode")` is called without opencode registered
- **Then** a `ValueError` is raised with message containing "opencode" and "pip install pactkit-opencode"

### AC5: External deployer registration works (R4)

- **Given** a mock `OpenCodeDeployer` class implementing `DeployerProtocol`
- **When** `register_deployer("opencode", OpenCodeDeployer)` is called
- **Then** subsequent `deploy(format="opencode")` dispatches to that class

### AC6: PluginDeployer class exists (R6)

- **Given** refactored `deployer.py`
- **When** `from pactkit.generators.deployer import PluginDeployer` is executed
- **Then** import succeeds and `PluginDeployer` implements `DeployerProtocol`

### AC7: All existing tests pass (R5)

- **Given** the full test suite (`tests/unit/`, `tests/e2e/`)
- **When** `pytest tests/ -v` is run
- **Then** all 3326+ tests pass with 0 failures

## Target Call Chain

```
cli.py: main()
  → deployer.py: deploy(format="classic", config=..., target=...)
    → _DEPLOYER_REGISTRY["classic"]  →  ClassicDeployer.deploy(config, target)
      → DeployerBase._deploy_skills(skills_dir, enabled_skills, profile)
      → DeployerBase._deploy_rules(claude_root, enabled_rules)
      → DeployerBase._deploy_agents(agents_dir, enabled_agents, profile)
      → DeployerBase._deploy_commands(commands_dir, enabled_commands, profile)
      → DeployerBase._deploy_ci(provider, project_root, config)
      → ClassicDeployer._generate_project_claude_md(config)
      → ClassicDeployer._deploy_plugin_json(plugin_meta_dir)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/generators/deploy_base.py` | Create `DeployerProtocol` (Protocol class) and `DeployerBase` with `_render_prompt`, `_deploy_skills`, `_deploy_rules`, `_deploy_agents`, `_deploy_commands`, `_deploy_ci` | None | Medium — must preserve all parameter signatures |
| 2 | `src/pactkit/generators/deploy_base.py` | Add `register_deployer()` function and `_DEPLOYER_REGISTRY` dict | Step 1 | Low |
| 3 | `src/pactkit/generators/deployer.py` | Create `ClassicDeployer(DeployerBase)` wrapping `_deploy_classic` logic; register in `_DEPLOYER_REGISTRY` | Steps 1-2 | Medium — most complex refactor |
| 4 | `src/pactkit/generators/deployer.py` | Create `PluginDeployer(DeployerBase)` wrapping `_deploy_plugin` logic | Steps 1-2 | Low |
| 5 | `src/pactkit/generators/deployer.py` | Refactor `deploy()` to use `_DEPLOYER_REGISTRY` dispatch; keep plugin/marketplace special cases | Steps 3-4 | High — public API must not break |
| 6 | `tests/unit/test_deploy_base.py` | Test Protocol compliance, registry, DeployerBase methods | Steps 1-5 | Low |
| 7 | `tests/` | Run full regression suite | Step 6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | Internal refactoring, no new user input |
| SEC-2 Authentication | N/A | No auth changes |
| SEC-3 Path Traversal | N/A | All file paths already use `atomic_write()` — no new write paths |
| SEC-4 Injection | N/A | No new template rendering; `_render_prompt` uses sequential `str.replace()` |
| SEC-5 Secrets | N/A | No credential handling changes |
| SEC-6 Dependencies | N/A | No new external dependencies |
| SEC-7 Config Safety | Low | `register_deployer()` accepts arbitrary classes — but only called at import time by trusted packages |
| SEC-8 Data Exposure | N/A | No new data flows |

## Adapter Compatibility Strategy

### 自动传递（无需通知下游 adapter）
新增/删除 command、skill、rule、agent — adapter 不用改。`DeployerBase._deploy_commands()` 等方法遍历 `VALID_COMMANDS` 集合，adapter 继承后自动获得最新逻辑。用户 `pip install --upgrade pactkit` 即可。

### 需要协调的变更（破坏性）
| 变更类型 | 影响 | 防护 |
|---------|------|------|
| DeployerBase 方法签名变化 | adapter 调用报错 | SemVer major bump + CI 交叉测试 |
| FormatProfile 新增必填字段 | adapter profile 缺值 | SemVer minor bump + 默认值兜底 |
| DeployerProtocol 新增方法 | adapter 缺方法 | import-time TypeError |

### 三道防线
1. **语义化版本**: adapter 声明 `pactkit >= 2.6.0, < 3.0.0`，破坏性变更 bump major，pip 自动拦截
2. **Import-time 检查**: adapter 被 import 时即调用 DeployerBase 方法，签名不匹配立即报错
3. **Core CI 交叉测试**: core 发版前自动 `pip install pactkit-opencode` 并运行兼容性测试

## Out of Scope

- Extracting OpenCode deployer to separate package (STORY-slim-058)
- Removing codex dead code (STORY-slim-059)
- Changing any prompt template content
- Adding new deployment formats
- Modifying FormatProfile fields
