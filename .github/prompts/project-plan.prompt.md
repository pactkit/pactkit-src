---
mode: agent
description: "Analyze requirements, create Spec and Story"
---

# Command: Plan (v1.3.0 Integrated Trace)
- **Usage**: `/project-plan "$ARGUMENTS"`
- **Agent**: System Architect

## 🧠 Phase 0: The Thinking Process
> **Execution Style**: Work through each phase incrementally — output progress as you go. Do NOT try to plan the entire Spec in your head before producing output. Start each phase, show your findings, then move to the next.
> **Tool Integration Note**: If the request involves adapting PactKit to a new AI coding tool (new `format` value like `cursor`, `trae`, etc.), **always start** by consulting `docs/guides/tool-integration-checklist.md`. Complete Dimension 0 (capability matrix) before writing any code.

1.  **Analyze Intent**: New feature (Expansion) or Bugfix/Refactor (Modification)?
2.  **Strategy**:
    - If **New Feature**: Focus on `system_design.mmd` (Architecture).
    - If **Modification**: Focus on pactkit-trace skill (Logic Flow).
3.  **Greenfield Detection**: Check if the request is a greenfield product ideation:
    - **Signals**: Keywords like "from scratch", "new app", "startup", "MVP", "product idea", "创业", "从零开始"; multi-story scope ("multiple features", "full system", "complete app"); empty sprint board; no existing source code files.
    - **If greenfield signals are detected**: Suggest to the user: "This looks like a greenfield product design. Consider using `/project-design` instead, which generates a full PRD and decomposes into multiple stories."
    - Ask the user to confirm the redirect. Do NOT auto-redirect.
    - **If user declines**: Proceed with `/project-plan` normally.
    - **If existing project** (stories on board, source files present): Skip this check — greenfield detection does not apply to established projects.

## 🛡️ Phase 0.5: Init Guard (Auto-detect)
1.  Check that `.github/pactkit.yaml`, `docs/product/sprint_board.md`, and `docs/architecture/graphs/` exist.yaml via `.github/pactkit.yaml`, `docs/product/sprint_board.md`, `docs/architecture/graphs/`).
2.  If exit code 1: project is not initialized — print the missing markers and **STOP**. Suggest running `/project-init`.
3.  If all exist: check config completeness (hooks, ci, issue_tracker sections). If stale, run `pactkit init --format copilot` (from terminal) and report what was added.
4.  If PASS: proceed to Phase 1.

## 🧠 Phase 0.7: Clarify Gate (Auto-detect Ambiguity)
> **PURPOSE**: Surface and resolve requirement ambiguity before the Spec is written. Better to clarify now than rewrite a Spec.
1.  **Detect Ambiguity**: Analyze the user's input (`$ARGUMENTS`) against these signals:
    - [High] No quantitative metrics ("高并发" without QPS, "fast" without benchmark)
    - [High] No boundary conditions ("user management" without specifying which operations)
    - [Medium] No technical constraints (no auth method, no framework specified)
    - [Low] Single sentence input (< 15 words) — likely under-specified but not blocking
    - [Medium] Vague quantifiers ("some", "many", "a few", "大量", "一些", "简单")
    - [Medium] No target user specified
2.  **Trigger Logic**:
    - 2 High + ≥ 1 Medium signals → **Auto-trigger** Clarify
    - ≥ 2 High signals (no Medium) → **Suggest** Clarify (ask user: "Input may be underspecified. Clarify? yes/skip")
    - 1 High + ≥ 2 Medium signals → **Suggest** Clarify
    - Otherwise → **Silent skip**
3.  **Greenfield Force-Trigger**: If Phase 0 detected a Greenfield project and the user chose to continue with `/project-plan` (not `/project-design`), **always trigger** Clarify regardless of score.
4.  **If triggered**: Generate 3–6 structured questions covering:
    - **Scope**: "What specific operations are included? Please list them."
    - **Users**: "Who is the target user? Are there multiple roles?"
    - **Constraints**: "Any technical constraints? (required framework, compatibility requirements)"
    - **Scale**: "Expected data volume / concurrency / user count?"
    - **Edge Cases**: "What should happen when [failure scenario]?"
    - **Non-Goals**: "What is explicitly NOT in scope?"
    - Ask questions in the user's language (Language Matching rule).
