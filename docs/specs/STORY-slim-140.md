# STORY-slim-140: commit-gate git-hook fallback for non-Claude environments

| Field | Value |
|-------|-------|
| ID | STORY-slim-140 |
| Status | Draft |
| Priority | P1 |
| Release | 2.17.0 |

## Background

STORY-slim-138 落地的 commit-gate 有两个拦截通道：Claude Code PreToolUse hook（写 `.claude/settings.json`）和 git pre-commit（opt-in，`--install-git-hook`）。当前只有前者自动安装——但 PreToolUse 是 Claude Code 专属机制：以 codex/opencode 为主环境的项目里，agent 发起的 `git commit` 没有任何默认拦截点，门禁形同虚设。

git 层拦截与 AI 工具无关（任何 agent 的 commit 都走 git CLI），因此非 Claude 环境 MUST 自动兜底到 git pre-commit。设计决策（2026-08-13 用户确认）：无 Claude 部署时自动安装，而非仅提示；`enterprise.no_git` 仍然豁免。

## Requirements

### R1: 非 Claude 环境自动安装 git hook (MUST)

`pactkit init` / `pactkit update` 的 post-deploy housekeeping 改为按部署格式分派：部署含 classic（或 all）→ 安装 PreToolUse hook（现状不变）；否则（纯 codex/opencode/copilot 部署）且项目存在 `.git` → 自动调用 `install_git_hook()`。`enterprise.no_git: true` 时全部跳过（现状不变）。

### R2: 门禁通道状态可见 (MUST)

部署摘要 MUST 输出本项目的 commit 门禁通道状态：`commit gate: PreToolUse hook` / `commit gate: git pre-commit` / `commit gate: none (reason)`。让"有没有门禁"一眼可查，不留静默缺口。

### R3: 幂等与共存 (MUST NOT)

重复执行 MUST NOT 重复追加 hook；已有非 pactkit 的 pre-commit MUST 链式保留（复用 slim-138 已有的链式+备份逻辑），MUST NOT 覆盖。

## Acceptance Criteria

### AC1: 纯 codex 部署自动装 git hook (R1, R2)

- **Given** 项目无 `.claude/` 目录，存在 `.git`，执行 `pactkit init --format codex`
- **When** 部署完成
- **Then** `.git/hooks/pre-commit` 存在且含 `pactkit commit-gate`；摘要输出 `commit gate: git pre-commit`

### AC2: Claude 环境行为不变 (R1, R2)

- **Given** 项目执行 `pactkit init --format classic`（或默认 all）
- **When** 部署完成
- **Then** `.claude/settings.json` 含 PreToolUse hook；不自动安装 git pre-commit；摘要输出 `commit gate: PreToolUse hook`

### AC3: no_git 豁免 (R1)

- **Given** pactkit.yaml 含 `enterprise.no_git: true`，纯 codex 部署
- **When** 部署完成
- **Then** 不安装任何 hook；摘要输出 `commit gate: none (enterprise.no_git)`

### AC4: 幂等与链式共存 (R3)

- **Given** 已有含第三方内容的 pre-commit
- **When** 连续两次执行 `pactkit update --format codex`
- **Then** 第三方内容保留，pactkit 调用仅出现一次，初次执行留有备份

### AC5: 测试套件全通过 (R1-R3)

- **Given** 全部修改完成
- **When** 运行 `.venv/bin/pytest tests/ -v`
- **Then** 所有测试通过，无新失败

## Target Call Chain

```
pactkit init/update --format X
  → cli.py post-deploy housekeeping（slim-138 落点）
    → format 含 classic/all → commit_gate.install_hook()     [PreToolUse 通道]
    → 否则且 .git 存在       → commit_gate.install_git_hook() [git 通道，本故事新增自动调用]
    → 摘要输出门禁通道状态（R2）
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/cli.py` | post-deploy 分派逻辑（classic→settings hook，否则→git hook）+ 通道状态输出 | None | Low |
| 2 | `src/pactkit/commit_gate.py` | 通道状态查询函数（供摘要/doctor 复用） | Step 1 | Low |
| 3 | `tests/unit/test_commit_gate.py` | AC1-AC4 分派/幂等/链式单测 | Step 1-2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 写 .git/hooks 文件——路径拼接基于 project_root，不接收外部路径输入 |
| SEC-2 | Yes | 读取既有 pre-commit 内容做链式判断，须容忍任意内容/编码 |
| SEC-3 | N/A | 无数据库相关 |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无认证/会话逻辑 |
| SEC-6 | N/A | 无 API/路由变更 |
| SEC-7 | Yes | hook 写入失败（权限等）降级为摘要 WARN，不得中断 deploy |
| SEC-8 | N/A | 无依赖变更 |

## Out of Scope

- Claude 环境下人肉 commit 的 git-hook 默认安装（用户决策仅覆盖"无 .claude"场景；Claude 环境的人肉绕过由 done-verify 归档核验兜底）
- pre-push / CI 端门禁（同 slim-138 边界）
- opencode/codex 各自的原生 hook 机制调研（如未来它们提供 PreToolUse 等价物，可增补通道）
