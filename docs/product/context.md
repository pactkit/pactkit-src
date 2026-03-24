# Project Context (Auto-generated)
> Last updated: 2026-03-24T20:32:40+08:00 by pactkit context

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
- Extracting _detect_stack() from _detect_file_ext() enables both file discovery and test mapping to share stack detection — DRY refactoring
- Standalone skill scripts using exec() require all imports in _SHARED_HEADER; new stdlib imports (dataclass) must be added to skills/__init__.py _SHARED_HEADER, not just the standalone header section
- detect_topology() must delegate to _TOPOLOGY_PARSERS parser.detect() first, not _TOPOLOGY_MARKERS alone — parsers and markers can diverge silently causing empty graphs
- _scan_hooks() only accepts files with 'use' prefix in hook dirs (src/hooks/, composables/) to prevent utility files from becoming hook nodes
- regression_workflow_impact hook/store matching uses node.id substring of changed file path, not reverse — e.g. 'useAuth' in 'src/hooks/useAuth.ts'

## Next Recommended Action
`/project-design`