5.  **User Response**:
    - User answers all/some → merge into `enriched_input`; proceed to Phase 1 with `enriched_input`
    - User inputs "skip" or declines → proceed with original input (Clarify MUST NOT block Plan)
6.  **Output**: The enriched_input (original + answers) is used as context for Phase 1 onwards.

## 🎬 Phase 1: Archaeology (The "Know Before You Change" Step)
> **Subagent Scope Rule**: When delegating research to an Explore subagent, always provide a **bounded** prompt: target function/class, directory scope, file limit, and expected output. Never delegate open-ended "trace the whole codebase" tasks.

1.  **Visual Scan**: Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --focus <module> --depth 2` to see the targeted dependency graph. Only expand to `--mode class` or `--mode call` if the focused scan is insufficient.
2.  **Logic Trace (CRITICAL)** — use pactkit-trace skill:
    - If modifying existing logic, trace the current implementation.
    - *Goal*: Identify the exact function/class responsible for the logic.
    - **Delegation Template**: When using an Explore subagent for trace, formulate the prompt with:
      - **Target**: specific function or class name to trace
      - **Scope**: specific directory (e.g., `src/pactkit/generators/`)
      - **Limit**: read at most 8-10 files
      - **Output**: what to return (entry file, call chain, key data transformations)
      - Example: `Agent(subagent_type="Explore", prompt="Find the deploy() entry point in src/pactkit/generators/deployer.py. Trace the call chain to file writes. Read at most 8 files. Return: entry function, call chain list, key data transformations.")`
3.  **Topology-Aware Trace (Conditional)** — if `detect_topology(root)` includes `api_call` or `agent`:
    - For **api_call**: Run `api_convention_summary(root)` and include path prefixes, fetch function names, and total call count in the Archaeologist Report. This prevents API path convention bugs in downstream implementation.
    - For **agent**: Note orchestration edges from AgentParser (LangGraph/YAML/MCP) in the report so downstream changes respect agent flow.

## 🎬 Phase 2: Design & Impact
1.  **Diff**: Compare User Request vs Current Reality (from Phase 1).
2.  **Update HLD**: Modify `docs/architecture/graphs/system_design.mmd`.
    - *Rule*: Keep the `code_graph.mmd` as is (it updates automatically).

## 🎬 Phase 3.1: Story ID Generation
1.  Run `pactkit next-id` from the terminal to get the next Story ID (reads developer prefix from .github/pactkit.yaml, scans `docs/specs/`).
2.  **Output checkpoint**: Print "Story ID determined: {ID}. Writing Spec now."

## 🎬 Phase 3.2a: Scaffold + Metadata Table & Requirements
1.  **Scaffold**: Run `python3 .github/skills/pactkit-scaffold/scripts/scaffold.py create_spec "{ID}" "{title}"` to generate `docs/specs/{ID}.md` from SPEC_TEMPLATE. This creates all sections, tables, and Given/When/Then skeleton — format is guaranteed by Code.
2.  **Read**: Read `docs/specs/{ID}.md` to see the scaffolded template.
3.  **Edit placeholders** (use Edit tool, NOT Write):
    - Edit `Release | TBD` → `Release | {version}` (from `pyproject.toml`/`package.json`, NOT `.github/pactkit.yaml`)
    - Edit `(Description of the problem or feature)` → actual Background content from your Trace findings
    - Edit `## Target Call Chain` placeholder → actual call chain from Phase 1
    - Edit `### R1: (Requirement Name) (MUST)` → actual requirements using RFC 2119 keywords (MUST/SHOULD/MAY). Add more R{N} sections as needed.
4.  **Output checkpoint**: Print "Spec skeleton filled. Adding acceptance criteria."

## 🎬 Phase 3.2b: Acceptance Criteria & Implementation Steps
1.  **Edit AC** (use Edit tool): Replace `### AC1: (Scenario Name) (R1)` and its Given/When/Then placeholders with actual scenarios. The template already provides the `- **Given**` / `- **When**` / `- **Then**` structure — fill in the content. Add more AC{N} sections as needed.
    - Each Scenario SHOULD map to a verifiable test case in `docs/test_cases/`.
2.  **Edit Implementation Steps** (optional): If Phase 1 Trace identifies 2+ files to modify, replace the placeholder rows in `## Implementation Steps` with actual steps. The table skeleton (headers + separator) is already in the template.
3.  **Output checkpoint**: Print "Acceptance criteria written. Running security scope."

