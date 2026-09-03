from dataclasses import dataclass

from pactkit import __version__

RULES_MODULES = {
    "core": """# Core Protocol

## Session Context
On new session, read local project context. If PactKit version drift matters, tell the user; run `pactkit update` only with explicit authorization.
If `pactkit.yaml` is missing (check `{PROJECT_CONFIG_DIR}/`), run `pactkit init` before proceeding.
You MAY read `.pactkit/context.md` as optional history; it never blocks
current-session work. Missing, stale, blocked, or completed records never
prevent work. Run `pactkit context` only for a useful handover.
If the file is missing, suggest `/project-init` only when the project itself is uninitialized.
If "Last updated" date is before today, suggest running `$daily-retro`.

## PDCA Nudge
When free-conversation analysis yields actionable bugs, architecture improvements, or features, SHOULD recommend the appropriate PDCA command. See PDCA Nudge Protocol below.

## Visual First
Before modifying code:
- Run `visualize` to view file dependency graph
- Run `visualize --mode class` for class inheritance
- Run `visualize --mode call --entry <func>` to trace call chains
- Run `visualize --mode module` for module-level architectural overview
- **PDCA Exemption**: When a PDCA command is active, the command's own visualize phases take precedence — skip Visual First.

## Strict TDD
- Write tests first (RED), then write implementation (GREEN)
- The agent MUST NOT skip TDD except when running `/project-hotfix`
- All tests MUST pass before committing

## Language Matching
- Match the user's language (Chinese→Chinese, English→English).
- Technical terms (function names, file paths, git commands) stay in original form.

## Subagent Model Selection
Select `model` based on task complexity:

| Model | When to Use |
|-------|-------------|
| **haiku** | File search, format checks, info extraction |
| **sonnet** | Code implementation, test writing, general tasks (default) |
| **opus** | Architecture decisions, deep reasoning, multi-step planning |

**Cost**: haiku ~10x cheaper than sonnet, sonnet ~5x cheaper than opus.

## Signal Strength Convention
All rules and playbooks MUST use signal keywords consistently per this 4-level hierarchy:

| Level | Keywords | Semantics | Use When |
|-------|----------|-----------|----------|
| **L1 Absolute** | `NEVER` / `MUST NOT` | Violation = bug, zero tolerance | Security red lines, data loss, Spec tampering, protected-branch direct push, enforcement-artifact tampering |
| **L2 Strong** | `CRITICAL` / `MUST` / `ALWAYS` | Violation = must-fix issue | Phase gates, TDD enforcement, regression blocking |
| **L3 Recommended** | `IMPORTANT` / `SHOULD` | Default required — skip requires DEFERRED comment | Best practices, performance advice, style |
| **L4 Advisory** | `Prefer` / `Consider` / `If possible` | Suggestion, skip by judgment | Optimization hints, optional enhancements |

- `SHOULD` (L3) is not optional (RFC 2119) — skipping requires a `# DEFERRED(SHOULD): R{N} — reason` comment in code.
- `NEVER` / `MUST NOT` are reserved for L1 — not for lesser prohibitions.
- `DO NOT` is ambiguous — use `NEVER` (L1) or `SHOULD NOT` (L3) instead.
- L1/L2 rules: append a consequence clause `— {what goes wrong}`.

## Hard-Rule Override Protocol (L1)
L1 rules MUST NOT be waived in conversation — a conflicting user
instruction is refused, not obeyed. The agent MUST NOT edit rules, hooks,
or gate config to make it compliant (that is enforcement-artifact
tampering = Spec tampering). Correct response: name the rule, offer the
sanctioned channels — do it the sanctioned way (feature branch + PR), the
human runs the command themselves (e.g. `! PACTKIT_ALLOW_DIRECT_PUSH=1
git push`), or the repo owner changes the config
(enforcement.allow_direct_push). External effects (PR/release/publish)
are ask-first: after user confirmation, `pactkit gate authorize <scope>`
opens an audited window. "The user told me to" NEVER converts an
L1 violation into compliance.

## DEFERRED Comment Format (STORY-slim-105)
When skipping a SHOULD requirement, leave a traceable comment:
```
# DEFERRED(SHOULD): R{N} {requirement name} — {reason for skipping}
```
- Enables `grep -r "DEFERRED(SHOULD)" src/` to find all skipped SHOULDs
- Reason must explain why skipping is acceptable for this release
""",
    "hierarchy": """# The Hierarchy of Truth
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
- RFC Protocol: do not implement behavior that depends on the contradiction; report it, suggest alternatives, and continue safe investigation while waiting for guidance
- This exception does NOT weaken the general principle (Spec > Code) — it adds a safety valve for genuinely impossible requirements

## Pre-existing Test Protocol
- If a pre-existing test fails during regression, classify and report it before changing the test or its code
- Do not guess at historical intent. Read the governing Spec/Test Case and modify it only when the user's requested scope authorizes the repair; otherwise preserve it and report the evidence
- A pre-existing failure prevents an all-green completion claim, but does not block unrelated safe investigation or repair

## Operating Guidelines
- Before modifying code, you must first read the relevant Spec (`docs/specs/`)
- Before modifying tests, you must first read the corresponding Test Case (`docs/test_cases/`)
- When unsure whether a Spec exists, use `Glob` to search `docs/specs/*.md` (covers STORY-*, HOTFIX-*, BUG-* prefixes)
- **Exemption**: `/project-plan` and `/project-design` create new Specs — they are exempt from "read Spec before modifying code" since the Spec does not yet exist.
""",
    "atlas": """# File Atlas

| Path | Purpose |
|------|---------|
| `docs/specs/{ID}.md` | **The Law** -- Requirement Specifications (Spec) |
| `commands/*.md` | **The Playbooks** -- Command Execution Logic |
| `docs/product/stories/{ITEM_ID}.yaml` | Story workflow/task facts |
| `docs/product/sprint_board.md` | Optional read-only Board projection |
| `docs/test_cases/{ID}_case.md` | Test Cases -- Gherkin Acceptance Scenarios |
| `docs/architecture/graphs/*.mmd` | Architecture Graphs -- Mermaid Architecture Diagrams |
| `tests/unit/` | Unit Tests |
| `tests/e2e/` | E2E Integration Tests |
| `docs/e2e/journey.md` | User Journey Definitions -- E2E cross-story user flow specs |
| `docs/product/archive/` | Archived Stories |
| `docs/product/prd.md` | Product Requirements Document (PRD) |
""",
    "workflow": """# Workflow Conventions

## Git Commit (Conventional Commit)
Format: `type(scope): description`

| Type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation change |
| `chore` | Build/tooling/dependency |
| `refactor` | Refactoring (no behavior change) |
| `test` | Add or modify tests |

- Infer scope from the modified module/directory (e.g. `board`, `auth`, `ui`)
- Description in English, concisely describing "why"
- All tests in the project's test suite must pass before committing

## Branch Naming
- Feature branch: `feature/STORY-{ID}-short-desc`
- Hotfix branch: `fix/HOTFIX-{ID}-short-desc`
- Bug fix branch: `fix/BUG-{ID}-short-desc`
- Main branch: `main` / `master` (no direct push — enforced by the
  push-gate; human bypass: `PACTKIT_ALLOW_DIRECT_PUSH=1`, config:
  `enforcement.allow_direct_push` in pactkit.yaml)
- Development branch: `develop`

## PR Conventions
- Title: `feat(scope): short description` (consistent with commit)
- Body: Summary + Test Plan
- Must pass CI and Code Review before merging

## Change Type Declaration (STORY-slim-105)
Before modifying code, declare the change type:

| Type | Meaning | Requirement |
|------|---------|-------------|
| `ROOT_CAUSE` | Fixing the root cause | None |
| `WORKAROUND` | Temporary bypass | MUST create tech-debt Story |

Choosing WORKAROUND is allowed, but incurs the cost of creating a tracking Story — no silent bypasses.
""",
    "routing": """# Command Reference (Routing Table)

## Commands (11 user-facing entry points)

### Init (`/project-init`)
- **Role**: System Architect
- **Playbook**: `commands/project-init.md`
- **When NOT to use**: Project already has `pactkit.yaml` and `docs/product/stories/`. Use `pactkit update` instead to sync after upgrades.

### Plan (`/project-plan`)
- **Role**: System Architect
- **Playbook**: `commands/project-plan.md`
- **When NOT to use**: Greenfield with no existing code — use `/project-design` first. For typos/config fixes — use `/project-hotfix` (no Spec needed).

### Clarify (`/project-clarify`)
- **Role**: System Architect
- **Playbook**: `commands/project-clarify.md`
- **When NOT to use**: Requirements are already clear and specific. Plan Phase 0.7 auto-triggers Clarify when ambiguity is detected — no need to invoke manually unless you want to force it.

### Act (`/project-act`)
- **Role**: Senior Developer
- **Playbook**: `commands/project-act.md`
- **When NOT to use**: No Spec exists yet — use `/project-plan` first. For typos/config/style fixes — use `/project-hotfix` (skips TDD overhead).

### Check (`/project-check`)
- **Role**: QA Engineer
- **Playbook**: `commands/project-check.md`
- **Responsibility**: Security Scan, Test Case Generation, API vs Browser.
- **When NOT to use**: Just want to run tests — use `pytest` directly. Act Phase 3 already runs regression; Check is for dedicated QA after implementation is complete.

### Done (`/project-done`)
- **Role**: Repo Maintainer
- **Playbook**: `commands/project-done.md`
- **When NOT to use**: Code is not yet implemented — use `/project-act` first. For version releases — use `/project-release` (Done archives stories; Release tags versions).

### Release (`/project-release`)
- **Role**: Repo Maintainer
- **Playbook**: `commands/project-release.md`
- **Goal**: Version release: snapshot, archive, and Git tag.
- **When NOT to use**: Just finishing a story — use `/project-done` (archive + commit). Release is for version milestones with changelog, tag, and PyPI publish.

### PR (`/project-pr`)
- **Role**: Repo Maintainer
- **Playbook**: `commands/project-pr.md`
- **Goal**: Push branch and create pull request via gh CLI.
- **When NOT to use**: Working on main branch directly (sole developer). PR is for branch-based collaboration workflows.

### Sprint (`/project-sprint`)
- **Role**: Team Lead (Orchestrator)
- **Playbook**: `commands/project-sprint.md`
- **Goal**: Automated PDCA Sprint orchestration via Subagent Team.
- **When NOT to use**: Single story to implement — use `/project-act` directly. Sprint orchestrates multiple stories via subagent team; overkill for one story.

### Hotfix (`/project-hotfix`)
- **Role**: Senior Developer
- **Playbook**: `commands/project-hotfix.md`
- **Goal**: Lightweight fast-fix channel that bypasses PDCA.
- **When NOT to use**: Change requires design decisions or has multiple requirements — use `/project-plan` + `/project-act` for full PDCA traceability.

### Design (`/project-design`)
- **Role**: Product Designer
- **Playbook**: `commands/project-design.md`
- **Goal**: Greenfield product design: PRD generation, story decomposition, board setup.
- **When NOT to use**: Adding a feature to an existing project — use `/project-plan` (single story). Design is for greenfield products or major multi-story initiatives.

## Embedded Skills (auto-invoked by commands above)

| Skill | Embedded In | Purpose |
|-------|-------------|---------|
| `pactkit-trace` | Plan Phase 1, Act Phase 1 | Deep code tracing and execution flow analysis |
| `pactkit-release` | Release Phase 1 (snapshot/archive) | Version release: snapshot, archive, Tag |

## Agent Skills (invoked via agent roles, not by commands)

| Skill | Available To | Purpose |
|-------|-------------|---------|
| `pactkit-draw` | visual-architect, system-architect agents | Generate Draw.io XML architecture diagrams |
| `pactkit-status` | system-medic agent | Project state overview |
| `pactkit-doctor` | system-medic agent | Diagnose project health |
| `pactkit-review` | qa-engineer agent | PR Code Review |
| `pactkit-analyze` | senior-developer (Act Phase 0.6 inline) | Cross-artifact consistency check: Spec ↔ Board ↔ Test Cases |
""",
    "mcp": """# MCP Integration (Conditional)
> **PRINCIPLE**: All MCP instructions are conditional. If an MCP server is not available, skip the instruction gracefully.

## Available MCP Servers

### Context7 (`mcp__context7__*`)
- **Purpose**: Fetch up-to-date library documentation and code examples
- **When to use**: If you are implementing with an unfamiliar library API, or need to verify current API signatures
- **Tools**: `resolve-library-id` → `get-library-docs`
- **Trigger**: If you are about to write code using a third-party library and are unsure about the API

### Memory MCP (`mcp__memory__*`)
- **Purpose**: Persistent knowledge graph for cross-session context — store architectural decisions, load prior context, record lessons learned
- **When to use**: If `mcp__memory__create_entities` tool is available in the current runtime
- **Tools**: `create_entities`, `create_relations`, `add_observations`, `search_nodes`, `read_graph`
- **Trigger**: If running Plan (store decisions), Act (load context), or Done (record lessons)
- **Entity naming**: Use `{STORY_ID}` (e.g., "STORY-037") as the entity name, `entityType: "story"`

## Usage by PDCA Phase

| Phase | MCP Server | Condition |
|-------|-----------|-----------|
| **Plan** | Memory | If `mcp__memory__*` tools are available |
| **Act** | Context7 | If implementing with unfamiliar library API |
| **Act** | Memory | If `mcp__memory__*` tools are available |
| **Done** | Memory | If `mcp__memory__*` tools are available |
""",
    "shared": """# Shared Protocols

## Current-session execution
Run each `project-*` command in the current host and conversation. Local continuation or experimental workflow records may be read as context, but never gate, block, or redirect normal Plan/Act/Check/Done work. Manual operations such as commit, archive, tag, publish, release, push, and pull request always require fresh authorization.

## Lazy Visualize Protocol
> Referenced by: Act Phase 4, Done Phase 2

If source files changed (per `LANG_PROFILES[stack].source_dirs`) OR `code_graph.mmd` is missing, run visualize in all 3 modes (file, class, call). Else skip with log: "Graph up-to-date — no source changes".

## Test Mapping Protocol
> Referenced by: Act Phase 3, Check Phase 5, Done Phase 2.5, Hotfix Phase 2

Map changed source files to test files via `LANG_PROFILES[stack].test_map_pattern`. If no mapping can be determined, fall back to the full test suite.

## Local Context Projection Format
> Referenced by: Init Phase 6, Plan Phase 3, Act Phase 4, Done Phase 4.5

Generate ignored `.pactkit/context.md` using this format:
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
{Last 5 records from docs/architecture/governance/lessons/}

## Next Recommended Action
{If In Progress: `/project-act STORY-XXX` | If Backlog only: `/project-plan` | If empty: `/project-design`}
```
""",
    "architecture": """# Architecture Principles

> Derived from SOLID, DRY, 12-Factor App, and Defense-in-Depth practices.
> Violations of MUST rules are treated as bugs. SHOULD rules are advisory.

## 1. Single Source of Truth (DRY)
- Every configuration value, schema definition, or structural rule MUST be defined in exactly one place.
- **Anti-pattern**: The same logic (e.g., a write-then-invalidate workflow, an IRI sanitization routine, a dual-write SQL statement) implemented independently in 3+ files. Each copy drifts over time — one gets a bugfix, the others don't.
- **Detection**: During Plan Phase 1 Lateral Scan, if `fan-in ≥ 3` or `grep` finds 3+ independent implementations of the same operation, MUST evaluate extracting a shared service/function.
- When standalone scripts cannot import the library, they MUST inline the value with a comment pointing to the canonical source.
- When updating a canonical value, search all inline copies with `grep` and update them in the same commit.

### No Dual-Write
- The same data MUST exist in exactly one authoritative location — two storage locations for the same truth source guarantees drift.
- **Anti-patterns**:

| Pattern | Example | Consequence |
|---------|---------|-------------|
| Memory + DB | In-memory object graph + relational DB both authoritative | Memory mutation not persisted; DB write silently dropped |
| Cache + Source | TTL cache + DB both treated as truth | Cache returns stale data after DB update |
| Frontend + Backend enums | UI status map + server enum defined independently | Values drift; frontend shows invalid state |
| File + DB | Config file + database storing same records | File overwritten on save; DB orphaned |

- **Fix pattern**: Choose ONE truth source. Others become:
  - **Read cache**: populated from truth source, invalidated on write
  - **Projection**: derived view, regenerated on demand

## 2. Open-Closed Principle (OCP)
- Adding a new variant MUST NOT require modifying existing functions — violates OCP when adding the Nth case means editing a growing if/elif chain.
- **Anti-pattern**: A `db_type` string checked in 13 if/elif branches across 6 files. Adding a new database type requires touching every branch — use a strategy pattern or registry instead.
- **Pattern**: Define a registry/dispatch table. New variants add an entry; existing code remains unchanged.

## 3. Dependency Inversion (DIP)
- Prompt templates MUST NOT contain hardcoded environment-specific paths.
- Pattern: use named placeholders (`{SKILLS_ROOT}`, `{BOARD_CMD}`, `{PACTKIT_YAML}`) resolved at deploy time by `_render_prompt(template, profile)`.
- Functions MUST accept a `profile: FormatProfile` parameter instead of format-specific booleans (`opencode_format=True`) or manual path strings (`skills_prefix="~/.config/opencode/skills"`).

## 4. Liskov Substitution (LSP) — Deploy Chain Parity
- All deployer classes (ClassicDeployer, OpenCodeDeployer, etc.) MUST support the same user-facing feature set:
  - Selective deployment (read `pactkit.yaml`)
  - Auto-merge on upgrade (`auto_merge_config_file`)
  - Legacy cleanup (`_cleanup_legacy`)
  - Project-level instructions file generation
- Format-specific features (e.g., hooks for Claude Code, opencode.json for OpenCode) are extensions, not omissions.

## 5. Interface Segregation (ISP)
- Each `FormatProfile` exposes only the fields relevant to that format:
  - `commands_dir = None` for formats without custom commands
  - `excluded_agent_fields` removes fields invalid for that format
- Consumers MUST check `if profile.has_custom_commands` before deploying commands — not hardcoded format checks.
- **Module size**: A single file exceeding 500 lines SHOULD be evaluated for splitting. A 565-line route handler mixing 5 resource domains is a sign that responsibilities are not separated.

## 6. Defense-in-Depth (Security)
- **Path traversal**: All file writes use `atomic_write()` which creates parent directories safely.
- **Config isolation**: `_generate_config_if_missing(format=)` writes to the format-specific directory only. Never cross-write.
- **No secret leakage**: `_render_prompt()` variables are all path-based, never credential-based.
- **Standalone script safety**: Skill scripts (board.py, scaffold.py) MUST NOT execute arbitrary imports. Use `try/except ImportError` fallback for pactkit imports.
- **Deny-by-Default**: Sensitive endpoints (metrics, admin, internal, debug) MUST require authentication by default — empty or missing config = denied, not allowed. Anti-pattern: `if settings.token: verify()` skips auth when token is empty.
- **Input Validation Before External Systems**: User input entering URLs, commands, SQL, or file paths MUST be validated/escaped at the boundary.

| Destination | Validation |
|-------------|------------|
| URL | Allowlist scheme + host; reject internal IPs (SSRF prevention) |
| Shell command | Use list args, not shell=True |
| SQL | Parameterized queries only |
| File path | Reject `..`, resolve and check prefix |

- **Security Timing Consistency**: Security-sensitive branches (authentication, authorization) MUST have consistent timing to prevent side-channel attacks — a fast-reject path that skips expensive operations (e.g., hash comparison) reveals information to attackers.

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

## 9. Merge over Replace (Incremental Sync)
- When writing to a file that may contain user-modified content or sections managed by other tools, SHOULD use incremental merge (Edit / patch / append) instead of full replacement (Write / overwrite) — full replacement silently destroys content the writer did not generate.
- **Decision Matrix**:

| Target File Characteristics | Strategy | Rationale |
|----------------------------|----------|-----------|
| Generated entirely by this tool, no user sections | Full replace is safe | Writer owns 100% of content |
| Contains user-modified sections OR mixed ownership | **Incremental merge** | Preserve content this tool did not generate |
| Config file with default + override pattern | **Merge missing keys only** | Existing values represent user intent |
| Append-only artifact (changelog, log, history) | **Append** | Never rewrite prior entries |

- **Litmus test**: "Does this file contain content I did not generate?" → If yes, incremental merge. If unsure, incremental merge.
- **Anti-pattern evidence**: BUG-010 (`_rewrite_yaml` destroyed user config), BUG-slim-089 (`_deploy_claude_md` overwrote user CLAUDE.md), STORY-033/STORY-slim-054 (backfill overwrote existing values). All were full-replace where merge was required.

## 10. Code Enforces, Prompt Instructs
- Deterministic constraints MUST be enforced by Code, not delegated to Prompt — if the LLM ignores the instruction, the constraint must still hold.
- **Litmus test**: Remove the prompt instruction. Does the system still enforce the constraint? If no → Code enforcement required.

| Constraint | Prompt-only (BAD) | Code-enforced (GOOD) |
|------------|-------------------|----------------------|
| Row limit | "Return at most 100 rows" | `validator.inject_limit(sql, 100)` |
| Input length | "Keep under 500 chars" | `if len(input) > 500: raise ValidationError` |
| Output format | "Return valid JSON" | `json.loads(response)` + retry on parse error |
| Dynamic values | "Use today's date" | `datetime.now()` at runtime, not import time |

- **Corollary (LLM ≠ Calculator)**: If input→output mapping is deterministic, use Code. LLM is for creativity, not computation. When demoting LLM to Code: implement deterministic version first, keep LLM as fallback for edge cases, remove fallback if it triggers <5%.

## 11. Concurrency & Async Safety
- Background tasks MUST NOT silently fail — every fire-and-forget pattern needs: error visibility (log or propagate), backpressure (queue with max size), and shutdown awareness (register with task manager).
- Request-scoped state MUST be cleaned up in a finally block — leaked state contaminates subsequent requests on the same worker.
- Shared mutable state accessed by multiple threads/tasks MUST be protected with appropriate synchronization (locks, semaphores). Semaphores SHOULD be lazily initialized at first use, not at import time.

## 12. Cache Lifecycle
- Every cache (decorator-based, module-level dict, TTL instance, singleton) MUST be registered in a central invalidation function.
- Write operations that change cached data MUST declare which caches they affect and trigger invalidation.
- Cache references MUST use the correct module path — moving a cached value to a different module without updating the invalidation registry silently breaks cache clearing.

## 13. Dead Code Hygiene
- Unused functions, empty/no-op middleware, and unwired components MUST be deleted or activated — dead code misleads readers into thinking it is load-bearing.

| Type | Example | Action |
|------|---------|--------|
| Dead function | Function with 0 callers | Delete |
| Empty middleware | Sets state that nothing reads | Delete |
| Unwired component | Initialized but never started | Wire up or delete |
| Commented code | `# old_impl()` blocks | Delete (git has history) |

## Quick Reference: Where to Make Changes

| Change Type | File to Edit | Auto-Propagation |
|-------------|-------------|------------------|
| New tool format | `profiles.py` → `FORMAT_PROFILES` | CLI, deployer, config, VALID_FORMATS |
| New document type | `schemas.py` → `SCHEMA_REGISTRY` | `pactkit schema`, playbooks via render_prompt |
| New template variable | `deployer.py` → `_render_prompt()` var_map | All deployed prompts |
| New spec rule | `schemas.py` + `spec_linter.py` | scaffold, playbooks |
| New prompt placeholder | `profiles.py` (if env-specific) or `schemas.py` (if doc-specific) | `_render_prompt()` |
""",
    "sectional": """# Sectional Write Protocol

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
""",
    "principles": """# Core Engineering Principles

> These are the always-present engineering guardrails. Full details in the on-demand rules.

## Single Source of Truth (DRY)
- Every configuration value, schema definition, or structural rule MUST be defined in exactly one place — two copies guarantee drift.
- No Dual-Write: The same data MUST exist in exactly one authoritative location. Others become read caches or projections.
- When updating a canonical value, search all inline copies with `grep` and update them in the same commit.

## No Magic Values (MUST NOT)
- Do not hardcode values that may change (URLs, thresholds, timeouts, feature flags). Extract to named constants or configuration.
- **Flexibility Litmus Test**: If changing a value requires `grep` + multi-file edits, it belongs in a named constant or config key.
- Applies to ALL artifacts: source code, rules, Specs, configs, playbooks, prompts.

## Reuse Priority
Before writing new code, check in order:
1. Does the framework already provide this? → Use the native API.
2. Does the project already encapsulate this? → Use the existing wrapper, do NOT bypass it.
3. Only if both above are "No" → Implement new code.

## Code Enforces, Prompt Instructs
- Deterministic constraints MUST be enforced by Code, not delegated to Prompt — if the LLM ignores the instruction, the constraint must still hold.
- **LLM ≠ Calculator**: If input→output mapping is deterministic, use Code. LLM is for creativity and reasoning.
- Litmus test: Remove the prompt instruction. Does the system still enforce the constraint? If no → Code enforcement required.

## Dependency Direction (MUST NOT)
- Do not import from higher-level modules into lower-level modules.
- Domain/core imports nothing from infrastructure; infrastructure imports from domain.
- Circular imports indicate a layering violation — fix the structure, not the symptoms.

## Open-Closed Principle
- New variants via registry/dispatch table, not if/elif chains — adding a new variant SHOULD NOT require modifying existing functions.

## Dead Code Hygiene
- Unused functions, empty/no-op middleware, and unwired components MUST be deleted or activated — dead code misleads readers.
""",
    "nudge": """# PDCA Nudge Protocol

> **Signal Level**: L3 Recommended (SHOULD) — non-blocking suggestion.

## When to Nudge

When AI analysis in **free conversation** (outside any PDCA command context) produces actionable conclusions, SHOULD append a PDCA command recommendation at the end of the reply.

## Trigger Matrix

| Signal | Command | Condition |
|--------|---------|-----------|
| Bug / error found (single file) | `/project-hotfix` | Single-file fix, no design decision needed |
| Bug + design change needed | `/project-plan` | Multi-file or unclear requirements |
| Architecture improvement identified | `/project-plan` | Involves 2+ file changes |
| New feature need identified | `/project-plan` | Single feature |
| New product / multi-feature need | `/project-design` | 3+ independent stories, greenfield |
| Existing Spec ready to implement | `/project-act STORY-XXX` | Story is on the Board |
| 3+ independent improvement items | `/project-sprint` | Multiple stories can run in parallel |
| Code quality issue (quick fix) | `/project-hotfix` | No behavior change |

## Nudge Format

Place at the **end** of the reply, after all analysis content:

```
💡 This analysis can be tracked via `{command}`:
> {one-sentence reason why this command fits}
```

When replying in Chinese, use:

```
💡 这个分析结果可以通过 `{command}` 来跟踪实现：
> {一句话说明为什么推荐这个命令}
```

## Suppression Rules (MUST NOT nudge when)

- **In PDCA context**: A PDCA command is already active (Plan/Act/Check/Done/Sprint/Hotfix/Design)
- **User opted out**: User explicitly said they just want to chat, not follow a workflow
- **No issue found**: Analysis confirms the current implementation is correct
- **Dedup**: The same command was already nudged earlier in this conversation
""",
    "solution": """# Solution Design Protocol

> Referenced by: Plan Phase 1, Act Phase 1

## Purpose
Evaluate the capability delta (framework native + project existing vs. needs implementation) before writing code — to avoid reinventing what the framework already provides or bypassing what the project has already encapsulated.

## Anti-Patterns This Protocol Prevents

| Anti-Pattern | Example | Consequence |
|--------------|---------|-------------|
| **Framework Blindness** | Framework has a caching layer, but writing custom cache from scratch | Duplicated logic, misses framework optimizations and bug fixes |
| **Project Blindness** | Project has `get_db_connection()`, but creating a new connection directly | Configuration drift, bypasses pooling/retry/logging the project already wired |
| **Hardcoded Coupling** | Importing a framework's internal module directly instead of using the project's wrapper | Tight coupling to framework internals; breaks when framework upgrades |

## Trigger Conditions

This protocol **MUST** be executed when (SHOULD — skipping increases reinvention risk):
- New feature involves frameworks already used by the project
- Requirement involves capabilities that frameworks commonly provide (auth, caching, scheduling, ORM, state management, etc.)

This protocol **MAY** be skipped when:
- Pure business logic not involving framework capabilities
- Documentation, configuration, or style changes only

## Protocol Execution

### Step 1: Identify Relevant Frameworks (SHOULD)
> **Goal**: Know which frameworks the project depends on, filter to those relevant to the requirement.

Read the project's dependency file (`pyproject.toml`, `package.json`, `go.mod`, `pom.xml`, `build.gradle`, `Cargo.toml`, etc.) and identify frameworks related to the current requirement.

**Early exit**: If no frameworks are relevant to the requirement, skip to Step 4 — the answer is "Needs new implementation."

**Output checkpoint**: `"Relevant frameworks: {name} v{version}, ..."`

### Step 2: Query Framework Native Capabilities (SHOULD)
> **Goal**: Does the framework already provide what we need?

**Query path (by priority):**
1. **Context7 MCP** (if available) — real-time, authoritative
2. **WebFetch** official docs (if Context7 unavailable) — real-time, requires parsing
3. **Training data** (fallback) — MUST declare framework version to avoid outdated APIs

**Focus**: Does the framework natively support this capability? What API or pattern? What config is needed?

**Output checkpoint**: `"Framework capability: {name} supports {capability} via {API/pattern}"` or `"No native support found."`

### Step 3: Query Project Existing Capabilities (SHOULD)
> **Goal**: What has the project already built or encapsulated from the framework?

Scan the project for:
- **Framework usage**: Search import statements to see which framework modules are already in use
- **Abstraction layer**: Look for factory functions (`get_*`, `build_*`, `create_*`), wiring/DI files, and wrapper modules that encapsulate framework details
- **Call chain**: If the above is insufficient, trace the call graph from the relevant module

**Output checkpoint**:
```
Project existing:
- Framework usage: {module} used in {file}
- Encapsulated: {function}() in {file} — {purpose}
```

### Step 3.5: Query Project Internal Patterns (SHOULD)
> **Goal**: Does the project already have multiple independent implementations of the same operation?

This step catches **intra-project duplication** that Steps 1-3 miss (they focus on framework-level reuse).

**Scan method** (tiered — use the most precise available):
1. **LSP** (if available): `incomingCalls` or `findReferences` on the core operation — type-aware, zero false positives
2. **visualize**: `visualize --mode call --reverse --entry <operation>` — fan-in from call graph
3. **grep**: `grep -rn "<operation>" src/` — text-level fallback

**Output checkpoint**: `"Internal pattern: {operation} has {N} implementations in {files}"`

### Step 4: Delta Assessment (MUST)
> **Goal**: Decide to reuse or implement.

**Assessment Matrix**

| Framework Has It | Project Uses It | Project Encapsulated | Decision |
|------------------|-----------------|----------------------|----------|
| Yes | No | — | **Enable framework capability** — prefer native over custom |
| Yes | Yes | Yes | **Reuse project wrapper** — do not bypass the abstraction layer |
| Yes | Yes | No | Evaluate: encapsulate or use directly |
| No | — | Has similar | **Extend** the existing project implementation |
| No | — | No | **Implement new** — this is the only case where new code is justified |
| — | — | ≥ 3 independent | **Extract shared service** — MUST evaluate shared abstraction before adding Nth implementation |

**Decision Constraints**
- **MUST NOT** bypass project abstraction layer to use framework directly — abstraction exists for unified configuration, testability, and isolation of change
- **SHOULD** prefer framework native capability over custom implementation — framework code is better tested and community-maintained
- **MUST** state reasoning if not using an available framework capability

### Step 5: Output Format

**Plan Phase** — write to `## Technical Design` in Spec:
```markdown
### Capability Assessment
| Need | Source | Decision |
|------|--------|----------|
| {capability} | {framework}.{module} (native) | Reuse / Enable / New |

### Reuse Points
- `{function}()` — {file}

### New Implementation Required
- {component}: {brief purpose}
```

**Act Phase** — brief assessment in Phase 1:
```
Capability assessment: Reuse {N}, Enable {N}, New {N}
- Reuse: {list}
- Enable: {list}
- New: {list}
```

## Implementation Constraints

When writing new code (Step 4 "Implement new"), apply these constraints:

### No Magic Values (MUST NOT)
Do not hardcode values that may change (URLs, thresholds, timeouts, feature flags). Extract to named constants or configuration. Exception: truly invariant values (HTTP status codes, math constants).

**Scope**: This constraint applies to **all artifacts**, not just source code — including rules files, Specs, configs, playbooks, and prompts. Any value that appears in 2+ places or that a user/project might need to customize SHOULD be parameterized.

**Flexibility Litmus Test**: If changing a value requires `grep` + multi-file edits, it should be a named constant, config key, or template variable instead.

| Artifact Type | Hardcode Anti-Pattern | Parameterized Pattern |
|---------------|----------------------|----------------------|
| Source code | `timeout = 30` | `timeout = config.DEFAULT_TIMEOUT` |
| Rules / playbooks | `run at most 8 files` | `run at most {MAX_TRACE_FILES} files` or define once, reference by name |
| Specs | `use SQLite for storage` | `use persistent storage (see Technical Design for engine choice)` |
| Config (YAML/JSON) | Inline URL `https://api.example.com` | `${API_BASE_URL}` or env-resolved placeholder |

### String Literal → Enum (SHOULD)
Any string value appearing in 3+ places SHOULD be promoted to a typed enum for IDE autocompletion, refactor safety, and compile-time typo detection.

**Language patterns**:
- Python: `class XType(str, enum.Enum)` — backward compatible with `==` string comparison
- TypeScript: `const X = { A: "a", B: "b" } as const`
- Go: `type X string; const A X = "a"`

**Migration**: Define enum → replace all literals → verify no remaining raw strings with `grep -rn '"old_value"' src/`

### Open-Closed Principle (SHOULD)
Design new code to be extensible without modification. If adding a new variant requires `if/elif` chains, consider a registry or strategy pattern instead.

### Single Responsibility (SHOULD)
Keep functions/classes focused on one concern. If a function name contains "and" or does multiple unrelated things, extract sub-operations.

### Dependency Direction (MUST NOT)
Do not import from higher-level modules into lower-level modules. Domain/core imports nothing from infrastructure; infrastructure imports from domain. Circular imports indicate a layering violation.

## Interaction with Other Protocols

| Protocol | Relationship |
|----------|--------------|
| **pactkit-trace** | Trace = call chains (vertical). This protocol = capability reuse (horizontal). Run Trace first, then this. |
| **Hierarchy of Truth** | Output goes into Spec (Tier 1). Implementation MUST follow Technical Design in Spec. |
""",
    "engineering": """# Engineering Concerns — Trigger Index

> Referenced by: Plan Phase 2, Act Phase 1.5
> Signal Level: L2 Strong (MUST)
> This file is a routing table. Detailed guidance lives in guides/ files loaded on demand.

## Plan Phase: NFR Decision Gate

When writing Spec's Technical Design, scan requirement keywords.
If matched, the Spec MUST include a decision for that concern:

| Keyword in Requirement | Concern | Spec Must Answer |
|------------------------|---------|-----------------|
| 定时/cron/schedule/parallel/concurrent/多线程/多进程 | concurrency | Concurrency model? (sync/async/threads/processes) |
| async/await/异步/event loop/协程 | async-patterns | Sync or async architecture? Blocking call strategy? |
| API/HTTP/webhook/第三方/external/REST/gRPC | api-integration | Timeout? Retry count? Circuit breaker? Fallback? |
| 数据库/DB/SQL/ORM/query/transaction/事务 | database | Connection pool? Lock strategy? Transaction scope? |
| 缓存/cache/Redis/Memcached/内存数据库 | caching | Strategy? TTL? Consistency? Eviction? |
| event/消息/queue/publish/subscribe/通知/MQ | event-driven | Sync/async delivery? Idempotency? DLQ? |
| 配置/config/环境变量/secret/密钥 | configuration | Config layering? Secret management? |
| log/日志/监控/metrics/trace/observability | observability | Log library? Level strategy? Trace ID? |
| 模块/module/抽象/decouple/拆分/重构 | module-design | Module boundary? Single responsibility? |
| timeout/超时/熔断/降级/circuit/breaker/阻塞 | resilience | Timeout strategy? Fallback? Health check? |
| 内存/memory/leak/GC/OOM/streaming/大文件 | memory-management | Bounded collections? Streaming? Cleanup? |
| 复用/reuse/已有/existing/library/依赖 | component-reuse | Stdlib? Project existing? Third-party? |
| review/代码审查/架构/convention/约定 | code-review-first | Exemplar file? Existing patterns? |
| retry/重试/backoff/幂等/idempoten/partial failure | error-recovery | Retry strategy? Backoff? Idempotency? Partial failure? |
| 一致性/consistency/saga/补偿/idempotency key/分布式事务 | data-consistency | Transaction scope? Compensation? Optimistic lock? |
| 兼容/backward/breaking change/deprecat/migration/版本 | backwards-compatibility | API version? Non-breaking migration? Deprecation? |
| N+1/unbounded/分页/pagina/index/索引/热路径/hot path | performance-antipatterns | Pagination? Batch fetch? Index? Cache? |
| shutdown/优雅关闭/SIGTERM/drain/信号处理 | graceful-shutdown | Signal handler? Drain timeout? Cleanup order? |
| 测试策略/test strategy/mock/stub/boundary/隔离/isolation | testing-strategy | Mock vs real? Boundary tests? Test isolation? |
| UI/界面/前端/组件/样式/交互/页面/导航/button/form/component | ui-state-accessibility | Loading/empty/error/disabled states? Keyboard & a11y? |
| 部署/deploy/rollout/上线/健康检查/health/容量/capacity/回滚/rollback/灰度/canary | operational-readiness | Health signals? Rollback criteria? Capacity bounds? |
| 新增依赖/添加依赖/pip install/npm install/pnpm add/yarn add/lockfile/升级依赖/supply chain | dependency-supply-chain | Why needed? Provenance/license? Pinned reproducibly? |
| 覆盖/overwrite/全量替换/full replace/写入既有文件/清空/wipe/修改配置/写入配置文件/merge over | write-safety | Merge-or-replace decision? Single truth source? |

Unmatched concerns → do not appear in Spec (avoid noise).

## Act Phase: Guide Loading Table

After reading Spec's Technical Design, load ONLY the matched guides:

| Concern | Guide File |
|---------|-----------|
| concurrency | {GUIDES_PATH}/concurrency.md |
| async-patterns | {GUIDES_PATH}/async-patterns.md |
| configuration | {GUIDES_PATH}/configuration.md |
| observability | {GUIDES_PATH}/observability.md |
| module-design | {GUIDES_PATH}/module-design.md |
| database | {GUIDES_PATH}/database.md |
| caching | {GUIDES_PATH}/caching.md |
| api-integration | {GUIDES_PATH}/api-integration.md |
| event-driven | {GUIDES_PATH}/event-driven.md |
| resilience | {GUIDES_PATH}/resilience.md |
| memory-management | {GUIDES_PATH}/memory-management.md |
| code-review-first | {GUIDES_PATH}/code-review-first.md |
| component-reuse | {GUIDES_PATH}/component-reuse.md |
| error-recovery | {GUIDES_PATH}/error-recovery.md |
| data-consistency | {GUIDES_PATH}/data-consistency.md |
| backwards-compatibility | {GUIDES_PATH}/backwards-compatibility.md |
| performance-antipatterns | {GUIDES_PATH}/performance-antipatterns.md |
| graceful-shutdown | {GUIDES_PATH}/graceful-shutdown.md |
| testing-strategy | {GUIDES_PATH}/testing-strategy.md |
| ui-state-accessibility | {GUIDES_PATH}/ui-state-accessibility.md |
| operational-readiness | {GUIDES_PATH}/operational-readiness.md |
| dependency-supply-chain | {GUIDES_PATH}/dependency-supply-chain.md |
| write-safety | {GUIDES_PATH}/write-safety.md |

MUST load only 1-3 relevant guides. NEVER load the entire guides/ directory.
""",
}

