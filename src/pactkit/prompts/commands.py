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

# Command: Plan (v1.3.0 Integrated Trace)
- **Usage**: `/project-plan "$ARGUMENTS"`
- **Agent**: System Architect

## 🧠 Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block.
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
> **INSTRUCTION**: Check if the project has been initialized before proceeding.
1.  **Check Markers**: Verify the existence of ALL three:
    - `.claude/pactkit.yaml` (project-level config)
    - `docs/product/sprint_board.md` (sprint board)
    - `docs/architecture/graphs/` (architecture graph directory)
2.  **If ANY marker is missing**:
    - Print: "⚠️ Project not initialized. Running `/project-init` first..."
    - Execute the full `/project-init` flow to scaffold the missing structure.
    - After `/project-init` completes, resume this Plan command from Phase 1.
3.  **If ALL markers exist**: Proceed to Step 4.
4.  **Config Completeness Check**: Verify `pactkit.yaml` has all expected sections (hooks, ci, issue_tracker, lint_blocking, auto_fix).
    - If any sections are missing, the config is stale. Run `pactkit update` to backfill missing sections.
    - Report what was added (e.g., "Config refreshed: added hooks, ci sections").
    - If the config is already complete and up to date, skip silently to Phase 1.

## 🧠 Phase 0.7: Clarify Gate (Auto-detect Ambiguity)
> **PURPOSE**: Surface and resolve requirement ambiguity before the Spec is written. Better to clarify now than rewrite a Spec.
1.  **Detect Ambiguity**: Analyze the user's input (`$ARGUMENTS`) against these signals:
    - No quantitative metrics ("高并发" without QPS, "fast" without benchmark)
    - No boundary conditions ("user management" without specifying which operations)
    - No technical constraints (no auth method, no framework specified)
    - Single sentence input (< 15 words) — likely under-specified
    - Vague quantifiers ("some", "many", "a few", "大量", "一些", "简单")
    - No target user specified
2.  **Trigger Logic**:
    - ≥ 2 High signals (no metrics, no boundaries) → **Auto-trigger** Clarify
    - 1 High + ≥ 2 Medium signals → **Auto-trigger** Clarify
    - ≥ 2 Medium signals → **Suggest** Clarify (ask user: "Input seems underspecified. Clarify? yes/skip")
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
1.  **Visual Scan**: Run `visualize` to see the module dependency graph.
    - **Mode Selection**: Use `--mode class` for structure analysis, `--mode call` for logic modification, default for overview.
    - **Large Codebase Heuristic**: If the project has more than 50 source files, use `--focus <module> --depth 2` instead of a full graph to avoid context window pollution.
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
    - **MUST**: Fill in the `Release` metadata field by reading the `version` field from `.claude/pactkit.yaml` (or `pyproject.toml`). Use that EXACT value — do NOT increment or predict a future version. If the file cannot be read, use `TBD`.
    - **OPTIONAL — Implementation Steps**: If Phase 1 Trace identifies 2+ files to modify, add `## Implementation Steps` section with table format:
      ```
      | Step | File | Action | Dependencies | Risk |
      |------|------|--------|--------------|------|
      | 1 | `src/foo.py` | Description | None | Low |
      ```
      The `Dependencies` column accepts `None`, `Step N`, or comma-separated step references. The `Risk` column accepts `Low`, `Medium`, `High`. This section is optional but RECOMMENDED for multi-file changes.
    - **MUST — Security Scope**: Add `## Security Scope` section to the Spec based on the changed files identified in Phase 1 Trace. Use these detection rules:
      | Check | Applicable When |
      |-------|-----------------|
      | SEC-1 | Any source code file modified (`.py`, `.js`, `.ts`, `.go`, `.java`, etc.) |
      | SEC-2 | Code contains `request.`, `form.`, `input`, `argv`, `sys.stdin`, `process.argv` |
      | SEC-3 | Files in `models/`, `dao/`, `repository/`; or code contains `SELECT`, `INSERT`, `UPDATE`, `DELETE`, ORM patterns |
      | SEC-4 | Frontend files (`.tsx`, `.vue`, `.svelte`, `.html`); or code contains `innerHTML`, `dangerouslySetInnerHTML`, template rendering |
      | SEC-5 | Files in `auth/`, `session/`, `login/`; or code contains `token`, `jwt`, `cookie`, `session` |
      | SEC-6 | Files in `api/`, `routes/`, `endpoints/`, `controllers/`; or new public endpoints added |
      | SEC-7 | Files in `api/`, `routes/`; or code contains exception handling patterns |
      | SEC-8 | Dependency files modified (`package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`) |

      **Docs/tests-only shortcut**: If ONLY files matching `docs/**`, `tests/**`, `*.md`, `README*` are modified, mark ALL checks N/A with reason "docs/tests only".

      Output format in the Spec:
      ```markdown
      ## Security Scope
      | Check | Applicable | Reason |
      |-------|------------|--------|
      | SEC-1 | Yes | Source code modified |
      | SEC-2 | No | No user input handling |
      | SEC-3 | Yes | models/user.py modified |
      ```
    - **Spec Lint Self-Check**: After writing the Spec, run `python3 src/pactkit/skills/spec_linter.py docs/specs/{ID}.md`. If ERROR rules fail, self-correct the Spec immediately (you wrote it — you have authority to fix it). Re-run until clean. This prevents the Spec from being rejected at Act Phase 0.5.
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

