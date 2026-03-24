# Project Context (Auto-generated)
> Last updated: 2026-03-24T14:08:08+08:00 by pactkit context

## Sprint Status
Backlog: 5 | In Progress: 0 | Done: 0 stories

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
- When adding a new pactkit.yaml config section, 4 touch points needed: get_default_config, DEEP_MERGE_KEYS, validate_config, generate_default_yaml. Table format in prompts saves chars vs individual sections.
- Plan Phase 3.2a scaffold-first: replaced AI freeform Write with {SCAFFOLD_CMD} create_spec + Read + Edit in src/pactkit/prompts/commands.py. Removed 3 inline format examples (~240 chars). Pre-existing tests (test_bug034, test_story055_commands, test_story_slim019) needed updates for new checkpoint wording.
- spec_linter.py _check_acceptance_criteria: per-subsection GWT check must use raw_text (with code blocks) not stripped text, because specs legitimately wrap Gherkin in fenced blocks
- Standalone scripts (visualize.py) need try/except ImportError guards for yaml.safe_load when reading pactkit.yaml — they cannot import from pactkit library
- Inline data in standalone scripts must have canonical-source comments pointing to the library module (e.g. _STACK_MARKERS → cleaners.py, _LANG_FILE_EXT → workflows.py) per Architecture Principle 1

## Next Recommended Action
`/project-plan`