# Merged global rules key — retained below as a migration source for 2.23 installs.
# The active registry is declared after the legacy constants.
# routing + principles + nudge). Deployed as a single pactkit.md to ~/.claude/rules/.
# Individual module keys are kept for COMMAND_RULES_MAP and inline embedding.
RULES_MODULES["pactkit"] = "\n\n---\n\n".join([
    RULES_MODULES["core"],
    RULES_MODULES["hierarchy"],
    RULES_MODULES["atlas"],
    RULES_MODULES["routing"],
    RULES_MODULES["principles"],
    RULES_MODULES["nudge"],
])

# STORY-slim-009: Split into Always-Load (core) + On-Demand (@reference) layers
# STORY-slim-112: Refined split — global = 6 core principles files, ondemand = 6 operational files
# Refactor: Merged 6 global core files into a single pactkit.md; renumbered on-demand 01-06.
#
# RULES_CORE_FILES: PactKit-managed rules deployed to ~/.claude/rules/ (always auto-loaded).
#   Only PactKit-deployed files here — user files (10-*, 13-*, slim-01-*) NOT included.
#
# RULES_ONDEMAND_FILES: PactKit-managed files deployed to ~/.claude/skills/_rules/
#   (loaded via @import in skill/command prompts, not auto-loaded every conversation).
#
# RULES_INSTRUCTIONS_CORE: ALL files that go into opencode.json instructions
#   (superset of RULES_CORE_FILES — includes user-managed safety rules).
RULES_CORE_FILES = {
    "pactkit": "pactkit.md",  # Merged: core + hierarchy + atlas + routing + principles + nudge
}

