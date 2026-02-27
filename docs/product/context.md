# Project Context (Auto-generated)
> Last updated: 2026-02-27T20:00:00Z by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 80+ items archived
- **Current Version**: 1.5.0
- **Branch**: main

## Current Stories
None

## Recent Completions
- STORY-056: Security Check Scope Filtering — Plan generates Security Scope, Check skips non-applicable SEC-* checks
- BUG-026: Version Sync on Init/Update — auto-sync pactkit.yaml to __version__
- STORY-055: PDCA Quality Gates — security checklist, lesson scoring, impl steps

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02-27 | Extending an existing config section requires only 4 touch points (get_default_config, _rewrite_yaml, validate_config, generate_default_yaml) — no DEEP_MERGE_KEYS/_BACKFILL_KEYS/KNOWN_KEYS needed; prompt-level filtering is fully testable via string assertions (score: 21/25) | STORY-056 |
| 2026-02-27 | Version sync requires 4 coordinated changes in config.py: import __version__, get_default_config(), _rewrite_yaml(), auto_merge_config_file() version-staleness check before if added: — full-config fixture tests must include 'version': __version__ (score: 21/25) | BUG-026 |
| 2026-02-27 | Adding new config sections requires 7 coordinated config.py touch points plus 2 full-config fixture updates; when restructuring prose into structured checklist, preserve pre-existing keyword tests by adding OWASP context notes (score: 22/25) | STORY-055 |
| 2026-02 | Deployment completeness tests must assert exact counts and exact names — importing VALID_* sets and asserting set(found) == VALID_* creates a self-updating contract | STORY-054 |
| 2026-02 | Impact-based reverse BFS is a clean extension to forward BFS — extract shared _scan_call_edges() helper; impact() maps callers to test files via stem-based pattern | STORY-053 |

## Next Recommended Action
`/project-plan` — board is empty, ready for next story