# Command: Act (v1.3.0 Stack-Aware)
- **Usage**: `/project-act $ARGUMENTS`
- **Agent**: Senior Developer

## 🧠 Phase 0: The Thinking Process (Mandatory)
1.  **Read Law**: Read the Spec (`docs/specs/`) carefully.
2.  **RFC Gate (Feasibility Check)**: If you identify a requirement in the Spec that is technically infeasible, contradictory, or would require violating a security/architectural constraint, invoke the **RFC Protocol**:
    - **STOP** implementation immediately. Do NOT write any code.
    - **Report** to the user: (a) quote the exact problematic requirement from the Spec, (b) explain why it is infeasible (technical reasoning), (c) suggest an alternative approach.
    - You MUST NOT modify the Spec unilaterally — only the user (or Architect via a new `/project-plan` cycle) may amend Tier 1.
    - Wait for user guidance before proceeding.
3.  **Locate Target**: Which file/function needs surgery?
4.  **Detect Stack & Select References**: Identify the project type from source files:
    - `.py` files → Python stack → Consult `DEV_REF_BACKEND` + `TEST_REF_PYTHON`
    - `.ts`/`.tsx`/`.vue`/`.svelte` files → Frontend stack → Consult `DEV_REF_FRONTEND` + `TEST_REF_NODE`
    - `.go` files → Go stack → Consult `DEV_REF_BACKEND` + `TEST_REF_GO`
    - `.java` files → Java stack → Consult `DEV_REF_BACKEND` + `TEST_REF_JAVA`
    - Mixed (frontend + backend) → Consult both `DEV_REF_FRONTEND` and `DEV_REF_BACKEND`
    - Use the Stack Reference guidelines throughout implementation and testing phases.
5.  **Memory MCP (Conditional)**: IF `mcp__memory__search_nodes` tool is available, load prior context:
    - Use `mcp__memory__search_nodes` with the STORY_ID to retrieve any stored architectural decisions or design rationale from the Plan phase
    - Use `mcp__memory__search_nodes` with relevant module/feature keywords to find related past decisions from other stories

## 🛡️ Phase 0.5: Spec Lint Gate (Mandatory)
> **PURPOSE**: Non-AI structural validation — ensures "Spec is Law" has physical enforcement before any code is written.
1.  **Run Linter**: Execute the Spec Linter on the current Story's spec:
    ```bash
    python3 src/pactkit/skills/spec_linter.py docs/specs/{STORY_ID}.md
    ```
    Replace `{STORY_ID}` with the actual Story ID from `$ARGUMENTS` (e.g., `STORY-042`).
2.  **If ERRORs found**: **STOP**. Output all ERROR and WARN items. Instruct the user:
    > "Spec Lint failed. Fix the issues above in `docs/specs/{STORY_ID}.md`, then re-run `/project-act`."
    Do NOT proceed to Phase 1.
3.  **If WARNs only**: Output the WARN list, then **continue** to Phase 1.
4.  **If all pass**: Continue silently to Phase 1.

## 📊 Phase 0.6: Consistency Check (Advisory)
> **PURPOSE**: Left-shift quality — catch Spec ↔ Board ↔ Test Case misalignment at the cheapest point (pure text, before any code).
> **NON-BLOCKING**: All findings are WARN or INFO. This phase NEVER stops Act.
1.  **Spec ↔ Board Alignment**:
    - Parse all `### R{N}:` subsections from `docs/specs/{STORY_ID}.md` → list of requirements
    - Parse the Story's task list from `docs/product/sprint_board.md` (the `- [ ]` items under this Story)
    - Cross-reference: for each requirement, find a matching task (exact `R{N}` ID OR ≥50% keyword overlap)
    - Output alignment matrix:
      ```
      | Spec Requirement | Board Task | Status |
      | R1: xxx          | Task: xxx  | ✅ Aligned |
      | R2: xxx          | —          | ⚠️ Missing Task |
      | —                | Task: yyy  | ⚠️ No matching Requirement |
      ```
