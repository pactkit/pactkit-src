# Project Context (Auto-generated)
> Last updated: 2026-03-21T23:45:00+08:00 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 4 (all archived to archive_202603.md)

## Current Stories
None — sprint board is empty.

## Recent Completions
- STORY-slim-016: Test Mapping & Stack-Aware Lint CLI — 2 new modules (test_mapper.py, lint_runner.py), 15 tests
- STORY-slim-015: Doctor & Release CLI — 3 new modules (doctor.py, backfill.py, issue_sync.py), 23 tests
- BUG-slim-003: CLI Migration Gaps — 6 fixes across prompts, cleaners, guards, validators

## Active Branches
- `main` — current production
- `feature/cython-build`

## Key Decisions
- Config resolution in CLI modules: `find_pactkit_yaml()` → `load_config(yaml_path)` two-step pattern (STORY-slim-016)
- Deterministic diagnostics are pure set-diff/regex/mtime with zero AI judgment (STORY-slim-015)
- Post-migration audits should compare MD rules vs CLI implementations systematically (BUG-slim-003)
- Migrating deterministic rules to CLI: backward compat with 2500+ keyword tests is the hardest part (STORY-slim-014)
- CI pipeline generation is project-level, not tool-format-level (STORY-slim-012)

## Next Recommended Action
Sprint board is empty. Run `/project-plan` to plan new work or `/project-design` for greenfield features.
