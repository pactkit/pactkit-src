# Project Context (Auto-generated)
> Last updated: 2026-06-10T11:17:05+08:00 by pactkit context

## Sprint Status
Backlog: 3 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
+ claude/naughty-euclid-e6a787
  develop
* main

## Key Decisions
- _write_sqlite_db reuses func_registry and rel_edges already in memory from _build_call_graph — no second AST scan; pactkit query reads db directly without touching pactkit.yaml
- SKILL.md model: frontmatter is passed through by deployer without transformation — source prompts in commands.py/workflows.py are the single source of truth for deployed skill metadata
- codegraph sync must be enforced by code (pactkit visualize/sync), not by prompt instructions — prompt-only enforcement is unreliable for deterministic operations
- Managed-block pattern (start/end markers + regex replace) is the canonical way to update mixed-ownership files — same pattern for CLAUDE.md and CLAUDE.local.md
- Engineering guides are additive: new GUIDES_FILES entries auto-deploy via _deploy_guides() without deployer changes. Test impact limited to count assertions in test_story_slim128.

## Next Recommended Action
`/project-plan`

## Agent Continuation
No active work session.
