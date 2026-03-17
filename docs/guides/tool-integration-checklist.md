# PactKit Tool Integration Checklist

> **Purpose**: This checklist ensures that adapting PactKit to a new AI coding tool is complete and consistent. It was distilled from the OpenCode integration (STORY-069/070/071/072/073 + BUG-035 + 1 Hotfix) — 29 files, 3939 insertions, 7 rounds of rework.
>
> **Usage**: Fill in the `Target Tool` column in Dimension 0 first. That determines which of Dimensions 1–10 apply and which need degraded fallback strategies.

---

## Dimension 0: Tool Capability Matrix (MUST complete first)

Before writing any code, fill in the `Target Tool` column. Each row determines your integration strategy.

### 0.1 Capability Survey

| Capability | Claude Code | OpenCode | Codex CLI | Target Tool |
|------------|-------------|----------|-----------|-------------|
| **Agents (multi-role)** | `.claude/agents/*.md` | `agents/*.md` (`mode: subagent`) | None (single agent) | ？ |
| **Commands (custom)** | `.claude/commands/*.md` | `commands/*.md` (frontmatter) | Different format | ？ |
| **Skills (scripts)** | `.claude/skills/*/` | `skills/*/SKILL.md` | `.codex/skills/` | ？ |
| **Rules (modules)** | `rules/*.md` + `@import` | `rules/*.md` + `instructions` | None (only AGENTS.md) | ？ |
| **Global config dir** | `~/.claude/` | `~/.config/opencode/` | `~/.codex/` | ？ |
| **Project config dir** | `.claude/` | `.opencode/` | `.codex/` | ？ |
| **Project instruction file** | `.claude/CLAUDE.md` | `./AGENTS.md` | `./AGENTS.md` | ？ |
| **`@import` rule loading** | Supported | Not supported (use `instructions`) | Not supported | ？ |
| **Model routing (agent level)** | None (prompt-level only) | `agent.{name}.model` in config | None (single model) | ？ |
| **Model routing (command level)** | None | `command.{name}.model` in config | None | ？ |
| **Permission config** | `settings.json` | `opencode.json` `permission` | Sandbox mode | ？ |
| **MCP support** | `settings.json` mcpServers | `opencode.json` `mcp` | Limited | ？ |
| **Multiple providers** | Anthropic only | 75+ providers (npm packages) | OpenAI only | ？ |
| **Image/Vision** | Native | Requires `capabilities` declaration | Unknown | ？ |
| **npm package system** | None | `@ai-sdk/*` per provider | None | ？ |
| **`pactkit.yaml` location** | `.claude/pactkit.yaml` | `.opencode/pactkit.yaml` | `.codex/pactkit.yaml`? | ？ |

### 0.2 Integration Strategy Decision

Based on the survey, choose a strategy for each capability:

| Capability | Strategy: Full Deploy | Strategy: Degraded Fallback |
|------------|----------------------|-----------------------------|
| **Has agents** | Deploy all 9 agent files with format conversion | Encode all 9 roles into AGENTS.md/rules with prompt-level routing |
| **Has commands** | Deploy all 11 commands with frontmatter conversion | Embed playbooks into AGENTS.md; trigger via `/` prefix convention |
| **Has skills** | Deploy all 10 skills, adapt discovery mechanism | Place scripts in global dir; use absolute paths in playbooks |
| **Has rules** | Deploy 7 rule modules, adapt loading mechanism | Inline all rules into one master file (AGENTS.md) |
| **Has model routing** | Config-level routing (agent/command model fields) | Prompt-level routing (Model Guard Protocol in AGENTS.md) |
| **Has `@import`** | Use `@import` references in main file | Use `instructions` glob / directory scan / full inline |
| **Multi-provider** | Implement `_resolve_model_id()` shortname → provider/id | Write model ID directly (no resolution needed) |
| **Single provider** | N/A | Write model ID directly |
| **Has permission config** | Generate permission block in tool config | Skip (tool uses other safety mechanism) |

---

## Dimension 1: Tool Research (Before Any Code)

