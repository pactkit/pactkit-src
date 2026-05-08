# STORY-slim-115: Worktree/Parallel Session Artifact Drift Prevention

| Field | Value |
|-------|-------|
| ID | STORY-slim-115 |
| Title | Worktree/Parallel Session Artifact Drift Prevention |
| Status | Draft |
| Release | TBD |

## Background

### The Problem

PactKit 的多个共享 artifact 文件在 worktree 或并行 session 场景下会发生 **drift（漂移）**——一个 session 的正确状态被另一个 session 的旧版本覆盖。

**真实案例（koi 项目，2026-05-07）**：
1. Session A 在 `59a043b` 完成 STORY-026/028，board 正确显示它们在 Done 区
2. Session B（`/dev` worktree）基于更早的 board 版本工作
3. Session B 完成 STORY-029，commit 时用自己的旧 board 覆盖了 Session A 的正确状态
4. 结果：已完成的 STORY-026/028 被"移回" Backlog，archive 中已有记录但 board 与之矛盾

### Hot Files 分析

以下文件被多个 PDCA 命令读写，是并行冲突的高危区：

| File | Written By | Conflict Risk |
|------|------------|---------------|
| `docs/product/sprint_board.md` | Plan (add), Act (move to In Progress), Done (move to Done, archive) | **HIGH** — 整个文件被覆盖 |
| `docs/product/context.md` | Plan, Act, Done, Hotfix (context update) | **MEDIUM** — 最后写入者覆盖 |
| `docs/architecture/governance/lessons.md` | Done (append lessons) | **LOW** — append-only 但仍可能丢行 |
| `docs/architecture/governance/rules.md` | Done (update test count invariant) | **LOW** — 单行更新 |
| `docs/product/archive/archive_YYYYMM.md` | Done (append archived stories) | **LOW** — append-only |

### Root Cause

1. **Worktree 隔离不完整**：worktree 创建时 fork 了主分支的状态，但返回时没有 merge 主分支的 board 变更
2. **Board 是 mutable 的单一文件**：状态转移（Backlog→In Progress→Done）是覆盖式操作，不是增量操作
3. **没有 conflict detection**：commit 时如果 board 被其他 session 修改过，git 不会自动冲突（不同位置的修改会 auto-merge，导致逻辑不一致）

## Target Call Chain

```
/project-act → Phase 0.6 → move story to In Progress → sprint_board.md
/project-done → Phase 3.5 → archive story → sprint_board.md + archive_YYYYMM.md
/dev worktree → ... → commit → merge back → potential board drift
```

## Requirements

### R1: Derived Board View (MUST)
Board 不再是手动维护的 mutable 文件，而是从 specs + archive 推导的 **view**：
- Story 存在于 `docs/specs/{ID}.md` 且 `status: backlog` → Backlog
- Story 存在于 `docs/specs/{ID}.md` 且 `status: in_progress` → In Progress  
- Story 存在于 archive 或 spec `status: done` → Done（显示在 archive，不在 board）

状态存储在 spec 文件的 frontmatter 或 metadata table 中，单 story 单文件，并行修改不同 story 不冲突。

### R2: Board Generation Command (MUST)
`pactkit board` 命令动态生成 board 视图：
```bash
pactkit board           # 输出 markdown 格式的当前 board
pactkit board --write   # 可选：写入 sprint_board.md（用于兼容现有工具）
```

### R3: Playbook Migration (MUST)
修改 PDCA 命令的 board 操作：
- `/project-plan`：`pactkit spec-status {ID} backlog` 设置 spec 状态
- `/project-act`：`pactkit spec-status {ID} in_progress` 设置 spec 状态
- `/project-done`：`pactkit spec-status {ID} done` 设置 spec 状态 + archive 追加

不再直接编辑 `sprint_board.md`。

### R4: Worktree Merge Protocol (SHOULD)
Worktree 返回主分支前，自动检查 board 相关文件是否有冲突：
- 如果 spec 文件被主分支修改过，提示用户 merge
- 如果 archive 文件被主分支追加过，auto-merge（append-only 安全）

### R5: Conflict Detection Hook (SHOULD)
Pre-commit hook 检测 board drift：
- 如果 `sprint_board.md` 的 base 版本与当前 HEAD 不同，警告用户
- 建议运行 `pactkit board --write` 重新生成

### R6: Backward Compatibility (MUST)
- 现有 `sprint_board.md` 格式保持不变（generated file 或 view）
- 不使用 `pactkit` CLI 的用户仍可手动编辑 board（但建议迁移）
- Migration path：运行 `pactkit board-migrate` 从现有 board 反推 spec status

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 User Input | N/A | Internal tooling, no user input |
| SEC-2 Secrets | N/A | No secrets involved |
| SEC-3 File Access | N/A | Only project-local files |
| SEC-4 Network | N/A | No network access |
| SEC-5 Auth | N/A | No auth changes |
| SEC-6 Data Validation | N/A | No external data |
| SEC-7 Crypto | N/A | No crypto |
| SEC-8 Logging | N/A | No sensitive data logging |

## Acceptance Criteria

### AC1: Derived Board Correctness (R1, R2)
- **Given** a project with 3 specs: A (status: backlog), B (status: in_progress), C (status: done)
- **When** `pactkit board` is run
- **Then** output shows A in Backlog, B in In Progress, Done section is empty (done stories go to archive)

### AC2: Spec Status Transition (R3)
- **Given** a spec STORY-001 with `status: backlog`
- **When** `pactkit spec-status STORY-001 in_progress` is run
- **Then** the spec file's status field is updated to `in_progress`
- **And** `pactkit board` shows STORY-001 in In Progress section

### AC3: Parallel Session Safety (R1)
- **Given** two parallel sessions working on different stories (STORY-A and STORY-B)
- **When** both sessions complete and commit
- **Then** both stories' spec status are correctly updated (no overwrite)
- **And** `pactkit board` shows correct state for both

### AC4: Migration from Existing Board (R6)
- **Given** an existing `sprint_board.md` with stories in various sections
- **When** `pactkit board-migrate` is run
- **Then** each story's spec file is updated with the correct status
- **And** `pactkit board` reproduces the original board structure

## Implementation Steps

| Step | File | Change |
|------|------|--------|
| 1 | `src/pactkit/board.py` | New module: `generate_board()`, `get_spec_status()`, `set_spec_status()` |
| 2 | `src/pactkit/cli.py` | Add `board`, `spec-status`, `board-migrate` commands |
| 3 | `pactkit-plugin/commands/project-plan.md` | Replace board edit with `pactkit spec-status` |
| 4 | `pactkit-plugin/commands/project-act.md` | Replace board edit with `pactkit spec-status` |
| 5 | `pactkit-plugin/commands/project-done.md` | Replace board edit with `pactkit spec-status` |
| 6 | `tests/unit/test_board.py` | Unit tests for board generation and status transitions |

## Notes

- 这个改动是 **breaking change**，需要在 release notes 中说明 migration path
- 考虑添加 `pactkit.yaml` 配置项 `board.mode: derived | legacy` 支持渐进迁移
- Context.md 的 drift 问题较轻（信息类文件，不影响工作流状态），可以后续处理
