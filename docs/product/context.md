# Project Context (Auto-generated)
> Last updated: 2026-03-26T14:24:53+08:00 by pactkit context

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
- regression_workflow_impact hook/store matching uses node.id substring of changed file path, not reverse — e.g. 'useAuth' in 'src/hooks/useAuth.ts'
- export_focus_graphs() in visualize.py uses forward_reach() (not reverse_reach()) because entry points (command/service/page) are graph roots that invoke downward — forward BFS shows their dependency tree
- board.py update_task: added 3-tier fuzzy fallback (single-task auto-mark, substring match, numeric index) to handle real-world callers that don't know exact task names on the board
- Position-based block removal (start, end tuples) is safer than str.find() for board operations — prevents substring false matches on similar story IDs
- Fixing _parse_story_blocks to return adjusted_end (len match) inherently fixed fix_board offset compensation — root cause fix in board.py:_parse_story_blocks eliminated downstream R2 symptom in board.py:fix_board

## Next Recommended Action
`/project-design`
