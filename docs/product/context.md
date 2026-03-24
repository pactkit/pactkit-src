# Project Context (Auto-generated)
> Last updated: 2026-03-24T15:10:49+08:00 by pactkit context

## Sprint Status
Backlog: 4 | In Progress: 0 | Done: 0 stories

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
+ worktree-agent-a1c545fc
  worktree-agent-a2d37818
  worktree-agent-a31efa03
  worktree-agent-a8a58db3
  worktree-agent-af6334c9

## Key Decisions
- spec_linter.py _check_acceptance_criteria: per-subsection GWT check must use raw_text (with code blocks) not stripped text, because specs legitimately wrap Gherkin in fenced blocks
- Standalone scripts (visualize.py) need try/except ImportError guards for yaml.safe_load when reading pactkit.yaml — they cannot import from pactkit library
- Inline data in standalone scripts must have canonical-source comments pointing to the library module (e.g. _STACK_MARKERS → cleaners.py, _LANG_FILE_EXT → workflows.py) per Architecture Principle 1
- Worktree isolation diverges from working-tree: verify visualize.py _scan_files() signature is preserved across stories to avoid breaking callers
- Extracting _detect_stack() from _detect_file_ext() enables both file discovery and test mapping to share stack detection — DRY refactoring

## Next Recommended Action
`/project-plan`
