# Project Context (Auto-generated)
> Last updated: 2026-02-28T12:00:00Z by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 80+ items archived
- **Current Version**: 1.5.0
- **Branch**: main

## Current Stories
None

## Recent Completions
- STORY-057: Playbook Implicit Instruction Cleanup — removed unverifiable Step 1.5, added [High]/[Medium] signal labels
- STORY-056: Security Check Scope Filtering — Plan generates Security Scope, Check skips non-applicable SEC-* checks
- BUG-026: Version Sync on Init/Update — auto-sync pactkit.yaml to __version__

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02-28 | Playbook instructions that reference unobservable state (e.g., "if last test run < 30s") are dead code for LLMs — remove rather than try to make them work; when a decision tree uses High/Medium signal classification, always label signals explicitly | STORY-057 |
| 2026-02-27 | Extending an existing config section requires only 4 touch points (vs 7 for a new section); prompt-level filtering logic is fully testable via string assertions | STORY-056 |
| 2026-02-27 | Version sync requires 4 coordinated changes in config.py; full-config fixture tests must include 'version': __version__ | BUG-026 |
| 2026-02-27 | Adding new config sections requires 7 coordinated config.py touch points plus 2 full-config fixture updates | STORY-055 |
| 2026-02 | Deployment completeness tests must assert exact counts and exact names — importing VALID_* sets and asserting set(found) == VALID_* creates a self-updating contract | STORY-054 |

## Next Recommended Action
`/project-plan` — board is empty, ready for next story
