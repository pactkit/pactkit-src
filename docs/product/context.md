# Project Context (Auto-generated)
> Last updated: 2026-03-18 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-slim-009, STORY-slim-008, STORY-slim-007, STORY-slim-006, STORY-slim-005, BUG-slim-001, STORY-slim-001

## Current Stories
- None active

## Recent Completions
- STORY-slim-009: Lazy Rule Loading — instructions 3 core files only, 6 on-demand via AGENTS.md @refs, -62% tokens/turn
- STORY-slim-008: Deploy Chain Parity — OpenCode matches Classic feature set
- STORY-slim-007: Document Schema Registry — schemas.py single source of truth

## Active Branches
- `main` — current production (v2.1.0)
- `codex-integration` — rebased to main, specs need re-creation

## Key Decisions
- **Lazy rule loading** (ADR-008): RULES_CORE_FILES (01/02, always-load) + RULES_ONDEMAND_FILES (03-08, @reference) + RULES_INSTRUCTIONS_CORE (includes user 09-credential-safety)
- **User-managed files** (09-*, 10-*) must NOT be in RULES_FILES to avoid KeyError in RULES_MODULES lookup
- **AGENTS.md @reference pattern**: OpenCode's equivalent of Claude Code @import lazy loading

## Next Recommended Action
- Codex integration: re-create STORY-slim-002/003/004 specs on codex-integration branch
- Or: version bump to v2.1.1 for lazy loading release
