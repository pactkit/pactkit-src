# Project Context (Auto-generated)
> Last updated: 2026-03-16 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: BUG-035, STORY-069 (archived)

## Current Stories
- None active

## Recent Completions
- BUG-035: OpenCode Format Should Follow Dual-Layer Architecture
- STORY-069: OpenCode Deployment Format Support
- BUG-034: Plan command playbook includes explicit metadata table template

## Active Branches
- `opencode-test` — OpenCode deployment format (ready to merge)

## Key Decisions
- OpenCode 遵循 Claude Code 双层架构：全局 + 项目级
- `pactkit init --format opencode` → `~/.config/opencode/` (全局: AGENTS.md + agents/ + commands/ + skills/)
- `/project-init` → `$CWD/` (项目: opencode.json + AGENTS.md)
- opencode.json 的 provider/apiKey 由用户自行配置

## Next Recommended Action
Merge `opencode-test` to main, then `/project-release` for version bump.
