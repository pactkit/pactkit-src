# STORY-007: `/project-status` — 冷启动项目状态感知命令

- **Priority**: 4 (Impact 4 / Effort 2)
- **Agent**: System Architect → Senior Developer
- **Release**: 1.1.0
- **Depends on**: STORY-006 (context.md format)

## Background

STORY-006 让 context.md 被动加载（通过 CLAUDE.md @import）。但有些场景需要**主动触发**状态查询：
- context.md 过期（上次 session 很久以前）
- 用户想看最新状态（包括 git 实时信息）
- 接手别人项目，需要快速定位

`/project-status` 是一个轻量只读命令——不创建文件、不改代码、不写 spec，只输出当前项目状态报告。

## Requirements

### R1: Status Report Output (MUST)
`/project-status` MUST 输出以下结构化报告（直接输出到终端，不写文件）：

```
## Project Status Report

### Sprint Board
- 📋 Backlog: {N} stories
- 🔄 In Progress: {N} stories (list with IDs + titles)
- ✅ Done: {N} stories

### Git State
- Branch: {current branch}
- Uncommitted changes: {Y/N, summary}
- Active feature branches: {list}

### Health Indicators
- Tests: {last known result or "unknown"}
- Architecture graphs: {fresh/stale/missing}
- Specs coverage: {N stories with specs / N total}

### Recommended Next Action
{Based on board state and git state}
```

### R2: Read-Only (MUST)
`/project-status` MUST NOT modify any files. It is a pure query command.

### R3: Routing Table Entry (MUST)
Add to routing table:
```
### Status (`/project-status`)
- **Role**: System Medic
- **Playbook**: `commands/project-status.md`
- **Goal**: Project state overview for cold-start orientation.
```

### R4: No Init Dependency (SHOULD)
`/project-status` SHOULD work even on non-initialized projects (no sprint_board.md). In this case, it outputs git state and suggests `/project-init`.

### R5: Context Refresh (SHOULD)
After outputting the report, `/project-status` SHOULD also update `docs/product/context.md` (if the project is initialized) to keep the cached context fresh.

## Acceptance Criteria

### Scenario 1: Initialized project with active stories
**Given** a project with sprint_board.md containing 2 In Progress and 3 Backlog stories
**When** user runs `/project-status`
**Then** report shows "🔄 In Progress: 2 stories" with IDs, "📋 Backlog: 3 stories", and recommends `/project-act STORY-XXX`

### Scenario 2: Uninitialized project
**Given** a project without docs/product/ directory
**When** user runs `/project-status`
**Then** report shows Git State section (branch, uncommitted changes) and recommends `/project-init`

### Scenario 3: Clean board (all done)
**Given** a project with all stories in Done section
**When** user runs `/project-status`
**Then** report shows "✅ Done: N stories" and recommends `/project-design` or `/project-plan` for next iteration

## Implementation Notes

1. New command playbook in `commands.py` key: `"project-status.md"`
2. New agent role or reuse System Medic (same diagnostic nature as Doctor)
3. Add to `VALID_COMMANDS` set in `config.py`
4. Routing table entry in `rules.py` routing module
5. Prompt-only implementation — the agent reads files and outputs a report, no Python logic needed
