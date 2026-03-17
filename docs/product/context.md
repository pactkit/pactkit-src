# Project Context (Auto-generated)
> Last updated: 2026-03-17 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-071, STORY-070, STORY-069, BUG-035

## Current Stories
- None active

## Recent Completions
- STORY-071: OpenCode Config Parity — Rules Modularization, Permission, MCP
- STORY-070: OpenCode Format Compliance — Fix Spec-Implementation Gaps
- STORY-069: OpenCode Deployment Format Support

## Active Branches
- `opencode-test` — OpenCode deployment format (ready to merge)

## Key Decisions
- OpenCode rules 模块化拆分：AGENTS.md (14行 header) + rules/*.md + opencode.json instructions
- 全局 opencode.json merge 策略：保留用户 provider，更新 instructions
- 项目级 opencode.json 包含 permission + MCP 模板
- `.opencode/pactkit.yaml` 不需要 — pactkit.yaml 保留在 `.claude/`
- OpenCode agents: mode: subagent, no name, agent: build for commands

## Next Recommended Action
运行 `pactkit init --format opencode` 重新部署更新后的配置，验证 rules 拆分和 opencode.json 生效。然后运行 `/project-pr` 将 opencode-test 分支合并到 main。
