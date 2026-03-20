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
> **Tool Integration Note**: If the request involves adapting PactKit to a new AI coding tool (new `format` value like `codex`, `cursor`, etc.), **always start** by consulting `docs/guides/tool-integration-checklist.md`. Complete Dimension 0 (capability matrix) before writing any code. See also `docs/guides/codex-integration-preresearch.md` for an example pre-research template.

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
    - `{PACTKIT_YAML}` (project-level config)
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
    - [High] No quantitative metrics ("高并发" without QPS, "fast" without benchmark)
    - [High] No boundary conditions ("user management" without specifying which operations)
    - [Medium] No technical constraints (no auth method, no framework specified)
    - [Medium] Single sentence input (< 15 words) — likely under-specified
    - [Medium] Vague quantifiers ("some", "many", "a few", "大量", "一些", "简单")
    - [Medium] No target user specified
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
1.  **Visual Scan**: Run `visualize` to see the module dependency graph. Use `--mode class` for structure, `--mode call` for logic.
    - For large codebases (50+ files), use `--focus <module> --depth 2` to limit scope.
2.  **Logic Trace (CRITICAL)** — use pactkit-trace skill:
    - If modifying existing logic, trace the current implementation.
    - *Goal*: Identify the exact function/class responsible for the logic.

## 🎬 Phase 2: Design & Impact
1.  **Diff**: Compare User Request vs Current Reality (from Phase 1).
2.  **Update HLD**: Modify `docs/architecture/graphs/system_design.mmd`.
    - *Rule*: Keep the `code_graph.mmd` as is (it updates automatically).

## 🎬 Phase 3: Deliverables
1.  **Story ID Generation** (STORY-072):
    - Read `developer` from `pactkit.yaml` (check `{PACTKIT_YAML}`).
    - If `developer` has a value (e.g., `alice`): use ID format `STORY-{developer}-{NNN}` (e.g., `STORY-alice-001`).
    - If `developer` is empty or missing: use ID format `STORY-{NNN}` (backward compatible).
    - NNN: scan `docs/specs/` for existing files with the same prefix, find the max number, increment by 1.
2.  **Spec**: Create `docs/specs/{ID}.md` detailing the *Change*.
    - **MUST — Metadata Table**: Include a metadata table at the top of the Spec using this EXACT format:
      ```markdown
      | Field | Value |
      |-------|-------|
      | ID | {ID} |
      | Status | Draft |
      | Priority | P2 |
      | Release | {version} |
      ```
      Field names MUST be exact case (ID, Status, Priority, Release) — not bold, not different names.
    - *Requirement*: Include a "Target Call Chain" section in the Spec based on your Trace findings.
    - **MUST**: Fill in the `## Requirements` section using RFC 2119 keywords (MUST/SHOULD/MAY).
    - **MUST**: Fill in the `## Acceptance Criteria` section with Given/When/Then scenarios.
    - Each Scenario SHOULD map to a verifiable test case in `docs/test_cases/`.
    - **MUST**: Fill in the `Release` metadata field by reading the `version` field from `{PACTKIT_YAML}` or `pyproject.toml`. Use that EXACT value — do NOT increment or predict a future version. If the file cannot be read, use `TBD`.
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
    - **Spec Lint Self-Check**: After writing the Spec, run `pactkit spec-lint docs/specs/{ID}.md`. If ERROR rules fail, self-correct the Spec immediately (you wrote it — you have authority to fix it). Re-run until clean. This prevents the Spec from being rejected at Act Phase 0.5.
2.  **Board**: Add Story using `add_story`.
3.  **Memory MCP (Conditional)**: IF Memory MCP is available, use create_entities to store design context (decisions, target files, rationale) under entity `{STORY_ID}`. Record story dependencies if applicable.
4.  **Session Context Update**: Update `docs/product/context.md` using the Context.md Canonical Format (see Shared Protocols). Set "Last updated by" to `/project-plan`.
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
4.  **Detect Stack & Select Stack Reference**: Identify the project type from source files (`.py`, `.ts`/`.tsx`, `.go`, `.java`). Apply the corresponding language-specific best practices throughout implementation and testing.
5.  **Memory MCP (Conditional)**: IF Memory MCP is available, use search_nodes to load prior context for {STORY_ID} — retrieve architectural decisions and design rationale from the Plan phase.

