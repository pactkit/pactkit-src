---
mode: agent
description: "QA verification: security scan, code quality scan, Spec alignment"
---

# Command: Check (v1.3.0 Deep QA)
- **Usage**: `/project-check $ARGUMENTS`
- **Agent**: QA Engineer

> **PRINCIPLE**: Check is a verification-only operation; identify issues but do not fix them.

## Severity Levels

| Level | Name | Action |
|-------|------|--------|
| **P0** | Critical | Must block — security vulnerability, data loss risk, correctness bug |
| **P1** | High | Should fix — logic error, significant violation, performance regression |
| **P2** | Medium | Fix or follow-up — code smell, maintainability concern |
| **P3** | Low | Optional — style, naming, minor suggestion |

## Phase 0: The Thinking Process
> **Execution Style**: Work through each phase incrementally — output progress as you go.
1.  **Analyze Context**: Read the active `docs/specs/{ID}.md`.
2.  **Determine Layer**:
    * *Logic Only?* -> Strategy: **API Level**.
    * *UI/DOM/Interaction?* -> Strategy: **Browser Level**.
3.  **Detect Stack**: If changed files include `.tsx`/`.vue`/`.svelte`, also apply frontend-specific checks (component structure, accessibility, rendering performance).
4.  **Gap Analysis**: Do we have a structured Test Case? If not, plan to create one.
5.  **Security Scope**: Check if the Spec contains a `## Security Scope` section.
    - If present: parse the `Applicable` column for each SEC-* check. Pass this scope to Phase 1.
    - If absent (legacy Spec): run `pactkit sec-scope <changed-files>` (run from terminal) to auto-detect, or fall back to all 8 checks.

## Phase 1: Security Scan (OWASP+)
> **Config**: If `.github/pactkit.yaml` contains `check.security_checklist: false`, skip this phase and log: "Security checklist disabled via config".
> **Scope**: If `.github/pactkit.yaml` contains `check.security_scope_override: full`, run ALL 8 checks regardless of the Spec's Security Scope. Otherwise, use the scope parsed in Phase 0.

For each SEC-* check:
- If the Security Scope (from Phase 0) marks the check as **Applicable: Yes** (or no scope available): execute the check and output **PASS**, **FAIL**, or **N/A** (not applicable to this story).
- If the Security Scope marks the check as **Applicable: No** or **N/A**: output `SEC-{N}: SKIPPED ({reason from scope table})` — do not execute the check.

Evaluate all applicable code related to the Story against this structured 8-item checklist:

| ID | Category | Check |
|----|----------|-------|
| SEC-1 | Secrets | No hardcoded API keys, tokens, or passwords in source code |
| SEC-2 | Input | All user inputs validated (schema validation or whitelist) |
| SEC-3 | SQL | All database queries use parameterized queries (no string concat) |
| SEC-4 | XSS | User-provided content sanitized before rendering |
| SEC-5 | Auth | Authentication tokens in httpOnly cookies (not localStorage) |
| SEC-6 | Rate | Rate limiting configured on public endpoints |
| SEC-7 | Error | Error messages do not expose stack traces or internal paths |
| SEC-8 | Deps | No known CVEs in dependencies (npm audit / pip-audit clean) |

**Severity rules**:
- Any **FAIL** on SEC-1 through SEC-5 → classify as **P0 Critical** — report immediately, do not wait for full scan.
- Any **FAIL** on SEC-6 through SEC-8 → classify as **P1 High**.

**Additional OWASP patterns to consider**: Injection (SQL/NoSQL/command injection), SSRF (Server-Side Request Forgery), Race Condition / TOCTOU (Time-of-Check-Time-of-Use), path traversal, session fixation. Flag any occurrence as P0 if exploitable.

**Cross-phase linkage (R5.1)**: If the Spec contains `## Implementation Steps` with Risk=High items, prioritize those files for security review.

Include the checklist results in Phase 5 Verdict under `### Security Checklist`.

