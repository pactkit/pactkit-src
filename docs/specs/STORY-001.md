# STORY-001: Config Schema — pactkit.yaml 加载、验证、默认值

- **Author**: System Architect
- **Status**: Draft
- **Priority**: 5 (Impact 5 / Effort 2)
- **Release**: 1.0.0

## Background

PactKit 已发布至 PyPI 并开源到 GitHub。当前 `pactkit init` 硬编码部署全部组件（9 agents + 13 commands + 3 skills + 6 rules），用户没有自由度。需要引入 `pactkit.yaml` 作为用户定制入口，让用户选择性启用/禁用组件。

此外，`--mode common` 及 `common_user.py` 将被移除，统一由 config 机制替代。

## Target Call Chain

```
cli.main()
  → config.load_config(path)         # NEW: 加载 pactkit.yaml
    → config.validate_config(data)    # NEW: 验证 schema
    → config.get_default_config()     # NEW: 生成默认值
  → deployer.deploy(config)           # MODIFIED: 接收 config 参数
```

## Requirements

### R1: Config Module (`src/pactkit/config.py`)
- **MUST** create a new `config.py` module with `load_config()`, `validate_config()`, `get_default_config()`, `generate_default_yaml()` functions.
- **MUST** define the full list of valid agent, command, skill, and rule identifiers as constants.

### R2: Default Config
- **MUST** return a default config where all components are enabled when no `pactkit.yaml` exists (backward compatible).
- Default config schema:

```yaml
version: 0.0.1
stack: auto
root: .

agents:
  - system-architect
  - senior-developer
  - qa-engineer
  - repo-maintainer
  - system-medic
  - security-auditor
  - visual-architect
  - code-explorer
  - product-designer

commands:
  - project-plan
  - project-act
  - project-check
  - project-done
  - project-init
  - project-doctor
  - project-draw
  - project-trace
  - project-sprint
  - project-review
  - project-hotfix
  - project-design
  - project-release

skills:
  - pactkit-visualize
  - pactkit-board
  - pactkit-scaffold

rules:
  - 01-core-protocol
  - 02-hierarchy-of-truth
  - 03-file-atlas
  - 04-routing-table
  - 05-workflow-conventions
  - 06-mcp-integration
```

### R3: Config Loading
- **MUST** accept an optional `path` parameter; if not provided, use `~/.claude/pactkit.yaml`.
- **MUST** return the default config if the file does not exist (no error).
- **MUST** parse YAML using `pyyaml` (add as dependency to `pyproject.toml`).
- **MUST** merge user config with defaults — missing keys inherit defaults.

### R4: Config Validation
- **MUST** warn (not error) if user config contains unknown agent/command/skill/rule names.
- **MUST** validate that `version` is a string, `stack` is one of `auto|python|node|go|java`, `root` is a string.
- **SHOULD** validate that lists contain only strings.

### R5: YAML Generation
- **MUST** provide a `generate_default_yaml()` function that returns the default config as a YAML string with comments.
- The generated YAML **SHOULD** include comment annotations explaining each section.

### R6: Remove Common Mode
- **MUST** delete `src/pactkit/common_user.py`.
- **MUST** delete `tests/unit/test_common_user.py`.
- **MUST** remove `--mode` argument from `cli.py` `init` and `update` subparsers.
- **MUST** remove the `common_user` import and branch from `cli.py`.

## Acceptance Criteria

### S1: Default config when no YAML exists
```
Given no pactkit.yaml file exists
When load_config() is called
Then it returns a dict with all agents, commands, skills, and rules enabled
```

### S2: Partial config merges with defaults
```
Given a pactkit.yaml with only "agents: [system-architect, senior-developer]"
When load_config() is called
Then agents = [system-architect, senior-developer]
And commands = full default list
And skills = full default list
And rules = full default list
```

### S3: Unknown name produces warning
```
Given a pactkit.yaml with "agents: [unknown-agent]"
When validate_config() is called
Then a warning is printed: "Unknown agent: unknown-agent"
And the function does not raise an exception
```

### S4: generate_default_yaml produces valid YAML
```
Given generate_default_yaml() is called
When the returned string is parsed by yaml.safe_load()
Then the result equals get_default_config()
```

### S5: Common mode fully removed
```
Given the source tree after STORY-001 implementation
When searching for "common_user" or "--mode common"
Then no references exist in src/ or tests/
```

### S6: CLI accepts init without --mode
```
Given the updated CLI
When running "pactkit init"
Then it deploys using the default (full) config
And the --mode flag is not recognized
```
