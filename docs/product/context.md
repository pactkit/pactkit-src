# Project Context (Auto-generated)
> Last updated: 2026-03-21T23:00:00+08:00 by /project-done

## Sprint Status
Backlog: 2 (STORY-slim-015, STORY-slim-016) | In Progress: 0 | Done: 13 stories

## Current Stories
- STORY-slim-015: Doctor & Release CLI — Deterministic Diagnostics (P1, 3 new modules)
- STORY-slim-016: Test Mapping & Stack-Aware Lint CLI (P2, 2 new modules)

## Recent Completions
- BUG-slim-003: CLI Migration Gaps — Prompt Inconsistencies & Implementation Mismatches (6 fixes, 20 tests)
- STORY-slim-014: Code is the Law — Deterministic Rule Migration (8 new modules, 10 CLI subcommands)
- STORY-slim-013: Reduce Cognitive Overload in PDCA Command Prompts

## Active Branches
- `main` — current production

## Key Decisions
- Post-migration audits should compare MD-defined rules vs Python CLI implementations systematically (BUG-slim-003)
- Migrating deterministic rules to CLI: backward compatibility with 2500+ keyword tests is the hardest part (STORY-slim-014)
- `(Mandatory)` labels on Phase 0 headers cause LLM extended thinking loops (STORY-slim-013)
- CI pipeline generation is project-level, not tool-format-level (STORY-slim-012)
- Rule injection should be command-scoped, not global (STORY-slim-011)

## Next Recommended Action
`/project-act STORY-slim-015` — Doctor & Release CLI (deterministic diagnostics)