2.  **Spec AC ↔ Test Case Coverage**:
    - Parse all `### AC{N}:` subsections from the Spec
    - Check if `docs/test_cases/{STORY_ID}_case.md` exists
    - If exists: cross-reference AC items with Scenario entries; report uncovered ACs
    - If not exists: output `ℹ️ Test Case not yet created (normal — generated during Check phase)`
3.  **Summary**:
    - Output counts: `Alignment: {N}/{total} requirements matched | Coverage: {N}/{total} ACs covered`
    - If WARNs found: "Consider updating the Board tasks to match Spec requirements before proceeding."
4.  **Continue**: Regardless of findings, proceed to Phase 1.

## 🎬 Phase 1: Precision Targeting
1.  **Visual Scan**: Run `visualize --focus <module>` to see neighbors.
    - For projects with 50+ source files, add `--depth 2` to limit the graph to 2 levels of dependencies.
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
    - **Iteration Cap**: Maximum **5 iterations**. If the loop does not reach GREEN after 5 iterations, **STOP** and report: "TDD loop exceeded 5 iterations. Likely cause: [error summary]. Please review."
    - **Environment Failure Bailout**: If a test fails with an environment-class error — `ModuleNotFoundError`, `ImportError`, `ConnectionError`, `ConnectionRefusedError`, `FileNotFoundError` (for config/env files), `PermissionError`, or timeout from an external service — apply the following **decision tree** before stopping:
      1. **Project-internal check**: Is the missing module/name under the project root directory (i.e., part of your codebase, not a third-party package)? Check if the module path maps to a file you are building in this Story.
         - **If YES (project-internal)**: This is NOT an environment error — it is incomplete implementation. Return to Phase 3 Step 1 and create or update the missing module. Do not trigger the bailout.
         - **If NO (third-party or external)**: Proceed to step 2.
      2. Attempt to resolve the third-party dependency (e.g., `pip install <package>`, update `requirements.txt`, check `.env` file).
      3. If the dependency cannot be resolved after one attempt, **STOP** and report to the user: "Test requires external service or missing dependency. Please ensure [service/package] is available."
    - **Normal TDD failures** (`AssertionError`, `TypeError`, `ValueError`, etc.) proceed normally — modify your source code and iterate.
3.  **Regression Check (Read-Only Gate)**: After the TDD loop is GREEN, run a broader regression check.
    - **Identify changed modules**: `git diff --name-only HEAD` to list modified source files.
    - **Doc-Only detection**: Classify changed files using `LANG_PROFILES[stack].source_dirs` and `file_ext`. If zero source files were changed (only `.md`, `.yml`, `docs/`, `.github/`, etc.), skip the broader regression — the TDD loop already validated the new tests. Log: `"Regression: SKIP — doc-only change, no source files modified"`. Proceed to Phase 4.
    - **Map to related tests**: For each changed file, find its corresponding test file using the `test_map_pattern` in `LANG_PROFILES`.
    - **Scope decision**: Check if any changed file is imported by 3+ other modules in `code_graph.mmd`. If yes, run the **full test suite**. If no (low fan-in, isolated change), run only the **mapped test files**.
    - **Fallback**: If no test mapping can be determined, or `code_graph.mmd` does not exist, fall back to the full test suite.
    - **CRITICAL — Pre-existing test failure protocol**:
      - If a pre-existing test (one you did NOT create in Phase 2) fails, **DO NOT modify** the failing test or the code it tests.
      - **DO NOT loop** — this is a one-shot check, not an iterative loop.
      - **STOP** and report to the user: which test failed, what it appears to test, and which of your changes likely caused the failure.
      - Suggest options: (a) you revert your change that caused the regression, or (b) the user reviews and provides guidance.
      - You MUST NOT assume you understand the design intent behind pre-existing tests — the project may have adopted PDCA mid-way and there is no Spec for older features.

