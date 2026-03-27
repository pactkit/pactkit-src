# Project Context (Auto-generated)
> Last updated: 2026-03-27T10:40:30+08:00 by pactkit context

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
- entry_points auto-discovery with _load_entry_point_deployers() enables pip install pactkit-opencode to self-register; pre-existing tests referencing extracted functions must be updated to import from adapter package
- VALID_FORMATS auto-derives from FORMAT_PROFILES.keys() — removing a profile cascades to config, CLI, and deployer with zero manual sync
- DeployerBase static methods use lazy imports to avoid circular dependencies between deploy_base.py and deployer.py
- Thin adapter conversion: pactkit-codex reduced from 15,356 lines (full fork) to 668 lines (thin adapter) by importing core via DeployerBase. Key: deploy_codex_playbooks needs explicit path replacement for ALL format prefixes (~/.claude/, ~/.config/opencode/ → ~/.codex/)
- When migrating commands to skills (subdir/SKILL.md format), all path assertions in pre-existing tests must be updated in the same commit — 17 tests broke because they asserted flat commands/*.md paths

## Next Recommended Action
`/project-design`
