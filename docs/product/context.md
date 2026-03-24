# Project Context (Auto-generated)
> Last updated: 2026-03-24T17:00:00+08:00 by /project-done

## Sprint Status
Backlog: 1 | In Progress: 0 | Done: 3 stories

## Current Stories
None

## Recent Completions
- STORY-slim-033: Java LanguageAnalyzer adapter (2026-03-24)
- STORY-slim-032: TreeSitterAnalyzer base class + Go adapter (2026-03-24)
- STORY-slim-031: Unified impact test mapping via LANG_PROFILES (2026-03-24)

## Active Branches
codex-integration
  codex-test
  codex/analyze-features-for-codex-integration
  develop
  feature/cython-build
* main
  opencode-test

## Key Decisions
- spec_linter.py _check_acceptance_criteria: per-subsection GWT check must use raw_text (with code blocks) not stripped text, because specs legitimately wrap Gherkin in fenced blocks
- Standalone scripts (visualize.py) need try/except ImportError guards for yaml.safe_load when reading pactkit.yaml — they cannot import from pactkit library
- Inline data in standalone scripts must have canonical-source comments pointing to the library module (e.g. _STACK_MARKERS → cleaners.py, _LANG_FILE_EXT → workflows.py) per Architecture Principle 1
- Worktree isolation diverges from working-tree: verify visualize.py _scan_files() signature is preserved across stories to avoid breaking callers
- Extracting _detect_stack() from _detect_file_ext() enables both file discovery and test mapping to share stack detection — DRY refactoring

## Next Recommended Action
`/project-act STORY-slim-034`
