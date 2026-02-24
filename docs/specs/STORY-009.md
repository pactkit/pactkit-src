# STORY-009: Config Auto-Merge — pactkit init 自动合并新组件

- **Priority**: 5 (Impact 5 / Effort 2)
- **Agent**: Senior Developer
- **Release**: 1.1.0
- **Depends on**: STORY-001 (config schema)

## Background

`pactkit init` 首次运行时生成 `~/.claude/pactkit.yaml`，包含当时所有已知组件。但当 PactKit 升级（新增命令/agent/skill/rule）后，用户的 yaml 仍是旧版列表。

当前行为：`load_config()` 中 `merged[key] = value` 直接用用户列表覆盖默认值——如果用户的 yaml 没有 `project-status`，部署时就跳过它。

用户需要手动编辑 `pactkit.yaml` 加入新组件，这违反了 "零配置升级" 的原则。

### 影响

STORY-007 新增了 `project-status` 命令，但所有现有用户执行 `pactkit init` 后不会部署该命令，直到手动编辑 yaml。

## Requirements

### R1: Auto-merge new components on init (MUST)
当 `pactkit init` 检测到 `pactkit.yaml` 已存在时，MUST 自动将新增的组件追加到用户列表中。

规则：
- 如果用户 yaml 的某个列表（如 commands）包含的全是合法值（全部在 `VALID_*` 中），则认为用户**没有做过裁剪**，应该用默认全量列表替换
- 如果用户 yaml 的某个列表是 `VALID_*` 的严格子集（即用户主动删除了某些组件），则只追加**新增**的组件（不在旧版默认中的）
- "新增" 的判断：在 `VALID_*` 中存在，但不在用户列表中，且不在上一个已知版本的默认列表中

### R2: Simpler approach — append missing (SHOULD)
更简单的实现方案（推荐）：
- 对于列表类型的配置项（agents, commands, skills, rules），将 `VALID_*` 中存在但用户列表中缺失的项自动追加
- 输出提示：`"  -> Auto-added: project-status (new in this version)"`
- 用户如果不想要某个组件，可以手动从 yaml 中删除——下次 init 不会再加回来

### R3: Opt-out persistence (MUST)
如果用户**主动删除**了某个组件（如从 yaml 中移除 `project-sprint`），`pactkit init` MUST NOT 在下次运行时把它加回来。

实现方式：在 yaml 中增加 `exclude` 字段，或用注释标记，或记录 "已知版本"。

### R4: Version tracking (SHOULD)
`pactkit.yaml` SHOULD 记录生成时的 PactKit 版本（或组件签名），用于判断哪些组件是 "新增的"。

### R5: Backward compatibility (MUST)
- 现有的 `pactkit.yaml`（没有版本标记）MUST 仍然正常工作
- 不能破坏 "用户裁剪了列表" 的场景

## Acceptance Criteria

### Scenario 1: Fresh install (no yaml)
**Given** `~/.claude/pactkit.yaml` does not exist
**When** user runs `pactkit init`
**Then** yaml is generated with all components from `VALID_*` sets (current behavior, unchanged)

### Scenario 2: Upgrade with new component
**Given** existing yaml with 13 commands (no `project-status`)
**When** PactKit is upgraded (source now has 14 commands) and user runs `pactkit init`
**Then** `project-status` is auto-added to the yaml and deployed, with output: `"  -> Auto-added: project-status"`

### Scenario 3: User intentionally excluded a component
**Given** user has manually removed `project-sprint` from yaml commands list
**When** user runs `pactkit init`
**Then** `project-sprint` is NOT re-added (respects user opt-out)

### Scenario 4: Multiple new components
**Given** existing yaml missing both `project-status` and a hypothetical future `project-foo`
**When** user runs `pactkit init`
**Then** both are auto-added, each with a log line

## Implementation Notes

1. Target file: `src/pactkit/config.py` — modify `load_config()` merge logic
2. May need to store a "known components at generation time" in the yaml
3. The simplest R3-compliant approach: add an `exclude:` section to yaml
4. Alternative R3 approach: store the PactKit version in yaml, diff component sets between versions

## Target Call Chain

```
cli.main()
  → config.load_config(path)
    → yaml.safe_load() + merge logic  ← CHANGE HERE
  → deployer.deploy(config=merged_config)
```
