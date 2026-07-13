# Project Context (Auto-generated)
> Last updated: 2026-07-13T17:51:18+08:00 by pactkit context

## Sprint Status
Backlog: 5 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
+ claude/naughty-euclid-e6a787
  develop
* main

## Key Decisions
- Managed-block pattern (start/end markers + regex replace) is the canonical way to update mixed-ownership files — same pattern for CLAUDE.md and CLAUDE.local.md
- Engineering guides are additive: new GUIDES_FILES entries auto-deploy via _deploy_guides() without deployer changes. Test impact limited to count assertions in test_story_slim128.
- Large @inject rules (architecture 11KB, solution 8.4KB, engineering 4.3KB) removed from COMMAND_RULES_MAP — loaded on-demand via Read in playbooks. Saves ~12,500 tokens/PDCA session.
- Hardcoding external tool CLI commands in SKILL_VISUALIZE_MD and deployer.py creates upgrade coupling — replaced with codegraph --help runtime discovery in _build_claude_md_managed_content()
- Adding project-debug required updating VALID_COMMANDS in config.py, VALID_SKILLS, COMMANDS_CONTENT registration in commands.py, and COMMAND_RULES_MAP in rules.py — plus 6 test files with hardcoded count assertions

## Next Recommended Action
`/project-plan`

## Agent Continuation
No active work session.