RULES_ONDEMAND_FILES = {
    "workflow": "01-workflow-conventions.md",   # Git/branch conventions — only Done/PR/Release
    "mcp": "02-mcp-integration.md",            # MCP server usage — only Act/Check/Design
    "shared": "03-shared-protocols.md",        # Visualize/test mapping — only execution phases
    "architecture": "04-architecture-principles.md",  # Full SOLID details — only Plan/Act
    "sectional": "05-sectional-write.md",      # Large file strategy — only file-generation tasks
    "solution": "06-solution-design.md",       # Framework capability assessment — only Plan/Act
    "engineering": "07-engineering-concerns.md",  # NFR trigger index — Plan/Act guide loading
}

# Full set of PactKit-MANAGED rules (used for deployment + CLAUDE_MD_TEMPLATE)
RULES_FILES = {**RULES_CORE_FILES, **RULES_ONDEMAND_FILES}

# Prefix/name lists for legacy cleanup (deployer uses filenames directly now).
# RULES_GLOBAL_PREFIXES: exact name(s) used in ~/.claude/rules/ for PactKit-managed files.
# RULES_ONDEMAND_PREFIXES: numeric prefixes used in ~/.claude/skills/_rules/.
RULES_GLOBAL_PREFIXES = ["pactkit"]
RULES_ONDEMAND_PREFIXES = ["01-", "02-", "03-", "04-", "05-", "06-", "07-"]

