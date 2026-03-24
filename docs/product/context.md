# Project Context (Auto-generated)
> Last updated: 2026-03-24T11:58:28+08:00 by pactkit context

## Sprint Status
Backlog: 6 | In Progress: 0 | Done: 0 stories

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

## Key Decisions
- Added 09-sectional-write as core rule in src/pactkit/prompts/rules.py RULES_MODULES. Threshold 300 lines based on P75-P90 analysis of specs/source/tests. Applies to any file type.
- When adding a new pactkit.yaml config section, 4 touch points needed: get_default_config, DEEP_MERGE_KEYS, validate_config, generate_default_yaml. Table format in prompts saves chars vs individual sections.
- Plan Phase 3.2a scaffold-first: replaced AI freeform Write with {SCAFFOLD_CMD} create_spec + Read + Edit in src/pactkit/prompts/commands.py. Removed 3 inline format examples (~240 chars). Pre-existing tests (test_bug034, test_story055_commands, test_story_slim019) needed updates for new checkpoint wording.
- spec_linter.py _check_acceptance_criteria: per-subsection GWT check must use raw_text (with code blocks) not stripped text, because specs legitimately wrap Gherkin in fenced blocks
- Standalone scripts (visualize.py) need try/except ImportError guards for yaml.safe_load when reading pactkit.yaml — they cannot import from pactkit library

## Next Recommended Action
`/project-plan`
