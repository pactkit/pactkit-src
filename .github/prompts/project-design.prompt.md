---
mode: agent
description: "Product design for greenfield projects: PRD generation, story decomposition, board setup"
---

# Command: Design (v1.3.0 Product Designer)
- **Usage**: `/project-design "$ARGUMENTS"`
- **Agent**: Product Designer

> **PURPOSE**: Transform a product vision into a comprehensive PRD, decompose it into
> implementable Specs, and populate the Sprint Board — bridging the gap between
> "I have an idea" and "I have a prioritized backlog ready for `/project-act`."

## 🧠 Phase 0: The Thinking Process
> **Execution Style**: Work through each phase incrementally — output progress as you go. Do NOT try to plan all PRD sections in your head before producing output. Start each section, show your findings, then move to the next.
1.  **Parse Vision**: What is the core product idea? What problem does it solve?
2.  **Identify Domain**: E-commerce, SaaS, internal tool, mobile app, CLI, etc.
3.  **Detect Stack Hints**: Does the user mention specific technologies? (React, Python, Go, etc.)
4.  **Scope Assessment**: Is this a full product or a module within an existing system?

## 🎬 Phase 1: PRD Generation
> **Goal**: Create `docs/product/prd.md` — the single source of truth for the product.

1.  **Scaffold**: Run `python3 .github/skills/pactkit-scaffold/scripts/scaffold.py create_prd "{ProductName}"`.
2.  **Read Scaffolded File**: Read `docs/product/prd.md` before writing content (required — Write/Edit tools cannot modify unread files).
3.  **Fill Sections** — Complete each section in the PRD using **sectional write**: Edit each Group into `prd.md` immediately after completing it, then print a checkpoint before moving on.

### Group A: Product Foundation (Sections 1.1-1.2)

### 1.1 Product Overview
- **Vision**: One-sentence product vision statement
- **Problem Statement**: What pain point does this solve? For whom?
- **Target Users**: Primary and secondary user segments

### 1.2 User Personas (minimum 2)
For each persona, fill:
- **Role**: Job title or user archetype
- **Goals**: What they want to achieve
- **Pain Points**: Current frustrations
- **Jobs-to-be-Done**:
  - *Functional*: What task are they trying to accomplish?
  - *Emotional*: How do they want to feel?
  - *Social*: How do they want to be perceived?

4.  **Edit**: Write Group A content (Sections 1.1-1.2) into `docs/product/prd.md`. Print checkpoint: "Group A written. Proceeding to Group B."

### Group B: Features & Design (Sections 1.3-1.6)

### 1.3 Feature Breakdown (Epics → Stories)
Organize features into Epics. For each Story within an Epic, score:

| Story | Impact (1-5) | Effort (1-5) | Priority (I/E) |
|-------|:------------:|:------------:|:--------------:|
| ...   | ...          | ...          | ...            |

- **Impact**: User value (how much does it matter?) + Business value (revenue, retention, growth)
- **Effort**: Technical complexity + Risk (unknowns, dependencies)
- **Priority**: Impact ÷ Effort — higher is better

### 1.4 Architecture Design
- Draw a system-level Mermaid architecture diagram
- Identify major components: frontend, backend, database, external services
- Note technology recommendations (not mandates)

### 1.5 Page/Screen Design
For each key screen:
- **Purpose**: What user goal does this screen serve?
- **Components**: UI component hierarchy (header, forms, lists, modals, etc.)
- **User Flow**: Step-by-step interaction sequence
- **shadcn Integration (Conditional)**: IF `components.json` exists in the project root, use `mcp__shadcn__search_items_in_registries` to find matching UI components for each page element. Include the shadcn component names (e.g., `@shadcn/button`, `@shadcn/card`) in the component hierarchy.

### 1.6 Prototype Generation
> **Goal**: Generate runnable HTML prototypes for each key page from Section 1.5.

1.  **For each key page** defined in Section 1.5, generate a single self-contained `.html` file:
    - **Tailwind CSS** via CDN: `<script src="https://cdn.tailwindcss.com"></script>`
    - **Lucide Icons** via CDN: `<script src="https://unpkg.com/lucide@latest"></script>`
    - **Vanilla JavaScript** for interactions (click handlers, toggles, form validation)
    - No React, Vue, or any framework — zero build step required
2.  **Write** each prototype to `docs/prototypes/{page-name}.html` (create the directory if needed).
3.  **Content Requirements**:
    - Responsive layout (mobile-first with Tailwind breakpoints)
    - Realistic placeholder content (not "Lorem ipsum" — use domain-relevant text from Personas)
    - Interactive elements wired up (buttons show feedback, forms validate, modals open/close)
    - Call `lucide.createIcons()` at the end of `<body>` to render icons
4.  **Browser Preview (Conditional)**: IF `mcp__playwright__browser_navigate` tool is available, open each prototype in the browser for live preview. IF Playwright MCP is not available, print the file path for manual opening.

5.  **Edit**: Write Group B content (Sections 1.3-1.6) into `docs/product/prd.md`. Print checkpoint: "Group B written. Proceeding to Group C."

### Group C: Technical & Strategy (Sections 1.7-2.0)

### 1.7 API Design
- List endpoints: `METHOD /path → description`
- Define core data models (entity fields and relationships)
- Specify auth strategy (JWT, session, OAuth, API key)

### 1.8 Non-Functional Requirements
- **Performance**: Response time targets, throughput expectations
- **Security**: Auth model, data encryption, OWASP baseline
- **Scalability**: Expected user load, horizontal vs vertical scaling

### 1.9 Success Metrics
Define measurable KPIs per Epic:

| Epic | Metric | Target | How to Measure |
|------|--------|--------|----------------|
| ...  | ...    | ...    | ...            |