## 🎬 Phase 4: Sync & Document
1.  **Hygiene**: Delete temp files.
2.  **Update Reality (Lazy Visualize)**:
    - Check if `git diff --name-only HEAD` includes any files in `LANG_PROFILES[stack].source_dirs` OR if `code_graph.mmd` does not exist.
    - **If source files changed OR graph missing**: Run all three visualize commands:
        - `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize`
        - `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize --mode class`
        - `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize --mode call`
    - **If no source files changed AND graph exists**: Skip with log: `"Graph up-to-date — no source changes"`
3.  **Update Board (CRITICAL)**:
    - Mark the tasks in `docs/product/sprint_board.md` as `[x]`.
    - Use `update_task` or manual edit.
""",

    "project-check.md": """---
description: "QA verification: security scan, code quality scan, Spec alignment"
allowed-tools: [Read, Bash, Grep, Glob]
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

## Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block before using any tools.
1.  **Analyze Context**: Read the active `docs/specs/{ID}.md`.
2.  **Determine Layer**:
    * *Logic Only?* -> Strategy: **API Level**.
    * *UI/DOM/Interaction?* -> Strategy: **Browser Level**.
3.  **Detect Stack**: If changed files include `.tsx`/`.vue`/`.svelte`, also consult `DEV_REF_FRONTEND` for client-side security and rendering performance checks.
4.  **Gap Analysis**: Do we have a structured Test Case? If not, plan to create one.
5.  **Security Scope**: Check if the Spec contains a `## Security Scope` section.
    - If present: parse the `Applicable` column for each SEC-* check. Pass this scope to Phase 1.
    - If absent (legacy Spec): fall back to running all 8 checks (backward compatible).

## Phase 1: Security Scan (OWASP+)
> **Config**: If `pactkit.yaml` contains `check.security_checklist: false`, skip this phase and log: "Security checklist disabled via config".
> **Scope**: If `pactkit.yaml` contains `check.security_scope_override: full`, run ALL 8 checks regardless of the Spec's Security Scope. Otherwise, use the scope parsed in Phase 0.

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
1.  **Verify Spec Structure**: Read `docs/specs/{STORY_ID}.md`.
    * *Check*: Does the Spec contain `## Acceptance Criteria` with Given/When/Then Scenarios?
    * *If missing*: WARN the user — "Spec lacks structured Acceptance Criteria. Run `/project-plan` to fix."
2.  **Extract Scenarios**: List all Scenarios from the Spec's `## Acceptance Criteria` section.
3.  **Check**: Does `docs/test_cases/{STORY_ID}_case.md` exist?
4.  **Action**: If missing, generate it based *strictly* on the Spec's Acceptance Criteria.
    * *Format*: Gherkin (Given/When/Then).
    * *Constraint*: Do not write Python code yet.
5.  **Coverage Report**: Compare Scenarios in Spec vs Test Cases. Report any uncovered Scenario.

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
""",

    # [FIX] Upgraded to v19.5 and added Auto-Fix Logic
    "project-done.md": """---
description: "Code cleanup, Board update, Git commit"
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Command: Done (v1.3.0 Smart Gatekeeper)
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
2.  **Update Reality (Lazy Visualize)**:
    - Check if `docs/architecture/graphs/code_graph.mmd` exists AND `git diff --name-only` includes any files in `LANG_PROFILES[stack].source_dirs`.
    - **If source files changed OR graph missing**: Run all three visualize commands:
        - `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize`
        - `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize --mode class`
        - `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize --mode call`
    - **If no source files changed AND graph exists**: Skip with log: `"Graph up-to-date — no source changes"`
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

### Step 1.3: Doc-Only Shortcut
> **PURPOSE**: If no source files were changed, skip or minimize regression — running 1000+ tests for a README edit wastes time.

1. **Classify changed files**: From the `git diff` and `git status` output (Step 1), identify which files are **source files** vs **non-source files**:
   - **Source files**: Files matching `LANG_PROFILES[stack].file_ext` (e.g., `.py`) whose path starts with any directory in `LANG_PROFILES[stack].source_dirs` (e.g., `src/` for Python).
   - **Non-source files**: Everything else — `.md`, `.yml`, `.yaml`, `.json`, `.mmd`, `docs/`, `.github/`, `tests/`, config files, specs, board files.
