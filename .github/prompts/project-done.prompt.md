---
mode: agent
description: "Code cleanup, Board update, Git commit"
---

# Command: Done (v1.3.0 Smart Gatekeeper)
- **Usage**: `/project-done`
- **Agent**: Repo Maintainer

## 🧠 Phase 0: The Thinking Process
1.  **Audit**: Are tests passing? Is the Board updated?
2.  **Semantics**: Determine correct Conventional Commit scope.

## 🎬 Phase 1: Context Loading
1.  **Read Spec**: Read `docs/specs/{ID}.md`.
2.  **Read Board**: Read `docs/product/sprint_board.md`.

## 🎬 Phase 2: Housekeeping (Deep Clean)
1.  Run language-specific cleanup (e.g., `find . -name '__pycache__' -exec rm -rf {} +` for Python) to remove language-specific temp artifacts.
2.  Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py` (file, `--mode class`, `--mode call` if source changed) to update graphs only if source files changed (file, `--mode class`, `--mode call`). If skipped, log: "Graph up-to-date — no source changes".
3.  **HLD Consistency Check**: Check project health: verify .github/pactkit.yaml exists, sprint_board.md is valid, and code graphs are up-to-date and check HLD drift. If drift > 3, WARN user: "system_design.mmd is {N} modules behind — consider updating it."

## 🎬 Phase 2.5: Regression Gate (CRITICAL)
> **CRITICAL**: Do NOT skip this step. This is the safety net before commit.

### Step 0: Source Change Pre-Check
- Run `git diff --name-only HEAD~1` (or vs. branch base) to list all changed files.
- Filter for source and test files only (exclude docs, configs, graphs).
- If **no source/test files changed** since the last commit (e.g., only docs, board, graphs, or config changed): log `"Regression: SKIP — no source/test changes since Act"` and proceed directly to Step 2.7 (Smart Lint Gate). This avoids re-running 3000+ tests when Act already verified the code.

### Step 1: Impact Analysis
- Check if `docs/architecture/graphs/code_graph.mmd` exists.

### Step 1.3: Classification Shortcut
Run the project test suite (e.g., `pytest tests/ -q` for Python, `npm test` for Node) (or run tests for changed files (e.g., `pytest <files>`)) to classify changes (doc-only → SKIP):
- **SKIP** → proceed to Step 2.7 (no regression needed).
- **FULL** → skip impact analysis, proceed directly to Step 3 (full regression).
- **IMPACT** → continue to Step 1.6.

### Step 1.6: Release Gate — Version Bump Override
If run the project test suite returns FULL (version/dependency change detected), proceed directly to Step 3.
Otherwise continue to Step 1.7.

### Step 1.7: Impact-Based Analysis (STORY-053)
> **PURPOSE**: Use `call_graph.mmd` to target only tests affected by changed functions.

1. **Preconditions**: All of the following must be true to attempt impact analysis:
   - `docs/architecture/graphs/call_graph.mmd` exists.
   - `regression.strategy` is `impact` (read from `.github/pactkit.yaml`; default: `impact`).
2. **Identify changed functions**: Use `git diff HEAD~1 --unified=0` on changed source files to extract modified function names (look for `def ` in the diff).
3. **Run impact command** for each changed function:
   ```bash
   python3 .github/skills/pactkit-visualize/scripts/visualize.py impact --entry <func_name>
   ```
   Collect all returned test file paths (space-separated).
4. **Deduplicate** the collected test paths.
5. **Decision** (threshold from `regression.max_impact_tests`, default 50):
   - If total impacted files < threshold: run only impacted test files.
     - Log: `"Regression: IMPACT-BASED — {N} test files based on call graph analysis"`
     - Run: `pytest {space-separated test paths}`
     - Skip Step 2. Proceed to Step 2.3 for logging.
   - If impacted files ≥ threshold or impact command fails: fall through to Step 2 (Decision Tree).
   - If no changed functions found in diff: fall through to Step 2.

### Step 2: Decision Tree (Safe-by-Default)
> **DEFAULT**: Run **full regression**. Run incremental only if: `code_graph.mmd` recently updated, ≤ 3 source files changed, test mappings exist via `LANG_PROFILES[stack].test_map_pattern`, no high-fan-in files (3+ importers), no test infra changes. For fast/small suites (< 500 tests), skip the decision tree and run full.
> **Fallback**: If `code_graph.mmd` does not exist, always run full regression.

### Step 2.3: Decision Logging (MUST)
After evaluating the decision tree, log the decision with format: `"Regression: {TYPE} — {reason}"` (e.g., SKIP, STORY-ONLY, FULL, IMPACT-BASED, INCREMENTAL).

### Step 2.5: Coverage Verification (Conditional)
Run `pactkit coverage-gate <changed-files>` from the terminal to verify coverage on changed source files.
- The command auto-detects modules, runs pytest --cov, and applies 3-tier thresholds:
  - **≥ 80%**: PASS — proceed normally
  - **50-79%**: WARN — output: "Changed file `{file}` has {N}% coverage. Consider running `/project-check` to generate missing tests."
  - **< 50%**: BLOCK — require user confirmation: "Changed file `{file}` has only {N}% coverage. Proceed anyway?"
- If `pactkit coverage-gate` (run from terminal) is unavailable, fall back to manual: construct `pytest --cov=<changed_modules> --cov-report=term-missing tests/` and parse output.
- Include coverage data in the output so the user can evaluate test quality.

### Step 2.7: Smart Lint Gate (STORY-030)
> **Purpose**: Stack-aware lint check with configurable behavior.

1. Run the project linter (e.g., `ruff check src/ tests/` for Python, `npm run lint` for Node) to execute the stack-aware lint gate. This auto-detects the project stack, reads `lint_command` from `LANG_PROFILES`, and respects `auto_fix` and `lint_blocking` from `.github/pactkit.yaml`.
   - If `auto_fix: true` in config: run the project linter runs fix pass first, then check pass.
   - If `lint_blocking: true` and lint fails: **STOP** the commit. Report errors and do NOT proceed.
   - If `lint_blocking: false` (default): Lint failures are reported as **warnings**. Print findings but proceed with commit.
2. If run the project linter is unavailable, fall back to manual lint: detect stack, read `lint_command` from LANG_PROFILES, run the command directly.
3. **Skip**: If no lint command found for the stack, skip silently: "No lint command configured — skipping lint gate."

### Step 3: Gate
- If any test fails, **STOP immediately**. Do NOT proceed to commit.
- **Do NOT attempt to fix** pre-existing test failures or modify code you do not understand.
- The agent MUST NOT assume it understands pre-existing test intent — the project may have adopted PDCA mid-way and there is no Spec for older features.
- Report the failure to the user with: which test failed, what it appears to test, and which change likely caused it.
- Only continue if ALL tests and lint checks are GREEN.

## 🎬 Phase 3: Hygiene Check & Fix
1.  **Verify**: Are tasks for this Story marked `[x]`?
2.  **Auto-Fix**:
    - If tests are GREEN but tasks are `[ ]`, **Ask the user**: "Tests passed but tasks are unchecked. Mark as done?"
    - If user agrees, update `sprint_board.md` immediately.
3.  **Lessons Auto-append (MUST)**: Run `pactkit lesson-append --story {STORY_ID} --text "lesson text" [--context "file.py:func"]` from the terminal.
    - The command checks specificity (references concrete file/function?) and dedup (different from last 5 entries?).
    - If both pass: appends row using format `| {date} | {lesson} | {context} |` where date=YYYY-MM-DD, context={STORY_ID}
    - If either fails: skip with log from command output.
    - If `pactkit lesson-append` (run from terminal) is unavailable, fall back to manual append with the same checks.
4.  **Invariants Refresh (MUST)**: Run `pactkit invariants-refresh --test-count {N}` from the terminal where {N} is the actual count from the most recent test run.
    - The command updates `docs/architecture/governance/rules.md` invariant "All {N}+ tests must pass".
    - If `pactkit invariants-refresh` (run from terminal) is unavailable, fall back to manual: read rules.md, find the pattern, replace the number.
5.  **Document Validators (Non-blocking)**: Run document structure checks as warnings:
    - `pactkit lint-context` (run from terminal) — validates `docs/product/context.md` structure
    - `pactkit lint-lessons` (run from terminal) — validates `docs/architecture/governance/lessons.md` structure
    - These are non-blocking: report warnings but do not stop the Done flow.
6.  **Spec Status Update (MUST)**: Run `pactkit spec-status docs/specs/{STORY_ID}.md Done` from the terminal to update `| Status | Draft |` to `| Status | Done |` in the spec file. If `pactkit spec-status` (run from terminal) is unavailable, manually edit the spec file.
7.  **Memory MCP (Conditional)**: IF Memory MCP is available, use add_observations to record lessons learned (patterns, pitfalls, key files) on the `{STORY_ID}` entity.

## 🎬 Phase 3.5: Archive (Optional)
1.  **Check**: Are all tasks for the current Story marked `[x]`?
2.  **Action**: If yes, run `python3 .github/skills/pactkit-board/scripts/board.py archive`.
3.  **Result**: Completed stories are moved to `docs/product/archive/archive_YYYYMM.md`.

## 🎬 Phase 3.5.5: Issue Tracker Verification (BUG/HOTFIX Only)
> **Purpose**: Verify GitHub Issue exists for BUG/HOTFIX items; STORY items are NOT synced to protect IP.
1.  Run `pactkit issue-sync {ITEM_ID}` from the terminal to handle the full issue lifecycle:
    - STORY items: skipped automatically (IP protection).
    - BUG/HOTFIX items: searches for existing issue, backfill-creates if missing, returns issue URL.
2.  If `pactkit issue-sync` (run from terminal) returns a URL, update the Sprint Board entry to include `[#{number}]({url})`.
3.  If `pactkit issue-sync` (run from terminal) is unavailable, fall back to manual `gh` CLI commands:
    a. **CLI Check**: Run `gh --version`. If unavailable, print warning and proceed to Phase 3.6.
    b. **Search**: Run `gh issue list --search "{ITEM_ID}" --state all --json number,title,url`.
    c. **If not found**: Create issue via `gh issue create`.
    d. **If any gh command fails**: Print warning, continue to Phase 3.6.

## 🎬 Phase 3.6: Issue Tracker Closure (BUG/HOTFIX Only)
> **Purpose**: Close linked external issues when BUG/HOTFIX is done. STORY items are skipped.
1.  **Check Item Type**: If current item is `STORY-*`, skip this phase silently.
2.  **Check Config**: Read `.github/pactkit.yaml` for `issue_tracker.provider`.
3.  **If `provider: github`**:
    - Parse the Sprint Board entry for a linked issue URL (e.g., `[#123](https://github.com/...)`)
    - If found: run `gh issue close <number> --comment "Completed in $(git rev-parse --short HEAD)"`
    - If `gh` CLI unavailable or closure fails: print warning, continue
4.  **If `provider: none` or section missing**: Skip silently.

## 🎬 Phase 4: Git Commit
0.  **Enterprise Check**: If `enterprise.no_git: true` in `.github/pactkit.yaml`, skip ALL git operations in this phase. Print: "ℹ️ Git operations disabled (enterprise.no_git)". Skip to the Session Context Update phase.
0.5.  **Deployment Verification (self-dev only)**: Only when developing PactKit itself (`pyproject.toml` name == "pactkit"):
    - Re-run `pactkit init --format copilot` from the terminal to update deployed files to redeploy all prompts, agents, commands, skills, and rules.
    - Smoke-check: for each AC that references prompt/deployed file content, `grep` 1-2 key assertions on deployed files (e.g., `.github/commands/*.md`).
    - Report: `Deploy verification: PASS ({N} assertions checked)` or `FAIL (details)`.
    - If FAIL, fix the deployment issue before committing.
    - **If NOT self-dev**: Skip this step silently.
1.  **Format**: `feat(scope): <title from spec>`
2.  **Execute**: Run the git commit command.
3.  **Post-Commit Prompts**:
    - **Version bump?** If `pyproject.toml` version was changed in this Story: "ℹ️ Version bump detected. Run `/project-release` to create snapshot and git tag."
    - **Feature branch?** If current branch is not `main`/`master`: "ℹ️ Working on a feature branch. Run `/project-pr` to push and create a pull request."
    - **CI Status Check (Conditional)**: If `ci.provider` is `github` in `.github/pactkit.yaml` and `gh` CLI is available:
      1. After push, run `gh run list --limit 1 --json status,name,databaseId` to check the latest workflow run.
      2. Report: `CI: [pass/fail/pending] — {workflow_name} #{run_id}`
      3. If CI fails, print a warning but do NOT block the Done flow.
      4. If `gh` CLI is unavailable or command fails, skip silently.

## 🎬 Phase 4.5: Session Context Update
1.  Generate `docs/product/context.md` manually (Sprint Status, Current Stories, Recent Completions, Active Branches, Key Decisions, Next Recommended Action) to generate `docs/product/context.md` (sections: - `## Sprint Status`
- `## Current Stories`
- `## Recent Completions`
- `## Active Branches`
- `## Key Decisions`
- `## Next Recommended Action`
- `## Agent Continuation`). Set "Last updated by" to `/project-done`. This also clears the Agent Continuation section to `No active work session.` since no `--continuation` flag is passed.
2.  **Commit Context**: `git add docs/product/context.md && git commit --amend --no-edit` to include context.md in the commit.


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

# Workflow Conventions

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
- Main branch: `main` / `master` (no direct push)
- Development branch: `develop`

## PR Conventions
- Title: `feat(scope): short description` (consistent with commit)
- Body: Summary + Test Plan
- Must pass CI and Code Review before merging

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
