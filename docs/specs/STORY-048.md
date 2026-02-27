# STORY-048: Worktree Isolation for Subagent Sprint

| Field     | Value |
|-----------|-------|
| ID        | STORY-048 |
| Status    | Draft |
| Priority  | Medium |
| Release   | 1.4.0 |
| Author    | System Architect |
| Source    | User Request: Claude Code worktree 特性集成 |

## Background

PactKit 的 `/project-sprint` 通过 subagent team 编排 PDCA 流程（Stage A: Build → Stage B: Check → Stage C: Close）。当前所有 subagent 共享同一个工作目录，这带来两个问题：

1. **写冲突**：Stage B 的 QA 和 Security subagent 并行运行时，若两者同时修改文件（如生成报告、修复 lint 问题），会产生竞态条件
2. **主工作区污染**：subagent 的中间产物（未提交的修改、临时文件）会污染用户的主工作区，导致用户在 sprint 期间无法继续其他工作

Claude Code 原生支持 `isolation: "worktree"` 参数，可为 Task tool 创建的 subagent 分配独立的 git worktree。每个 worktree 是 repo 的完整副本，拥有独立的工作树和 index，但共享同一个 `.git` 目录。

本 Spec 的目标是将 worktree 隔离集成到 Sprint playbook 中，使 subagent 在隔离环境中工作，消除竞态和污染问题。

## Target Call Chain

```
/project-sprint (Lead Orchestrator)
  → Phase 2: PDCA Execution
    → Stage A: Task(subagent_type="system-architect", isolation="worktree")
      → subagent 在独立 worktree 中执行 Plan + Act
      → 完成后 Lead 检查 worktree 变更，合并回主分支
    → Stage B: Task(subagent_type="qa-engineer", isolation="worktree")  [并行]
              Task(subagent_type="security-auditor", isolation="worktree")  [并行]
      → 两个 subagent 各自在独立 worktree 中执行，零冲突
    → Stage C: Task(subagent_type="repo-maintainer", isolation="worktree")
      → 在独立 worktree 中执行 Done 流程
```

## Requirements

### R1: Sprint Playbook 集成 Worktree 隔离 (MUST)

修改 `SPRINT_PROMPT`（`src/pactkit/prompts/workflows.py`）中 Stage A / B / C 的 Task 调用指令，为所有 subagent 添加 `isolation: "worktree"` 参数：

```
# Before
Task(subagent_type="system-architect")

# After
Task(subagent_type="system-architect", isolation="worktree")
```

适用于所有 3 个 Stage 的全部 subagent（system-architect、qa-engineer、security-auditor、repo-maintainer）。

### R2: Worktree 变更回收策略 (MUST)

当 subagent 在 worktree 中产生文件变更时，Claude Code 会返回 worktree 路径和分支名。Sprint playbook MUST 包含以下回收指引：

1. **Stage A (Build)**：subagent 完成后，Lead MUST 将 worktree 分支的变更合并到当前工作分支（`git merge` 或 `git cherry-pick`）
2. **Stage B (Check)**：QA 和 Security subagent 产出的是报告文件（`docs/product/reports/`），Lead SHOULD 将报告文件从 worktree 复制回主工作区
3. **Stage C (Close)**：Closer 执行 commit 和 archive，Lead MUST 确保 commit 出现在目标分支上

### R3: 无变更时自动清理 (SHOULD)

Claude Code 的 worktree 机制在 subagent 未产生任何文件变更时，会自动清理 worktree。Sprint playbook SHOULD 在指引中说明这一行为，避免 Lead 在无变更的 worktree 上执行无效的合并操作。

### R4: 错误处理增强 (MUST)

在 Sprint playbook 的「Error Handling」section 中补充 worktree 相关的错误场景：

- **合并冲突**：如果 worktree 分支与当前分支存在合并冲突，Lead MUST 停止并报告冲突详情，等待用户手动解决
- **Worktree 残留**：如果 sprint 因错误中断，Lead SHOULD 提示用户检查并清理残留的 worktree（`git worktree list` + `git worktree remove`）

### R5: 向后兼容 (MUST)

worktree 隔离为 Sprint playbook 的默认行为。但如果用户的环境不支持 git worktree（如 shallow clone、某些 CI 环境），Sprint MUST NOT 因此失败——应回退到当前的共享工作目录模式，并打印警告。

## Acceptance Criteria

### AC1: Build Stage Worktree 隔离
**Given** 执行 `/project-sprint` 且 git 环境支持 worktree
**When** Stage A (Build) 启动 system-architect subagent
**Then** subagent 在独立 worktree 中执行
**And** 完成后 Build 产物（Spec 文件、实现代码、测试）被合并回工作分支

### AC2: Check Stage 并行隔离
**Given** Stage B 启动 QA 和 Security 两个 subagent
**When** 两个 subagent 并行执行
**Then** 各自在独立的 worktree 中运行，互不影响
**And** 报告文件被回收到主工作区的 `docs/product/reports/` 目录

### AC3: 合并冲突处理
**Given** subagent 的 worktree 分支与当前分支存在合并冲突
**When** Lead 尝试回收变更
**Then** Lead 停止 sprint 执行
**And** 向用户报告冲突的文件列表和建议操作

### AC4: 无 Worktree 环境回退
**Given** 用户的 git 环境不支持 worktree（如 shallow clone）
**When** 执行 `/project-sprint`
**Then** 回退到共享工作目录模式（当前行为）
**And** 打印警告信息说明未启用隔离

### AC5: 现有 Sprint 行为不退化
**Given** 在支持 worktree 的标准 git 环境中执行 `/project-sprint`
**When** 完整 PDCA 流程执行完毕
**Then** 最终产物（Spec、代码、测试、报告、commit）与不使用 worktree 时完全一致
**And** 所有现有 sprint 相关测试通过

## Out of Scope

- 用户手动通过 `EnterWorktree` 进入 worktree 的交互式体验（本 Spec 仅覆盖 Sprint subagent 的自动化场景）
- 跨 worktree 的 subagent 间通信（当前通过 TaskList/SendMessage 机制已满足，无需额外适配）
- Worktree 的持久化管理（worktree 为临时资源，用完即弃）