2. **Decision**:
   - If **zero source files** changed AND **no test files** were added/modified:
     - Log: `"Regression: SKIP — doc-only change, no source files modified"`
     - Skip regression entirely. Proceed directly to Step 2.7 (Lint Gate).
   - If **zero source files** changed BUT **new test files** exist (e.g., `tests/unit/test_story*.py` created in this Story):
     - Log: `"Regression: STORY-ONLY — {N} new test files, no source changes"`
     - Run ONLY those new test files (they were already validated in Act Phase 3 TDD loop, but re-confirm here).
     - Skip the full suite. Proceed to Step 2.7.
   - If **any source files** changed: Continue to Step 1.5 (normal flow).

### Step 1.5: Fast-Suite Shortcut
> If the last test run completed in **< 30 seconds** (check pytest output or prior run time), skip the decision tree and always run **full regression** — the suite is fast enough that optimizing for incremental provides no benefit. Proceed directly to Step 3.

### Step 1.6: Release Gate — Version Bump Override (R5)
> **PURPOSE**: Release commits require a full suite to ensure no regressions are hidden.
1. Run `git diff HEAD~1 pyproject.toml | grep version` (or vs. branch base).
2. If a version change is detected (e.g., `1.4.0` → `1.4.1`):
   - Log: `"Regression: FULL — version bump detected, release requires full test suite"`
   - Skip impact analysis. Proceed directly to Step 3 (full regression).
3. If no version change: continue to Step 1.7.

### Step 1.7: Impact-Based Analysis (STORY-053)
> **PURPOSE**: Use `call_graph.mmd` to target only tests affected by changed functions.

1. **Preconditions**: All of the following must be true to attempt impact analysis:
   - `docs/architecture/graphs/call_graph.mmd` exists.
   - `regression.strategy` is `impact` (read from `pactkit.yaml`; default: `impact`).