## 🎬 Phase 3.2c: Security Scope
1.  **MUST**: Run `pactkit sec-scope <changed-files>` from the terminal to auto-detect SEC-1~SEC-8 applicability.
2.  **Edit** the `## Security Scope` section already in the template: replace the placeholder SEC-1 row with actual SEC-* assessments from the output above. The table skeleton (Check/Applicable/Reason headers) is already in the template.
3.  **Fallback**: If `pactkit sec-scope` (run from terminal) is unavailable, manually Edit each SEC-1 through SEC-8 entry. Apply docs/tests-only shortcut if applicable (mark ALL N/A with Reason "docs/tests only").
4.  **Output checkpoint**: Print "Security scope filled. Running lint."

## 🎬 Phase 3.2d: Spec Lint Self-Check
1.  Run `python3 .github/skills/pactkit-scaffold/scripts/spec_linter.py docs/specs/{ID}.md`.
2.  If any ERROR or WARNING rules fire, self-correct the Spec immediately (you wrote it — you have authority to fix it). Re-run until `python3 .github/skills/pactkit-scaffold/scripts/spec_linter.py` reports 0 errors AND 0 warnings.
3.  This prevents the Spec from being rejected at Act Phase 0.5.
4.  **Output checkpoint**: Print "Spec lint passed (0 errors AND 0 warnings)."

## 🎬 Phase 3.3: Board, Memory & Handover
1.  **Board**: Add Story using `add_story`.
2.  **Memory MCP (Conditional)**: IF Memory MCP is available, use create_entities to store design context (decisions, target files, rationale) under entity `{STORY_ID}`. Record story dependencies if applicable.
3.  **Session Context Update**: Generate `docs/product/context.md` manually (Sprint Status, Current Stories, Recent Completions, Active Branches, Key Decisions, Next Recommended Action) to generate `docs/product/context.md`. Set "Last updated by" to `/project-plan`.
4.  **Handover**: "Trace complete. Spec created. Ready for Act."


---

## Rules Reference

# Core Protocol

## Session Context
On new session, check `.github/pactkit.yaml` exists. If not, run `pactkit init --format copilot` from the terminal.
If `.github/pactkit.yaml` does not exist (check `.github/`), run `pactkit init --format copilot` from the terminal to create it before proceeding.
Then read `docs/product/context.md` to understand project state before taking action.
If the file is missing, suggest `/project-init` to bootstrap the project.
If "Last updated" date is before today, suggest running `$daily-retro`.