# On-demand deploy directory name (deployed under skills/)
RULES_ONDEMAND_DIR = "_rules"

# Files to inject into opencode.json instructions (always-load layer)
# Includes user-managed safety rules (09-credential-safety) even though PactKit
# doesn't deploy their content — they are written by the user or by separate tools.
# SEC-1: credential safety must ALWAYS be in context.
RULES_INSTRUCTIONS_CORE = [
    "rules/pactkit.md",
    "rules/09-credential-safety.md",  # user-managed but security-critical
]

# User-managed credential safety rule (not in RULES_MODULES, but always required)
# SEC-1: This file must be injected into every command regardless of config.
CREDENTIAL_SAFETY_FILE = "09-credential-safety.md"

# STORY-slim-011: Command → Rules mapping
# Each command loads only the rules it needs, reducing token waste.
# "credential" is a special key referencing CREDENTIAL_SAFETY_FILE (user-managed).
# Keys must exist in RULES_FILES: pactkit (merged core+hierarchy+atlas+routing+
# principles+nudge), workflow, mcp, shared, architecture, sectional, solution,
# engineering; plus the virtual "credential".
# NOTE: core/hierarchy/atlas/routing were merged into the single "pactkit" rule
# file — stale keys were silently skipped by deployers (drift found 2026-08-13).
COMMAND_RULES_MAP = {
    # Slimmed: architecture/solution/engineering removed from @inject — loaded on-demand via Read
    # in command playbooks when their trigger conditions are met (Phase 1.5, Solution Design, etc.)
    "project-init": ["pactkit", "sectional", "shared", "credential"],
    "project-plan": ["pactkit", "sectional", "mcp", "shared", "credential"],
    "project-clarify": ["pactkit", "credential"],
    "project-act": ["pactkit", "mcp", "shared", "credential"],
    "project-check": ["pactkit", "mcp", "shared", "credential"],
    "project-done": ["pactkit", "workflow", "shared", "credential"],
    "project-release": ["pactkit", "workflow", "credential"],
    "project-pr": ["pactkit", "workflow", "credential"],
    "project-hotfix": ["pactkit", "workflow", "shared", "credential"],
    "project-design": ["pactkit", "sectional", "mcp", "credential"],
    "project-sprint": [
        "pactkit", "sectional", "workflow",
        "mcp", "shared", "credential",
    ],
    "project-debug": ["pactkit", "shared", "credential"],
}