## Phase 2: Code Quality Scan
Apply a code quality checklist to all code related to the Story:

- **Error Handling**: Swallowed exceptions, overly broad catch, missing error handling, async errors
- **Performance**: N+1 queries, CPU hotspots in hot paths, missing cache, unbounded memory growth
- **Boundary Conditions**: Null/undefined handling, empty collections, off-by-one, division by zero, numeric overflow
- **Logic Correctness**: Does the implementation match Spec intent? Are edge cases handled?

For each finding, assign a severity (P0-P3). Flag issues that may cause silent failures.

## Phase 3: Spec Verification & Test Case Definition (The Law)
1.  **Verify Spec Structure**: Run `python3 .github/skills/pactkit-scaffold/scripts/spec_linter.py docs/specs/{STORY_ID}.md` to validate Spec structure (E006 checks for `## Acceptance Criteria`).
    * *If ERRORs*: WARN the user — "Spec structure issues found. Run `/project-plan` to fix."
    * *If WARNs only*: Note warnings and continue.
2.  **Extract Scenarios**: List all Scenarios from the Spec's `## Acceptance Criteria` section.
3.  **Check**: Does `docs/test_cases/{STORY_ID}_case.md` exist?
4.  **Action**: If missing, generate it based *strictly* on the Spec's Acceptance Criteria.
    * *Format*: Gherkin (Given/When/Then).
    * *Constraint*: Do not write Python code yet.
5.  **Validate Test Case Structure**: Run `pactkit lint-testcase docs/test_cases/{STORY_ID}_case.md` from the terminal to validate the test case file structure. If errors, WARN the user.
6.  **Coverage Report**: Compare Scenarios in Spec vs Test Cases. Report any uncovered Scenario.

## Phase 3.5: Test Quality Gate
> **Purpose**: Prevent tautological or low-value tests from passing the regression gate unchallenged.

1.  **Identify Story Tests**: Find all test files created or modified for the current Story (use `git diff --name-only` or match `test_{STORY_ID}` / `test_story*` patterns).
2.  **Read & Audit**: Read each test file and check for these anti-patterns:
    - **Tautological assertions** (P1): `assert True`, `assert 1 == 1`, or any assertion that can never fail regardless of implementation correctness.
    - **Missing assertions** (P1): Test functions that execute code but contain no `assert` statement — they pass silently without verifying anything.
    - **Over-mocking** (P2): Test mocks or stubs every dependency so that no real logic is exercised; the test only verifies the mock wiring, not actual behavior.
    - **Happy-path only** (P2): All test methods only cover the success case with no error inputs, boundary conditions, or edge cases tested.
3.  **Report**: For each finding, assign the severity above and include it in the Phase 5 verdict.
4.  **Gate**: If any P1 test quality issue is found, flag it as a required fix (same as a code quality P1).

## Phase 4: E2E Execution (Config-Driven)
> Read `.github/pactkit.yaml` field `e2e.type` to select strategy. Default: `none` (skip).

| e2e.type | Test Path | Tools | Cleanup |
|----------|-----------|-------|---------|
| `none` | Skip — log "E2E skipped" | — | — |
| `cli` | `{e2e.test_dir}/cli/test_{STORY_ID}_cli.py` | pytest + subprocess | pytest `tmp_path` fixture (auto) |
| `frontend` | `{e2e.test_dir}/browser/test_{STORY_ID}_browser.py` | Playwright + MSW mock from `e2e.api_spec` | MSW in-memory interceptors (auto) |
| `backend` | `{e2e.test_dir}/api/test_{STORY_ID}_api.py` | pytest + httpx, contract via `e2e.api_spec` | transaction rollback via fixtures |
| `fullstack` | `{e2e.test_dir}/browser/test_{STORY_ID}_full.py` | docker-compose up + Playwright | `docker-compose down -v` |

