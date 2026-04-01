---
mode: agent
description: "Implement code per Spec, strict TDD"
---

# Command: Act (v1.3.0 Stack-Aware)
- **Usage**: `/project-act $ARGUMENTS`
- **Agent**: Senior Developer

## 🧠 Phase 0: The Thinking Process
> **Execution Style**: Work through each phase incrementally — output progress as you go. Do NOT try to plan all implementation steps in your head before producing output.
1.  **Read Law**: Read the Spec (`docs/specs/`) carefully.
2.  **RFC Gate (Feasibility Check)**: If you identify a requirement in the Spec that is technically infeasible, contradictory, or would require violating a security/architectural constraint, invoke the **RFC Protocol**:
    - **STOP** implementation immediately. Do NOT write any code.
    - **Report** to the user: (a) quote the exact problematic requirement from the Spec, (b) explain why it is infeasible (technical reasoning), (c) suggest an alternative approach.
    - You MUST NOT modify the Spec unilaterally — only the user (or Architect via a new `/project-plan` cycle) may amend Tier 1.
    - Wait for user guidance before proceeding.
3.  **Locate Target**: Which file/function needs surgery?
4.  **Detect Stack & Select Stack Reference**: Identify the project type from source files (`.py`, `.ts`/`.tsx`, `.go`, `.java`). Apply the corresponding language-specific best practices throughout implementation and testing.
5.  **Memory MCP (Conditional)**: IF Memory MCP is available, use search_nodes to load prior context for {STORY_ID} — retrieve architectural decisions and design rationale from the Plan phase.

## 🛡️ Phase 0.5: Spec Lint Gate (MUST)
> **PURPOSE**: Non-AI structural validation — ensures "Spec is Law" has physical enforcement before any code is written.
1.  **Run Linter**: Execute the Spec Linter on the current Story's spec:
    ```bash
    python3 .github/skills/pactkit-scaffold/scripts/spec_linter.py docs/specs/{STORY_ID}.md
    ```
    Replace `{STORY_ID}` with the actual Story ID from `$ARGUMENTS` (e.g., `STORY-042`).
2.  **If ERRORs found**: **STOP**. Output all ERROR and WARN items. Instruct the user:
    > "Spec Lint failed. Fix the issues above in `docs/specs/{STORY_ID}.md`, then re-run `/project-act`."
    Do NOT proceed to Phase 1.
3.  **If WARNs only**: Output the WARN list, then **continue** to Phase 1.
4.  **If all pass**: Continue silently to Phase 1.

## 📊 Phase 0.6: Consistency Check (Lightweight)
> **PURPOSE**: Quick pre-flight to verify artifacts exist. Full alignment analysis is deferred to `/project-check` (normal workflow).
> **NON-BLOCKING**: This phase NEVER stops Act.
1.  **Spec exists?**: Check if `docs/specs/{STORY_ID}.md` exists. If not: WARN "Spec not found".
2.  **Board entry exists?**: Check if `{STORY_ID}` appears in `docs/product/sprint_board.md`. If not: WARN "Board entry not found".
3.  **Move to In Progress**: If `{STORY_ID}` is found on the board, move it to In Progress section.
4.  **Continue**: Regardless of findings, proceed to Phase 1.

## 🎬 Phase 1: Precision Targeting
1.  **Targeted Visual Scan**: Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --focus <module>` only (single targeted mode). For large codebases, add `--depth 2`. Do NOT run full 3-mode visualize here — that is handled by Phase 4 Lazy Visualize after implementation.
2.  **Trace Verification** — use pactkit-trace skill:
    - Before touching any code, confirm the call site and ensure you don't break existing callers.
3.  **Topology-Aware Trace (Conditional)** — if `detect_topology(root)` includes `api_call` or `agent`:
    - For **api_call**: Run `api_convention_summary(root)` to check API path prefixes and fetch function conventions. Use these conventions when writing new API calls to maintain consistency.
    - For **agent**: Check AgentParser output for orchestration edges so new code doesn't break agent flow.

## 🎬 Phase 2: Test Scaffolding (TDD)
1.  **Constraint**: DO NOT write source code yet.
2.  **Action**: Create a reproduction test case in `tests/unit/`.
    - Use the knowledge from Phase 1 to mock/stub dependencies correctly.

## 🎬 Phase 3: Implementation
1.  **Write Code**: Implement logic in the appropriate source directory.
    - **Context7 (Conditional)**: IF implementing with an unfamiliar library API, use Context7 MCP to fetch up-to-date documentation before writing code.
2.  **TDD Loop (Safe Iteration)**: Run ONLY the tests created in Phase 2. Loop until GREEN.
    - Do NOT include pre-existing tests in this loop.
    - **Iteration Cap**: Maximum **5 iterations**. If exceeded, **STOP** and report.
    - **Environment Failure Bailout**: For environment errors (`ModuleNotFoundError`, `ImportError`, `ConnectionError`, `ConnectionRefusedError`, `PermissionError`, timeout):
      - **Project-internal check first**: If the missing module is project-internal (part of your codebase): NOT a bailout — do not modify source code for env issues, go back and implement it.
      - If third-party: attempt to resolve the dependency (e.g., `pip install`), then STOP and report if unresolvable.
3.  **Regression Check (Read-Only Gate)**: After the TDD loop is GREEN, run the project's test suite as a broader regression check.
    - Run the project test suite (e.g., `pytest tests/ -q` for Python, `npm test` for Node) (uses `git diff` + `LANG_PROFILES` to classify: SKIP/FULL/IMPACT). Doc-only changes are auto-skipped.
    - If IMPACT: run `pactkit test-map <changed-files>` (run from terminal) for incremental test selection. If any changed file has 3+ importers in `code_graph.mmd`, run full suite. Fallback: full suite.
    - **CRITICAL — Pre-existing test failure protocol**: If a pre-existing test fails, **DO NOT modify** it. **STOP** and report to the user. This is a one-shot check, not an iterative loop.
4.  **Lint Gate**: Run the project linter (e.g., `ruff check src/ tests/` for Python, `npm run lint` for Node) to check code style. If lint errors are found, fix them before proceeding. If run the project linter is unavailable, run the stack's lint command directly.

## 🎬 Phase 4: Sync & Document
1.  Run language-specific cleanup (e.g., `find . -name '__pycache__' -exec rm -rf {} +` for Python) and run `python3 .github/skills/pactkit-visualize/scripts/visualize.py` (file, `--mode class`, `--mode call` if source changed) (runs file, `--mode class`, `--mode call` if source changed).
2.  **Update Board (CRITICAL)**: Run `python3 .github/skills/pactkit-board/scripts/board.py update_task {STORY_ID} "Task Name"` for each completed task to mark it as `[x]`.
3.  **Update Continuation State**: Run `pactkit context --continuation --last-command "/project-act {STORY_ID}" --phase "Phase 4: complete"` from the terminal to record the agent's stopping point for session handoff.


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
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py` to view file dependency graph
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode class` for class inheritance
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode call --entry <func>` to trace call chains
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode module` for module-level architectural overview
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
