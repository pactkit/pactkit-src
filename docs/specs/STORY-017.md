# STORY-017: project-init 自动生成项目级 CLAUDE.md

| Field     | Value |
|-----------|-------|
| ID        | STORY-017 |
| Title     | project-init 自动生成项目级 CLAUDE.md |
| Status    | In Progress |
| Priority  | Medium |
| Release   | 1.1.3 |

## Background

`$PROJECT_ROOT/.claude/CLAUDE.md` 是 Claude Code 的项目级指令文件，用于提供项目特定的上下文信息（架构概览、dev commands 等）。目前该文件需要手动创建，`/project-init` 命令不会自动生成它。

全局 `~/.claude/CLAUDE.md` 由 deployer 自动生成（包含 `@import` 规则引用），而项目级 CLAUDE.md 是独立的、项目特定的，二者不冲突。

## Requirements

1. **MUST**: `project-init` 命令 MUST 在 Phase 1 中自动生成 `$PROJECT_ROOT/.claude/CLAUDE.md`（如果不存在）。
2. **MUST**: 生成的内容 MUST 包含项目名称、检测到的 stack/language 信息。
3. **MUST**: 生成的内容 MUST 包含 `@./docs/product/context.md` 引用以启用跨会话上下文。
4. **MUST**: 生成的内容 MUST 包含基于 `LANG_PROFILES` 的 dev commands（test runner、lint command）。
5. **MUST NOT**: 如果 `$PROJECT_ROOT/.claude/CLAUDE.md` 已存在，MUST NOT 覆盖。
6. **SHOULD**: 内容 SHOULD 保持简洁，以指令为导向（不放描述性文档）。

## Target Call Chain

```
/project-init (prompt)
  └── Phase 1: Environment & Config
       ├── Check/Create pactkit.yaml
       └── [NEW] Check/Create .claude/CLAUDE.md  ← 新增步骤
```

修改点：`src/pactkit/prompts/commands.py` → `project-init.md` prompt

## Acceptance Criteria

### Scenario 1: project-init prompt 包含 CLAUDE.md 生成步骤
- **Given**: `COMMANDS_CONTENT["project-init.md"]` 内容
- **When**: 检查 prompt 文本
- **Then**: 包含生成 `$PROJECT_ROOT/.claude/CLAUDE.md` 的指令

### Scenario 2: prompt 指示不覆盖已存在的 CLAUDE.md
- **Given**: `COMMANDS_CONTENT["project-init.md"]` 内容
- **When**: 检查 prompt 文本
- **Then**: 包含 "如果已存在则跳过" 的条件指令

### Scenario 3: prompt 指示包含 context.md 引用
- **Given**: `COMMANDS_CONTENT["project-init.md"]` 内容
- **When**: 检查 prompt 文本
- **Then**: 包含 `@./docs/product/context.md` 相关指令

### Scenario 4: prompt 指示使用 LANG_PROFILES 的 dev commands
- **Given**: `COMMANDS_CONTENT["project-init.md"]` 内容
- **When**: 检查 prompt 文本
- **Then**: 包含引用 `LANG_PROFILES`（test_runner、lint_command）的指令

## Tasks

- [ ] 在 `project-init.md` prompt 中 Phase 1 添加生成项目级 CLAUDE.md 的步骤
- [ ] 编写测试验证 prompt 内容