### 2.0 MVP Roadmap (Three-Horizon Framework)
Assign each Story to a horizon:

- **Now (Sprint 1-3)**: Core MVP — must-have features to validate the product
- **Next (Sprint 4-8)**: Differentiation — features that create competitive advantage
- **Later (Sprint 9+)**: Scale — platform expansion, optimization, advanced features

6.  **Edit**: Write Group C content (Sections 1.7-2.0) into `docs/product/prd.md`. Print checkpoint: "Group C written. PRD complete."

## 🎬 Phase 2: Architecture
1.  **Update HLD**: Write the architecture Mermaid diagram from Section 1.4 into `docs/architecture/graphs/system_design.mmd`.
2.  **Visualize** (if existing code): Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py visualize`.

## 🎬 Phase 3: Story Decomposition
> **Goal**: Convert PRD Feature Breakdown into individual Specs.

1.  **Determine STORY IDs**: Run `pactkit next-id` from the terminal to get the next available STORY-NNN number.
2.  **Sort**: Order stories by horizon (Now → Next → Later), then by Priority Score (descending).
3.  **For each Story**:
    - Run `python3 .github/skills/pactkit-scaffold/scripts/scaffold.py create_spec "STORY-{NNN}" "{title}"`.
    - **Read the scaffolded file** before writing content (required — Write/Edit tools cannot modify unread files).
    - Fill in the Spec:
      - `## Requirements` — using RFC 2119 keywords (MUST/SHOULD/MAY)
      - `## Acceptance Criteria` — Given/When/Then scenarios
      - Add Priority Score to the spec header: `- **Priority**: {score} (Impact {I} / Effort {E})`
4.  **Security Scope**: After filling each Spec, run `pactkit sec-scope <changed-files>` (run from terminal) to populate the `## Security Scope` section. If `pactkit sec-scope` (run from terminal) is unavailable, manually fill SEC-1 through SEC-8.
5.  **Spec Lint Self-Check**: After each Spec is generated, run `python3 .github/skills/pactkit-scaffold/scripts/spec_linter.py docs/specs/{STORY_ID}.md`. If ERRORs found, self-correct and re-run until clean. This prevents malformed Specs from blocking the Sprint pipeline at Act Phase 0.5.
5.  **Batch Checkpoint**: Every 3 Specs completed, print a progress checkpoint (e.g., "3/8 Specs created. Continuing."). This prevents unbounded continuous output.
6.  **Dependency Graph**: Add a Mermaid dependency graph at the end of the PRD showing Story execution order and critical path.

## 🎬 Phase 4: Board Setup
1.  **Add Stories**: For each Story (ordered by horizon → priority):
    - Run `python3 .github/skills/pactkit-board/scripts/board.py add_story "STORY-{NNN}" "{title}" "{task list}"`.
2.  **Verify**: Read `docs/product/sprint_board.md` to confirm all stories are listed.

## 🎬 Phase 4.5: Session Context Update
1.  **Update Context**: Generate `docs/product/context.md` manually (Sprint Status, Current Stories, Recent Completions, Active Branches, Key Decisions, Next Recommended Action) to regenerate `docs/product/context.md` with the newly created stories and board state.

## 🎬 Phase 5: Handover
1.  **Summary Table**: Output a table of all created artifacts:

| Artifact | Path | Count |
|----------|------|-------|
| PRD | `docs/product/prd.md` | 1 |
| Prototypes | `docs/prototypes/{page-name}.html` | M |
| Specs | `docs/specs/STORY-{NNN}.md` | N |
| Board Entries | `docs/product/sprint_board.md` | N |
| Architecture | `docs/architecture/graphs/system_design.mmd` | 1 |

2.  **Story Overview**: List stories grouped by horizon (Now/Next/Later) with priority scores.
3.  **Handover**: "PRD created. {N} stories ready for `/project-act`."

## ⚠️ What This Command Does NOT Do
- Does NOT write implementation code — only PRD, Specs, and architecture design
- Does NOT include market sizing (TAM/SAM/SOM) or pricing strategy — AI cannot produce reliable market data
- Does NOT generate production UI code (React/Vue/Svelte) — prototypes are HTML + Tailwind only, meant for design validation not deployment
- Does NOT enforce a specific tech stack — recommendations only, not mandates
- Does NOT depend on WebSearch — works entirely from user input


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
- All tests MUST pass before committing

## Language Matching
- Match the user's language (Chinese→Chinese, English→English).
- Technical terms (function names, file paths, git commands) stay in original form.

## Signal Strength Convention
All rules and playbooks MUST use signal keywords consistently per this 4-level hierarchy:

| Level | Keywords | Semantics | Use When |
|-------|----------|-----------|----------|
| **L1 Absolute** | `NEVER` / `MUST NOT` | Violation = bug, zero tolerance | Security red lines, data loss, Spec tampering |
| **L2 Strong** | `CRITICAL` / `MUST` / `ALWAYS` | Violation = must-fix issue | Phase gates, TDD enforcement, regression blocking |
| **L3 Recommended** | `IMPORTANT` / `SHOULD` | Violation = warning, non-blocking | Best practices, performance advice, style |
| **L4 Advisory** | `Prefer` / `Consider` / `If possible` | Suggestion, skip by judgment | Optimization hints, optional enhancements |

- `NEVER` and `MUST NOT` are reserved for L1 — do not use them for anything less than absolute prohibition.
- `DO NOT` is ambiguous — replace with `NEVER` (L1) or `MUST NOT` (L1) for prohibitions, or rephrase as `SHOULD NOT` (L3) for recommendations.
- When writing an L1 or L2 rule, append a consequence clause: `— {what goes wrong if violated}`.

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
