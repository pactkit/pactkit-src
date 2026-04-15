# Project Context (Auto-generated)
> Last updated: 2026-04-15T12:16:35+08:00 by pactkit context

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
develop
* main

## Key Decisions
- Adding new visualize modes requires syncing prompts/skills.py:SKILL_VISUALIZE_MD, prompts/rules.py:Visual First, prompts/skills.py:SKILL_RELEASE_MD, prompts/commands.py:Init Phase 3
- deployer.py:_build_command_rules_header dispatched on profile.name — must dispatch on profile.rules_import_style for OCP; OpenCode profile had rules_import_style='instructions' but actually inlines rules in commands, corrected to 'inline'
- validate_deployed_content() guard caught real adapter bugs (missing _replace_slash_commands in copilot agents, missing _replace_cli_with_scripts in codex rules) — static analysis on deploy output is high-value for multi-adapter systems
- Borrowed Claude Code P3 (graduated safety language) + P6 (NO_TOOLS) patterns; applied to 01-core-protocol.md, 02-hierarchy-of-truth.md, 10-safety.md, project-act.md, project-check.md
- pyproject.toml [project].dependencies must only include packages needed for core CLI startup (pyyaml); adapter and tree-sitter packages go in [project.optional-dependencies] with extras (opencode, codex, visualize, all)

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