# Managed file prefixes for rules/ directory cleanup (deployer will clean these, leave user files intact)
# STORY-slim-112: Only global prefixes here — on-demand prefixes handled separately via RULES_ONDEMAND_PREFIXES
RULES_MANAGED_PREFIXES = RULES_GLOBAL_PREFIXES

# CLAUDE_MD_TEMPLATE: auto-generated from RULES_CORE_FILES (STORY-slim-007: DRY principle)
# Classic mode: only global rules are in ~/.claude/rules/ (on-demand in skills/_rules/)
# OpenCode uses split strategy: core via instructions, ondemand via AGENTS.md @refs (STORY-slim-009)
_claude_rules_imports = "\n".join(f"@~/.claude/rules/{filename}" for filename in sorted(RULES_CORE_FILES.values()))
CLAUDE_MD_TEMPLATE = f"""# PactKit Global Constitution (v{__version__} Modular)

{_claude_rules_imports}

You MAY read `.pactkit/context.md` as optional history; it never blocks
current-session work. Refresh it with `pactkit context` only for a useful handover.
The file is generated locally and is not imported or committed.
"""

# Backward-compatible: combine all modules for anything that still reads this
CONSTITUTION_EXPERT = CLAUDE_MD_TEMPLATE


# ---------------------------------------------------------------------------
# STORY-slim-20260825b1c83a046b4b: scenario-driven rule registry
# ---------------------------------------------------------------------------
#
# Keep the pre-2.24 values above addressable as migration evidence.  Existing
# project configuration used their file-stem identifiers, so deleting them
# outright would turn an upgrade into a surprising configuration failure.  The
# active public constants below are projections of RULE_DEFINITIONS; callers
# must not infer ownership or load policy from a filename.

LEGACY_RULE_CONTENTS = {
    filename: RULES_MODULES[key]
    for key, filename in RULES_FILES.items()
}


