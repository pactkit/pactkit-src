# Project Context (Auto-generated)
> Last updated: 2026-03-26T20:43:04+08:00 by pactkit context

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
- _atomic_mmd_write() in visualize.py prevents truncated .mmd on crash via tmp+rename; all 4 write sites converted
- test_story_slim056.py _init_project() helper creates realistic pactkit project fixture for subprocess E2E tests; 60 tests cover all 25 subcommands
- entry_points auto-discovery with _load_entry_point_deployers() enables pip install pactkit-opencode to self-register; pre-existing tests referencing extracted functions must be updated to import from adapter package
- VALID_FORMATS auto-derives from FORMAT_PROFILES.keys() — removing a profile cascades to config, CLI, and deployer with zero manual sync
- DeployerBase static methods use lazy imports to avoid circular dependencies between deploy_base.py and deployer.py

## Next Recommended Action
`/project-design`
