# Project Context (Auto-generated)
> Last updated: 2026-03-17 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-slim-008, STORY-slim-007, STORY-slim-006, STORY-slim-005, BUG-slim-001, STORY-slim-001

## Current Stories
- None active

## Recent Completions
- STORY-slim-008: Deploy Chain Parity — `_deploy_opencode()` now reads pactkit.yaml, calls auto_merge/cleanup_legacy/_generate_project_agents_md/_print_mcp_recommendations; `_generate_config_if_missing(format=)` is format-aware
- STORY-slim-007: Document Schema Registry — `schemas.py` as single source of truth; spec_linter imports schemas; scaffold/board inline with source-of-truth comment; `{CONTEXT_SECTIONS}` and `{LESSONS_ROW_FORMAT}` injected into render_prompt; `pactkit schema` CLI command added
- STORY-slim-006: Prompt Template Variables — 48 hardcoded paths → 11 template variables via `_render_prompt()`

## Active Branches
- `main` — current production (v2.0.2)
- `codex-integration` — preresearch complete, specs ready for implementation

## Key Decisions
- **schemas.py** (`src/pactkit/schemas.py`): single source of truth for all 5 doc structure types; standalone scripts (board.py, scaffold.py) inline copies with source-of-truth comment; spec_linter.py imports directly with fallback
- **_deploy_opencode parity**: Added auto_merge + _cleanup_legacy + _generate_project_agents_md + _print_mcp_recommendations_opencode; no premature _deploy_standard() abstraction
- **`_generate_config_if_missing(format=)`**: Now accepts format param, uses resolve_pactkit_yaml_dir(format=) for correct path selection

## Next Recommended Action
- Version bump to 2.1.0 for FormatProfile + schemas + deploy parity release
- Then: codex-integration branch — start STORY-slim-002 (Codex CLI deploy architecture + Agent TOML)