@dataclass(frozen=True)
class RuleDefinition:
    """One logical PactKit rule, independent from a host filesystem path."""

    id: str
    filename: str
    content: str
    owner: str
    level: str
    scope: tuple[str, ...]
    load_policy: str
    failure: str
    trigger: str
    skip_when: tuple[str, ...]
    evidence: tuple[str, ...]
    override: str
    clauses: tuple[str, ...] = ()
    legacy_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleClause:
    """One independently enforceable statement in a rendered rule."""

    id: str
    level: str
    trigger: str
    skip_when: tuple[str, ...]
    evidence: tuple[str, ...]
    failure: str
    override: str


@dataclass(frozen=True)
class PhaseContract:
    """Outcome contract for one command, independent of its playbook."""

    phase: str
    entry: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    invariants: tuple[str, ...]
    completion_evidence: tuple[str, ...]
    failure_semantics: str
    allowed_next: tuple[str, ...]
    external_effects: tuple[str, ...] = ()

    @property
    def next_commands(self) -> tuple[str, ...]:
        """Compatibility alias for the pre-2.24 PhasePolicy API."""
        return self.allowed_next

    def render(self) -> str:
        """Render a compact, tool-neutral contract for an active command."""
        title = self.phase.replace("_", " ").title()
        sections = (
            ("Entry", (self.entry,)),
            ("Inputs", self.inputs),
            ("Outputs", self.outputs),
            ("Invariants", self.invariants),
            ("Completion Evidence", self.completion_evidence),
            ("Failure Semantics", (self.failure_semantics,)),
            ("Allowed Next", self.allowed_next or ("none",)),
            ("External Effects", self.external_effects or ("none",)),
        )
        lines = [f"# {title} Contract"]
        for heading, values in sections:
            lines.extend(("", f"## {heading}", *(f"- {value}" for value in values)))
        return "\n".join(lines) + "\n"


RUNTIME_KERNEL = """# PactKit Runtime Contract

## Activation
PactKit phase rules are active only when the user invokes a PactKit skill or
the task explicitly requests that workflow. Do not redirect ordinary questions
or coding into PDCA automatically.

## Current Session
Work in the current host and current session. Do not require a new session, a
runner, delegated work item, or resumable agent thread unless the user asks for
that execution model. Historical workflow records and phase states are evidence,
never exclusive locks.

## Authority and Safety
Follow the user's latest explicit instruction within platform safety and
permission boundaries. Obtain applicable authorization before push, pull
request, release, publication, destructive deletion, or external messages.
Never expose passwords, API keys, tokens, or other credentials, and never
persist secrets in source control or generated evidence.

## Rule Semantics
Hard rules may block only credential exposure, permissions, or material risk of
irreversible damage. Required rules define evidence needed to claim a phase is
complete; missing evidence keeps completion incomplete but never prevents safe
investigation, implementation, testing, or repair. Defaults may be changed
with project evidence. Advisories never create gates.

## Failure Handling
Classify failures as current regression, pre-existing failure, obsolete
contract/test, or environment/dependency failure. Continue safe in-scope work
when possible and report unresolved evidence without creating a workflow lock.

## Language and Loading
Match the user's language. Load only rules declared by the active skill and
only the engineering guides selected by the Spec or current risk.
"""


LEGACY_PHASE_RULE_CONTENTS = {
    "phase-plan": """# Plan Contract

Create or amend a Spec from current project evidence. Clarification improves
precision but a user may decline it. Record assumptions and decisions in the
Spec; do not make historical workflow state a planning gate.
""",
    "phase-act": """# Act Contract

Read the active Spec and preflight declared inputs before the first source
write. Use tests to establish intended behavior before implementation when the
change is testable. Missing required evidence makes the phase incomplete, not
locked: continue safe investigation and repair in this session.
""",
    "phase-check": """# Check Contract

Review the implementation without changing it. Report security, quality, test
quality, and Spec-alignment findings with evidence. A failed check identifies
work to repair; it does not prevent a later Act run.
""",
    "phase-done": """# Done Contract

Only claim completion when required evidence exists. Reuse a recent verified
regression result when no source changed. Commit, archive, and other external
side effects require current authorization.
""",
    "phase-pr": """# PR Contract

Prepare a reviewable summary and test evidence. Push and pull-request creation
are external side effects and require current authorization.
""",
    "phase-release": """# Release Contract

Verify version, changelog, artifacts, and release evidence. Tags, publication,
and GitHub releases require explicit current authorization.
""",
    "phase-hotfix": """# Hotfix Contract

Use the smallest safe repair path. Validate the regression and affected tests;
escalate to a Spec when scope or product behavior expands beyond a hotfix.
""",
}

SHARED_RULES = {
    "pdca-lifecycle": """# PDCA Lifecycle

## Entry
Activate a phase only when the user invokes its skill or explicitly asks for
that workflow. Resolve the current objective, project root, and relevant Story
from the current request and repository evidence; old run state is advisory.

## Execution
Work in the current conversation. Reuse valid evidence already produced in this
session. Do not repeat a completed step unless inputs changed or verification
shows a reason. Ask only when a missing decision would materially change the
result or authorize an external or destructive action.

## Transition
Finishing one phase does not automatically authorize the next phase. Continue
into another phase only when the user's request includes it, such as Sprint, or
when the user explicitly invokes the next skill. A new session is optional.

## Completion
Report complete only when that phase's required outputs and evidence exist.
Missing evidence means incomplete-with-next-action, not a lock on reading,
diagnosis, implementation, testing, or repair.

## Interruption and Change
If the user interrupts, replaces the request, or changes a requirement, stop
the superseded work and follow the latest instruction. Update stale artifacts
when authorized; never force execution against a known-obsolete Spec or state.

## Exit
End with the achieved outcome, remaining evidence gaps, and the smallest useful
next action. Do not manufacture a handoff, background run, or separate session.
""",
    "shared-execution": """# Shared Execution

## Hierarchy of Truth
Code is not the law. Tier 1: Specs (`docs/specs/*.md`) and Test Cases;
Tier 2: Tests; Tier 3: Implementation. On conflict, the higher tier
takes precedence — modify the lower tier, never the reverse. When the
Spec itself is wrong, fix the Spec first, then sync tests and code; never
patch code around a known-bad Spec.

## Execution
Use the current session. Failure classification is: current regression,
pre-existing failure, obsolete contract/test, or environment failure. Only a
hard risk blocks its exact action; otherwise record evidence and continue.
""",
    "spec-preflight": """# Spec Preflight

For an Act bound to a Spec, read declared references and constraints before the
first source write. A receipt is bound to project root and Spec hash. A missing
receipt prevents a completion claim, not safe read/test/repair work. Hotfixes
and explicit user overrides may proceed with a recorded rationale.
""",
    "external-tools": """# External Tools

MCP and external tools are conditional. Use them when available and useful;
their absence is a warning, not a workflow blocker.
""",
    "git-workflow": """# Git Workflow

Use the repository's established commit and branch conventions. Do not push,
create a pull request, tag, publish, or release without current authorization.
""",
    "capability-design": """# Capability Design

Before reimplementing an available framework or project capability, compare
the needed behavior with its public interface and document the chosen gap.

1. Read the project dependency file (`pyproject.toml`, `package.json`,
   `go.mod`, `pom.xml`/`build.gradle`) and list frameworks relevant to the
   requirement.
2. For each needed capability, decide the source: framework native, existing
   project wrapper, or new implementation.
3. Record the assessment — Plan writes it into the Spec's Technical Design,
   Act outputs a brief version before implementation:
   | Need | Source | Decision |
   |------|--------|----------|
   | {capability} | {framework module / project wrapper / new} | Reuse / Enable / New |
4. MUST NOT bypass an existing project wrapper to use the framework directly;
   state the reason when declining an available native capability.
5. Skip when the change is pure business logic or documentation/config only.

## Knowledge Provenance
Claims about external APIs, version behavior, config keys, and protocol
formats MUST come from a verified source, in priority order: the project's
own code (read it) > Context7 MCP or official docs > training memory.
Training memory is the LAST resort: mark the claim "unverified" in output
and verify before relying on it. A fabricated-from-memory API or signature
is a defect, not a style issue. Design decisions (patterns, formats,
conventions) SHOULD name their reference — an existing project file, a
doc, or a well-known standard; invented-here with no reference is a
review flag.
""",
    "engineering-index": RULES_MODULES["engineering"],
    "sectional-heuristics": """# Sectional Editing Heuristics

For large files, prefer small verified edits and preserve surrounding context.
This is a host editing technique, not an engineering law or completion gate.
""",
    "pactkit-maintainer": """# PactKit Maintainer Overlay

Apply this overlay only while changing the PactKit repository: preserve adapter
parity, prompt integrity, deployment ownership, and bounded prompt budgets.
Do not load this overlay in business projects.
""",
    "sprint-orchestrator": """# Sprint Orchestrator

Keep exactly one phase active at a time in the current session. Before each
stage, load that phase's managed capsule using the host-native instruction in
the Sprint command. A completed or failed capsule becomes historical evidence
and cannot constrain later safe work. Check failures return to Act for repair;
external effects remain subject to current authorization.
""",
}


