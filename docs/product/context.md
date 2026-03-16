# Project Context (Auto-generated)
> Last updated: 2026-03-16 by hotfix

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-069, BUG-035 + R7 hotfix

## Current Stories
- None active

## Recent Completions
- STORY-069 R7 hotfix: Agent tools format conversion for OpenCode
- BUG-035: OpenCode Format Should Follow Dual-Layer Architecture
- STORY-069: OpenCode Deployment Format Support

## Active Branches
- `opencode-test` — OpenCode deployment format (ready to merge)

## Key Decisions
- OpenCode 遵循 Claude Code 双层架构：全局 + 项目级
- OpenCode agent tools 格式：record `{ read: true }` 不是 string `"Read, Write"`
- `pactkit init --format opencode` → `~/.config/opencode/`
- `/project-init` → `$CWD/opencode.json`

## Next Recommended Action
测试 `opencode` 命令是否正常启动，然后合并到 main。
