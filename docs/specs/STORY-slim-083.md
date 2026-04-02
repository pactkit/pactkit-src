# STORY-slim-083: Copilot deployer adapter package (pactkit-copilot)

| Field | Value |
|-------|-------|
| ID | STORY-slim-083 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.12 |

## Background

当前 `.github/` 下的 GitHub Copilot 格式文件（skills/、prompts/、agents/、copilot-instructions.md）是手动创建的静态文件，没有 deployer 适配包支持。运行 `pactkit update --format copilot` 会抛出 ValueError，因为 `_DEPLOYER_REGISTRY` 中没有注册 "copilot" 格式的 deployer。

现有的 opencode 和 codex 适配包（`pactkit-opencode`、`pactkit-codex`）已经建立了成熟的适配包模式：继承 `DeployerBase`，实现 `deploy()` 方法，通过 `entry_points` 自动注册到 `_DEPLOYER_REGISTRY`。需要创建 `pactkit-copilot` 适配包，遵循相同模式。

关键区别：Copilot 的部署目标是项目根目录下的 `.github/`（不是 HOME 目录 `~/.github/`），因为 GitHub Copilot 读取的是 repo 内的配置。FormatProfile 已在 `profiles.py` 中定义（line 176-196），`rules_import_style="inline"`（无 @include 支持）。

Phase 1 Trace 还发现 `deployer.py` 中 `_build_command_rules_header()` 通过 `profile.name` 硬编码分支而非使用 `profile.rules_import_style` 字段——新增 copilot 时需修复此逻辑以遵循 OCP。

## Requirements

### R1: CopilotDeployer class (MUST)

Create `CopilotDeployer` class inheriting `DeployerBase`, implementing `DeployerProtocol`. Set `profile = get_profile("copilot")`. Implement `deploy(config=None, target=None)` method that orchestrates skill, rule, agent, command, and project-instructions deployment to `.github/` under the project root (or `target` if specified).

### R2: Entry-point auto-registration (MUST)

Register `CopilotDeployer` via `entry_points` in `pyproject.toml`:
```
[project.entry-points."pactkit.deployers"]
copilot = "pactkit_copilot:CopilotDeployer"
```
After `pip install pactkit-copilot`, `pactkit update --format copilot` MUST work without any manual registration.

### R3: Deploy skills, rules, agents, commands (MUST)

- **Skills**: Deploy to `.github/skills/{skill_name}/SKILL.md` using `DeployerBase.deploy_skills()` with `_render_prompt()` for template variable substitution.
- **Agents**: Deploy to `.github/agents/{agent_name}.md` using `DeployerBase.deploy_agents()`, excluding fields in `profile.excluded_agent_fields`.
- **Commands (Prompts)**: Deploy to `.github/prompts/{command_name}.prompt.md` using `DeployerBase.deploy_commands()`. Rules header uses `rules_import_style="inline"` (full rules text inlined, not @import references).
- **Rules**: Deployed inline within commands (no separate `.github/rules/` files needed for copilot).

### R4: Project instructions file generation (MUST)

Generate `copilot-instructions.md` in `.github/` as the project-level instructions file. Content MUST be derived from `_generate_project_instructions()` (or equivalent), not hardcoded. This is the equivalent of `CLAUDE.md` for Claude Code or `instructions.md` for OpenCode.

### R5: Selective deployment (MUST)

Read `pactkit.yaml` (`exclude_skills`, `exclude_commands`) to support selective deployment. If a skill or command is in the exclude list, it MUST NOT be deployed.

### R6: Fix _build_command_rules_header OCP violation (SHOULD)

Refactor `_build_command_rules_header()` in `deployer.py` to dispatch on `profile.rules_import_style` instead of `profile.name`. Current code checks `profile.name == "opencode"` for inline style; adding copilot would require another hardcoded branch. The field `rules_import_style` already exists on FormatProfile and should be the canonical dispatch key.

## Acceptance Criteria

### AC1: CopilotDeployer is registered and discoverable (R1, R2)

- **Given** `pactkit-copilot` package is installed via `pip install`
- **When** `get_deployer("copilot")` is called
- **Then** returns a `CopilotDeployer` instance that satisfies `DeployerProtocol`

### AC2: pactkit update --format copilot deploys all artifacts (R1, R3)

