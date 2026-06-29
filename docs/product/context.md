# Project Context (Auto-generated)
> Last updated: 2026-06-29T14:59:29+08:00 by pactkit context

## Sprint Status
Backlog: 4 | In Progress: 0 | Done: 1 stories

## Current Stories
None

## Recent Completions
- HOTFIX-slim-130: Fix skill frontmatter parsing

## Active Branches
+ claude/naughty-euclid-e6a787
  develop
* main

## Key Decisions
- SKILL.md model: frontmatter is passed through by deployer without transformation — source prompts in commands.py/workflows.py are the single source of truth for deployed skill metadata
- codegraph sync must be enforced by code (pactkit visualize/sync), not by prompt instructions — prompt-only enforcement is unreliable for deterministic operations
- Managed-block pattern (start/end markers + regex replace) is the canonical way to update mixed-ownership files — same pattern for CLAUDE.md and CLAUDE.local.md
- Engineering guides are additive: new GUIDES_FILES entries auto-deploy via _deploy_guides() without deployer changes. Test impact limited to count assertions in test_story_slim128.
- Large @inject rules (architecture 11KB, solution 8.4KB, engineering 4.3KB) removed from COMMAND_RULES_MAP — loaded on-demand via Read in playbooks. Saves ~12,500 tokens/PDCA session.

## Next Recommended Action
`/project-plan`

## Agent Continuation
No active work session.