| # | Check | Detail | Verification |
|---|-------|--------|--------------|
| 1.1 | **Read all official docs** | agents, commands, skills, rules, config, permissions, MCP — every concept | List doc URLs |
| 1.2 | **Config format diff** | Compare frontmatter fields, YAML vs JSON, required vs optional fields | Make a diff table |
| 1.3 | **File system conventions** | Global dir (`~/.config/tool/`), project dir (`.tool/`), file naming | Confirm paths |
| 1.4 | **Rules loading mechanism** | `@import`? `instructions` field? directory auto-scan? | Test with a toy rule file |
| 1.5 | **Model routing mechanism** | Agent-level? Command-level? Config file? Not supported? | Compare with Claude Code |
| 1.6 | **Permission model** | How does the tool restrict dangerous operations? What format? | Config example |
| 1.7 | **MCP support** | `remote`/`local`/`stdio` types? config format? | End-to-end MCP test |
| 1.8 | **Image/Vision support** | How does tool declare vision capability? Auto-detected or explicit? | Paste image test |
| 1.9 | **`settings.json` equivalents** | What replaces Claude Code's `settings.json` for user preferences? | Mapping table |
| 1.10 | **Dual-layer architecture** | Does the tool distinguish global config (`~/.tool/`) from project config (`.tool/`)? | Architecture diagram |

