# Project Context (Auto-generated)
> Last updated: 2026-04-02T10:53:42+08:00 by pactkit context

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
codex-integration
  codex-test
  codex/analyze-features-for-codex-integration
  develop
  feature/cython-build
* main
  opencode-test
  worktree-agent-a1c545fc
  worktree-agent-a2a614d9
  worktree-agent-a2c72eb4
  worktree-agent-a2d37818
  worktree-agent-a31efa03
+ worktree-agent-a69e176d
  worktree-agent-a8a58db3
  worktree-agent-ace1a8fe
  worktree-agent-aeb84ca4
  worktree-agent-af6334c9

## Key Decisions
- nearest-ancestor config discovery: tests for STORY-078/079 need updating when analyzer signatures change — always check downstream test_story_* files
- key_to_module index in visualize.py:_build_module_graph must register hyphen-to-underscore variants for Python packages (pydantic-core vs pydantic_core)
- Adding new visualize modes requires syncing prompts/skills.py:SKILL_VISUALIZE_MD, prompts/rules.py:Visual First, prompts/skills.py:SKILL_RELEASE_MD, prompts/commands.py:Init Phase 3
- deployer.py:_build_command_rules_header dispatched on profile.name — must dispatch on profile.rules_import_style for OCP; OpenCode profile had rules_import_style='instructions' but actually inlines rules in commands, corrected to 'inline'
- validate_deployed_content() guard caught real adapter bugs (missing _replace_slash_commands in copilot agents, missing _replace_cli_with_scripts in codex rules) — static analysis on deploy output is high-value for multi-adapter systems

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
