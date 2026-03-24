# Project Context (Auto-generated)
> Last updated: 2026-03-24T19:55:34+08:00 by pactkit context

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 3 stories

## Current Stories
None

## Recent Completions
- STORY-slim-039: PDCA Sequence Parser
- STORY-slim-040: TopologyParser ABC + Auto-Detect
- STORY-slim-041: PdcaParser Refactor

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
- Standalone scripts (visualize.py) need try/except ImportError guards for yaml.safe_load when reading pactkit.yaml — they cannot import from pactkit library
- Inline data in standalone scripts must have canonical-source comments pointing to the library module (e.g. _STACK_MARKERS → cleaners.py, _LANG_FILE_EXT → workflows.py) per Architecture Principle 1
- Worktree isolation diverges from working-tree: verify visualize.py _scan_files() signature is preserved across stories to avoid breaking callers
- Extracting _detect_stack() from _detect_file_ext() enables both file discovery and test mapping to share stack detection — DRY refactoring
- Standalone skill scripts using exec() require all imports in _SHARED_HEADER; new stdlib imports (dataclass) must be added to skills/__init__.py _SHARED_HEADER, not just the standalone header section

## Next Recommended Action
`/project-design`
