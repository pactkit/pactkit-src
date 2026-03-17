# Project Context (Auto-generated)
> Last updated: 2026-03-17 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-slim-001, STORY-073, STORY-072, STORY-071, STORY-070

## Current Stories
- None active

## Recent Completions
- STORY-slim-001: Tool Integration Checklist (11 dimensions, 60+ checks, Codex pre-research)
- STORY-073: OpenCode Format Final Mile — Command Model Routing + Claude Code Residuals
- STORY-072: Multi-Developer Story ID Prefix — pactkit.yaml multi-path + developer field

## Active Branches
- `main` — current

## Key Decisions
- New tool integration: fill Dimension 0 capability matrix FIRST, determines strategy
- OpenCode: 17/17 capability matrix items PASS (vision via Bedrock is user-env issue)
- pactkit.yaml path: .claude/ (Claude Code), .opencode/ (OpenCode), .codex/ (Codex future)
- Model routing: in opencode.json command section, NOT in shared command frontmatter
- developer 前缀: STORY-slim-001 验证生效

## Next Recommended Action
`git push origin main` 推送最新改动，然后 `pactkit init --format opencode` 重新部署。
