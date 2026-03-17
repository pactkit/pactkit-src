# Project Context (Auto-generated)
> Last updated: 2026-03-17 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-slim-006, STORY-slim-005, BUG-slim-001, STORY-slim-001

## Current Stories
- None active

## Recent Completions
- STORY-slim-006: Prompt Template Variables — 48 hardcoded paths replaced with {VISUALIZE_CMD}/{BOARD_CMD}/{SCAFFOLD_CMD}/{SKILLS_ROOT}/{PACTKIT_YAML} etc.; `_render_prompt()` uses sequential str.replace to avoid format_map limitations
- STORY-slim-005: FormatProfile Abstraction — frozen dataclass registry, VALID_FORMATS + PACTKIT_YAML_CANDIDATES auto-generated
- BUG-slim-001: project-init creates .claude in OpenCode env — env detection moved before pactkit init

## Active Branches
- `main` — current production (v2.0.2)

## Key Decisions
- **`_render_prompt(template, profile)`** (deployer.py): deploy-time template injection; uses sequential `str.replace` (not `format_map`) to safely handle complex user-facing placeholders like `{R1, R2, ...}`
- **11 template variables** fully documented in `FormatProfile` docstring (profiles.py) — source of truth
- **FormatProfile** (`profiles.py`): single source of truth for env paths; adding new format = one registry entry
- **Plugin legacy mode**: `_render_prompt(classic)` then `_rewrite_skills_prefix(_prefix)` for plugin/marketplace

## Next Recommended Action
- STORY-slim-002/003/004: Codex CLI integration (specs ready in codex-integration branch, preresearch complete)
- Version bump to 2.1.0 for FormatProfile + template system + Codex support release

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-slim-005, BUG-slim-001, STORY-slim-001, STORY-073, STORY-072

## Current Stories
- None active

## Recent Completions
- STORY-slim-005: FormatProfile Abstraction — frozen dataclass registry replaces 40+ hardcoded paths and opencode_format boolean anti-pattern
- BUG-slim-001: project-init creates .claude in OpenCode env — env detection moved before pactkit init call
- STORY-slim-001: Tool Integration Checklist (11 dimensions, 60+ checks, Codex pre-research complete)

## Active Branches
- `main` — current production (v2.0.2)

## Key Decisions
- **FormatProfile** (`src/pactkit/profiles.py`): Single source of truth for all env-specific paths and behaviors. Adding a new tool format requires only one registry entry.
- **Profile priority**: OpenCode > Classic > Codex in auto-detect; explicit `--format` always wins
- **excluded_agent_fields**: frozenset per-profile replaces hardcoded CLAUDE_ONLY_FIELDS in deployer
- **Legacy mode**: `_legacy_prefix` param preserved in _deploy_* functions for plugin/marketplace
- **OPENCODE_SKILLS_PREFIX constant removed** — use `get_profile("opencode").skills_path_var`

## Next Recommended Action
- STORY-slim-006: prompts 40+ hardcoded `~/.claude/skills/` paths → `{SKILLS_PATH}` placeholder rendered at deploy time
- STORY-slim-002/003/004: Codex CLI integration (specs in codex-integration branch, preresearch complete)
- Version bump to 2.1.0 for FormatProfile + Codex support

## Current Stories
- None active

## Recent Completions
- STORY-slim-001: Tool Integration Checklist (11 dimensions, 60+ checks, Codex pre-research)
- STORY-073: OpenCode Format Final Mile — Command Model Routing + Claude Code Residuals
- STORY-072: Multi-Developer Story ID Prefix — pactkit.yaml multi-path + developer field

## Active Branches
- `main` — current

## Key Decisions
- New tool integration: fill Dimension 0 capability matrix FIRST, determines strategy
- OpenCode: 17/17 capability matrix items PASS (vision via Bedrock is user-env issue)
- pactkit.yaml path: .claude/ (Claude Code), .opencode/ (OpenCode), .codex/ (Codex future)
- Model routing: in opencode.json command section, NOT in shared command frontmatter
- developer 前缀: STORY-slim-001 验证生效

## Next Recommended Action
`git push origin main` 推送最新改动，然后 `pactkit init --format opencode` 重新部署。
