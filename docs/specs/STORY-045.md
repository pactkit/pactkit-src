# STORY-045: Auto-PR Enhancement — Structured PR Body Generation

| Field     | Value |
|-----------|-------|
| ID        | STORY-045 |
| Status    | Draft |
| Priority  | Medium |
| Release   | 1.3.1 |
| Author    | System Architect |
| Source    | Gap Analysis: SpecKit auto-PR |

## Background

PactKit 的 Done phase 已有 `gh pr create` 指引（Phase 4: Git Commit），但 PR 的 title 和 body 依赖 Agent 临时组织。不同 session 生成的 PR 格式不一致，且经常遗漏关键信息（测试结果、Spec 链接、验收标准覆盖情况）。

SpecKit 将 auto-PR 作为 first-class 功能。PactKit 需要在现有 Done playbook 基础上增强：从 Spec、Board、测试结果中自动提取信息，生成结构化的 PR body。

## Target Call Chain

```
/project-done (commands.py)
  → Phase 4: Git Commit (existing)
  → Phase 4.2 (NEW): Auto-PR Generation
    → _should_create_pr()
      → Check: is current branch != main/master?
      → Check: does remote branch exist?
    → _generate_pr_body(story_id)
      → Read Spec: docs/specs/{ID}.md → extract title, requirements summary
      → Read Board: sprint_board.md → extract task completion status
      → Read test output: last pytest result
      → Compose structured body
    → gh pr create --title "..." --body "..."
  → Phase 4.5: Session Context Update (existing)
```

## Requirements

### R1: PR 自动触发判定 (MUST)

在 Done Phase 4（Git Commit）完成后，新增 **Phase 4.2: Auto-PR**。

**触发条件（ALL must be true）：**
1. 当前分支不是 `main` 或 `master`
2. 当前分支已 push 到 remote（或 Phase 4.2 负责 push）
3. 该分支尚无 open PR（通过 `gh pr list --head <branch>` 检查）

**不触发时：**
- 直接在 main 上工作 → 跳过，输出 "Skipping PR: working on main branch"
- 已有 open PR → 跳过，输出 PR URL

### R2: PR Title 生成 (MUST)

格式：`{type}({scope}): {spec_title}`
- `type`: 从 Spec ID 推断（STORY → feat, BUG → fix, HOTFIX → fix）
- `scope`: 从修改的主要目录推断
- `spec_title`: 从 Spec 文件的一级标题提取（去掉 ID 前缀）
- 长度不超过 70 字符

### R3: PR Body 结构化生成 (MUST)

```markdown
## Summary
{从 Spec ## Background 提取 1-3 句摘要}

## Changes
{从 Spec ## Requirements 提取，列出 R1-RN 的标题，标注 MUST/SHOULD/MAY}

## Acceptance Criteria
{从 Spec ## Acceptance Criteria 提取，以 checklist 格式}
- [x] AC1: {title}  — covered by test
- [x] AC2: {title}  — covered by test
- [ ] AC3: {title}  — manual verification needed

## Test Results
{从最近的 pytest 输出提取}
- Unit: {N} passed, {N} failed
- E2E: {N} passed, {N} failed
- Coverage: {N}% (if available)

## Spec
- [{STORY_ID}](docs/specs/{STORY_ID}.md)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### R4: 用户确认 (MUST)

PR 创建前必须向用户展示预览并等待确认：
1. 输出完整的 PR title + body 预览
2. 询问 "Create this PR? (yes/no/edit)"
3. `yes` → 执行 `gh pr create`
4. `no` → 跳过 PR 创建
5. `edit` → 用户提供修改意见后重新生成

### R5: Push 保障 (MUST)

如果当前分支未 push 到 remote：
1. 执行 `git push -u origin <branch>`
2. 如果 push 失败，STOP 并报告（不创建 PR）

### R6: Done Playbook 集成 (MUST)

修改 `project-done.md` playbook：
- Phase 4（Git Commit）后插入 Phase 4.2
- Phase 4.2 在 Phase 4.5（Session Context Update）之前执行
- 如果 `gh` CLI 不可用，打印 warning 并跳过

## Acceptance Criteria

### AC1: Feature 分支自动触发
**Given** 当前在 `feature/STORY-045-auto-pr` 分支，已 commit
**When** Done Phase 4.2 执行
**Then** 检测到非 main 分支且无 open PR
**And** 生成 PR 预览并询问用户

### AC2: PR Body 包含结构化信息
**Given** STORY-045 的 Spec 有 Background、Requirements、Acceptance Criteria
**When** PR body 生成
**Then** body 包含 Summary、Changes、Acceptance Criteria、Test Results、Spec link

### AC3: Main 分支跳过
**Given** 当前在 main 分支
**When** Done Phase 4.2 执行
**Then** 输出 "Skipping PR: working on main branch"
**And** 直接进入 Phase 4.5

### AC4: 已有 PR 跳过
**Given** 当前分支已有 open PR
**When** Done Phase 4.2 执行
**Then** 输出已有 PR 的 URL
**And** 不创建新 PR

### AC5: 用户可拒绝
**Given** PR 预览已展示
**When** 用户输入 "no"
**Then** 不执行 `gh pr create`
**And** Done 流程继续到 Phase 4.5

### AC6: gh CLI 不可用时优雅降级
**Given** `gh` CLI 未安装
**When** Done Phase 4.2 执行
**Then** 输出 warning "gh CLI not available — skipping auto-PR"
**And** Done 流程继续

## Out of Scope

- PR review/merge 自动化
- PR template 配置化（未来可通过 `.github/PULL_REQUEST_TEMPLATE.md` 扩展）
- 多 commit PR 的 changelog 生成