RULE_CLAUSES = {
    "runtime.activation": RuleClause(
        id="runtime.activation", level="required",
        trigger="when deciding whether PactKit phase rules apply",
        skip_when=("no PactKit workflow is invoked or requested",),
        evidence=("the user explicitly invoked or requested the workflow",),
        failure="incomplete_continue",
        override="the user's latest explicit workflow choice controls activation",
    ),
    "runtime.current-session": RuleClause(
        id="runtime.current-session", level="default",
        trigger="while executing an active workflow",
        skip_when=("the user requests another supported execution model",),
        evidence=("work continues in the current host session unless the user chooses otherwise",),
        failure="record_deviation",
        override="the user may explicitly request another supported execution model",
    ),
    "runtime.language": RuleClause(
        id="runtime.language", level="advisory",
        trigger="when producing user-facing output",
        skip_when=("the user requests another language",),
        evidence=("output matches the user's language",),
        failure="warn_continue", override="the user may request another language",
    ),
    "runtime.evidence-reuse": RuleClause(
        id="runtime.evidence-reuse", level="default",
        trigger="before repeating a completed verification",
        skip_when=("inputs changed", "freshness is uncertain", "the user requests a rerun"),
        evidence=("the evidence input fingerprint still matches current inputs",),
        failure="record_deviation",
        override="rerun when freshness is uncertain or the user requests it",
    ),
    "safety.credentials": RuleClause(
        id="safety.credentials", level="hard",
        trigger="before exposing or persisting a secret",
        skip_when=("the content is verified non-secret test data",),
        evidence=("no credential or secret is disclosed or committed",),
        failure="block_exact_action", override="not overridable beyond platform policy",
    ),
    "safety.authorization": RuleClause(
        id="safety.authorization", level="hard",
        trigger="before an external side effect such as push, PR, publish, release, or message",
        skip_when=("the action is read-only or confined to the authorized local workspace",),
        evidence=("current user authorization covers the exact action and target",),
        failure="block_exact_action", override="explicit current authorization is required",
    ),
    "safety.irreversible-damage": RuleClause(
        id="safety.irreversible-damage", level="hard",
        trigger="before a destructive or materially irreversible operation",
        skip_when=("the operation is read-only or safely reversible",),
        evidence=("the exact target is resolved and recovery or authorization is established",),
        failure="block_exact_action",
        override="explicit authorization cannot override platform safety",
    ),
}


def _phase_contract(
    phase: str, entry: str, inputs: tuple[str, ...], outputs: tuple[str, ...],
    invariants: tuple[str, ...], evidence: tuple[str, ...],
    allowed_next: tuple[str, ...], external_effects: tuple[str, ...] = (),
) -> PhaseContract:
    return PhaseContract(
        phase=phase, entry=entry, inputs=inputs, outputs=outputs,
        invariants=invariants, completion_evidence=evidence,
        failure_semantics="incomplete_continue", allowed_next=allowed_next,
        external_effects=external_effects,
    )


PHASE_CONTRACTS = {
    "project-init": _phase_contract(
        "bootstrap", "explicit initialization request",
        ("project root", "selected host profile"),
        ("project governance scaffold",),
        ("preserve existing project and user files",),
        ("required project markers exist",),
        ("project-plan", "project-design"),
    ),
    "project-plan": _phase_contract(
        "plan", "explicit planning request for one bounded change",
        ("current user intent", "repository evidence"),
        ("Spec", "Story record", "change risk profile"),
        ("requirements are testable and scope is explicit",),
        ("Spec lint passes", "requirements map to acceptance criteria"),
        ("project-act",),
    ),
    "project-clarify": _phase_contract(
        "clarify", "explicit clarification request or material ambiguity",
        ("current request", "known constraints"), ("clarified brief",),
        ("unanswered questions remain visible and never become invented facts",),
        ("decisions and assumptions are distinguishable",), ("project-plan",),
    ),
    "project-act": _phase_contract(
        "act", "explicit implementation request with a usable objective",
        ("current request", "Spec when Spec-bound", "declared inputs"),
        ("implementation", "behavioral tests"),
        ("scope integrity", "edit the source of truth", "safe work remains available"),
        ("Spec alignment", "fresh adequate behavioral tests", "regression classification"),
        ("project-check", "project-done"),
    ),
    "project-check": _phase_contract(
        "check", "explicit verification or review request",
        ("implementation diff", "Spec and test evidence"),
        ("evidence-backed verdict",),
        (
            "review is read-only unless the user also requests repair",
            # STORY-slim-2026090301691dea72e8: verification-setup falsifications
            # (admin-tested business permissions, stale-process test runs).
            "verification setup matches the Spec's actor and environment",
            "test environment provenance is confirmed (running code == code under test)",
            # STORY-slim-2026090301691dea72e8: whack-a-mole fixing pattern.
            "a defect finding sweeps its class — same-pattern sites are checked before a pass verdict",
            # STORY-slim-2026090333d6b72f7645: ISO 12207 validation vs verification —
            # admin-tested business permissions passed while the real scenario broke.
            "user-path validation is distinguished from Spec-conformance verification —"
            " key scenarios run through the real end-user path, not a privileged one",
        ),
        (
            "security, quality, test adequacy, freshness, and Spec alignment assessed",
            "test environment provenance is confirmed",
        ),
        ("project-act", "project-done"),
    ),
    "project-done": _phase_contract(
        "done", "explicit finalization request for verified work",
        ("fresh verification evidence", "project governance state"),
        ("consistent project records", "optional commit"),
        ("reuse fresh evidence and disclose every remaining gap",),
        # STORY-slim-2026090301691dea72e8: "adequate" includes actor and
        # environment dimensions (admin-tested business permissions passed
        # while the real scenario was broken).
        ("required verification is adequate for the Spec's actor and environment, and current", "status projections agree"), (),
        ("commit", "archive"),
    ),
    "project-release": _phase_contract(
        "release", "explicit release request",
        ("verified version", "changelog", "artifacts"),
        ("release-ready artifacts",),
        ("publishing requires exact current authorization",),
        ("version and artifact provenance agree",), (),
        ("tag", "publish", "release"),
    ),
    "project-pr": _phase_contract(
        "pr", "explicit pull-request request",
        ("reviewable branch", "fresh test evidence"), ("reviewable PR",),
        ("push and PR creation require exact current authorization",),
        ("summary, risk, and test evidence are complete",), (),
        ("push", "pull request"),
    ),
    "project-hotfix": _phase_contract(
        "hotfix", "explicit bounded repair request",
        ("reproduced symptom", "affected scope"),
        ("minimal repair", "focused regression test"),
        ("escalate when product behavior or architecture expands",),
        ("reported failure is fixed", "affected tests pass"),
        ("project-check", "project-done"),
    ),
    "project-design": _phase_contract(
        "design", "explicit greenfield or multi-story product design request",
        ("product objective", "users and constraints"),
        ("PRD", "decomposed Specs", "Story records"),
        ("outcomes and non-goals remain explicit",),
        ("scope, risks, and dependencies are traceable",),
        ("project-plan", "project-act"),
    ),
    "project-sprint": _phase_contract(
        "sprint", "explicit request to execute an ordered PDCA sequence",
        ("selected Story or confirmed wave",), ("ordered phase outcomes",),
        ("exactly one phase capsule is active at a time",),
        ("each entered phase meets its own completion evidence",), (),
    ),
    "project-debug": _phase_contract(
        "debug", "explicit diagnosis request",
        ("observable symptom", "bounded target"),
        ("reproduced symptom", "ranked root-cause conclusion"),
        ("test hypotheses against evidence before proposing a cause",),
        ("cause and uncertainty are stated",),
        ("project-hotfix", "project-plan"),
    ),
}


PHASE_RULE_CONTENTS = {
    "phase-plan": PHASE_CONTRACTS["project-plan"].render(),
    "phase-act": PHASE_CONTRACTS["project-act"].render(),
    "phase-check": PHASE_CONTRACTS["project-check"].render(),
    "phase-done": PHASE_CONTRACTS["project-done"].render(),
    "phase-pr": PHASE_CONTRACTS["project-pr"].render(),
    "phase-release": PHASE_CONTRACTS["project-release"].render(),
    "phase-hotfix": PHASE_CONTRACTS["project-hotfix"].render(),
}


def _definition(
    rule_id: str, filename: str, content: str, *, scope: tuple[str, ...],
    load_policy: str = "command", level: str = "required",
    failure: str = "incomplete_continue", legacy_ids: tuple[str, ...] = (),
    trigger: str | None = None, skip_when: tuple[str, ...] = (),
    evidence: tuple[str, ...] | None = None, override: str | None = None,
    clauses: tuple[str, ...] = (),
) -> RuleDefinition:
    resolved_trigger = trigger or (
        "every host interaction" if load_policy == "global"
        else "when referenced by the active PactKit skill"
    )
    resolved_evidence = evidence or (
        "rule is present in the host's active instruction artifact",
    )
    resolved_override = override or (
        "not overridable without changing the exact hard-risk condition"
        if level == "hard"
        else "user may override with an explicit reason within safety boundaries"
    )
    return RuleDefinition(
        id=rule_id, filename=filename, content=content, owner="pactkit",
        level=level, scope=scope, load_policy=load_policy, failure=failure,
        trigger=resolved_trigger, skip_when=skip_when, evidence=resolved_evidence,
        override=resolved_override, clauses=clauses, legacy_ids=legacy_ids,
    )


