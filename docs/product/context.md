# Project Context (Auto-generated)
> Last updated: 2026-03-26T15:33:31+08:00 by pactkit context

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
- Fixing _parse_story_blocks to return adjusted_end (len match) inherently fixed fix_board offset compensation — root cause fix in board.py:_parse_story_blocks eliminated downstream R2 symptom in board.py:fix_board
- Helpers added to visualize.py standalone header get stripped by load_script(); always place new functions below the SCRIPT BODY marker
- dict.pop() in shared config references causes caller mutation; use .get() for read-only access to avoid breaking multi-call scenarios
- _atomic_mmd_write() in visualize.py prevents truncated .mmd on crash via tmp+rename; all 4 write sites converted
- test_story_slim056.py _init_project() helper creates realistic pactkit project fixture for subprocess E2E tests; 60 tests cover all 25 subcommands

## Next Recommended Action
`/project-design`
