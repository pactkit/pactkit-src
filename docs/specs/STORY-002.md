# STORY-002: Selective Deployment — Deployer 按 Config 过滤部署

- **Author**: System Architect
- **Status**: Draft
- **Priority**: 5 (Impact 5 / Effort 3)
- **Release**: 1.0.0
- **Depends**: STORY-001

## Background

STORY-001 引入了 `pactkit.yaml` config schema 和加载机制。本 Story 将 deployer 改造为读取 config 并选择性部署组件，使用户可以通过编辑 `pactkit.yaml` 来定制自己的 PDCA 工具集。

## Target Call Chain

```
cli.main()
  → config.load_config()                    # STORY-001
  → deployer.deploy(config)                 # MODIFIED: 接收 config
    → deployer._deploy_skills(config)       # MODIFIED: 按 config.skills 过滤
    → deployer._deploy_rules(config)        # MODIFIED: 按 config.rules 过滤
    → deployer._deploy_expert(config)       # MODIFIED: 按 config.agents/commands 过滤
      → deployer._deploy_agents(config)     # EXTRACT: 从 _deploy_expert 拆出
      → deployer._deploy_commands(config)   # EXTRACT: 从 _deploy_expert 拆出
    → config.generate_default_yaml()        # 生成 pactkit.yaml 到 target
```

## Requirements

### R1: Deployer 接受 Config 参数
- **MUST** modify `deploy()` signature to accept a `config: dict` parameter.
- **MUST** load config from `pactkit.yaml` in the target directory if no config is passed (backward compatible).
- **MUST** fall back to `get_default_config()` if no config exists anywhere.

### R2: Selective Agent Deployment
- **MUST** only deploy agents listed in `config['agents']`.
- **MUST** clean up previously managed agent files that are no longer in the config list.
- **SHOULD** preserve user-custom agent files (files not in `AGENTS_EXPERT` registry).

### R3: Selective Command Deployment
- **MUST** only deploy commands listed in `config['commands']`.
- **MUST** map config command names to filenames (e.g., `project-plan` → `project-plan.md`).
- **MUST** clean up previously managed command files not in the config list.

### R4: Selective Skill Deployment
- **MUST** only deploy skills listed in `config['skills']`.
- **MUST** skip skills not in the config list entirely (no directory creation).

### R5: Selective Rule Deployment
- **MUST** only deploy rules listed in `config['rules']`.
- **MUST** update `CLAUDE.md` template to only `@import` the enabled rules.
- **SHOULD** preserve user-custom rule files (files without managed prefixes).

### R6: Config File Generation on Init
- **MUST** generate `pactkit.yaml` in the target directory during `pactkit init` if it doesn't exist.
- **MUST** use `generate_default_yaml()` from STORY-001 to create the file.
- **MUST NOT** overwrite an existing `pactkit.yaml` (preserve user customization).

### R7: CLI Integration
- **MUST** modify `cli.py` to load config and pass it to `deploy()`.
- **MUST** support the `-t` / `--target` flag for custom deployment target.
- **SHOULD** print a summary of enabled/disabled components after deployment.

### R8: Deployment Summary
- **MUST** print a summary showing what was deployed:
  ```
  ✅ Deployed: 5/9 Agents, 8/13 Commands, 3/3 Skills, 6/6 Rules
  ```
- **SHOULD** list disabled components when not deploying the full set.

## Acceptance Criteria

### S1: Full config deploys everything
```
Given a pactkit.yaml with all components enabled (default)
When pactkit init is executed
Then all 9 agents, 13 commands, 3 skills, 6 rules are deployed
And the output matches current behavior
```

### S2: Partial agent config
```
Given a pactkit.yaml with agents: [system-architect, senior-developer]
When pactkit init is executed
Then only system-architect.md and senior-developer.md exist in agents/
And no other agent .md files exist in agents/
```

### S3: Partial command config
```
Given a pactkit.yaml with commands: [project-plan, project-act, project-done]
When pactkit init is executed
Then only project-plan.md, project-act.md, project-done.md exist in commands/
```

### S4: CLAUDE.md reflects enabled rules only
```
Given a pactkit.yaml with rules: [01-core-protocol, 05-workflow-conventions]
When pactkit init is executed
Then CLAUDE.md contains @import for 01-core-protocol.md and 05-workflow-conventions.md
And CLAUDE.md does NOT contain @import for other rule files
```

### S5: Idempotent re-deploy preserves user config
```
Given pactkit.yaml exists with custom settings
When pactkit update is executed
Then pactkit.yaml is NOT overwritten
And deployment uses the existing config
```

### S6: Config file auto-generated on first init
```
Given no pactkit.yaml in the target directory
When pactkit init is executed
Then pactkit.yaml is created with full default config
And all components are deployed
```

### S7: Deployment summary is printed
```
Given a partial config with 5 agents and 8 commands enabled
When pactkit init is executed
Then output contains "Deployed: 5/9 Agents, 8/13 Commands, 3/3 Skills, 6/6 Rules"
```

### S8: Custom target directory works
```
Given the -t /tmp/preview flag is passed
When pactkit init -t /tmp/preview is executed
Then all files are deployed to /tmp/preview/
And pactkit.yaml is created at /tmp/preview/pactkit.yaml
```