* **Playwright MCP**: IF available, use for browser verification (frontend/fullstack).
* **Chrome DevTools MCP**: IF available, use for performance tracing.
* **`e2e.env_file`** (default `.env.test`): Load test credentials (API tokens, DB strings) from this file before running E2E. If file missing, WARN but continue.
* **`e2e.blocking`** (default `false`): If `false`, E2E failures → WARN. If `true`, E2E failures → FAIL (blocks `/project-done`).

## Phase 4.5: PactGuard Compliance Scan (Config-Gated)
> Read `.github/pactkit.yaml` field `check.pactguard.enabled`. Default: `false` (skip).

1.  If `check.pactguard.enabled` is `false` (default) → **silently skip** this phase entirely. Do NOT add a row to the Verdict table.
2.  If enabled: check if `pactguard` CLI is available (`which pactguard`). If not found → silently skip.
3.  Run: `pactguard check --mode {check.pactguard.mode} -r {check.pactguard.ruleset} --json-output <changed_files>`
    - If `check.pactguard.ruleset` is empty, omit the `-r` flag (use PactGuard defaults).
4.  Parse JSON output. Add to Phase 5 Verdict table: `PactGuard | PASS/WARN/FAIL | N violations`
5.  If `check.pactguard.blocking: true` and violations found → contribute FAIL to overall verdict.
6.  If `pactguard` exits with error → add `PactGuard | WARN | execution error` to Verdict. Do NOT block.

## Phase 4.7: Observability Scan (Config-Gated)
> Read `.github/pactkit.yaml` field `check.observe.enabled`. Default: `false` (skip).

1.  If `check.observe.enabled` is `false` (default) → **silently skip** this phase entirely. Do NOT add a row to the Verdict table.
2.  If enabled: detect available MCP sources (`mcp__chrome-devtools__*`, `mcp__playwright__*`). If none available → silently skip.
3.  Collect signals (or run `pactkit observe --json` (run from terminal) for structured collection):
    - Chrome DevTools: `list_console_messages`, `list_network_requests` (cap: `check.observe.max_console`, `check.observe.max_network`)
    - Playwright: `browser_take_screenshot` for post-test visual verification
4.  Classify signals by severity (ERROR/WARNING/INFO per R3 in Spec).
5.  Add to Phase 5 Verdict table: `Observability | PASS/WARN/FAIL | N console errors, M network failures`

## Phase 5: The Verdict
1.  **Run Unit (Incremental)**: Run `pactkit test-map <changed-files>` from the terminal to map source files to test files. Run only mapped tests. Fallback to full suite if no mapping.
2.  **Run E2E**: If `e2e.type` is not `none`, execute the E2E test file created in Phase 4.
3.  **Report**: Output structured verdict:

```
## QA Verdict: STORY-{ID}

**Result**: PASS / FAIL

### Scan Summary
| Category | P0 | P1 | P2 | P3 |
|----------|----|----|----|----|
| Security     |    |    |    |    |
| Quality      |    |    |    |    |
| Test Quality |    |    |    |    |

### Issues (if any)
- **[P0] [file:line]** Description
- **[P1] [file:line]** Description

### Spec Alignment
- [x] S1: ... (Covered)
- [ ] S2: ... (Gap)

### Security Checklist
| ID | Check | Result |
|----|-------|--------|
| SEC-1 | Secrets | PASS/FAIL/N/A |
| SEC-2 | Input | PASS/FAIL/N/A |
| SEC-3 | SQL | PASS/FAIL/N/A |
| SEC-4 | XSS | PASS/FAIL/N/A |
| SEC-5 | Auth | PASS/FAIL/N/A |
| SEC-6 | Rate | PASS/FAIL/N/A |
| SEC-7 | Error | PASS/FAIL/N/A |
| SEC-8 | Deps | PASS/FAIL/N/A |

### Test Results
- Unit: X passed, Y failed
- E2E: X passed, Y failed
```


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

### Credential Safety

NEVER print passwords, keys, or tokens to stdout.
NEVER commit secrets to version control.
