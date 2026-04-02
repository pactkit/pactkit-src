# STORY-003: Init Guard — project-plan / project-doctor 自动检测初始化状态

- **Author**: System Architect
- **Status**: Draft
- **Priority**: High
- **Release**: 1.0.0
- **Depends**: STORY-001, STORY-002

## Background

用户安装 PactKit 后经常忘记运行 `project-init` 就直接使用 `project-plan` 或 `project-doctor`，导致：
- `docs/specs/` 目录不存在，Spec 无法写入
- `docs/product/sprint_board.md` 不存在，Board 操作失败
- `docs/architecture/graphs/` 不存在，`visualize` 脚本报错
- `.claude/pactkit.yaml`（项目级）不存在，配置读取失败

## Target Call Chain

```
User runs /project-plan
  → Phase 0.5: Init Guard (NEW)
    → Check .claude/pactkit.yaml exists?
    → Check docs/product/sprint_board.md exists?
    → Check docs/architecture/graphs/ exists?
    → If ANY missing:
        → Print warning: "⚠️ Project not initialized. Running /project-init first..."
        → Execute /project-init steps
        → Resume original command
  → Phase 1: Archaeology (existing)
```

## Requirements

### R1: Init Guard for project-plan
- The `project-plan` command **MUST** include a new "Phase 0.5: Init Guard" between Phase 0 (Thinking) and Phase 1 (Archaeology).
- The guard **MUST** check for the existence of these three markers:
  1. `.claude/pactkit.yaml` (project-level config)
  2. `docs/product/sprint_board.md` (sprint board)
  3. `docs/architecture/graphs/` (architecture graph directory)
- If **any** marker is missing, the command **MUST** print a warning message and then execute the full `/project-init` flow before resuming `project-plan`.
- If **all** markers exist, the command **SHOULD** silently skip to Phase 1.

### R2: Init Guard for project-doctor
- The `project-doctor` command **MUST** include the same "Phase 0.5: Init Guard" with identical check logic.
- For `project-doctor`, the guard **MUST** offer the user a choice: auto-fix (run `/project-init`) or continue with diagnosis only.
- The rationale: Doctor is diagnostic — users may want to see the full health report even if uninitialized.

### R3: Implementation Scope
- Changes **MUST** be limited to the prompt templates in `src/pactkit/prompts/commands.py`.
- No Python runtime code changes are required — this is a prompt-only modification.
- The Init Guard text **MUST** be added to the `COMMANDS_CONTENT` dict entries for `project-plan.md` and `project-doctor.md`.

### R4: Idempotency
- The Init Guard **MUST NOT** cause issues if `project-init` has already been run.
- `project-init` is already idempotent (`mkdir -p`, `if missing` checks), so re-execution is safe.

## Acceptance Criteria

### Scenario 1: project-plan on uninitialized project
```gherkin
Given a project directory without .claude/pactkit.yaml
When the user runs /project-plan "Add feature X"
Then the command MUST print "⚠️ Project not initialized."
And the command MUST execute /project-init steps automatically
And the command MUST then proceed with normal Plan phases
```

### Scenario 2: project-plan on initialized project
```gherkin
Given a project directory with .claude/pactkit.yaml, docs/product/sprint_board.md, and docs/architecture/graphs/
When the user runs /project-plan "Add feature X"
Then the Init Guard MUST pass silently
And the command MUST proceed directly to Phase 1
```

### Scenario 3: project-doctor on uninitialized project
```gherkin
Given a project directory without docs/architecture/graphs/
When the user runs /project-doctor
Then the command MUST detect the missing markers
And the command MUST offer the user a choice: "Auto-fix with /project-init" or "Continue diagnosis"
```

### Scenario 4: Partially initialized project
```gherkin
Given a project directory with .claude/pactkit.yaml but missing docs/product/sprint_board.md
When the user runs /project-plan "Add feature X"
Then the Init Guard MUST detect the missing marker
And the command MUST execute /project-init to repair the incomplete state
```

## Files to Modify

| File | Change |
|------|--------|
| `src/pactkit/prompts/commands.py` | Add Phase 0.5 Init Guard to `project-plan.md` entry |
| `src/pactkit/prompts/commands.py` | Add Phase 0.5 Init Guard to `project-doctor.md` entry |
| `tests/unit/test_commands_content.py` | Verify Init Guard text is present in both command templates |