## 🛡️ Phase 0.5: Spec Lint Gate (Mandatory)
> **PURPOSE**: Non-AI structural validation — ensures "Spec is Law" has physical enforcement before any code is written.
1.  **Run Linter**: Execute the Spec Linter on the current Story's spec:
    ```bash
    pactkit spec-lint docs/specs/{STORY_ID}.md
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
1.  **Visual Scan**: Run `visualize --focus <module>` to see neighbors. For large codebases, add `--depth 2`.
2.  **Trace Verification** — use pactkit-trace skill:
    - Before touching any code, confirm the call site and ensure you don't break existing callers.

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
3.  **Regression Check (Read-Only Gate)**: After the TDD loop is GREEN, run a broader regression check.
    - **Identify changed modules**: `git diff --name-only HEAD` to list modified source files.
    - **Doc-Only detection**: Classify changed files using `LANG_PROFILES[stack].source_dirs`. If zero source files changed, skip regression. Log: `"Regression: SKIP — doc-only change"`.
    - **Map to related tests**: Use Test Mapping Protocol (see Shared Protocols) for incremental test selection.
    - **Scope decision**: If any changed file has 3+ importers in `code_graph.mmd`, run full suite. Otherwise, run only mapped tests.
    - **Fallback**: If no test mapping can be determined, fall back to the full test suite.
    - **CRITICAL — Pre-existing test failure protocol**: If a pre-existing test fails, **DO NOT modify** it. **STOP** and report to the user. This is a one-shot check, not an iterative loop.

## 🎬 Phase 4: Sync & Document
1.  **Hygiene**: Delete temp files.
2.  **Update Reality (Lazy Visualize)**: Apply the Lazy Visualize Protocol (see Shared Protocols) — run `visualize`, `--mode class`, and `--mode call` if source files changed.
3.  **Update Board (CRITICAL)**: Mark the tasks in `docs/product/sprint_board.md` as `[x]`.
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
1.  **Analyze Context**: Read the active `docs/specs/{ID}.md`.
2.  **Determine Layer**:
    * *Logic Only?* -> Strategy: **API Level**.
    * *UI/DOM/Interaction?* -> Strategy: **Browser Level**.
3.  **Detect Stack**: If changed files include `.tsx`/`.vue`/`.svelte`, also apply frontend-specific checks (component structure, accessibility, rendering performance).
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
* **Action**: Create/Run `tests/e2e/browser/test_{STORY_ID}_browser.py`.
* **Playwright MCP (Conditional)**: IF Playwright MCP is available, use it for browser-level verification (navigation, snapshots, interactions).
* **Chrome DevTools MCP (Conditional)**: IF Chrome DevTools MCP is available, use it for performance tracing and runtime diagnostics.

## Phase 5: The Verdict
1.  **Run Suite**: Execute the specific test file created above (Story E2E test).
2.  **Run Unit (Incremental)**: Use Test Mapping Protocol (see Shared Protocols) to run only tests related to changed modules. Fallback to full suite if no mapping.
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
1.  **Audit**: Are tests passing? Is the Board updated?
2.  **Semantics**: Determine correct Conventional Commit scope.

## 🎬 Phase 1: Context Loading
1.  **Read Spec**: Read `docs/specs/{ID}.md`.
2.  **Read Board**: Read `docs/product/sprint_board.md`.

## 🎬 Phase 2: Housekeeping (Deep Clean)
1.  **Action**: Remove language-specific temp artifacts per `LANG_PROFILES[stack].cleanup`.
2.  **Update Reality (Lazy Visualize)**: Apply the Lazy Visualize Protocol (see Shared Protocols) — run `visualize`, `--mode class`, and `--mode call` if `LANG_PROFILES[stack].source_dirs` files changed. If no source changes and graph exists, skip with log: "Graph up-to-date — no source changes".
3.  **HLD Consistency Check**: Verify `system_design.mmd` component counts match reality. Warn if stale.

## 🎬 Phase 2.5: Regression Gate (MANDATORY)
> **CRITICAL**: Do NOT skip this step. This is the safety net before commit.

### Step 1: Impact Analysis
- Run `git diff --name-only HEAD~1` (or vs. branch base) to list all changed files.
- Check if `docs/architecture/graphs/code_graph.mmd` exists.

### Step 1.3: Doc-Only Shortcut
Classify changed files using `LANG_PROFILES[stack].source_dirs` and `file_ext`:
- **Zero source files** changed, no new tests → SKIP regression, proceed to Step 2.7.
- **Zero source files** but new test files exist → run only those test files, proceed to Step 2.7.
- **Any source files** changed → continue to Step 1.6.

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
   {VISUALIZE_CMD} impact --entry <func_name>
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

### Step 2.3: Decision Logging (MANDATORY)
After evaluating the decision tree, log the decision with format: `"Regression: {TYPE} — {reason}"` (e.g., SKIP, STORY-ONLY, FULL, IMPACT-BASED, INCREMENTAL).

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
3.  **Lessons Auto-append (MANDATORY)**: Append a lesson to `docs/architecture/governance/lessons.md` if it passes these two checks:
    - **Specific?** Does the lesson reference a concrete file, function, or pattern? (Not just a generic principle)
    - **Non-duplicate?** Is it meaningfully different from the last 5 entries in `lessons.md`?
    - If both yes: append row using format `{LESSONS_ROW_FORMAT}` where date=YYYY-MM-DD, context={STORY_ID}
    - If either no: skip with log: `"Lesson skipped: {reason}"`
4.  **Invariants Refresh (MANDATORY)**: Update the Invariants section in `docs/architecture/governance/rules.md`:
    - Read the current `rules.md` file.
    - Update the test count to match the actual number from the most recent test run (e.g., "All {N}+ tests must pass").
    - Preserve the Architecture Decisions (ADR) table — only update the Invariants section.
    - If `rules.md` does not exist, skip silently.
5.  **Memory MCP (Conditional)**: IF Memory MCP is available, use add_observations to record lessons learned (patterns, pitfalls, key files) on the `{STORY_ID}` entity.

## 🎬 Phase 3.5: Archive (Optional)
1.  **Check**: Are all tasks for the current Story marked `[x]`?
2.  **Action**: If yes, run `{BOARD_CMD} archive`.
3.  **Result**: Completed stories are moved to `docs/product/archive/archive_YYYYMM.md`.

## 🎬 Phase 3.5.5: Issue Tracker Verification (BUG/HOTFIX Only)
> **Purpose**: Verify GitHub Issue exists for BUG/HOTFIX items; STORY items are NOT synced to protect IP.
1.  **Check Item Type**: Parse the current item ID (e.g., `STORY-001`, `BUG-001`, `HOTFIX-001`).
    - **If STORY-***: Skip this phase entirely. Print: "ℹ️ Issue sync skipped for STORY (IP protection)". Proceed to Phase 3.6.
    - **If BUG-* or HOTFIX-***: Continue with issue verification.
2.  **Check Config**: Read `pactkit.yaml` for `issue_tracker.provider`.
3.  **If `provider: none` or section missing**: Skip silently, proceed to Phase 3.6.
4.  **If `provider: github`**:
    a. **CLI Check**: Run `gh --version`. If unavailable, print warning "Issue tracker verification skipped: gh CLI unavailable" and proceed to Phase 3.6.
    b. **Search**: Run `gh issue list --search "{ITEM_ID}" --state all --json number,title,url` to find existing issue.
    c. **If issue found**:
       - Check if Sprint Board entry has issue link (e.g., `[#N](url)`)
       - If no link: update Sprint Board entry to include `[#{number}]({url})`
       - Proceed to Phase 3.6 for closure
    d. **If issue NOT found (Backfill)**:
       - Create issue: `gh issue create --title "{ITEM_ID}: {Item Title}" --body "Spec: docs/specs/{ITEM_ID}.md\n\n**Status**: Backfilled during Done phase"`
       - Parse the returned issue URL
       - Update Sprint Board entry to include `[#{number}]({url})`
       - Proceed to Phase 3.6 for closure
    e. **If any gh command fails**: Print warning with error message, continue to Phase 3.6.

## 🎬 Phase 3.6: Issue Tracker Closure (BUG/HOTFIX Only)
> **Purpose**: Close linked external issues when BUG/HOTFIX is done. STORY items are skipped.
1.  **Check Item Type**: If current item is `STORY-*`, skip this phase silently.
2.  **Check Config**: Read `pactkit.yaml` for `issue_tracker.provider`.
3.  **If `provider: github`**:
    - Parse the Sprint Board entry for a linked issue URL (e.g., `[#123](https://github.com/...)`)
    - If found: run `gh issue close <number> --comment "Completed in $(git rev-parse --short HEAD)"`
    - If `gh` CLI unavailable or closure fails: print warning, continue
4.  **If `provider: none` or section missing**: Skip silently.

## 🎬 Phase 4: Git Commit
0.  **Enterprise Check**: If `enterprise.no_git: true` in `pactkit.yaml`, skip ALL git operations in this phase. Print: "ℹ️ Git operations disabled (enterprise.no_git)". Skip to the Session Context Update phase.
1.  **Format**: `feat(scope): <title from spec>`
2.  **Execute**: Run the git commit command.
3.  **Post-Commit Prompts**:
    - **Version bump?** If `pyproject.toml` version was changed in this Story: "ℹ️ Version bump detected. Run `/project-release` to create snapshot and git tag."
    - **Feature branch?** If current branch is not `main`/`master`: "ℹ️ Working on a feature branch. Run `/project-pr` to push and create a pull request."

## 🎬 Phase 4.5: Session Context Update
> **Purpose**: Generate `docs/product/context.md` so the next session auto-loads project state.
1.  **Write Context**: Update `docs/product/context.md` with the following required sections (from `schemas.CONTEXT_SECTIONS`):
{CONTEXT_SECTIONS}
    Set "Last updated by" to `/project-done`.
2.  **Commit Context**: `git add docs/product/context.md && git commit --amend --no-edit` to include context.md in the commit.
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
1.  **Environment Check**: Is this a fresh folder or legacy project?
2.  **Compliance**: Does the user need `pactkit.yaml`?
3.  **Strategy**: If legacy, I must prioritize `visualize` to capture Reality.

## 🛡️ Phase 0.5: Git Repository Guard
> **INSTRUCTION**: Check if the directory is inside a git repository. This check is non-interactive — never prompt the user.
1.  **Check**: Run `git rev-parse --is-inside-work-tree` (suppress stderr).
2.  **If NOT a git repo** (command fails):
    - Print warning: "⚠️ No git repository detected. Git operations (commit, branch) will not work. Run `git init` to initialize one."
    - Continue with the rest of init. Do NOT prompt or block.
3.  **If already a git repo**: Skip silently to Phase 1.

## 🎬 Phase 1: Environment & Config
1.  **Check CLI Availability**: Run `pactkit version` to check if CLI is available.
    - **If available**: Proceed to Step 2.
    - **If NOT available** (command fails): Print warning: "⚠️ pactkit CLI not found. Install with: `pip install pactkit`". Then manually create a minimal `pactkit.yaml` (in `.claude/` or `.opencode/` depending on environment) with `stack: <detected>`, `version: 0.0.1`, `root: .`, `developer: ""` and skip to Step 4.
2.  **Environment Detection** (MUST run BEFORE any `pactkit init/update` call — BUG-slim-001):
    - Check if `~/.config/opencode/AGENTS.md` exists OR `which opencode` succeeds.
    - Set `DETECTED_ENV`:
      - **OpenCode detected** → `DETECTED_ENV=opencode`
      - **Otherwise** → `DETECTED_ENV=classic`
    - This variable determines the `--format` flag for all subsequent `pactkit` CLI calls.
3.  **Generate Config**: Check if `pactkit.yaml` exists (check `.claude/pactkit.yaml` then `.opencode/pactkit.yaml`).
    - **If missing**:
      - If `DETECTED_ENV=opencode`: Run `pactkit init --format opencode`
      - If `DETECTED_ENV=classic`: Run `pactkit init`
    - **If exists**:
      - If `DETECTED_ENV=opencode`: Run `pactkit update --format opencode`
      - If `DETECTED_ENV=classic`: Run `pactkit update`
4.  **Stack Detection** (config-first, then file-based fallback):
    - **Config-first**: If `pactkit.yaml` exists (in `.claude/` or `.opencode/`) and has a `stack` value set (including `auto`), use that value and skip file-based detection.
    - **File-based detection** (only if no config value):
      - Valid values: `python`, `node`, `go`, `java`, `auto`
      - If `pyproject.toml` or `requirements.txt` or `setup.py` exists → `stack: python`
      - If `package.json` exists → `stack: node`
      - If `go.mod` exists → `stack: go`
      - If `pom.xml` or `build.gradle` exists → `stack: java`
    - **Safe fallback**: If none match and no config exists, default to `stack: auto` and print warning: "⚠️ No stack detected, defaulting to auto. You can set `stack:` in `pactkit.yaml` later."
    - Do NOT block on user input for stack selection mid-flow.
5.  **Project Instructions File** (environment-aware):
    - **If `DETECTED_ENV=classic`**: Check/Create `./.claude/CLAUDE.md` if missing (do NOT overwrite).
      - Use the directory name as the project name. Fill test_runner and lint_command from the detected language stack in LANG_PROFILES.
      - Include: venv instructions (if detected), dev commands, `@./docs/product/context.md` reference for cross-session context.
    - **If `DETECTED_ENV=opencode`**: Do NOT create `.claude/` or `CLAUDE.md`. Proceed to Step 6.
6.  **OpenCode Project Setup** (only if `DETECTED_ENV=opencode`):
    - Ensure `pactkit.yaml` exists in `.opencode/` (already handled by Step 3).
    - Generate `./opencode.json` if missing:
      ```json
      {
        "$schema": "https://opencode.ai/config.json",
        "instructions": ["AGENTS.md", "docs/product/context.md"],
        "permission": { "edit": "allow", "bash": { "*": "allow", "rm -rf /*": "deny" } },
        "mcp": { "context7": { "type": "remote", "url": "https://mcp.context7.com/mcp" } }
      }
      ```
    - Generate `./AGENTS.md` if missing (project instructions, can reference global AGENTS.md or be standalone).
    - Print: "ℹ️ OpenCode environment detected. Generated opencode.json, AGENTS.md, and pactkit.yaml."

## 🎬 Phase 2: Architecture Governance
1.  **Scaffold**: Determine the skills path based on `DETECTED_ENV`:
    - If `DETECTED_ENV=opencode`: `SKILLS_PATH=~/.config/opencode/skills`
    - If `DETECTED_ENV=classic`: `SKILLS_PATH=~/.claude/skills`
    Run `python3 $SKILLS_PATH/pactkit-visualize/scripts/visualize.py init_arch`.
    - *Result*: Folders created. Placeholders (`system_design.mmd`) created.
2.  **Ensure**: `mkdir -p docs/product docs/specs docs/test_cases tests/e2e/api tests/e2e/browser tests/unit`.

## 🎬 Phase 3: Discovery (Reverse Engineering)
1.  **Scan Reality**: Run `python3 $SKILLS_PATH/pactkit-visualize/scripts/visualize.py visualize`.
    - *Goal*: If this is an existing project, overwrite the empty `code_graph.mmd` with the REAL class structure immediately.
2.  **Class Scan**: Run `python3 $SKILLS_PATH/pactkit-visualize/scripts/visualize.py visualize --mode class`.
3.  **Verify**: Read `docs/architecture/graphs/code_graph.mmd` and `class_graph.mmd`.
    - *Check*: Is it still "No code yet"? If files exist in src, this graph MUST contain classes.

## 🎬 Phase 4: Project Skeleton
1.  **Board**: Run `python3 $SKILLS_PATH/pactkit-scaffold/scripts/scaffold.py create_board` if `docs/product/sprint_board.md` does not exist.
    - This ensures the board has all three section headers: `## 📋 Backlog`, `## 🔄 In Progress`, `## ✅ Done`.

## 🎬 Phase 5: Knowledge Base (The Law)
1.  **Law**: Write `docs/architecture/governance/rules.md`.
2.  **History**: Write `docs/architecture/governance/lessons.md`.

## 🎬 Phase 6: Session Context Bootstrap
1.  **Generate Context**: Write `docs/product/context.md` using the Context.md Canonical Format (see Shared Protocols). Set "Last updated by" to `/project-init`.

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
