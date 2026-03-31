# Project Context (Auto-generated)
> Last updated: 2026-03-31T16:17:59+08:00 by pactkit context

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
- Frontend API path convention bugs are structurally preventable: ApiCallParser+api_convention_summary in trace phase surfaces prefix/wrapper conventions before implementation, eliminating a class of copy-paste path errors
- Rendering-only changes to visualize.py can be isolated by extracting a shared render helper (_render_nested_call_graph) that both forward and reverse BFS call — keeps AST parsing untouched
- dict.update() on call_edges causes last-wins overwrite when scanning same-name functions across files; use extend-merge pattern instead
- CLI args must mirror visualize.py standalone argparse; feature implemented in visualize.py but not exposed in cli.py is effectively dead code
- tree-sitter comment nodes are direct children of function body nodes (block/statement_block), enabling scoped dispatch hint queries without parent traversal. Per-language comment query needed: Go/TS use (comment), Java uses [(line_comment)(block_comment)].

## Next Recommended Action
`/project-design`