- **Given** a project with `pactkit.yaml` at `.github/pactkit.yaml`
- **When** `pactkit update --format copilot` is executed
- **Then** skills are deployed to `.github/skills/{name}/SKILL.md`, agents to `.github/agents/{name}.md`, commands to `.github/prompts/{name}.prompt.md`, and project instructions to `.github/copilot-instructions.md`

### AC3: Skills deployment uses template rendering (R3)

- **Given** a skill template containing `{VISUALIZE_CMD}` placeholder
- **When** deployed via CopilotDeployer
- **Then** the placeholder is replaced with the copilot-specific path (using `_render_prompt()` with copilot profile)

### AC4: Commands use inline rules (R3, R6)

- **Given** a command template with `@rules` references
- **When** deployed via CopilotDeployer (where `rules_import_style="inline"`)
- **Then** the rules content is inlined directly into the command file (no `@` imports in output)

### AC5: Selective deployment respects exclude lists (R5)

- **Given** `pactkit.yaml` with `exclude_skills: [pactkit-draw]` and `exclude_commands: [project-sprint]`
- **When** `pactkit update --format copilot` is executed
- **Then** `pactkit-draw` skill and `project-sprint` command are NOT deployed; all other artifacts ARE deployed

### AC6: Project instructions file generated (R4)

- **Given** CopilotDeployer runs deploy
- **When** deployment completes
- **Then** `.github/copilot-instructions.md` exists and contains project context references (not hardcoded content)

### AC7: _build_command_rules_header dispatches on rules_import_style (R6)

- **Given** `deployer.py` `_build_command_rules_header()` function
- **When** called with a profile where `rules_import_style="inline"`
- **Then** returns inlined rules content (regardless of `profile.name` value — no name-based branching)

## Target Call Chain

```
CLI (pactkit update --format copilot)
  → cli.py: update_command(format="copilot")
    → deployer.py: deploy(format_name="copilot", config=config, target=target)
      → deploy_base.py: get_deployer("copilot")
        → _DEPLOYER_REGISTRY["copilot"] → CopilotDeployer
      → CopilotDeployer.deploy(config, target)
        → DeployerBase.deploy_skills(profile, config, target)
          → deployer.py: _deploy_skills(profile, config, target)
            → _render_prompt(template, profile) per skill
            → atomic_write(.github/skills/{name}/SKILL.md)
        → DeployerBase.deploy_agents(profile, config, target)
          → deployer.py: _deploy_agents(profile, config, target)
            → atomic_write(.github/agents/{name}.md)
        → DeployerBase.deploy_commands(profile, config, target)
          → deployer.py: _deploy_commands(profile, config, target)
            → _build_command_rules_header(profile)  [REFACTOR: use rules_import_style]
            → _render_prompt(template, profile) per command
            → atomic_write(.github/prompts/{name}.prompt.md)
        → _generate_project_instructions(profile, target)
          → atomic_write(.github/copilot-instructions.md)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `pactkit-copilot/pyproject.toml` | Create adapter package with entry_points registration | None | Low |
| 2 | `pactkit-copilot/src/pactkit_copilot/__init__.py` | Implement CopilotDeployer(DeployerBase) with deploy() | Step 1 | Medium |
| 3 | `src/pactkit/generators/deployer.py` | Refactor `_build_command_rules_header()` to dispatch on `rules_import_style` | None | Medium |
| 4 | `src/pactkit/generators/deployer.py` | Refactor `_generate_project_claude_md()` → generic `_generate_project_instructions()` | Step 3 | Medium |
| 5 | `pactkit-copilot/tests/` | Unit tests: registration, deploy smoke, selective deployment | Steps 1-4 | Low |
| 6 | `tests/unit/` | Core tests: `_build_command_rules_header` dispatch on `rules_import_style` | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code: new deployer class + refactored dispatch |
| SEC-2 | No | No user input handling — config read from pactkit.yaml |
| SEC-3 | No | No database patterns |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session (sec-scope false positive on "config" keyword) |
| SEC-6 | No | No API/route files |
| SEC-7 | Yes | Error handling: deployer must handle missing config, bad target paths |
| SEC-8 | Yes | New pyproject.toml for pactkit-copilot adapter package |

## Out of Scope

- CI/CD pipeline for pactkit-copilot (will be added in a separate STORY)
- Legacy cleanup for `.github/` (manual files remain until first `pactkit update --format copilot`)
- Hooks support (Copilot does not support hooks)
- `pactkit init --format copilot` changes (init already handles copilot profile via existing code paths)
- PyPI publishing of pactkit-copilot (separate release story)
