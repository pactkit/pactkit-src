# Project Context (Auto-generated)
> Last updated: 2026-03-17 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-073, STORY-072, STORY-071, STORY-070, STORY-069, BUG-035

## Current Stories
- None active

## Recent Completions
- STORY-073: OpenCode Format Final Mile — Command Model Routing + Claude Code Residuals
- STORY-072: Multi-Developer Story ID Prefix — pactkit.yaml multi-path + developer field
- STORY-071: OpenCode Config Parity — Rules Modularization, Permission, MCP
- STORY-070: OpenCode Format Compliance — agent mode, command frontmatter

## Active Branches
- `opencode-test` — OpenCode deployment format (ready to merge)

## Key Decisions
- Command model 路由：frontmatter `model:` 字段 + command_models 配置 + provider 自动映射
- pactkit.yaml 跟着 AI 工具目录走：.claude/ 或 .opencode/
- developer 前缀解决多人 Story ID 冲突
- OpenCode rules 模块化：AGENTS.md header + rules/*.md + instructions
- /project-init 条件分支：Claude Code → CLAUDE.md, OpenCode → AGENTS.md

## Next Recommended Action
1. 运行 `pactkit init --format opencode` 重新部署（model 路由生效）
2. 运行 `/project-pr` 将 opencode-test 分支合并到 main