## Visual First
Before modifying code:
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py` to view module dependency graph
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode class` for class inheritance
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode call --entry <func>` to trace call chains
- **PDCA Exemption**: When a PDCA command is active, the command's own visualize phases take precedence — skip Visual First.

## Strict TDD
- Write tests first (RED), then write implementation (GREEN)
- The agent MUST NOT skip TDD except when running `/project-hotfix`
- All tests must pass before committing

## Language Matching
- Match the user's language (Chinese→Chinese, English→English).
- Technical terms (function names, file paths, git commands) stay in original form.


# Sectional Write Protocol

## Rule
When generating **any file** (code, document, test, HTML, etc.) that will exceed **300 lines**:

1. **Write skeleton first**: Create the file with the structural framework (imports, class/function signatures, section headings) via a single Write call
2. **Edit block-by-block**: Fill in one logical block at a time, using Edit after each block before starting the next
3. **Checkpoint between blocks**: After each Edit, print a brief progress message (e.g., "Block 2/5 written.")
4. **Never accumulate**: Do NOT compose the entire file in reasoning before writing — write as you go

## Applies To — any file type over 300 lines
- Documents: PRD, specs, README, architecture guides
- Source code: large modules, multi-endpoint API files, data models
- Tests: test files with many test classes or scenarios
- HTML/templates: prototypes, page templates

## Does NOT Apply To
- Short files (< 300 lines): single Write is fine
- Small config files (YAML, JSON, TOML)

## Anti-Pattern (DO NOT)
```
Compose entire file in head → one Write call at the end
```

## Correct Pattern
```
Write skeleton → Edit block 1 → checkpoint → Edit block 2 → checkpoint → ...
```

# The Hierarchy of Truth
> **CRITICAL**: Code is NOT the law.
1.  **Tier 1**: **Specs** (`docs/specs/*.md`) & **Test Cases** (`docs/test_cases/*.md`).
2.  **Tier 2**: **Tests** (The verification of the law).
3.  **Tier 3**: **Implementation** (The mutable reality).

## Conflict Resolution Rules
- When Spec conflicts with code: **Spec takes precedence**, modify the code
- When Spec conflicts with tests: **Spec takes precedence**, modify the tests
- When the Spec itself is found to be incorrect: fix the Spec first, then sync code and tests

## RFC Protocol (Spec Amendment Escalation)
- If the Senior Developer determines a Spec requirement is technically infeasible, contradictory, or would violate security/architectural constraints, they MUST invoke the RFC Protocol rather than producing non-compliant code
- RFC Protocol: STOP implementation, report the infeasibility to the user, suggest alternatives, and wait for guidance
- This exception does NOT weaken the general principle (Spec > Code) — it adds a safety valve for genuinely impossible requirements

## Pre-existing Test Protocol
- If a pre-existing test fails during regression, **do not modify** the failing test or the code it tests
- STOP and report: which test failed, what it tests, which change caused it
- You MUST NOT assume you understand the design intent behind pre-existing tests

## Operating Guidelines
- Before modifying code, you must first read the relevant Spec (`docs/specs/`)
- Before modifying tests, you must first read the corresponding Test Case (`docs/test_cases/`)
- When unsure whether a Spec exists, use `Glob` to search `docs/specs/*.md` (covers STORY-*, HOTFIX-*, BUG-* prefixes)
- **Exemption**: `/project-plan` and `/project-design` create new Specs — they are exempt from "read Spec before modifying code" since the Spec does not yet exist.

# File Atlas

| Path | Purpose |
|------|---------|
| `docs/specs/{ID}.md` | **The Law** -- Requirement Specifications (Spec) |
| `commands/*.md` | **The Playbooks** -- Command Execution Logic |
| `docs/product/sprint_board.md` | Sprint Board -- Current Iteration Board |
| `docs/test_cases/{ID}_case.md` | Test Cases -- Gherkin Acceptance Scenarios |
| `docs/architecture/graphs/*.mmd` | Architecture Graphs -- Mermaid Architecture Diagrams |
| `tests/unit/` | Unit Tests |
| `tests/e2e/` | E2E Integration Tests |
| `docs/product/archive/` | Archived Stories |
| `docs/product/prd.md` | Product Requirements Document (PRD) |

# MCP Integration (Conditional)
> **PRINCIPLE**: All MCP instructions are conditional. If an MCP server is not available, skip the instruction gracefully.

## Available MCP Servers

### Context7 (`mcp__context7__*`)
- **Purpose**: Fetch up-to-date library documentation and code examples
- **When to use**: If you are implementing with an unfamiliar library API, or need to verify current API signatures
- **Tools**: `resolve-library-id` → `get-library-docs`
- **Trigger**: If you are about to write code using a third-party library and are unsure about the API

### shadcn (`mcp__shadcn__*`)
- **Purpose**: Search, browse, and install UI components from shadcn registries
- **When to use**: If the project has a `components.json` file in the project root (indicates shadcn is configured)
- **Tools**: `search_items_in_registries`, `view_items_in_registries`, `get_item_examples_from_registries`, `get_add_command_for_items`
- **Trigger**: If designing or implementing UI pages and `components.json` exists

### Playwright MCP (`mcp__playwright__*`)
- **Purpose**: Browser automation for testing — snapshots, clicks, screenshots, form filling
- **When to use**: If `mcp__playwright__browser_snapshot` tool is available in the current runtime
- **Tools**: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_take_screenshot`, `browser_fill_form`
- **Trigger**: If running browser-level QA checks (Check command Strategy B)

### Chrome DevTools MCP (`mcp__chrome-devtools__*`)
- **Purpose**: Performance tracing, console message inspection, network request analysis
- **When to use**: If `mcp__chrome-devtools__take_snapshot` tool is available in the current runtime
- **Tools**: `performance_start_trace`, `list_console_messages`, `list_network_requests`, `take_snapshot`, `take_screenshot`
- **Trigger**: If running browser-level QA checks that need performance or runtime diagnostics

### Memory MCP (`mcp__memory__*`)
- **Purpose**: Persistent knowledge graph for cross-session context — store architectural decisions, load prior context, record lessons learned
- **When to use**: If `mcp__memory__create_entities` tool is available in the current runtime
- **Tools**: `create_entities`, `create_relations`, `add_observations`, `search_nodes`, `read_graph`
- **Trigger**: If running Plan (store decisions), Act (load context), or Done (record lessons)
- **Entity naming**: Use `{STORY_ID}` (e.g., "STORY-037") as the entity name, `entityType: "story"`

### Draw.io MCP (`mcp__drawio__*`)
- **Purpose**: Open generated diagrams directly in Draw.io editor for instant visual verification and interactive editing
- **When to use**: If `mcp__drawio__open_drawio_xml` tool is available in the current runtime
- **Tools**: `open_drawio_xml`, `open_drawio_csv`, `open_drawio_mermaid`
- **Trigger**: After generating a `.drawio` XML file or when visualizing existing `.mmd` Mermaid files in Draw.io

## Usage by PDCA Phase

| Phase | MCP Server | Condition |
|-------|-----------|-----------|
| **Plan** | Memory | If `mcp__memory__*` tools are available |
| **Plan** | Draw.io MCP | If `mcp__drawio__*` tools are available (diagram generation) |
| **Design** | shadcn | If `components.json` exists in project root |
| **Design** | Draw.io MCP | If `mcp__drawio__*` tools are available (architecture visualization) |
| **Act** | Context7 | If implementing with unfamiliar library API |
| **Act** | Memory | If `mcp__memory__*` tools are available |
| **Check** | Playwright MCP | If `mcp__playwright__*` tools are available |
| **Check** | Chrome DevTools | If `mcp__chrome-devtools__*` tools are available |
| **Done** | Memory | If `mcp__memory__*` tools are available |

# Shared Protocols

## Lazy Visualize Protocol
> Referenced by: Act Phase 4, Done Phase 2

If source files changed (per `LANG_PROFILES[stack].source_dirs`) OR `code_graph.mmd` is missing, run visualize in all 3 modes (file, class, call). Else skip with log: "Graph up-to-date — no source changes".

## Test Mapping Protocol
> Referenced by: Act Phase 3, Check Phase 5, Done Phase 2.5, Hotfix Phase 2

Map changed source files to test files via `LANG_PROFILES[stack].test_map_pattern`. If no mapping can be determined, fall back to the full test suite.

## Context.md Canonical Format
> Referenced by: Init Phase 6, Plan Phase 3, Done Phase 4.5

Write `docs/product/context.md` using this format:
```markdown
# Project Context (Auto-generated)
> Last updated: {ISO timestamp} by {command}

## Sprint Status
{In Progress stories with IDs | Backlog count | Done count}

## Current Stories
{Active stories with brief descriptions}

## Recent Completions
{Last 3 completed stories, one line each}

## Active Branches
{git branch output, or "None" if no feature/fix branches}

## Key Decisions
{Last 5 lessons from lessons.md}

## Next Recommended Action
{If In Progress: `/project-act STORY-XXX` | If Backlog only: `/project-plan` | If empty: `/project-design`}
```

# Architecture Principles

> Derived from SOLID, DRY, 12-Factor App, and Defense-in-Depth practices.
> Violations of MUST rules are treated as bugs. SHOULD rules are advisory.

## 1. Single Source of Truth (DRY)
- Every configuration value, schema definition, or structural rule MUST be defined in exactly one place.
- Canonical locations:
  - Environment paths/capabilities → `profiles.py` (`FormatProfile`)
  - Document structure rules → `schemas.py` (`SPEC_REQUIRED_SECTIONS`, `BOARD_SECTIONS`, `CONTEXT_SECTIONS`, etc.)
  - Valid component sets → `config.py` (`VALID_AGENTS`, `VALID_COMMANDS`, `VALID_SKILLS`, `VALID_RULES`)
- When standalone scripts (board.py, scaffold.py) cannot import the library, they MUST inline the value with a comment pointing to the canonical source:
  ```python
  # Canonical: src/pactkit/schemas.py BOARD_SECTION_BACKLOG
  _BACKLOG = '## 📋 Backlog'
  ```
- When updating a canonical value, search all inline copies with `grep` and update them in the same commit.

## 2. Open-Closed Principle (OCP)
- Adding a new tool format (e.g., `cursor`, `trae`) MUST NOT require modifying existing functions.
- Pattern: add a new `FormatProfile` entry to `FORMAT_PROFILES` in `profiles.py`. All downstream code (`deployer`, `config`, `CLI`) auto-picks it up.
- Adding a new document type MUST only require adding constants to `schemas.py` and an entry to `SCHEMA_REGISTRY`.

## 3. Dependency Inversion (DIP)
- Prompt templates MUST NOT contain hardcoded environment-specific paths.
- Pattern: use named placeholders (`{SKILLS_ROOT}`, `{BOARD_CMD}`, `{PACTKIT_YAML}`) resolved at deploy time by `_render_prompt(template, profile)`.
- Functions MUST accept a `profile: FormatProfile` parameter instead of format-specific booleans (`opencode_format=True`) or manual path strings (`skills_prefix=".github/skills"`).

## 4. Liskov Substitution (LSP) — Deploy Chain Parity
- All deployer classes (ClassicDeployer, OpenCodeDeployer, etc.) MUST support the same user-facing feature set:
  - Selective deployment (read `.github/pactkit.yaml`)
  - Auto-merge on upgrade (`auto_merge_config_file`)
  - Legacy cleanup (`_cleanup_legacy`)
  - Project-level instructions file generation
- Format-specific features (e.g., hooks for GitHub Copilot, opencode.json for OpenCode) are extensions, not omissions.

## 5. Interface Segregation (ISP)
- Each `FormatProfile` exposes only the fields relevant to that format:
  - `commands_dir = None` for formats without custom commands
  - `excluded_agent_fields` removes fields invalid for that format
- Consumers MUST check `if profile.has_custom_commands` before deploying commands — not hardcoded format checks.

## 6. Defense-in-Depth (Security)
- **Path traversal**: All file writes use `atomic_write()` which creates parent directories safely.
- **Config isolation**: `_generate_config_if_missing(format=)` writes to the format-specific directory only. Never cross-write.
- **No secret leakage**: `_render_prompt()` variables are all path-based, never credential-based.
- **Standalone script safety**: Skill scripts (board.py, scaffold.py) MUST NOT execute arbitrary imports. Use `try/except ImportError` fallback for pactkit imports.

## 7. Template Rendering Safety
- Use sequential `str.replace()` in `_render_prompt()` — NOT `str.format_map()` or f-strings.
  - Reason: prompt templates contain user-facing complex keys like `{R1, R2, ...}`, `{score}`, `{NNN}` that cause `ValueError: Empty attribute` in Python's format parser.
- JSON literals in templates (`{"key": "value"}`) are naturally safe with sequential replacement — no escaping needed.
- When converting f-string prompt constants to template strings, add legacy variables (e.g., `{M}` for backticks) to the `_render_prompt` var_map.

## 8. Schema Consistency Gate
- Every document type with a structure schema in `schemas.py` SHOULD have a corresponding linter/validator.
- Currently enforced:
  - Spec → `spec_linter.py` (E001-E008, W001-W005) — **blocks /project-act**
  - Board → `board.py` regex parsing — **runtime enforcement**
- Currently advisory only:
  - context.md, lessons.md, test_case → referenced in playbook text via `{CONTEXT_SECTIONS}`, `{LESSONS_ROW_FORMAT}`
- When adding a new schema to `schemas.py`, consider whether it needs a linter gate or if prompt-level enforcement is sufficient.

## Quick Reference: Where to Make Changes

| Change Type | File to Edit | Auto-Propagation |
|-------------|-------------|------------------|
| New tool format | `profiles.py` → `FORMAT_PROFILES` | CLI, deployer, config, VALID_FORMATS |
| New document type | `schemas.py` → `SCHEMA_REGISTRY` | `pactkit schema`, playbooks via render_prompt |
| New template variable | `deployer.py` → `_render_prompt()` var_map | All deployed prompts |
| New spec rule | `schemas.py` + `spec_linter.py` | scaffold, playbooks |
| New prompt placeholder | `profiles.py` (if env-specific) or `schemas.py` (if doc-specific) | `_render_prompt()` |

### Credential Safety

NEVER print passwords, keys, or tokens to stdout.
NEVER commit secrets to version control.
