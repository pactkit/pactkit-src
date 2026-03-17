# Project Context (Auto-generated)
> Last updated: 2026-03-17 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-072, STORY-071, STORY-070, STORY-069, BUG-035

## Current Stories
- None active

## Recent Completions
- STORY-072: Multi-Developer Story ID Prefix — pactkit.yaml multi-path + developer field
- STORY-071: OpenCode Config Parity — Rules Modularization, Permission, MCP
- STORY-070: OpenCode Format Compliance — agent mode, command frontmatter

## Active Branches
- `opencode-test` — OpenCode deployment format (ready to merge)

## Key Decisions
- pactkit.yaml 跟着 AI 工具目录走：Claude Code → .claude/，OpenCode → .opencode/
- load_config() 多路径查找：.claude/ → .opencode/ → 默认配置
- developer 前缀解决多人 Story ID 冲突：STORY-{prefix}-{NNN}
- OpenCode rules 模块化：AGENTS.md header + rules/*.md + opencode.json instructions
- OpenCode agents: mode: subagent, no name, agent: build for commands

## Next Recommended Action
运行 `pactkit init --format opencode` 重新部署。然后 `/project-pr` 将 opencode-test 合并到 main。
