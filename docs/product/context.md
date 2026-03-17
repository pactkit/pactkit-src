# Project Context (Auto-generated)
> Last updated: 2026-03-17 by /project-plan

## Sprint Status
Backlog: 2 | In Progress: 0 | Done: STORY-slim-006, STORY-slim-005, BUG-slim-001, STORY-slim-001

## Current Stories
- STORY-slim-007: Document Schema Registry — schemas.py as single source of truth for all doc formats (Backlog, P1)
- STORY-slim-008: Deploy Chain Parity — OpenCode missing load_config/auto_merge/cleanup/project-AGENTS.md (Backlog, P1)

## Recent Completions
- STORY-slim-006: Prompt Template Variables — 48 hardcoded paths → 11 template variables via `_render_prompt()`
- STORY-slim-005: FormatProfile Abstraction — frozen dataclass registry, eliminated opencode_format bool
- BUG-slim-001: project-init env detection before pactkit init

## Active Branches
- `main` — current production (v2.0.2)

## Key Decisions
- **Document Schema Gap**: 7 doc types, 47 rules found; only 12 code-enforced (spec_linter), 13 prompt-only, 7 undocumented
- **Deploy Chain Gap**: `_deploy_opencode()` missing 6 functions vs `_deploy_classic()` — no selective deploy, no auto-merge, no project-level AGENTS.md
- **schemas.py**: New file to centralize all document structure rules (Spec sections, Board headers, context.md sections, lessons.md format)
- **Execution order**: STORY-slim-007 first (schemas), then STORY-slim-008 (deploy parity), then Codex integration

## Next Recommended Action
Start STORY-slim-007: create schemas.py and wire up spec_linter + scaffold + board consumers
