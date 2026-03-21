# Project Context (Auto-generated)
> Last updated: 2026-03-21T23:30:00+08:00 by /project-done

## Sprint Status
Backlog: 1 (STORY-slim-016) | In Progress: 0 | Done: 14 stories

## Current Stories
- STORY-slim-016: Test Mapping & Stack-Aware Lint CLI (P2, 2 new modules)

## Recent Completions
- STORY-slim-015: Doctor & Release CLI — 3 new modules (doctor.py, backfill.py, issue_sync.py), 23 tests
- BUG-slim-003: CLI Migration Gaps — 6 fixes across prompts, cleaners, guards, validators
- STORY-slim-014: Code is the Law — 8 new modules, 10 CLI subcommands

## Active Branches
- `main` — current production

## Key Decisions
- Deterministic diagnostics (doctor, backfill, issue-sync) are pure set-diff/regex/mtime with zero AI judgment (STORY-slim-015)
- Post-migration audits should compare MD rules vs CLI implementations systematically (BUG-slim-003)
- Migrating deterministic rules to CLI: backward compat with 2500+ keyword tests is the hardest part (STORY-slim-014)
- `(Mandatory)` labels on Phase 0 headers cause LLM extended thinking loops (STORY-slim-013)
- CI pipeline generation is project-level, not tool-format-level (STORY-slim-012)

## Next Recommended Action
`/project-act STORY-slim-016` — Test Mapping & Stack-Aware Lint CLI
