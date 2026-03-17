# Project Context (Auto-generated)
> Last updated: 2026-03-17 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-070, STORY-069, BUG-035

## Current Stories
- None active

## Recent Completions
- STORY-070: OpenCode Format Compliance — Fix Spec-Implementation Gaps
- STORY-069 R7 hotfix: Agent tools format conversion for OpenCode
- BUG-035: OpenCode Format Should Follow Dual-Layer Architecture

## Active Branches
- `opencode-test` — OpenCode deployment format (ready to merge)

## Key Decisions
- OpenCode 遵循 Claude Code 双层架构：全局 + 项目级
- OpenCode agent tools 格式：record `{ read: true }` 不是 string `"Read, Write"`
- OpenCode agents 需要 `mode: subagent` 字段，不需要 `name` 字段
- OpenCode commands 用 `agent: build` 替代 `allowed-tools`
- `pactkit init --format opencode` → `~/.config/opencode/`

## Next Recommended Action
重新运行 `pactkit init --format opencode` 更新部署文件，然后测试 OpenCode 是否正常工作。
