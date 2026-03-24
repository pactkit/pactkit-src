# Project Context (Auto-generated)
> Last updated: 2026-03-24T10:29:54+08:00 by pactkit context

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 1 stories

## Current Stories
None

## Recent Completions
- STORY-slim-024: Spec Lint W007 — Req-AC Coverage

## Active Branches
codex-integration
  codex-test
  codex/analyze-features-for-codex-integration
  develop
  feature/cython-build
* main
  opencode-test

## Key Decisions
- Monolithic prompt Phase 3.2 in commands.py caused AI thinking stalls; splitting into 4 sub-phases (3.2a-3.2d) with output checkpoints forces incremental generation and eliminates the bottleneck
- code-explorer maxTurns reduced from 50 to 15 in agents.py; Plan Phase 1 now requires bounded Explore prompts with target/scope/limit/output via Delegation Template in commands.py
- Added 09-sectional-write as core rule in src/pactkit/prompts/rules.py RULES_MODULES. Threshold 300 lines based on P75-P90 analysis of specs/source/tests. Applies to any file type.
- When adding a new pactkit.yaml config section, 4 touch points needed: get_default_config, DEEP_MERGE_KEYS, validate_config, generate_default_yaml. Table format in prompts saves chars vs individual sections.
- Plan Phase 3.2a scaffold-first: replaced AI freeform Write with {SCAFFOLD_CMD} create_spec + Read + Edit in src/pactkit/prompts/commands.py. Removed 3 inline format examples (~240 chars). Pre-existing tests (test_bug034, test_story055_commands, test_story_slim019) needed updates for new checkpoint wording.

## Next Recommended Action
`/project-design`
