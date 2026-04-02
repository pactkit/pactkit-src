# STORY-005: Plugin Distribution — 支持 Claude Code Plugin 格式分发

- **Author**: System Architect
- **Status**: Draft
- **Priority**: High
- **Release**: 1.1.0
- **Depends**: None

## Background

PactKit 当前仅通过 `pip install pactkit && pactkit init` 部署，将文件写入 `~/.claude/`。Claude Code 已推出 Plugin 生态系统，支持通过 `/plugin marketplace add` + `/plugin install` 一键安装插件。

Plugin 格式在以下方面优于 pip 模式：

| 维度 | pip 模式 | plugin 模式 |
|------|---------|------------|
| 安装 | `pip install` + `pactkit init` 两步 | `/plugin install` 一步 |
| 更新 | `pip install -U` + `pactkit update` | marketplace 自动更新 |
| 卸载 | 手动清理 `~/.claude/` 下散落文件 | `/plugin uninstall` 干净移除 |
| 团队协作 | 每人手动安装 | `.claude/settings.json` 声明后团队自动提示 |
| 隔离性 | 文件散落在全局 `~/.claude/` | plugin cache 目录隔离 |

两种分发方式并存：pip 适合需要 `pactkit.yaml` 精细配置的高级用户，plugin 适合开箱即用的快速上手场景。

## Target Architecture

### Plugin 目录结构

```
pactkit-plugin/                        # 自包含 plugin root
├── .claude-plugin/
│   └── plugin.json                    # 插件清单 (name, version, description...)
├── CLAUDE.md                          # 内联所有 rules 的 constitution (不用 @import)
├── agents/
│   ├── system-architect.md
│   ├── senior-developer.md
│   ├── qa-engineer.md
│   ├── repo-maintainer.md
│   ├── system-medic.md
│   ├── security-auditor.md
│   ├── visual-architect.md
│   ├── code-explorer.md
│   └── product-designer.md
├── commands/
│   ├── project-plan.md
│   ├── project-act.md
│   ├── project-check.md
│   ├── project-done.md
│   ├── project-init.md
│   ├── project-doctor.md
│   ├── project-draw.md
│   ├── project-trace.md
│   ├── project-sprint.md
│   ├── project-review.md
│   ├── project-hotfix.md
│   ├── project-design.md
│   └── project-release.md
└── skills/
    ├── pactkit-visualize/
    │   ├── SKILL.md
    │   └── scripts/visualize.py
    ├── pactkit-board/
    │   ├── SKILL.md
    │   └── scripts/board.py
    └── pactkit-scaffold/
        ├── SKILL.md
        └── scripts/scaffold.py
```

### Target Call Chain

```
CLI: pactkit init --format plugin -t dist/
  → cli.py: main()
    → deployer.py: deploy(format="plugin", target="dist/")
      → _deploy_plugin_json(plugin_root)        # 新增: 生成 .claude-plugin/plugin.json
      → _deploy_claude_md_inline(plugin_root)    # 新增: 内联所有 rules 到 CLAUDE.md
      → _deploy_agents(agents_dir, ...)          # 复用现有逻辑
      → _deploy_commands(commands_dir, ...)       # 复用现有逻辑
      → _deploy_skills(skills_dir, ...)           # 复用现有逻辑
```

## Requirements

### R1: CLI 新增 `--format` 参数
- **MUST** 在 `pactkit init` 命令增加 `--format` 参数，接受 `classic` 和 `plugin` 两个值
- **MUST** `--format classic` 为默认值，行为与当前完全一致
- **MUST** `--format plugin` 生成自包含的 plugin 目录结构
- **MUST** `--format plugin` 默认输出目录为 `./pactkit-plugin/`（可通过 `-t` 覆盖）

### R2: plugin.json 清单生成
- **MUST** 在 `.claude-plugin/plugin.json` 中包含 `name`、`version`、`description` 字段
- **MUST** `version` 与 `pyproject.toml` 中的版本保持同步（从 `importlib.metadata` 读取）
- **SHOULD** 包含 `author`、`homepage`、`repository`、`license`、`keywords` 字段

### R3: CLAUDE.md 内联模式
- **MUST** 在 plugin 模式下，将所有 rules 模块的内容内联到 CLAUDE.md 中（不使用 `@import`）
- **MUST** 保持 constitution 标题和模块分隔，便于阅读
- **MUST NOT** 引用 `~/.claude/` 路径（plugin 是自包含的）

