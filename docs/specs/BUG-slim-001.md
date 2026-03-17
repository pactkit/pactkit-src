# BUG-slim-001: project-init creates .claude directory in OpenCode environment

| Field | Value |
|-------|-------|
| ID | BUG-slim-001 |
| Status | Draft |
| Priority | P1 |
| Release | 2.0.3 |

## Background

用户在 OpenCode 终端使用 `/project-init` 命令初始化新项目时，发现项目目录下同时生成了 `.claude/` 和 `.opencode/` 两个隐藏目录。预期行为是：OpenCode 环境下只生成 `.opencode/` 相关文件。

### 根因分析

Bug 由三层问题叠加导致：

| 层次 | 文件 | 行号 | 问题 |
|------|------|------|------|
| **1. Playbook 缺 --format 标记** | `~/.config/opencode/commands/project-init.md` | 28 | 写的是 `pactkit init`，未传 `--format=opencode` |
| **2. CLI 默认 classic** | `src/pactkit/cli.py` | 35 | `default="classic"`，不传 format 走 Claude Code 路径 |
| **3. deployer 硬编码 .claude/** | `src/pactkit/generators/deployer.py` | 974 | `_generate_project_claude_md()` 直接写 `claude_dir = project_root / '.claude'` |

### 执行链路

```
用户在 OpenCode 终端执行 /project-init
  → playbook Phase 1 Step 2: "Run `pactkit init`" (无 --format)
    → cli.py: default="classic"
      → deploy(format="classic")
        → _deploy_classic()
          → _generate_project_claude_md()
            → claude_dir = project_root / '.claude'  ← 创建 .claude/
  → playbook Phase 1 Step 5: 检测到 OpenCode 环境
    → 生成 opencode.json, AGENTS.md
    → 确保 .opencode/pactkit.yaml 存在         ← 创建 .opencode/
  结果：.claude/ 和 .opencode/ 同时存在
```

## Requirements

### R1: Playbook 根据环境传递正确的 --format (MUST)

`project-init.md` Phase 1 Step 2 的 `pactkit init` 调用 MUST 根据检测到的环境传递 `--format` 参数：
- OpenCode 环境：`pactkit init --format opencode`
- Claude Code 环境：`pactkit init`（default classic）

实现方式：在 playbook Phase 1 Step 2 中，明确指示 agent 根据环境选择 format：
- 如果 `~/.config/opencode/AGENTS.md` 存在 或 `which opencode` 成功 → 使用 `--format opencode`
- 否则 → 使用默认（classic）

### R2: Playbook Phase 1 Step 4 环境分支修复 (MUST)

Phase 1 Step 4 当前逻辑：
- Claude Code 环境 → 创建 `.claude/CLAUDE.md`
- OpenCode 环境 → 跳过 CLAUDE.md（Step 5 创建 AGENTS.md）

但 Step 2 已经通过 `pactkit init`（无 format）触发了 `_generate_project_claude_md()`，在 Step 4 判断之前就已创建 `.claude/`。

修复：Step 4 的 Claude Code 环境判断需移到 Step 2 之前，或 Step 2 已根据 R1 传递正确 format 后 Step 4 可简化。

### R3: commands.py CMD_INIT_MD 源码同步 (MUST)

`src/pactkit/prompts/commands.py` 中的 `CMD_INIT_MD` 常量是 playbook 的源码。修改 MUST 在源码中完成，然后通过 `pactkit update --format opencode` 重新部署。

## Acceptance Criteria

### AC1: OpenCode 环境下不创建 .claude/

- **Given** 用户在 OpenCode 终端环境下（`~/.config/opencode/AGENTS.md` 存在）
- **When** 执行 `/project-init`，playbook 触发 `pactkit init`
- **Then** 项目目录下不存在 `.claude/` 目录
- **And** 存在 `.opencode/pactkit.yaml`
- **And** 存在 `AGENTS.md`（项目根）

### AC2: Claude Code 环境下行为不变

- **Given** 用户在 Claude Code 环境下（无 OpenCode）
- **When** 执行 `/project-init`
- **Then** 项目目录下存在 `.claude/CLAUDE.md`
- **And** 不存在 `.opencode/` 目录

### AC3: Playbook 中 pactkit init 带正确 format

- **Given** 部署后的 `project-init.md` 命令文件
- **When** 检查 Phase 1 Step 2
- **Then** 包含环境检测逻辑，OpenCode 环境下使用 `pactkit init --format opencode`

## Target Call Chain

```
/project-init (修复后)
  → Phase 1 Step 2:
    IF OpenCode detected:
      → pactkit init --format opencode
        → deploy(format="opencode")
          → _deploy_opencode()        ← 只生成 .opencode/ 相关
    ELSE:
      → pactkit init
        → deploy(format="classic")
          → _deploy_classic()
            → _generate_project_claude_md()  ← 只在 classic 下生成 .claude/
```

## Implementation Steps

| Step | File | Action | Risk |
|------|------|--------|------|
| 1 | `src/pactkit/prompts/commands.py` | 修改 `CMD_INIT_MD` Phase 1 Step 2：环境检测 + `--format opencode` | Medium |
| 2 | `pactkit update --format opencode` | 重新部署命令文件到 `~/.config/opencode/commands/` | Low |
| 3 | `tests/unit/test_bug036_*.py` | 新增测试验证 playbook 包含环境检测逻辑 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1~8 | No | Playbook text change only |

## Out of Scope

- `_generate_project_claude_md()` 的 deployer 层面环境感知改造（该函数在 classic format 下行为正确）
- `cli.py` 的 default 值修改（`default="classic"` 在 CLI 层面是合理的，bug 在 playbook 层）