**Lesson from OpenCode**: Skipping 1.2 caused STORY-070 (wrong agent format, wrong command frontmatter). Skipping 1.4 caused STORY-071 (tried @import, doesn't work in OpenCode).

---

## Dimension 2: Deployment Architecture (`deployer.py`)

| # | Check | Detail | Reference |
|---|-------|--------|-----------|
| 2.1 | **Add `_deploy_{tool}()` function** | Main orchestrator function, mirrors `_deploy_opencode()` pattern | STORY-069 |
| 2.2 | **Add format branch in `deploy()`** | `elif format == "{tool}": _deploy_{tool}(target)` | STORY-069 |
| 2.3 | **Separate global from project-level** | Global deploy (`pactkit init`) writes only shared resources. Project-level handled by `/project-init` playbook | BUG-035 |
| 2.4 | **Two-layer directory structure** | Global: `~/.config/{tool}/`, Project: `.{tool}/` — never mix them | BUG-035 |
| 2.5 | **Add global config writer** | `_update_global_{tool}_config()` with merge strategy — preserve user fields, update managed fields | STORY-071 R7 |
| 2.6 | **Add project config generator** | `_deploy_{tool}_project_config()` for `/project-init` playbook to call | BUG-035 |

**Lesson from BUG-035**: First attempt wrote `opencode.json` to the global deploy target. Wrong — `opencode.json` is project-level, `pactkit init` should not create it.

---

## Dimension 3: Agent Format Conversion

*Skip if target tool has no agents concept — use Dimension 0.2 fallback instead.*

| # | Check | Detail | Reference |
|---|-------|--------|-----------|
| 3.1 | **Identification method** | Filename as name (OpenCode) vs `name:` frontmatter (Claude Code) | STORY-070 |
| 3.2 | **Mode field** | Does tool need `mode: subagent`? `mode: primary`? No mode field? | STORY-070 |
| 3.3 | **Tools format** | String `"Read, Write"` vs record `{ read: true }` vs array `["read"]` | STORY-069 R7 |
| 3.4 | **Model field** | Should `model: inherit` be omitted? Is format shortname or `provider/id`? | STORY-070 |
| 3.5 | **Remove previous tool's fields** | Strip `permissionMode`, `memory`, `skills`, or other Claude Code-specific fields | STORY-070 |
| 3.6 | **Routing reference path** | Agent footer's routing reference must point to the new tool's global rules file | STORY-070 |
| 3.7 | **opencode_format flag pattern** | Use a boolean flag `{tool}_format=False` in `_deploy_agents()` to branch logic | STORY-069 |

**Lesson from STORY-070**: Initial OpenCode agents still had `name:`, `permissionMode`, `memory`, `skills` — all Claude Code artifacts. Always compare against the official agent format doc.

---

## Dimension 4: Command Format Conversion

*If target tool has no commands concept, skip — embed playbooks in AGENTS.md.*

| # | Check | Detail | Reference |
|---|-------|--------|-----------|
| 4.1 | **Permission declaration** | `allowed-tools: [...]` → `agent: build` → other format? | STORY-070 |
| 4.2 | **Model routing location** | In frontmatter `model:`? In external config? Not supported? | STORY-073 |
| 4.3 | **Model ID in shared files** | **Never write provider-specific model IDs into shared command files** — put them in user-local config | Hotfix |
| 4.4 | **Argument syntax** | `$ARGUMENTS` / `$1` / `$2` compatible? | Verify with tool docs |
| 4.5 | **Description field** | Is `description:` required? Different format? | STORY-070 |
| 4.6 | **Conversion function** | `_convert_command_frontmatter_{tool}(content)` function for format conversion | STORY-070 |

**Lesson from Hotfix**: Model routing was first implemented by writing `nexus-anthropic-bedrock/claude-sonnet-4.6` into command frontmatter — a provider-specific internal ID that leaked into shared files. Always separate: what goes in shared files (generic) vs local config (user-specific).

---

## Dimension 5: Rules Loading

| # | Check | Detail | Reference |
|---|-------|--------|-----------|
| 5.1 | **`@import` supported?** | If no, must use alternative — `instructions` glob, directory scan, or full inline | STORY-071 |
| 5.2 | **Alternative loading mechanism** | `instructions: ["rules/*.md"]` (OpenCode) / directory auto-scan / direct config field | STORY-071 |
| 5.3 | **Main rules file name** | `CLAUDE.md` (Claude Code) → `AGENTS.md` (OpenCode/Codex) → `{tool}.md`? | STORY-071 |
| 5.4 | **Slim vs inline** | If `@import` not supported: slim main file + modular files + instructions glob | STORY-071 |
| 5.5 | **File size limit** | Target tool's context window — does inlining 12KB into one file cause issues? | Test with tool |
| 5.6 | **`_deploy_agents_md_slim()` function** | Writes slim header file; rules loaded via config mechanism | STORY-071 R6 |

**Lesson from STORY-071**: Inlining all rules into one `AGENTS.md` (12KB, 273 lines) worked technically but was poor practice. When `@import` isn't supported, use `instructions` glob to load modular files instead.

---

## Dimension 6: Skills Format

| # | Check | Detail | Reference |
|---|-------|--------|-----------|
| 6.1 | **Discovery mechanism** | Filename scan? `SKILL.md` frontmatter? Registry file? | STORY-069 |
| 6.2 | **Required frontmatter** | `name` + `description` (OpenCode) or other fields? | STORY-069 |
| 6.3 | **Script path prefix constant** | Add `{TOOL}_SKILLS_PREFIX = "~/.config/{tool}/skills"` constant | STORY-069 |
| 6.4 | **`_rewrite_skills_prefix()`** | Pass new prefix to existing function — no new function needed | STORY-069 |
| 6.5 | **Verify no `~/.claude/` leakage** | After deploy, check no commands/agents contain the old prefix | STORY-073 |

---

## Dimension 7: `pactkit.yaml` Config File

| # | Check | Detail | Reference |
|---|-------|--------|-----------|
| 7.1 | **Add new path to `PACTKIT_YAML_CANDIDATES`** | `['.claude/pactkit.yaml', '.opencode/pactkit.yaml', '.{tool}/pactkit.yaml']` | STORY-072 |
| 7.2 | **Update `resolve_pactkit_yaml_dir()`** | Detect `.{tool}/` directory presence, write config there | STORY-072 |
| 7.3 | **Update `_generate_config_if_missing()`** | Uses `resolve_pactkit_yaml_dir()` — should work automatically | STORY-072 |
| 7.4 | **Add `command_models` defaults** | If tool supports command-level model routing, add defaults to schema | STORY-073 |
| 7.5 | **Test multi-path in CI** | CI runner has no `.{tool}/` — verify `load_config()` returns defaults gracefully | STORY-072 |

---

## Dimension 8: Playbook and Prompt Text

| # | Check | Detail | Reference |
|---|-------|--------|-----------|
| 8.1 | **Init Guard markers** | Update to `(.claude/ OR .opencode/ OR .{tool}/) pactkit.yaml exists` | STORY-072 |
| 8.2 | **`/project-init` conditional branch** | `Claude Code → CLAUDE.md`, `OpenCode → AGENTS.md`, `{tool} → {tool}-specific file` | STORY-073 |
| 8.3 | **Release field in `/project-plan`** | "read from `pactkit.yaml` in `.claude/` or `.opencode/` or `.{tool}/`" | STORY-072 |
| 8.4 | **Doctor/Sprint workflow paths** | Grep for hardcoded paths in `skills.py` and `workflows.py` | STORY-072 |
| 8.5 | **Check for reverse instructions** | Search for "Do NOT create X in .{tool}/" — delete old negative instructions | STORY-072 |
| 8.6 | **YAML comment generalization** | Comments in generated `pactkit.yaml` must not reference any specific tool path | STORY-073 |
| 8.7 | **Source docstrings** | `skills.py` and other modules must mention all supported tool paths | STORY-073 |

**Lesson from STORY-072**: There was an active instruction "Do NOT create `pactkit.yaml` in `.opencode/`" — a direct contradiction from an earlier design decision. Always search for negative/prohibitive instructions before finalizing.

---

## Dimension 9: CLI and External Config

| # | Check | Detail | Reference |
|---|-------|--------|-----------|
| 9.1 | **`init` `--format` choices** | Add `"{tool}"` to `init_parser` choices | STORY-069 |
| 9.2 | **`update` `--format` choices** | Add `"{tool}"` to `update_parser` choices | STORY-069 |
| 9.3 | **`upgrade` `--format` choices** | Add `"{tool}"` to `upgrade_parser` choices | STORY-070 |
| 9.4 | **Global config merge strategy** | Preserve user fields (`provider`, `apiKey`, etc.), only update managed fields (`instructions`, `command`) | STORY-071 |
| 9.5 | **Permission config template** | What dangerous operations to deny by default? `.env` file protection? | STORY-071 |
| 9.6 | **MCP config template** | Which public no-auth MCP servers to pre-configure? (context7, etc.) | STORY-071 |
| 9.7 | **Model ID never in shared config** | Any auto-generated config that ships as part of PactKit must not contain provider-specific model IDs | Hotfix |

---

## Dimension 10: Verification and Release

| # | Check | Detail | Reference |
|---|-------|--------|-----------|
| 10.1 | **Docker container test** | `docker run python:3.12-slim` → `pip install pactkit` → `pactkit init --format {tool}` | Release |
| 10.2 | **File structure check** | All expected dirs and files created at correct paths | Container test |
| 10.3 | **Agent format check** | `mode:`, no `name:`, record tools, no Claude-only fields | Container test |
| 10.4 | **Command format check** | No `allowed-tools:`, correct agent field, no model: in frontmatter | Container test |
| 10.5 | **Config file check** | `pactkit.yaml` written to `.{tool}/` not `.claude/`, `developer: ""` present | Container test |
| 10.6 | **Global config check** | Tool config has managed fields (`instructions`, etc.), user fields preserved | Container test |
| 10.7 | **CI compatibility** | Tests pass without the target tool installed (no `~/.config/{tool}/` on runner) | CI run |
| 10.8 | **README update** | Add new tool to Quick Start, deployment architecture, config reference | Release |
| 10.9 | **Docs site update** | All 8+ pages: index, installation, configuration, agents, commands, skills, workflow, MCP | Release |
| 10.10 | **Landing page update** | Hero text, Quick Start steps — must not say "Claude Code only" | Release |
| 10.11 | **PyPI version bump** | Bump minor version (x.Y.z → x.Y+1.0) for new tool support | Release |
| 10.12 | **Shared files are generic** | No provider names, internal URLs, or user-specific IDs in deployed files | Hotfix lesson |

---

## Rework Log (OpenCode Integration)

Use this table as a reference for how things went wrong and what the fix was:

| Round | Problem | Root Cause | Fix |
|-------|---------|------------|-----|
| BUG-035 | `opencode.json` placed in global dir | Misunderstood dual-layer architecture | Moved to project-level; added global config writer |
| STORY-070 | Agent had wrong format (name, tools, fields) | Didn't read official agent format docs | Added `opencode_format` flag with full field transformation |
| STORY-070 | Command still used `allowed-tools` | Forgot to convert command frontmatter | Added `_convert_command_frontmatter_opencode()` |
| STORY-071 | AGENTS.md was 12KB monolith | Assumed `@import` worked | Slimmed to 14 lines + modular `rules/*.md` + instructions glob |
| STORY-071 | No permission/MCP config | Out of scope initially | Added to project-level config generator |
| STORY-072 | `pactkit.yaml` hardcoded to `.claude/` | Config path tied to Claude Code | Multi-path lookup + env-aware generation |
| STORY-072 | 10+ playbook locations with hardcoded paths | Scattered hardcodes | Systematic grep + update all 10 locations |
| STORY-073 | Command model routing didn't work | `model:` not added to command files | Moved model routing to `opencode.json` `command` section |
| STORY-073 | `project-init` always created CLAUDE.md | No conditional branch | Added `if OpenCode: create AGENTS.md else: create CLAUDE.md` |
| Hotfix | Internal provider name leaked into shared files | Model ID written to command frontmatter | Model ID moved to user-local `opencode.json` only |