RULE_DEFINITIONS = {
    "runtime": _definition(
        "runtime", "pactkit-runtime.md", RUNTIME_KERNEL,
        scope=("global",), load_policy="global", level="required",
        failure="incomplete_continue", legacy_ids=("pactkit", "01-core-protocol"),
        trigger="when PactKit is installed in the current host",
        evidence=("ordinary work remains outside PDCA unless explicitly activated",),
        override="the user's latest explicit workflow choice controls activation",
        clauses=tuple(RULE_CLAUSES),
    ),
"phase-plan": _definition("phase-plan", "phases/plan-contract.md", PHASE_RULE_CONTENTS["phase-plan"], scope=("project-plan", "project-design", "project-clarify"), load_policy="phase", legacy_ids=("plan",),
        trigger="while /project-plan or /project-design or /project-clarify executes in the current session",
        evidence=("the phase capsule is @import-ed by the active project-plan skill",),
    ),
"phase-act": _definition("phase-act", "phases/act-contract.md", PHASE_RULE_CONTENTS["phase-act"], scope=("project-act",), load_policy="phase", legacy_ids=("act",),
        trigger="while /project-act executes in the current session",
        evidence=("the phase capsule is @import-ed by the active project-act skill",),
    ),
"phase-check": _definition("phase-check", "phases/check-contract.md", PHASE_RULE_CONTENTS["phase-check"], scope=("project-check",), load_policy="phase", legacy_ids=("check",),
        trigger="while /project-check executes in the current session",
        evidence=("the phase capsule is @import-ed by the active project-check skill",),
    ),
"phase-done": _definition("phase-done", "phases/done-contract.md", PHASE_RULE_CONTENTS["phase-done"], scope=("project-done",), load_policy="phase", legacy_ids=("done",),
        trigger="while /project-done executes in the current session",
        evidence=("the phase capsule is @import-ed by the active project-done skill",),
    ),
"phase-pr": _definition("phase-pr", "phases/pr-contract.md", PHASE_RULE_CONTENTS["phase-pr"], scope=("project-pr",), load_policy="phase", legacy_ids=("pr",),
        trigger="while /project-pr executes in the current session",
        evidence=("the phase capsule is @import-ed by the active project-pr skill",),
    ),
"phase-release": _definition("phase-release", "phases/release-contract.md", PHASE_RULE_CONTENTS["phase-release"], scope=("project-release",), load_policy="phase", legacy_ids=("release",),
        trigger="while /project-release executes in the current session",
        evidence=("the phase capsule is @import-ed by the active project-release skill",),
    ),
"phase-hotfix": _definition("phase-hotfix", "phases/hotfix-contract.md", PHASE_RULE_CONTENTS["phase-hotfix"], scope=("project-hotfix",), load_policy="phase", legacy_ids=("hotfix",),
        trigger="while /project-hotfix executes in the current session",
        evidence=("the phase capsule is @import-ed by the active project-hotfix skill",),
    ),
"pdca-lifecycle": _definition("pdca-lifecycle", "execution/pdca-lifecycle.md", SHARED_RULES["pdca-lifecycle"], scope=("pdca",), legacy_ids=("04-routing-table",),
        trigger="during any PDCA phase transition or completion claim",
        evidence=("the capsule is @import-ed by the active command skill",),
    ),
"shared-execution": _definition("shared-execution", "execution/shared-execution.md", SHARED_RULES["shared-execution"], scope=("execution",), legacy_ids=("02-hierarchy-of-truth", "03-shared-protocols", "07-shared-protocols", "shared"),
        trigger="during phase execution in the current session",
        evidence=("the capsule is @import-ed by the active command skill",),
    ),
    "spec-preflight": _definition(
        "spec-preflight", "execution/spec-preflight.md",
        SHARED_RULES["spec-preflight"], scope=("project-act",),
        trigger="before the first source write in a Spec-bound Act",
        skip_when=("no Spec reference", "project-hotfix is active"),
        evidence=("preflight receipt matches project root and Spec hash",),
    ),
"external-tools": _definition("external-tools", "execution/external-tools.md", SHARED_RULES["external-tools"], scope=("external",), load_policy="conditional", level="default", failure="record_deviation", legacy_ids=("02-mcp-integration", "06-mcp-integration", "mcp"),
        trigger="when a phase needs an external tool or network service",
        evidence=("the capsule is @import-ed by the active command skill",),
    ),
"git-workflow": _definition("git-workflow", "execution/git-workflow.md", SHARED_RULES["git-workflow"], scope=("git",), legacy_ids=("01-workflow-conventions", "05-workflow-conventions", "workflow"),
        trigger="before a git push, pull request, tag, or other external VCS effect",
        evidence=("the capsule is @import-ed by the active command skill",),
    ),
"capability-design": _definition("capability-design", "design/capability-design.md", SHARED_RULES["capability-design"], scope=("design",), load_policy="conditional", level="default", failure="record_deviation", legacy_ids=("04-architecture-principles", "06-solution-design", "08-architecture-principles", "solution"),
        trigger="when a requirement involves a framework the project already uses",
        evidence=("the capsule is @import-ed by the active command skill",),
    ),
"engineering-index": _definition("engineering-index", "engineering/index.md", SHARED_RULES["engineering-index"], scope=("engineering",), load_policy="conditional", level="default", failure="record_deviation", legacy_ids=("03-file-atlas", "07-engineering-concerns", "engineering"),
        trigger="when Act Phase 1.5 selects engineering-concern guides",
        evidence=("the capsule is @import-ed by the active command skill",),
    ),
"sectional-heuristics": _definition("sectional-heuristics", "execution/sectional-heuristics.md", SHARED_RULES["sectional-heuristics"], scope=("editing",), load_policy="conditional", level="advisory", failure="warn_continue", legacy_ids=("05-sectional-write", "09-sectional-write", "sectional"),
        trigger="when generating or reviewing long structured document sections",
        evidence=("the capsule is @import-ed by the active command skill",),
    ),
"pactkit-maintainer": _definition("pactkit-maintainer", "maintainer/pactkit-maintainer.md", SHARED_RULES["pactkit-maintainer"], scope=("pactkit-self",), load_policy="conditional", level="default", failure="record_deviation",
        trigger="while changing the PactKit repository itself",
        evidence=("the capsule is @import-ed by the active command skill",),
    ),
"sprint-orchestrator": _definition("sprint-orchestrator", "execution/sprint-orchestrator.md", SHARED_RULES["sprint-orchestrator"], scope=("project-sprint",),
        trigger="while /project-sprint runs an ordered phase sequence",
        evidence=("the capsule is @import-ed by the active command skill",),
    ),
}


RULE_ID_ALIASES = {
    alias: definition.id
    for definition in RULE_DEFINITIONS.values()
    for alias in (definition.id, *definition.legacy_ids)
}


def normalize_rule_id(rule_id: str) -> str | None:
    """Return the current logical ID for a current or 2.23 legacy ID."""
    return RULE_ID_ALIASES.get(rule_id.removesuffix(".md"))


# Public compatibility projections.  RULES_MODULES keeps legacy source keys
# for older imports, and adds all active logical IDs.
RULES_MODULES.update({key: item.content for key, item in RULE_DEFINITIONS.items()})
GLOBAL_RULE_IDS = frozenset({"runtime"})
RULES_CORE_FILES = {
    rule_id: RULE_DEFINITIONS[rule_id].filename for rule_id in GLOBAL_RULE_IDS
}
RULES_ONDEMAND_FILES = {
    key: item.filename
    for key, item in RULE_DEFINITIONS.items()
    if item.load_policy != "global"
}
RULES_FILES = {**RULES_CORE_FILES, **RULES_ONDEMAND_FILES}
RULES_GLOBAL_PREFIXES = ["pactkit-runtime"]
RULES_ONDEMAND_PREFIXES = []
RULES_ONDEMAND_DIR = "_rules"
RULES_INSTRUCTIONS_CORE = ["rules/pactkit-runtime.md"]

COMMAND_RULES_MAP = {
    "project-init": ["runtime", "pdca-lifecycle", "phase-plan", "shared-execution"],
    "project-plan": ["runtime", "pdca-lifecycle", "phase-plan", "shared-execution"],
    "project-clarify": ["runtime", "pdca-lifecycle", "phase-plan"],
    "project-act": ["runtime", "pdca-lifecycle", "phase-act", "shared-execution", "spec-preflight"],
    "project-check": ["runtime", "pdca-lifecycle", "phase-check", "shared-execution"],
    "project-done": ["runtime", "pdca-lifecycle", "phase-done", "shared-execution", "git-workflow"],
    "project-release": ["runtime", "pdca-lifecycle", "phase-release", "git-workflow"],
    "project-pr": ["runtime", "pdca-lifecycle", "phase-pr", "git-workflow"],
    "project-hotfix": ["runtime", "pdca-lifecycle", "phase-hotfix", "shared-execution"],
    "project-design": ["runtime", "pdca-lifecycle", "phase-plan"],
    "project-sprint": ["runtime", "pdca-lifecycle", "sprint-orchestrator", "shared-execution"],
    "project-debug": ["runtime", "pdca-lifecycle", "shared-execution"],
}

# Candidate rules are available to a command but are not activated until the
# command's documented trigger is observed.  Keeping this separate from
# COMMAND_RULES_MAP prevents deployers from accidentally preloading them.
COMMAND_CONDITIONAL_RULES_MAP = {
    "project-init": ["sectional-heuristics"],
    "project-plan": ["external-tools", "capability-design", "engineering-index", "sectional-heuristics"],
    "project-act": ["external-tools", "capability-design", "engineering-index"],
    "project-check": ["external-tools"],
    "project-design": ["external-tools", "capability-design", "sectional-heuristics"],
}


PHASE_POLICIES = PHASE_CONTRACTS
SPRINT_PHASE_SEQUENCE = ("phase-plan", "phase-act", "phase-check", "phase-done")

RULES_MANAGED_PREFIXES = RULES_GLOBAL_PREFIXES
_claude_rules_imports = "\n".join(
    f"@~/.claude/rules/{filename}" for filename in RULES_CORE_FILES.values()
)
CLAUDE_MD_TEMPLATE = f"""# PactKit Runtime Contract (v{__version__})

{_claude_rules_imports}
"""
CONSTITUTION_EXPERT = CLAUDE_MD_TEMPLATE