### R4: 组件全量部署
- **MUST** plugin 模式下部署全部 agents、commands、skills（不受 `pactkit.yaml` 过滤）
- **MAY** 未来支持通过 CLI 参数选择性排除组件

### R5: marketplace.json 生成
- **MUST** 提供 `pactkit init --format marketplace -t dist/` 命令，生成包含 `marketplace.json` 的 marketplace 仓库结构
- **MUST** `marketplace.json` 包含 `name`、`owner`、`plugins` 字段，符合 Claude Code 规范
- **MUST** `plugins[0].source` 指向 plugin 子目录的相对路径

### R6: 保持 pip 模式完全兼容
- **MUST NOT** 修改 `--format classic`（默认模式）的任何行为
- **MUST** 所有现有测试继续通过
- **MUST** `pactkit init`（无 `--format`）的行为与改动前完全一致

## Acceptance Criteria

### Scenario 1: Plugin 目录生成
```gherkin
Given the user runs `pactkit init --format plugin -t /tmp/pactkit-plugin`
When the command completes
Then /tmp/pactkit-plugin/.claude-plugin/plugin.json MUST exist
And /tmp/pactkit-plugin/CLAUDE.md MUST exist and contain inline rule content (no @import)
And /tmp/pactkit-plugin/agents/ MUST contain 9 agent markdown files
And /tmp/pactkit-plugin/commands/ MUST contain 13 command markdown files
And /tmp/pactkit-plugin/skills/ MUST contain 3 skill directories each with SKILL.md and scripts/
```

### Scenario 2: plugin.json 内容正确
```gherkin
Given the generated plugin.json
When parsed as JSON
Then field "name" MUST equal "pactkit"
And field "version" MUST match the installed pactkit package version
And field "description" MUST be a non-empty string
And field "license" MUST equal "MIT"
```

### Scenario 3: CLAUDE.md 自包含
```gherkin
Given the generated CLAUDE.md in plugin mode
When the content is inspected
Then it MUST NOT contain any "@~/.claude/" references
And it MUST contain the full text of "Core Protocol" section
And it MUST contain the full text of "Hierarchy of Truth" section
And it MUST contain the full text of all enabled rule modules
```

### Scenario 4: Classic 模式不受影响
```gherkin
Given the user runs `pactkit init -t /tmp/classic`
When the command completes
Then /tmp/classic/CLAUDE.md MUST contain @~/.claude/rules/ import lines
And /tmp/classic/rules/ MUST contain individual rule markdown files
And no .claude-plugin/ directory MUST exist in /tmp/classic/
```

### Scenario 5: Marketplace 仓库生成
```gherkin
Given the user runs `pactkit init --format marketplace -t /tmp/pactkit-marketplace`
When the command completes
Then /tmp/pactkit-marketplace/marketplace.json MUST exist
And /tmp/pactkit-marketplace/pactkit-plugin/ MUST be a valid plugin directory
And marketplace.json plugins[0].source MUST equal "./pactkit-plugin"
```

### Scenario 6: Plugin 可被 Claude Code 加载
```gherkin
Given the generated plugin directory
When the user runs `claude --plugin-dir ./pactkit-plugin`
Then Claude Code MUST load without plugin errors
And `/plugin` Errors tab MUST show no errors for pactkit
And all pactkit skills MUST be available via /pactkit:pactkit-visualize etc.
```

## Files to Modify

| File | Change |
|------|--------|
| `src/pactkit/cli.py` | 新增 `--format` 参数 (`classic` / `plugin` / `marketplace`) |
| `src/pactkit/generators/deployer.py` | 新增 `_deploy_plugin_json()`, `_deploy_claude_md_inline()`, `_deploy_marketplace_json()`, `deploy()` 增加 format 分支 |
| `tests/unit/test_deployer.py` | 新增 plugin 模式和 marketplace 模式测试 |
| `tests/unit/test_cli.py` | 新增 `--format` 参数解析测试 |

## Design Notes

1. **复用优先**: `_deploy_agents()`, `_deploy_commands()`, `_deploy_skills()` 不需要修改，只需传入不同的 target 目录
2. **Config 忽略**: plugin 模式忽略 `pactkit.yaml`，始终全量部署。这是刻意设计——plugin 用户期望开箱即用
3. **版本同步**: `plugin.json` 的 version 从 `importlib.metadata.version("pactkit")` 读取，确保与 PyPI 发布版本一致
4. **无 hooks**: 本次不引入 `hooks/hooks.json`，留给后续 Story 扩展
