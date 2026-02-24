from pactkit.prompts.workflows import (
    DESIGN_PROMPT,
    HOTFIX_PROMPT,
    SPRINT_PROMPT,
)

COMMANDS_CONTENT = {
    "project-plan.md": """---
description: "Analyze requirements, create Spec and Story"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Command: Plan (v19.5 Integrated Trace)
- **Usage**: `/project-plan "$ARGUMENTS"`
- **Agent**: System Architect

## 🧠 Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block.
1.  **Analyze Intent**: New feature (Expansion) or Bugfix/Refactor (Modification)?
2.  **Strategy**:
    - If **New Feature**: Focus on `system_design.mmd` (Architecture).
    - If **Modification**: Focus on pactkit-trace skill (Logic Flow).

## 🛡️ Phase 0.5: Init Guard (Auto-detect)
> **INSTRUCTION**: Check if the project has been initialized before proceeding.
1.  **Check Markers**: Verify the existence of ALL three:
    - `.claude/pactkit.yaml` (project-level config)
    - `docs/product/sprint_board.md` (sprint board)
    - `docs/architecture/graphs/` (architecture graph directory)
2.  **If ANY marker is missing**:
    - Print: "⚠️ Project not initialized. Running `/project-init` first..."
    - Execute the full `/project-init` flow to scaffold the missing structure.
    - After `/project-init` completes, resume this Plan command from Phase 1.
3.  **If ALL markers exist**: Skip silently to Phase 1.

## 🎬 Phase 1: Archaeology (The "Know Before You Change" Step)
1.  **Visual Scan**: Run `visualize` to see the module dependency graph.
    - **Mode Selection**: Use `--mode class` for structure analysis, `--mode call` for logic modification, default for overview.
2.  **Logic Trace (CRITICAL)** — use pactkit-trace skill:
    - If modifying existing logic, trace the current implementation:
      Use `Grep` to locate entry points, then `visualize --mode call --entry <func>` to map call chains.
    - *Goal*: Identify the exact function/class responsible for the logic.

## 🎬 Phase 2: Design & Impact
1.  **Diff**: Compare User Request vs Current Reality (from Phase 1).
2.  **Update HLD**: Modify `docs/architecture/graphs/system_design.mmd`.
    - *Rule*: Keep the `code_graph.mmd` as is (it updates automatically).

## 🎬 Phase 3: Deliverables
1.  **Spec**: Create `docs/specs/{ID}.md` detailing the *Change*.
    - *Requirement*: Include a "Target Call Chain" section in the Spec based on your Trace findings.
    - **MUST**: Fill in the `## Requirements` section using RFC 2119 keywords (MUST/SHOULD/MAY).
    - **MUST**: Fill in the `## Acceptance Criteria` section with Given/When/Then scenarios.
    - Each Scenario SHOULD map to a verifiable test case in `docs/test_cases/`.
    - **MUST**: Fill in the `Release` metadata field with the current version from `pactkit.yaml` (or leave `TBD` if unknown).
2.  **Board**: Add Story using `add_story`.
3.  **Memory MCP (Conditional)**: IF `mcp__memory__create_entities` tool is available, store the design context:
    - Use `mcp__memory__create_entities` with: `name: "{STORY_ID}"`, `entityType: "story"`, `observations: [key architectural decisions, target files, design rationale]`
    - IF this story depends on other stories, use `mcp__memory__create_relations` to record dependencies (e.g., `from: "{STORY_ID}", to: "STORY-XXX", relationType: "depends_on"`)
4.  **Session Context Update**: Update `docs/product/context.md` to reflect the new Story:
    - Read `docs/product/sprint_board.md` (now containing the new Story)
    - Read `docs/architecture/governance/lessons.md` (last 5 entries)
    - Run `git branch --list 'feature/*' 'fix/*'`
    - Write `docs/product/context.md` using the standard format (see `/project-done` Phase 4.5 for format)
    - Set "Last updated by" to `/project-plan`
5.  **Handover**: "Trace complete. Spec created. Ready for Act."
""",

    # [FIX] Added Board Update Step to Phase 4
    "project-act.md": """---
description: "Implement code per Spec, strict TDD"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Command: Act (v22.0 Stack-Aware)
- **Usage**: `/project-act $ARGUMENTS`
- **Agent**: Senior Developer

## 🧠 Phase 0: The Thinking Process (Mandatory)
1.  **Read Law**: Read the Spec (`docs/specs/`) carefully.
2.  **Locate Target**: Which file/function needs surgery?
3.  **Detect Stack & Select References**: Identify the project type from source files:
    - `.py` files → Python stack → Consult `DEV_REF_BACKEND` + `TEST_REF_PYTHON`
    - `.ts`/`.tsx`/`.vue`/`.svelte` files → Frontend stack → Consult `DEV_REF_FRONTEND` + `TEST_REF_NODE`
    - `.go` files → Go stack → Consult `DEV_REF_BACKEND` + `TEST_REF_GO`
    - `.java` files → Java stack → Consult `DEV_REF_BACKEND` + `TEST_REF_JAVA`
    - Mixed (frontend + backend) → Consult both `DEV_REF_FRONTEND` and `DEV_REF_BACKEND`
    - Use the Stack Reference guidelines throughout implementation and testing phases.
4.  **Memory MCP (Conditional)**: IF `mcp__memory__search_nodes` tool is available, load prior context:
    - Use `mcp__memory__search_nodes` with the STORY_ID to retrieve any stored architectural decisions or design rationale from the Plan phase
    - Use `mcp__memory__search_nodes` with relevant module/feature keywords to find related past decisions from other stories

## 🎬 Phase 1: Precision Targeting
1.  **Visual Scan**: Run `visualize --focus <module>` to see neighbors.
2.  **Call Chain**: Run `visualize --mode call --entry <function>` to trace call dependencies.
3.  **Trace Verification** — use pactkit-trace skill:
    - Before touching any code, confirm the call site.
    - Use `Grep` to find all callers, then `visualize --mode call --entry <func>` to trace dependencies.
    - *Goal*: Ensure you don't break existing callers.

## 🎬 Phase 2: Test Scaffolding (TDD)
1.  **Constraint**: DO NOT write source code yet.
2.  **Action**: Create a reproduction test case in `tests/unit/`.
    - Use the knowledge from Phase 1 to mock/stub dependencies correctly.

## 🎬 Phase 3: Implementation
1.  **Write Code**: Implement logic in the appropriate source directory.
    - **Context7 (Conditional)**: IF you are implementing with an unfamiliar library API, use `mcp__context7__resolve-library-id` followed by `mcp__context7__get-library-docs` to fetch up-to-date documentation before writing code. This ensures correct API usage and avoids deprecated patterns.
2.  **TDD Loop (Safe Iteration)**: Run ONLY the tests created in Phase 2 (the new test file for this Story). Loop until GREEN.
    - This loop is safe because you wrote these tests and understand their intent.
    - Do NOT include pre-existing tests in this loop.
3.  **Regression Check (Read-Only Gate)**: After the TDD loop is GREEN, run a broader regression check.
    - **Identify changed modules**: `git diff --name-only HEAD` to list modified source files.
    - **Map to related tests**: For each changed file, find its corresponding test file using the `test_map_pattern` in `LANG_PROFILES`.
    - **Run regression**: Execute the mapped test files plus the full test suite if unsure about change scope.
    - **Fallback**: If no test mapping can be determined or you are unsure about dependency impact, fall back to the full test suite.
    - **CRITICAL — Pre-existing test failure protocol**:
      - If a pre-existing test (one you did NOT create in Phase 2) fails, **DO NOT modify** the failing test or the code it tests.
      - **DO NOT loop** — this is a one-shot check, not an iterative loop.
      - **STOP** and report to the user: which test failed, what it appears to test, and which of your changes likely caused the failure.
      - Suggest options: (a) you revert your change that caused the regression, or (b) the user reviews and provides guidance.
      - You MUST NOT assume you understand the design intent behind pre-existing tests — the project may have adopted PDCA mid-way and there is no Spec for older features.
4.  **Lint Check (Conditional)**: IF a CI config exists (`.github/workflows/*.yml` or similar) or `lint_command` is set in `LANG_PROFILES`:
    - Run the `lint_command` for the detected stack (e.g., `ruff check src/ tests/` for Python).
    - If lint fails, fix the lint errors in your own new/modified files only, then re-run.
    - Do NOT modify pre-existing files to fix lint unless the lint error is in a file you changed in this Story.

## 🎬 Phase 4: Sync & Document
1.  **Hygiene**: Delete temp files.
2.  **Update Reality**:
    - Run `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize`
    - Run `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize --mode class`
3.  **Update Board (CRITICAL)**:
    - Mark the tasks in `docs/product/sprint_board.md` as `[x]`.
    - Use `update_task` or manual edit.
""",

    "project-check.md": """---
description: "QA verification: security scan, code quality scan, Spec alignment"
allowed-tools: [Read, Bash, Grep, Glob]
---

# Command: Check (v22.0 Deep QA)
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

## Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block before using any tools.
1.  **Analyze Context**: Read the active `docs/specs/{ID}.md`.
2.  **Determine Layer**:
    * *Logic Only?* -> Strategy: **API Level**.
    * *UI/DOM/Interaction?* -> Strategy: **Browser Level**.
3.  **Detect Stack**: If changed files include `.tsx`/`.vue`/`.svelte`, also consult `DEV_REF_FRONTEND` for client-side security and rendering performance checks.
4.  **Gap Analysis**: Do we have a structured Test Case? If not, plan to create one.

## Phase 1: Security Scan (OWASP+)
Apply a comprehensive security checklist to all code related to the Story:

- **Input/Output Safety**: XSS, Injection (SQL/NoSQL/command), SSRF, path traversal
- **AuthN/AuthZ**: Missing auth guards, tenant checks, IDOR, session fixation
- **Race Condition**: TOCTOU (check-then-act), concurrent read-modify-write, missing locks
- **Secrets & PII**: API keys in code/logs, excessive PII logging, hardcoded credentials
- **Runtime Risks**: Unbounded loops, missing timeouts, resource exhaustion, ReDoS
- **Cryptography**: Weak algorithms (MD5/SHA1), hardcoded IVs, encryption without authentication
- **Supply Chain**: Unpinned dependencies, dependency confusion, known CVEs

For each finding, assign a severity (P0-P3) and note both exploitability and impact.
If a P0 issue is found, report it immediately — do not wait for the full scan.

## Phase 2: Code Quality Scan
Apply a code quality checklist to all code related to the Story:

- **Error Handling**: Swallowed exceptions, overly broad catch, missing error handling, async errors
- **Performance**: N+1 queries, CPU hotspots in hot paths, missing cache, unbounded memory growth
- **Boundary Conditions**: Null/undefined handling, empty collections, off-by-one, division by zero, numeric overflow
- **Logic Correctness**: Does the implementation match Spec intent? Are edge cases handled?

For each finding, assign a severity (P0-P3). Flag issues that may cause silent failures.

## Phase 3: Spec Verification & Test Case Definition (The Law)
1.  **Verify Spec Structure**: Read `docs/specs/{STORY_ID}.md`.
    * *Check*: Does the Spec contain `## Acceptance Criteria` with Given/When/Then Scenarios?
    * *If missing*: WARN the user — "Spec lacks structured Acceptance Criteria. Run `/project-plan` to fix."
2.  **Extract Scenarios**: List all Scenarios from the Spec's `## Acceptance Criteria` section.
3.  **Check**: Does `docs/test_cases/{STORY_ID}_case.md` exist?
4.  **Action**: If missing, generate it based *strictly* on the Spec's Acceptance Criteria.
    * *Format*: Gherkin (Given/When/Then).
    * *Constraint*: Do not write Python code yet.
5.  **Coverage Report**: Compare Scenarios in Spec vs Test Cases. Report any uncovered Scenario.

## Phase 4: Layered Execution
Choose the strategy identified in Phase 0:

### Strategy A: API Level (Fast & Stable)
* **Context**: Backend logic, calculations.
* **Action**: Create/Run `tests/e2e/api/test_{STORY_ID}.py` using `pytest` + `requests`.

### Strategy B: Browser Level (Visual & Real)
* **Context**: UI, DOM, User Flows.
* **Action**:
    1.  **Check Tool**: Is `playwright` installed?
    2.  Create/Run `tests/e2e/browser/test_{STORY_ID}_browser.py`.
    * *Note*: Use `--headless` unless debugging.
* **Playwright MCP (Conditional)**: IF `mcp__playwright__browser_snapshot` tool is available, prefer using Playwright MCP for browser-level verification:
    - Use `browser_navigate` to load the target page
    - Use `browser_snapshot` to capture the accessibility tree (preferred over screenshots for assertions)
    - Use `browser_click` and `browser_fill_form` for interaction testing
    - Use `browser_take_screenshot` for visual evidence
* **Chrome DevTools MCP (Conditional)**: IF `mcp__chrome-devtools__take_snapshot` tool is available, use Chrome DevTools MCP for runtime diagnostics:
    - Use `performance_start_trace` (with `reload: true, autoStop: true`) to capture Core Web Vitals and performance insights
    - Use `list_console_messages` (filter by `types: ["error", "warn"]`) to detect runtime errors
    - Use `list_network_requests` to verify API calls and detect failed requests

## Phase 5: The Verdict
1.  **Run Suite**: Execute the specific test file created above (Story E2E test).
2.  **Run Unit (Incremental)**: Run only unit tests related to changed modules, not the full suite.
    - **Identify changed modules**: `git diff --name-only HEAD` to list modified source files.
    - **Map to related tests**: Use `test_map_pattern` in `LANG_PROFILES` to find corresponding test files.
    - **Run incremental**: Execute only the mapped test files.
    - **Fallback**: If no test mapping can be determined, fall back to full `pytest tests/unit/`.
3.  **Report**: Output structured verdict:

```
## QA Verdict: STORY-{ID}

**Result**: PASS / FAIL

### Scan Summary
| Category | P0 | P1 | P2 | P3 |
|----------|----|----|----|----|
| Security |    |    |    |    |
| Quality  |    |    |    |    |

### Issues (if any)
- **[P0] [file:line]** Description
- **[P1] [file:line]** Description

### Spec Alignment
- [x] S1: ... (Covered)
- [ ] S2: ... (Gap)

### Test Results
- Unit: X passed, Y failed
- E2E: X passed, Y failed
```
""",

    # [FIX] Upgraded to v19.5 and added Auto-Fix Logic
    "project-done.md": """---
description: "Code cleanup, Board update, Git commit"
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Command: Done (v19.8 Smart Gatekeeper)
- **Usage**: `/project-done`
- **Agent**: Repo Maintainer

## 🧠 Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block.
1.  **Audit**: Are tests passing? Is the Board updated?
2.  **Semantics**: Determine correct Conventional Commit scope.

## 🎬 Phase 1: Context Loading
1.  **Read Spec**: Read `docs/specs/{ID}.md`.
2.  **Read Board**: Read `docs/product/sprint_board.md`.

## 🎬 Phase 2: Housekeeping (Deep Clean)
1.  **Action**: Remove language-specific temp artifacts (see `LANG_PROFILES` cleanup list; default for Python):
    - `rm -rf __pycache__ .pytest_cache`
    - `rm -f .DS_Store *.tmp *.log`
2.  **Update Reality**:
    - Run `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize`
    - Run `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize --mode class`
3.  **HLD Consistency Check**: Read `docs/architecture/graphs/system_design.mmd` and verify component counts match reality:
    - Compare any numeric labels in subgraphs (e.g., "8 commands", "9 skills") against the actual component counts from `config.py` VALID_* registries or the project source.
    - If a mismatch is found, **warn** the user: "⚠️ system_design.mmd is stale: says {old} but actual is {new}. Update the HLD."
    - If the user agrees, update the mismatch in `system_design.mmd`.
    - If `system_design.mmd` does not exist, skip silently.

## 🎬 Phase 2.5: Regression Gate (MANDATORY)
> **CRITICAL**: Do NOT skip this step. This is the safety net before commit.

### Step 1: Impact Analysis
- Run `git diff --name-only HEAD~1` (or vs. branch base) to list all changed files.
- Check if `docs/architecture/graphs/code_graph.mmd` exists.

### Step 2: Decision Tree (Safe-by-Default)
> **DEFAULT**: Run **full regression** (`pytest tests/`). This is the safe default.

Run **incremental tests** only if ALL of the following conditions are true:
- `code_graph.mmd` exists AND was updated in the current session (not stale)
- Changed source files ≤ 3 (small, isolated change set)
- ALL changed source files have direct test mappings via `test_map_pattern` in `LANG_PROFILES`
- NO changed file is imported by 3+ other modules in `code_graph.mmd`
- NO test infrastructure files were changed (`conftest.py`, `pytest.ini`, `pyproject.toml [tool.pytest]`)
- NO version change in `pactkit.yaml` (version bump implies broader impact)

**Fallback**: If `code_graph.mmd` does not exist (e.g., non-PDCA project or not yet generated), always run full regression.

### Step 2.5: Coverage Verification (Conditional)
IF `pytest-cov` is available, run tests with coverage on changed source files:
- `pytest --cov=<changed_modules> --cov-report=term-missing tests/`
- **≥ 80%** line coverage on changed files: PASS — proceed normally
- **50-79%**: WARN — output: "Changed file `{file}` has {N}% coverage. Consider running `/project-check` to generate missing tests."
- **< 50%**: BLOCK — require user confirmation: "Changed file `{file}` has only {N}% coverage. Proceed anyway?"
- Include coverage data in the output so the user can evaluate test quality.

### Step 2.7: CI Lint Gate (Conditional)
> **Purpose**: Catch lint errors that CI will reject, before committing.

1. **Detect CI config**: Check if `.github/workflows/*.yml`, `.gitlab-ci.yml`, or a lint-related config (e.g., `[tool.ruff]` in `pyproject.toml`, `.eslintrc*`, `.golangci.yml`) exists.
2. **If CI config exists**: Run the `lint_command` from `LANG_PROFILES` for the detected stack.
   - Example (Python): `ruff check src/ tests/`
   - Example (Node): `npx eslint .`
3. **Gate**: If lint fails, **STOP immediately**. Report the lint errors and do NOT proceed to commit.
4. **Skip**: If no CI config and no lint tool detected, skip silently: "No CI lint config detected — skipping lint gate."

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
3.  **Lessons Auto-append (MANDATORY)**: Append a new row to `docs/architecture/governance/lessons.md`:
    - Format: `| {YYYY-MM-DD} | {one-line summary of what was learned} | {STORY_ID} |`
    - Date: today's date
    - Summary: one sentence describing the key insight, pattern, or pitfall from this Story
    - This is NOT conditional on Memory MCP — always append to lessons.md
4.  **Invariants Refresh (MANDATORY)**: Update the Invariants section in `docs/architecture/governance/rules.md`:
    - Read the current `rules.md` file.
    - Update the test count to match the actual number from the most recent test run (e.g., "All {N}+ tests must pass").
    - Preserve the Architecture Decisions (ADR) table — only update the Invariants section.
    - If `rules.md` does not exist, skip silently.
5.  **Memory MCP (Conditional)**: IF `mcp__memory__add_observations` tool is available, record lessons learned:
    - Use `mcp__memory__add_observations` on the `{STORY_ID}` entity with: implementation patterns used, pitfalls encountered, key files modified, and any non-obvious decisions made during implementation
    - This builds a cumulative project knowledge base that persists across sessions

## 🎬 Phase 3.5: Archive (Optional)
1.  **Check**: Are all tasks for the current Story marked `[x]`?
2.  **Action**: If yes, run `python3 ~/.claude/skills/pactkit-board/scripts/board.py archive`.
3.  **Result**: Completed stories are moved to `docs/product/archive/archive_YYYYMM.md`.

## 🎬 Phase 3.7: Deploy & Verify (If Applicable)
> **Purpose**: Ensure the committed code works correctly in deployed form.
1.  **Detect Deployer**: Check if the project has a deployer (`pactkit init` or configured in `pactkit.yaml`).
2.  **Deploy**: If a deployer exists, run it (e.g., `python3 pactkit init`).
3.  **Smoke Test**: Spot-check deployed artifacts to verify they contain expected content.
4.  **Skip**: If no deployer is detected, skip this phase and note "No deployer found — skipping deploy verification."
5.  **Gate**: If deployment or verification fails, **STOP**. Do NOT proceed to commit.

## 🎬 Phase 3.8: Release (Conditional) — use pactkit-release skill
> If this Story involves a version bump, invoke the release workflow:
1.  **Detect**: Check if `pyproject.toml` version was changed in this Story.
2.  **If yes**: Run `update_version`, `snapshot`, and `archive` via pactkit-board skill. Tag with `git tag`.
3.  **Verify Snapshots**: After the snapshot step, check that `docs/architecture/snapshots/{version}_*.mmd` files exist. If missing, report: "❌ Snapshot verification failed: expected files in snapshots/ for {version}."
4.  **If no version change**: Skip to Phase 4.

## 🎬 Phase 4: Git Commit
1.  **Format**: `feat(scope): <title from spec>`
2.  **Execute**: Run the git commit command.

## 🎬 Phase 4.5: Session Context Update
> **Purpose**: Generate `docs/product/context.md` so the next session auto-loads project state.
1.  **Read Board**: Read `docs/product/sprint_board.md` and extract:
    - Stories in 🔄 In Progress (with IDs and titles)
    - Stories in 📋 Backlog (count)
    - Stories in ✅ Done (most recent 3, with IDs and titles)
2.  **Read Lessons**: Read `docs/architecture/governance/lessons.md` and extract the last 5 entries.
3.  **Active Branches**: Run `git branch --list 'feature/*' 'fix/*'` to list active branches.
4.  **Write Context**: Write `docs/product/context.md` with this format:
    ```markdown
    # Project Context (Auto-generated)
    > Last updated: {ISO timestamp} by /project-done

    ## Sprint Status
    {In Progress stories with IDs | Backlog count | Done count}

    ## Recent Completions
    {Last 3 completed stories, one line each}

    ## Active Branches
    {git branch output, or "None" if no feature/fix branches}

    ## Key Decisions
    {Last 5 lessons from lessons.md}

    ## Next Recommended Action
    {If In Progress stories exist: `/project-act STORY-XXX` | If only Backlog: `/project-plan` | If board empty: `/project-design`}
    ```
5.  **Commit Context**: `git add docs/product/context.md && git commit --amend --no-edit` to include context.md in the commit.
""",

    "project-init.md": """---
description: "Initialize project scaffolding and governance structure"
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Command: Init (v18.6 Rich)
- **Usage**: `/project-init`
- **Agent**: System Architect

## 🧠 Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block before using any tools.
1.  **Environment Check**: Is this a fresh folder or legacy project?
2.  **Compliance**: Does the user need `pactkit.yaml`?
3.  **Strategy**: If legacy, I must prioritize `visualize` to capture Reality.

## 🎬 Phase 1: Environment & Config
1.  **Action**: Check/Create `./.claude/pactkit.yaml` in **Current Directory**.
    - *Content*: `stack: <detected>`, `version: 0.0.1`, `root: .`
    - **Do NOT add any fields not listed above** (e.g., no `language` field).
2.  **Stack Detection** (for `stack` field in `pactkit.yaml`):
    - Valid values: `python`, `node`, `go`, `java` (use the language name only, NOT the build system)
    - If `pyproject.toml` or `requirements.txt` or `setup.py` exists → `stack: python`
    - If `package.json` exists → `stack: node`
    - If `go.mod` exists → `stack: go`
    - If `pom.xml` or `build.gradle` exists → `stack: java`
    - If none match → ask the user to specify
    - The detected stack determines which `LANG_PROFILES` entry to use for test runner, cleanup, etc.
3.  **Project CLAUDE.md**: Check/Create `./.claude/CLAUDE.md` if missing (do NOT overwrite if it already exists).
    - *Purpose*: Project-level instructions for Claude Code (separate from global `~/.claude/CLAUDE.md`).
    - *Content template*:
      ```markdown
      # {Project Name} — Project Context

      ## Dev Commands

      ```
      # Run tests
      {test_runner from LANG_PROFILES}

      # Lint
      {lint_command from LANG_PROFILES}
      ```

      @./docs/product/context.md
      ```
    - Use the directory name as the project name.
    - Fill `test_runner` and `lint_command` from `LANG_PROFILES` based on the detected language.
    - The `@./docs/product/context.md` reference enables cross-session context loading.

## 🎬 Phase 2: Architecture Governance
1.  **Scaffold**: Run `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py init_arch`.
    - *Result*: Folders created. Placeholders (`system_design.mmd`) created.
2.  **Ensure**: `mkdir -p docs/product docs/specs docs/test_cases tests/e2e/api tests/e2e/browser tests/unit`.

## 🎬 Phase 3: Discovery (Reverse Engineering)
1.  **Scan Reality**: Run `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize`.
    - *Goal*: If this is an existing project, overwrite the empty `code_graph.mmd` with the REAL class structure immediately.
2.  **Class Scan**: Run `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize --mode class`.
3.  **Verify**: Read `docs/architecture/graphs/code_graph.mmd` and `class_graph.mmd`.
    - *Check*: Is it still "No code yet"? If files exist in src, this graph MUST contain classes.

## 🎬 Phase 4: Project Skeleton
1.  **Board**: Create `docs/product/sprint_board.md` if missing.

## 🎬 Phase 5: Knowledge Base (The Law)
1.  **Law**: Write `docs/architecture/governance/rules.md`.
2.  **History**: Write `docs/architecture/governance/lessons.md`.

## 🎬 Phase 6: Session Context Bootstrap
1.  **Generate Context**: Write `docs/product/context.md` with initial project state:
    - Read `docs/product/sprint_board.md` (likely empty for new projects)
    - Read `docs/architecture/governance/lessons.md` (last 5 entries)
    - Run `git branch --list 'feature/*' 'fix/*'`
    - Write `docs/product/context.md` using the standard format (see `/project-done` Phase 4.5 for format)
    - Set "Last updated by" to `/project-init`

## 🎬 Phase 7: Handover
1.  **Output**: "✅ PactKit Initialized. Reality Graph captured. Knowledge Base ready."
2.  **Advice**: "⚠️ IMPORTANT: Run `/project-plan 'Reverse engineer'` to align the HLD."
""",

}

# Register additional prompts into COMMANDS_CONTENT
COMMANDS_CONTENT["project-sprint.md"] = SPRINT_PROMPT
COMMANDS_CONTENT["project-hotfix.md"] = HOTFIX_PROMPT
COMMANDS_CONTENT["project-design.md"] = DESIGN_PROMPT
