# Project Context (Auto-generated)
> Last updated: 2026-03-19 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-slim-010, STORY-slim-009, STORY-slim-008, STORY-slim-007, STORY-slim-006, STORY-slim-005, BUG-slim-001, STORY-slim-001

## Current Stories
- None active

## Recent Completions
- STORY-slim-010: Version Sync Fix & Deployer DRY Refactor — fixed .claude/pactkit.yaml version, extracted 3 helpers (_build_rule_id_to_key, _build_rule_id_to_filename, _render_skill_md), 2338 tests green
- STORY-slim-009: Lazy Rule Loading — instructions 3 core files only, 6 on-demand via AGENTS.md @refs, -62% tokens/turn
- STORY-slim-008: Deploy Chain Parity — OpenCode matches Classic feature set

## Active Branches
- `main` — current production (v2.1.1)
- `codex-integration` — blocked (no Codex API key)

## Key Decisions
- **DRY helpers** (STORY-slim-010): deployer.py reverse map builders extracted as module-level helpers; inspect.getsource() tests prevent regression
- **Lazy rule loading** (ADR-008): RULES_CORE_FILES + RULES_ONDEMAND_FILES + RULES_INSTRUCTIONS_CORE
- **AGENTS.md @reference pattern**: OpenCode's equivalent of Claude Code @import lazy loading

## Next Recommended Action
- Codex integration when API key available (STORY-slim-002/003/004)
- Or: further code quality work (type annotations, _generate_project_claude_md refactor)