2. **Identify changed functions**: Use `git diff HEAD~1 --unified=0` on changed source files to extract modified function names (look for `def ` in the diff).
3. **Run impact command** for each changed function:
   ```bash
   python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py impact --entry <func_name>
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
> **DEFAULT**: Run **full regression** (`pytest tests/`). This is the safe default.

Run **incremental tests** only if ALL of the following conditions are true:
- `code_graph.mmd` exists AND appears in `git diff HEAD~1 --name-only` or `git status --short` (i.e., the graph was recently updated, not stale)
- Changed source files ≤ 3 (small, isolated change set)
- At least ONE changed source file has a direct test mapping via `test_map_pattern` in `LANG_PROFILES`, OR total test count < 500 (fast enough for full suite as fallback)
- NO changed file is imported by 3+ other modules in `code_graph.mmd`
- NO test infrastructure files were changed (`conftest.py`, `pytest.ini`, `pyproject.toml [tool.pytest]`)
- NO version change in `pactkit.yaml` (version bump implies broader impact)

**Fallback**: If `code_graph.mmd` does not exist (e.g., non-PDCA project or not yet generated), always run full regression.

### Step 2.3: Decision Logging (MANDATORY)
After evaluating the decision tree, output the decision and the reason:
- If skip: `"Regression: SKIP — doc-only change, no source files modified"`
- If story-only: `"Regression: STORY-ONLY — {N} new test files, no source changes"`
- If full (version bump): `"Regression: FULL — version bump detected, release requires full test suite"`
- If full (other): `"Regression: FULL — {reason}"` (e.g., "Regression: FULL — config.py imported by 5 modules")
- If impact-based: `"Regression: IMPACT-BASED — {N} test files based on call graph analysis"`
- If incremental: `"Regression: INCREMENTAL — {N} mapped test files, {conditions summary}"`
- This log helps the user understand why full regression was chosen and builds trust in the decision tree.

### Step 2.5: Coverage Verification (Conditional)
IF `pytest-cov` is available, run tests with coverage on changed source files:
- `pytest --cov=<changed_modules> --cov-report=term-missing tests/`
- **≥ 80%** line coverage on changed files: PASS — proceed normally
- **50-79%**: WARN — output: "Changed file `{file}` has {N}% coverage. Consider running `/project-check` to generate missing tests."
- **< 50%**: BLOCK — require user confirmation: "Changed file `{file}` has only {N}% coverage. Proceed anyway?"
- Include coverage data in the output so the user can evaluate test quality.

### Step 2.7: Smart Lint Gate (STORY-030)
> **Purpose**: Stack-aware lint check with configurable behavior.

1. **Detect Stack**: Read `lint_command` from `LANG_PROFILES` for the detected project stack.
   - Example (Python): `ruff check src/ tests/`
   - Example (Node): `npx eslint .`
2. **Auto-Fix (Conditional)**: Read `auto_fix` from `pactkit.yaml`.
   - If `auto_fix: true`: Run lint with fix flag first (e.g., `ruff check --fix src/ tests/`), then re-run lint to verify.
   - If `auto_fix: false` (default): Skip auto-fix, run lint in check-only mode.
3. **Run Lint**: Execute the lint command for the detected stack.
4. **Blocking Behavior**: Read `lint_blocking` from `pactkit.yaml`.
   - If `lint_blocking: true`: Lint failures **STOP** the commit. Report errors and do NOT proceed.
   - If `lint_blocking: false` (default): Lint failures are reported as **warnings**. Print findings but proceed with commit.
5. **Skip**: If no lint command found for the stack, skip silently: "No lint command configured — skipping lint gate."

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
3.  **Lessons Auto-append with Quality Gate (MANDATORY)**: Evaluate the lesson before appending to `docs/architecture/governance/lessons.md`:
    - **Step 1 — Score** the lesson on 5 dimensions (1=Low, 3=Medium, 5=High):
      | Dimension | 1 (Low) | 3 (Medium) | 5 (High) |
      |-----------|---------|------------|----------|
      | Specificity | Abstract principles only | Has code example | Covers all usage patterns |
      | Actionability | Unclear what to do | Main steps understandable | Immediately actionable |
      | Scope Fit | Too broad or narrow | Mostly appropriate | Name and content aligned |
      | Non-redundancy | Nearly identical to existing | Some unique perspective | Completely unique value |
      | Coverage | Partial coverage | Main cases covered | Includes edge cases |
    - **Step 2 — Bonus**: If Check Phase produced any P0 or P1 findings that inspired this lesson, add **+3** to the total.
    - **Step 3 — Gate**: Read `done.lesson_quality_threshold` from `pactkit.yaml` (default: **15**).
      - If total score < threshold: **do NOT append**. Log: `"Lesson skipped (score {N}/25 < threshold {T})"`
      - If total score >= threshold: append row with format: `| {YYYY-MM-DD} | {summary} (score: {N}/25) | {STORY_ID} |`
    - This is NOT conditional on Memory MCP — always evaluate and either append or log skip.
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

## 🎬 Phase 3.5.5: Issue Tracker Verification (Backfill Safety Net)
> **Purpose**: Verify GitHub Issue exists for the Story; create backfill if Plan phase was skipped.
1.  **Check Config**: Read `pactkit.yaml` for `issue_tracker.provider`.
2.  **If `provider: none` or section missing**: Skip silently, proceed to Phase 3.6.
3.  **If `provider: github`**:
    a. **CLI Check**: Run `gh --version`. If unavailable, print warning "Issue tracker verification skipped: gh CLI unavailable" and proceed to Phase 3.6.
    b. **Search**: Run `gh issue list --search "{STORY_ID}" --state all --json number,title,url` to find existing issue.
    c. **If issue found**:
       - Check if Sprint Board entry has issue link (e.g., `[#N](url)`)
       - If no link: update Sprint Board entry to include `[#{number}]({url})`
       - Proceed to Phase 3.6 for closure
    d. **If issue NOT found (Backfill)**:
       - Create issue: `gh issue create --title "{STORY_ID}: {Story Title}" --body "Spec: docs/specs/{STORY_ID}.md\n\n**Status**: Backfilled during Done phase"`
       - Parse the returned issue URL
       - Update Sprint Board entry to include `[#{number}]({url})`
       - Proceed to Phase 3.6 for closure
    e. **If any gh command fails**: Print warning with error message, continue to Phase 3.6.

## 🎬 Phase 3.6: Issue Tracker Closure (Conditional)
> **Purpose**: Close linked external issues when the Story is done.
1.  **Check Config**: Read `pactkit.yaml` for `issue_tracker.provider`.
2.  **If `provider: github`**:
    - Parse the Sprint Board entry for a linked issue URL (e.g., `[#123](https://github.com/...)`)
    - If found: run `gh issue close <number> --comment "Completed in $(git rev-parse --short HEAD)"`
    - If `gh` CLI unavailable or closure fails: print warning, continue
3.  **If `provider: none` or section missing**: Skip silently.

## 🎬 Phase 4: Git Commit
0.  **Enterprise Check**: If `enterprise.no_git: true` in `pactkit.yaml`, skip ALL git operations in this phase. Print: "ℹ️ Git operations disabled (enterprise.no_git)". Skip to the Session Context Update phase.
1.  **Format**: `feat(scope): <title from spec>`
2.  **Execute**: Run the git commit command.
3.  **Post-Commit Prompts**:
    - **Version bump?** If `pyproject.toml` version was changed in this Story: "ℹ️ Version bump detected. Run `/project-release` to create snapshot and git tag."
    - **Feature branch?** If current branch is not `main`/`master`: "ℹ️ Working on a feature branch. Run `/project-pr` to push and create a pull request."

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

    "project-clarify.md": """---
description: "Standalone requirement clarification before planning"
allowed-tools: [Read, Bash, Glob, Grep]
---

# Command: Clarify (v1.0.0)
- **Usage**: `/project-clarify "$ARGUMENTS"`
- **Agent**: System Architect

> **PURPOSE**: Standalone requirement clarification. Run before `/project-plan` to surface ambiguities and produce a clarified brief.

## Phase 1: Ambiguity Analysis
1.  Analyze `$ARGUMENTS` against the AMBIGUITY_SIGNALS checklist (same as Plan Phase 0.7).
2.  Generate 3–6 structured questions (Scope, Users, Constraints, Scale, Edge Cases, Non-Goals).
3.  Ask questions in the user's language.

## Phase 2: Clarified Brief Output
1.  After user responses, produce a **Clarified Brief**:
    ```markdown
    ## Clarified Brief: {feature name}
    - **Scope**: {confirmed operations}
    - **Users**: {confirmed target users / roles}
    - **Constraints**: {technical constraints}
    - **Scale**: {performance expectations}
    - **Edge Cases**: {failure scenarios and expected behavior}
    - **Non-Goals**: {explicitly excluded}
    ```
2.  Output: "Ready for Plan. Run: `/project-plan \\"{clarified brief summary}\\"`"
""",

    "project-init.md": """---
description: "Initialize project scaffolding and governance structure"
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Command: Init (v1.3.0 Rich)
- **Usage**: `/project-init`
- **Agent**: System Architect

## 🧠 Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block before using any tools.
1.  **Environment Check**: Is this a fresh folder or legacy project?
2.  **Compliance**: Does the user need `pactkit.yaml`?
3.  **Strategy**: If legacy, I must prioritize `visualize` to capture Reality.

## 🛡️ Phase 0.5: Git Repository Guard
> **INSTRUCTION**: Check if the directory is inside a git repository before creating files.
1.  **Check**: Run `git rev-parse --is-inside-work-tree` (suppress stderr).
2.  **If NOT a git repo** (command fails):
    - Ask the user: "No git repository detected. Initialize one with `git init`?"
    - **If user confirms**: Run `git init` in the current directory.
    - **If user declines**: Print warning: "⚠️ Git operations (commit, branch) will not work without a repository." Continue with the rest of init.
3.  **If already a git repo**: Skip silently to Phase 1.

## 🎬 Phase 1: Environment & Config
1.  **Check CLI Availability**: Run `pactkit version` to check if CLI is available.
    - **If available**: Proceed to Step 2.
    - **If NOT available** (command fails): Print warning: "⚠️ pactkit CLI not found. Install with: `pip install pactkit`". Then manually create a minimal `.claude/pactkit.yaml` with `stack: <detected>`, `version: 0.0.1`, `root: .` and skip to Step 4.
2.  **Generate Config**: Check if `./.claude/pactkit.yaml` exists.
    - **If missing**: Run `pactkit init` to generate complete configuration.
    - **If exists**: Run `pactkit update` to backfill any missing sections (preserves user customizations).
3.  **Stack Detection** (auto-detected by `pactkit init`, or manual fallback):
    - Valid values: `python`, `node`, `go`, `java`
    - If `pyproject.toml` or `requirements.txt` or `setup.py` exists → `stack: python`
    - If `package.json` exists → `stack: node`
    - If `go.mod` exists → `stack: go`
    - If `pom.xml` or `build.gradle` exists → `stack: java`
    - If none match → ask the user to specify
4.  **Project CLAUDE.md**: Check/Create `./.claude/CLAUDE.md` if missing (do NOT overwrite if it already exists).
    - *Purpose*: Project-level instructions for Claude Code (separate from global `~/.claude/CLAUDE.md`).
    - *Venv Detection*: Check if a virtual environment exists (`.venv/`, `venv/`, or `env/` with `bin/python3`).
    - *Content template*:
      ```markdown
      # {Project Name} — Project Context

      {IF venv detected}
      ## Virtual Environment
      Always use the project's virtual environment:
      - **Activate**: `source {venv_path}/bin/activate`
      - **Python**: `{venv_path}/bin/python3`
      - **Pytest**: `{venv_path}/bin/pytest`
      - **Pip**: `{venv_path}/bin/pip`
      {END IF}

      ## Dev Commands

      ```
      # Run tests
      {IF venv detected}{venv_path}/bin/{ELSE}{END IF}{test_runner from LANG_PROFILES}

      # Lint
      {lint_command from LANG_PROFILES}
      ```

      @./docs/product/context.md
      ```
    - Use the directory name as the project name.
    - Fill `test_runner` and `lint_command` from `LANG_PROFILES` based on the detected language.
    - If venv detected, prefix test commands with venv bin path (e.g., `.venv/bin/pytest`).
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

    "project-release.md": """---
description: "Version release: snapshot, archive, Git tag, and GitHub Release"
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Command: Release (v1.4.0)
- **Usage**: `/project-release`
- **Agent**: Repo Maintainer

## 🧠 Phase 0: Pre-flight Check
1.  **Version Detection**: Check if `pyproject.toml` version was changed vs the previous commit.
    - Run `git diff HEAD~1 pyproject.toml | grep version` (or vs branch base)
    - Capture the new version value (e.g., `1.4.1`).
    - If no version change detected: print "ℹ️ No version bump detected. Update `pyproject.toml` version before releasing." and STOP.
2.  **Read Config**: Read `pactkit.yaml` to detect stack and release configuration.

## 🎬 Phase 1: Invoke pactkit-release Skill
1.  **Delegate to skill**: Invoke the `pactkit-release` skill with `VERSION={version}` from Phase 0.
    - The skill handles the full release protocol:
      Version Update → Spec Backfill → Architecture Snapshot → Git Operations → GitHub Release.
    - Pass the detected version so the skill skips its own auto-detection step.
""",

    "project-pr.md": """---
description: "Push branch and create pull request via gh CLI"
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Command: PR (v1.4.0)
- **Usage**: `/project-pr`
- **Agent**: Repo Maintainer

## 🧠 Phase 0: Pre-flight Check
1.  **Branch Check**:
    - Run `git branch --show-current` to get current branch name
    - If branch is `main` or `master`: print "Skipping PR: working on main branch" → STOP
2.  **Existing PR Check**:
    - Run `gh pr list --head <branch> --state open --json number` to check for existing PR
    - If PR exists: print "PR already open: <URL>" → STOP
    - If `gh` CLI unavailable: print "⚠️ gh CLI not available — cannot create PR" → STOP
3.  **Story Detection**: Infer active Story ID from branch name (e.g., `feature/STORY-051-desc` → `STORY-051`).

## 🎬 Phase 1: Push Assurance
1.  **Check Remote**: If remote tracking branch does not exist, run `git push -u origin <branch>`.
2.  **If push fails**: STOP and report the error.

## 🎬 Phase 2: PR Generation
1.  **Generate PR Title**: Format `{type}({scope}): {spec_title}`
    - `type`: `feat` for STORY, `fix` for BUG/HOTFIX
    - `scope`: infer from primary modified directory
    - `spec_title`: extract from `# {ID}: {Title}` heading in Spec (strip the ID prefix)
    - Max 70 characters
2.  **Generate PR Body**: Extract from Spec and test results:
    ```markdown
    ## Summary
    {1-3 sentences from Spec ## Background}

    ## Changes
    {R1, R2, ... from Spec ## Requirements, one bullet each with MUST/SHOULD/MAY}

    ## Acceptance Criteria
    {AC1, AC2, ... as checklist items — mark [x] if a test for it passed}

    ## Test Results
    - Unit: {N} passed, {N} failed
    - E2E: {N} passed, {N} failed

    ## Spec
    - [{STORY_ID}](docs/specs/{STORY_ID}.md)

    🤖 Generated with [Claude Code](https://claude.com/claude-code)
    ```
3.  **User Confirmation**: Show the PR title + body preview. Ask: "Create this PR? (yes/no/edit)"
    - `yes` → execute `gh pr create --title "..." --body "..."`
    - `no` → skip
    - `edit` → accept user feedback, regenerate, ask again
4.  **Output**: Print PR URL on success.
""",

}

# Register additional prompts into COMMANDS_CONTENT
COMMANDS_CONTENT["project-sprint.md"] = SPRINT_PROMPT
COMMANDS_CONTENT["project-hotfix.md"] = HOTFIX_PROMPT
COMMANDS_CONTENT["project-design.md"] = DESIGN_PROMPT
