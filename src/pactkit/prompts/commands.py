from pactkit.prompts.workflows import (
    DEBUG_PROMPT,
    DESIGN_PROMPT,
    HOTFIX_PROMPT,
    SPRINT_PROMPT,
)

LEGACY_COMMANDS_CONTENT = {
    "project-plan.md": """---
description: "Analyze requirements, create Spec and Story"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Command: Plan (v1.3.0 Integrated Trace)
- **Usage**: `/project-plan "$ARGUMENTS"`
- **Agent**: System Architect

Previous workflow/checkpoint records are optional historical context only. They
must not block planning, require a new session, or determine this command's
completion.

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
1.  Run `pactkit guard` to check init markers (pactkit.yaml via `{PACTKIT_YAML}`, `docs/product/stories/`, `docs/architecture/graphs/`).
2.  If exit code 1: project is not initialized — print the missing markers and do not create the Spec yet. Suggest `/project-init`; safe inspection and initialization repair remain available in this session.
3.  If all exist: check config completeness (ci, issue_tracker sections). If stale, report the missing or outdated sections and ask for explicit authorization before running `pactkit update`; otherwise continue planning with the existing configuration.
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
7.  **Checkpoint**: Record `intent_clarified` with the original input fingerprint and the sanitized confirmed answers.

## 🎬 Phase 1: Archaeology (The "Know Before You Change" Step)
> **Subagent Scope Rule**: When delegating research to an Explore subagent, always provide a **bounded** prompt: target function/class, directory scope, file limit, and expected output. Never delegate open-ended "trace the whole codebase" tasks.

1.  **Provider-Routed Scan**: Run `pactkit query --explore <target> --json --explain`. The router enforces configured Codegraph priority, freshness and fail-closed behavior. Do not invoke `visualize`, Codegraph, SQLite or `rg` directly. Use `--allow-fallback` only after explicitly recording why degradation is acceptable.
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
4.  **Lateral Scan (MUST for Modification)** — after tracing the target, scan horizontally for existing implementations of the same operation pattern:
    - Identify the core operation(s) the requirement involves (e.g., "write to OWL", "send notification", "create DB record").
    - Use a tiered strategy to count existing implementations in the project:
      - **Prefer LSP** (if available): `incomingCalls` or `findReferences` on the core operation's function/method — gives type-aware, zero-false-positive results.
      - **Fallback visualize**: `visualize --mode call --reverse --entry <operation>` — reads fan-in from the project's call graph.
      - **Fallback grep**: `grep -rn "<operation>" src/` — text-level search when neither LSP nor visualize is available.
    - **Output checkpoint**:
      ```
      Lateral Scan:
      - Operation: {name}
      - Existing implementations: {N} ({file1}:{func1}, {file2}:{func2}, ...)
      - Assessment: {Reuse existing | Extract shared abstraction | New is justified}
      ```
    - **Threshold**: If the same operation has **≥ 3 independent implementations**, the Spec's Technical Design MUST include a shared abstraction evaluation before adding the Nth implementation.
    - **Skip condition**: Pure greenfield features with no existing codebase analog — log "Lateral Scan: no existing pattern found" and proceed.
5.  **Solution Design Protocol (Conditional)** — if the requirement involves frameworks already used by the project:
    - Execute the **Capability Design** module from `{SKILLS_ROOT}/_rules/design/capability-design.md` to evaluate capability delta (framework native + project existing vs. needs implementation).
    - Include the Capability Assessment output in Phase 2 Spec writing.
6.  **Checkpoint**: Record `archaeology` with provider decision, freshness, query targets, and bounded trace summary.

## 🎬 Phase 2: Design & Impact
1.  **Diff**: Compare User Request vs Current Reality (from Phase 1).
2.  **Duplication Audit**: Run the Duplication Audit from system-architect protocol — if this is the Nth same-kind implementation, grep existing implementations and assess shared abstraction needs before writing Spec.
3.  **Engineering Concerns Assessment** — scan the requirement for NFR keywords:
    - Reference the Engineering Concerns trigger index (`{SKILLS_ROOT}/_rules/engineering/index.md`) keyword table.
    - For each matched concern, the Spec's Technical Design MUST include a decision (e.g., concurrency model, timeout strategy, caching policy).
    - Unmatched concerns → do not add (avoid noise).
    - **Output checkpoint**: `"Engineering concerns identified: {list}. Decisions will be included in Technical Design."`
4.  **Update HLD**: Modify `docs/architecture/graphs/system_design.mmd`.
    - *Rule*: Keep the `code_graph.mmd` as is (it updates automatically).

## 🎬 Phase 3.1: Story ID Generation
1.  Run `pactkit generate-id` to allocate a decentralized time-prefixed Story ID; it preserves the `developer` prefix from pactkit.yaml.
2.  **Output checkpoint**: Print "Story ID determined: {ID}. Writing Spec now."
3.  **Record the identity locally**: State the generated Story ID before creating its Spec. Any optional local checkpoint is historical evidence only and never controls a future session.

## 🎬 Phase 3.2a: Scaffold + Metadata Table & Requirements
1.  **Scaffold**: Run `{SCAFFOLD_CMD} create_spec "{ID}" "{title}"` in the current session.
2.  **Read**: Read `docs/specs/{ID}.md` to see the scaffolded template.
3.  **Edit placeholders** (use Edit tool, NOT Write):
    - Edit `Release | TBD` → `Release | {version}` (from `pyproject.toml`/`package.json`, NOT `{PACTKIT_YAML}`)
    - Edit `(Description of the problem or feature)` → actual Background content from your Trace findings
    - Edit `## Target Call Chain` placeholder → actual call chain from Phase 1
    - Edit `### R1: (Requirement Name) (MUST)` → actual requirements using RFC 2119 keywords (MUST/SHOULD/MAY). Add more R{N} sections as needed.
    - Edit `## Dependency Surface` fields (dangling ID = E010; feeds `pactkit spec-graph`)
4.  **Journey Segment (Conditional)**: If `docs/e2e/journey.md` exists in the project:
    - Read `docs/e2e/journey.md` to identify defined journeys and their steps.
    - Assess whether this Story's scope touches any journey step (e.g., modifies a UI flow, changes an API endpoint used in a journey).
    - If yes: add a `## Journey Segment` section to the Spec with the format:
      ```
      ## Journey Segment

      - Journey: {Journey Name}
      - Steps: {step numbers, e.g., "2-3" or "4"}
      - Impact: {brief description of how this story affects the journey}
      ```
    - If the Story does not affect any journey: do NOT add this section (Act Phase 4 Journey Sync will auto-skip).
5.  **Output checkpoint**: Print "Spec skeleton filled. Adding acceptance criteria."
6.  **Milestone output**: Report `spec_scaffolded`, then `requirements_written` in your progress output; each milestone claim must be verifiable against the real Spec file.

## 🎬 Phase 3.2b: Acceptance Criteria & Implementation Steps
1.  **Edit AC** (use Edit tool): Replace `### AC1: (Scenario Name) (R1)` and its Given/When/Then placeholders with actual scenarios. The template already provides the `- **Given**` / `- **When**` / `- **Then**` structure — fill in the content. Add more AC{N} sections as needed.
    - Each Scenario SHOULD map to a verifiable test case in `docs/test_cases/`.
2.  **Edit Implementation Steps** (optional): If Phase 1 Trace identifies 2+ files to modify, replace the placeholder rows in `## Implementation Steps` with actual steps. The table skeleton (headers + separator) is already in the template.
3.  **Output checkpoint**: Print "Acceptance criteria written. Running security scope."
4.  **Checkpoint**: Record `acceptance_written`; placeholders or missing Given/When/Then MUST fail.

## 🎬 Phase 3.2c: Security Scope
1.  **MUST**: Run `pactkit sec-scope <changed-files>` to auto-detect SEC-1~SEC-8 applicability.
2.  **Edit** the `## Security Scope` section already in the template: replace the placeholder SEC-1 row with actual SEC-* assessments from the output above. The table skeleton (Check/Applicable/Reason headers) is already in the template.
3.  **Fallback**: If `pactkit sec-scope` is unavailable, manually Edit each SEC-1 through SEC-8 entry. Apply docs/tests-only shortcut if applicable (mark ALL N/A with Reason "docs/tests only").
4.  **Output checkpoint**: Print "Security scope filled. Running lint."
5.  **Checkpoint**: Record `security_scoped` from the real Spec.

## 🎬 Phase 3.2d: Spec Lint Self-Check
1.  Run `pactkit spec-lint docs/specs/{ID}.md`. If `pactkit` is not on `$PATH`, use `python3 -m pactkit spec-lint docs/specs/{ID}.md` instead.
2.  If any ERROR or WARNING rules fire, self-correct the Spec immediately (you wrote it — you have authority to fix it). Re-run until `pactkit spec-lint` reports 0 errors AND 0 warnings.
3.  This prevents the Spec from being rejected at Act Phase 0.5.
4.  **Output checkpoint**: Print "Spec lint passed (0 errors AND 0 warnings)."
5.  **Checkpoint**: Record `spec_linted`; the engine reruns canonical lint and rejects warnings.

## 🎬 Phase 3.3: Board, Memory & Current-Session Continuation
1.  **Board**: Run `{BOARD_CMD} add_story "{STORY_ID}" "{title}" "{task1}|..."` in the current session.
2.  **Memory MCP (Conditional)**: IF Memory MCP is available, use create_entities to store design context (decisions, target files, rationale) under entity `{STORY_ID}`. Record story dependencies if applicable.
3.  **Session Context Update**: Run `pactkit context` to refresh ignored `.pactkit/context.md` with canonical sections `{CONTEXT_SECTIONS}`. Never stage or commit it.
4.  **Continue**: "Trace complete. Spec created. Continue with Act in this session when requested; a new session is optional."
5.  **Completion evidence**: Report the exact title and ordered task list created. If validation fails, fix the local artifacts where safe or report the concrete gap; never create a workflow block that prevents a later session from continuing.
""",
    # [FIX] Added Board Update Step to Phase 4
    "project-act.md": """---
description: "Implement code per Spec, strict TDD"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Command: Act (v1.3.0 Stack-Aware)
- **Usage**: `/project-act $ARGUMENTS`
- **Agent**: Senior Developer

## 🧠 Phase 0: The Thinking Process
> **Execution Style**: Work through each phase incrementally — output progress as you go. Do NOT try to plan all implementation steps in your head before producing output.
1.  **Read Law**: Read the Spec (`docs/specs/`) carefully.
2.  **RFC Gate (Feasibility Check)**: If you identify a requirement in the Spec that is technically infeasible, contradictory, or would require violating a security/architectural constraint, invoke the **RFC Protocol**:
    - Do not implement the contradictory requirement. Continue safe investigation and collect the evidence needed to resolve it; do not write source code whose behavior depends on that unresolved requirement.
    - **Report** to the user: (a) quote the exact problematic requirement from the Spec, (b) explain why it is infeasible (technical reasoning), (c) suggest an alternative approach.
    - You MUST NOT modify the Spec unilaterally — only the user (or Architect via a new `/project-plan` cycle) may amend Tier 1.
    - Wait for user guidance before proceeding.
3.  **Locate Target**: Which file/function needs surgery?
4.  **Detect Stack & Select Stack Reference**: Identify the project type from source files (`.py`, `.ts`/`.tsx`, `.go`, `.java`). Apply the corresponding language-specific best practices throughout implementation and testing.
5.  **Memory MCP (Conditional)**: IF Memory MCP is available, use search_nodes to load prior context for {STORY_ID} — retrieve architectural decisions and design rationale from the Plan phase.

## 🛡️ Phase 0.5: Spec Lint Gate (MUST)
<!-- PACTKIT_ACT_OP:spec_lint -->
> **PURPOSE**: Non-AI structural validation — ensures "Spec is Law" has physical enforcement before any code is written.
1.  **Run Linter**: Execute the Spec Linter on the current Story's spec:
    ```bash
    pactkit spec-lint docs/specs/{STORY_ID}.md
    ```
    If `pactkit` is not on `$PATH`, use `python3 -m pactkit spec-lint docs/specs/{STORY_ID}.md` instead.
    Replace `{STORY_ID}` with the actual Story ID from `$ARGUMENTS` (e.g., `STORY-042`).
2.  **If ERRORs found**: Output all ERROR and WARN items and mark phase completion as incomplete. Fix the Spec where authorized, or continue safe read-only investigation; do not create a permanent workflow lock or require a new session.
3.  **If WARNs only**: Output the WARN list, then **continue** to Phase 1.
4.  **If all pass**: Continue silently to Phase 1.

## 📊 Phase 0.6: Consistency Check (Lightweight)
> **PURPOSE**: Quick pre-flight to verify artifacts exist. Full alignment analysis is deferred to `/project-check` (normal workflow).
> **NON-BLOCKING**: This phase NEVER stops Act.
1.  **Spec exists?**: Check if `docs/specs/{STORY_ID}.md` exists. If not: WARN "Spec not found".
2.  **Story record exists?**: Run `pactkit board list` and check `{STORY_ID}`. Treat `sprint_board.md` as a projection only.
3.  **Move to In Progress**: If `{STORY_ID}` is found on the board, run `{BOARD_CMD} move_story "{STORY_ID}" "in_progress"`.
4.  **Continue**: Regardless of findings, proceed to Phase 1.

## 🧾 Phase 0.7: Spec Input Preflight (MUST)
> **PURPOSE**: Deterministically place referenced implementation inputs and constraints in the current context before any source edit.
1. Run `pactkit spec-preflight docs/specs/{STORY_ID}.md` in the current session.
2. Review the emitted file excerpts, CSS custom properties, interfaces, and MUST/NEVER/禁止/必须/对齐 constraints before writing code.
3. If a required input is missing, ambiguous, outside the project root, or exceeds its extraction budget, mark completion incomplete and fix the declaration where authorized. Safe reading, diagnosis and repair remain available.
4. Continue directly to Phase 1 in this session; a new session is never required.

## 🎬 Phase 1: Precision Targeting
0.  **Previous-session context (optional)**: You MAY read the Agent Continuation section of the local `.pactkit/context.md` (if present) for handover notes from an earlier session. It is never an execution gate: a stale, missing, or empty section does not prevent this session from implementing and verifying the current Story.
1.  **Provider-Routed Scan**: Run `pactkit query --explore <module> --json --explain`. Record the complete provider decision in preflight evidence. Do not invoke Codegraph, visualize, SQLite or `rg` directly; `--allow-fallback` must be explicit and auditable.
2.  **Trace Verification** — use pactkit-trace skill:
    - Run `pactkit query --chain <symbol> --json --explain`; confirm the call site and existing callers before editing.
3.  **Interface Summary (Code Enforce)** — for non-target modules discovered by trace:
    - Run `pactkit interface-summary <file>` for each related module you do NOT plan to modify.
    - This outputs signatures + types + docstrings only (function bodies excluded by code).
    - Only escalate to full `Read <file>` when you confirm the module needs modification.
    - If `pactkit` is not on `$PATH`, use `python3 -m pactkit interface-summary <file>`.
4.  **Topology-Aware Trace (Conditional)** — if `detect_topology(root)` includes `api_call` or `agent`:
    - For **api_call**: Run `api_convention_summary(root)` to check API path prefixes and fetch function conventions. Use these conventions when writing new API calls to maintain consistency.
    - For **agent**: Check AgentParser output for orchestration edges so new code doesn't break agent flow.
5.  **Solution Design Protocol (Conditional)** — if the implementation involves frameworks already used by the project:
    - Execute the **Capability Design** module from `{SKILLS_ROOT}/_rules/design/capability-design.md` to evaluate capability delta before writing code.
    - Output brief capability assessment before proceeding to Phase 1.5.

## 🔧 Phase 1.5: Engineering Concerns Loading (Conditional)
> **PURPOSE**: Load only the NFR guides relevant to this Story — keeps context minimal while ensuring engineering rigor.
1.  **Read Spec Technical Design**: Check if the Spec contains engineering concern decisions (from Plan Phase 2).
2.  **Identify concerns**: Extract the concern keywords mentioned (e.g., database, api-integration, resilience). Reference `{SKILLS_ROOT}/_rules/engineering/index.md` for the keyword→guide mapping table.
3.  **Load guides**: For each identified concern, read the corresponding guide file from `{GUIDES_PATH}/`:
    - MUST load only 1-3 relevant guides (those matching the Spec's concerns).
    - NEVER load all 13 guides.
    - If Spec has no engineering concerns section, skip this phase silently.
4.  **Apply decisions**: Use the loaded guides as risk-driven decision support. Their hard-safety notes are non-negotiable; defaults may be changed with project evidence.
5.  **Output checkpoint**: `"Engineering guides loaded: {list}. Applying as implementation constraints."`

## 🎬 Phase 2: Test Scaffolding (TDD)
<!-- PACTKIT_ACT_OP:tdd_red_green -->
1.  **Constraint**: NEVER write source code in this phase — doing so breaks TDD causality: tests must exist before the code they verify.
2.  **Action**: Create a reproduction test case in `tests/unit/`.
    - Use the knowledge from Phase 1 to mock/stub dependencies correctly.
3.  **Optional handover note**: After confirming RED, you may record a local handover note via `pactkit context --continuation` (see Phase 4 step 3). It must never be required to continue the TDD loop.

## 🎬 Phase 3: Implementation
1.  **Write Code**: Implement logic in the appropriate source directory.
    - **Context7 (Conditional)**: IF implementing with an unfamiliar library API, use Context7 MCP to fetch up-to-date documentation before writing code.
2.  **TDD Loop (Safe Iteration)**: Run ONLY the tests created in Phase 2. Loop until GREEN.
    - Do NOT include pre-existing tests in this loop.
    - Reassess the approach after several unsuccessful iterations, but keep investigating and repairing in the current session while progress is possible.
    - **Environment Failure Bailout**: For environment errors (`ModuleNotFoundError`, `ImportError`, `ConnectionError`, `ConnectionRefusedError`, `PermissionError`, timeout):
      - **Project-internal check first**: If the missing module is project-internal (part of your codebase): NOT a bailout — do not modify source code for env issues, go back and implement it.
      - If third-party: inspect the dependency and attempt a safe resolution (for example, `pip install` only when it is the project's approved dependency-install command). If it remains unavailable, clearly report the environmental limitation and continue any work that can be verified locally.
    - After GREEN, optionally record a local handover note (`pactkit context --continuation`).
3.  **Regression Check (Read-Only Gate)**: After the TDD loop is GREEN, run the project's test suite as a broader regression check.
    <!-- PACTKIT_ACT_OP:regression_classification -->
    - Run `pactkit regression` (uses `git diff` + `LANG_PROFILES` to classify: SKIP/FULL/IMPACT). Doc-only changes are auto-skipped.
    - If IMPACT: run `pactkit test-map <changed-files>` for incremental test selection. Query importers through `pactkit query --callers <file> --json --explain`; if any changed file has 3+ importers, run full suite. Fallback is allowed only through router policy.
    - **Pre-existing test failure protocol**: Do not casually modify an unrelated failing test. Diagnose whether the Story caused it; fix it when the causal path is understood, otherwise report it as a QA gap while continuing all safe, relevant Story work.
4.  **Lint Gate**: Run `pactkit lint` to check code style. If lint errors are found, fix them before proceeding. If `pactkit lint` is unavailable, run the stack's lint command directly.
    <!-- PACTKIT_ACT_OP:lint -->
    - After regression and lint pass, optionally record a local handover note (`pactkit context --continuation`).
5.  **Hardcode Self-Check (STORY-slim-105)**: Review the code you just wrote for hardcoded values:
    - URLs (`http://`, `https://`) that should be config
    - Magic numbers (non-obvious integers like `30000`, `8080`) that should be named constants
    - Environment-specific paths that should be parameterized
    - If found, extract to config/constants before proceeding.

## 🎬 Phase 4: Sync & Document
1.  Run `pactkit clean` and `pactkit visualize --lazy` (runs file, `--mode class`, `--mode call` if source changed; codegraph sync is handled automatically).
    <!-- PACTKIT_ACT_OP:graph_sync -->
1b. **Journey Sync (Conditional)**:
    - **Skip if**: `docs/e2e/journey.md` does not exist in the project.
    - **Skip if**: Current Story's Spec has no `## Journey Segment` section.
    - **If triggered**:
      1. Read `docs/e2e/journey.md`
      2. Locate the journey step(s) referenced in the Spec's `## Journey Segment` (format: `- Journey: {Name}` / `- Steps: {N}` / `- Impact: {desc}`)
      3. Review: do the step assertions still hold after this Story's code changes?
      4. If outdated: Edit the affected step(s) in journey.md — update assertions, add new structure assertions, or adjust step description. MUST use Edit (incremental), MUST NOT use Write (full replace).
      5. If still accurate: skip with log "Journey steps verified — no update needed"
2.  **Update Board (CRITICAL)**: Run `{BOARD_CMD} update_task {STORY_ID} "Task Name"` for each completed task to mark it as `[x]`.
    Mid-story additions use `{BOARD_CMD} add_task {STORY_ID} "Task Name"` (subcommands: add_story, add_task, update_task, snapshot, move_story, archive, list_stories, fix_board, render).
    <!-- PACTKIT_ACT_OP:board_update -->
3.  **Update local context (optional)**: You may run `pactkit context --continuation --last-command "/project-act {STORY_ID}" --phase "Phase 4: complete"` for a later handoff.
    <!-- PACTKIT_ACT_OP:continuation_update -->
4.  **Coverage Table Output (STORY-slim-105)**: Output a coverage table listing each R{N} from the Spec:
    <!-- PACTKIT_ACT_OP:requirement_coverage -->

    | Spec 条目 | 类型 | 状态 | 位置 |
    |-----------|------|------|------|
    | R1 xxx | MUST | ✓ | file.py:line |
    | R2 xxx | SHOULD | DEFERRED | — reason |

    - For implemented items: show file:line location
    - For skipped SHOULD items: show DEFERRED with reason (must match comment in code)
    - User verifies this table — do not claim "done" without it
5.  **Honest completion report**: Only claim completed items after the coverage table, Story tests, regression, lint, and Board tasks have been verified. A local handover note is optional evidence and must not block a later session.
""",
    "project-check.md": """---
description: "QA verification: security scan, code quality scan, Spec alignment"
allowed-tools: [Read, Bash, Grep, Glob]
---

# Command: Check (v1.3.0 Deep QA)
- **Usage**: `/project-check $ARGUMENTS`
- **Agent**: QA Engineer

> **PRINCIPLE**: Check is a verification-only operation; identify issues but NEVER modify code — fixes made during QA bypass the TDD loop and produce untested changes.

> **TOOL RESTRICTION**: This entire command is analysis-only.
> NEVER use Edit, Write, or Bash write operations (e.g., `sed -i`, `tee`, `>`, `>>`) in any phase.
> Tool calls that modify files will produce incorrect analysis — the QA verdict
> must reflect the code AS-IS, not code you changed during review.

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
    - If absent (legacy Spec): run `pactkit sec-scope <changed-files>` to auto-detect, or fall back to all 8 checks.

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
1.  **Verify Spec Structure**: Run `pactkit spec-lint docs/specs/{STORY_ID}.md` (or `python3 -m pactkit spec-lint docs/specs/{STORY_ID}.md` if `pactkit` is not on `$PATH`) to validate Spec structure (E006 checks for `## Acceptance Criteria`).
    * *If ERRORs*: WARN the user — "Spec structure issues found. Run `/project-plan` to fix."
    * *If WARNs only*: Note warnings and continue.
2.  **Extract Scenarios**: List all Scenarios from the Spec's `## Acceptance Criteria` section.
3.  **Check**: Does `docs/test_cases/{STORY_ID}_case.md` exist?
4.  **Action**: If missing, generate it based *strictly* on the Spec's Acceptance Criteria.
    * *Format*: Gherkin (Given/When/Then).
    * *Constraint*: Do not write Python code yet.
5.  **Validate Test Case Structure**: Run `pactkit lint-testcase docs/test_cases/{STORY_ID}_case.md` to validate the test case file structure. If errors, WARN the user.
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
> Read `pactkit.yaml` field `e2e.type` to select strategy. Default: `none` (skip).

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

### Journey-Based Coverage (Conditional)
> If `docs/e2e/journey.md` exists in the project, consult it to determine which journey segments the current story affects.

- Read `docs/e2e/journey.md` and identify journeys whose steps overlap with the current story's functionality.
- E2E tests SHOULD cover the affected journey segments (not necessarily the full journey).
- `journey.md` is the journey definition source (cross-story flows); `docs/test_cases/` is the single-story acceptance source. Both inform E2E scope.

### Playwright Assertion Strategy
> When writing or reviewing Playwright E2E tests, follow these guidelines to produce stable, non-flaky assertions.

**Element Locator Priority** (most stable first):

| Priority | Method | When to Use |
|----------|--------|-------------|
| 1 | Accessibility role + name (`getByRole`) | Always prefer — resilient to markup changes |
| 2 | `data-testid` attribute (`getByTestId`) | Fallback when role/name insufficient |
| 3 | CSS selector | Last resort — only when above unavailable |

**AI Content Assertion Boundaries**:
- MUST assert: structure exists (code block, chart component, answer area rendered)
- MUST assert: content is non-empty (response container has text/children)
- MUST assert: no error/exception state displayed
- MUST NOT assert: specific text content (AI output is non-deterministic)
- MUST NOT assert: specific numeric values (AI calculations vary across runs)

**Wait Strategy for Async AI Responses**:
- Use loading state disappearance as completion signal — not fixed sleep/timeout
- Alternative: streaming completion marker (e.g., `[data-streaming="false"]`)
- Anti-pattern: `await page.waitForTimeout(5000)` — fragile, slows CI

## Phase 4.5: PactGuard Compliance Scan (Config-Gated)
> Read `pactkit.yaml` field `check.pactguard.enabled`. Default: `false` (skip).

1.  If `check.pactguard.enabled` is `false` (default) → **silently skip** this phase entirely. Do NOT add a row to the Verdict table.
2.  If enabled: check if `pactguard` CLI is available (`which pactguard`). If not found → silently skip.
3.  Run: `pactguard check --mode {check.pactguard.mode} -r {check.pactguard.ruleset} --json-output <changed_files>`
    - If `check.pactguard.ruleset` is empty, omit the `-r` flag (use PactGuard defaults).
4.  Parse JSON output. Add to Phase 5 Verdict table: `PactGuard | PASS/WARN/FAIL | N violations`
5.  If `check.pactguard.blocking: true` and violations found → contribute FAIL to overall verdict.
6.  If `pactguard` exits with error → add `PactGuard | WARN | execution error` to Verdict. Do NOT block.

## Phase 4.7: Observability Scan (Config-Gated)
> Read `pactkit.yaml` field `check.observe.enabled`. Default: `false` (skip).

1.  If `check.observe.enabled` is `false` (default) → **silently skip** this phase entirely. Do NOT add a row to the Verdict table.
2.  If enabled: detect available MCP sources (`mcp__chrome-devtools__*`, `mcp__playwright__*`). If none available → silently skip.
3.  Collect signals (or run `pactkit observe --json` for structured collection):
    - Chrome DevTools: `list_console_messages`, `list_network_requests` (cap: `check.observe.max_console`, `check.observe.max_network`)
    - Playwright: `browser_take_screenshot` for post-test visual verification
4.  Classify signals by severity (ERROR/WARNING/INFO per R3 in Spec).
5.  Add to Phase 5 Verdict table: `Observability | PASS/WARN/FAIL | N console errors, M network failures`

## Phase 5: The Verdict
1.  **Run Unit (Incremental)**: Run `pactkit test-map <changed-files>` to map source files to test files. Run only mapped tests. Fallback to full suite if no mapping.
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
""",
    # [FIX] Upgraded to v19.5 and added Auto-Fix Logic
    "project-done.md": """---
description: "Code cleanup, Board update, Git commit"
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Command: Done (v1.3.0 Smart Gatekeeper)
- **Usage**: `/project-done`
- **Agent**: Repo Maintainer

## 🧠 Phase 0: The Thinking Process
1.  **Audit**: Are tests passing? Is the Board updated?
2.  **Semantics**: Determine correct Conventional Commit scope.

## 🎬 Phase 1: Context Loading
1.  **Read Spec**: Read `docs/specs/{ID}.md`.
2.  **Read Story Facts**: Run `pactkit board list`; never use the Board projection for completion decisions.

## 🎬 Phase 2: Housekeeping (Deep Clean)
1.  Run `pactkit clean` to remove language-specific temp artifacts.
2.  Run `pactkit visualize --lazy` when `LANG_PROFILES.source_dirs` changed; it updates file, `--mode class`, then `--mode call` graphs and Codegraph. Otherwise log: "Graph up-to-date — no source changes".
3.  **HLD Consistency Check**: Run `pactkit doctor` and check HLD drift. If drift > 3, WARN user: "system_design.mmd is {N} modules behind — consider updating it."

## 🎬 Phase 2.5: Regression Gate (CRITICAL)
> **CRITICAL**: Do NOT skip this step. This is the safety net before commit.

### Step 0: Source Change Pre-Check
- If context records a verified `/project-act` and no source/test changed since it, log `"Regression: SKIP — Act already verified, no intervening changes"` and continue at Phase 3.
- Otherwise classify changed files with `git diff --name-only HEAD~1`; doc/config/graph-only changes log `"Regression: SKIP — no source/test changes since Act"` and continue at Smart Lint Gate.

### Step 1: Impact Analysis
- Check graph availability through `pactkit query --impact <target> --json --explain`; do not select providers manually.

### Step 1.3: Classification Shortcut
Run `pactkit regression` (or `pactkit regression <files>`) to classify changes (doc-only → SKIP):
- **SKIP** → proceed to Step 2.7 (no regression needed).
- **FULL** → skip impact analysis, proceed directly to Step 3 (full regression).
- **IMPACT** → continue to Step 1.6.

### Step 1.6: Release Gate — Version Bump Override
If `pactkit regression` returns FULL (version/dependency change detected), proceed directly to Step 3.
Otherwise continue to Step 1.7.

### Step 1.7: Impact-Based Analysis (STORY-053)
With `regression.strategy=impact`, extract changed `def` names from `git diff HEAD~1 --unified=0`; run `{VISUALIZE_CMD} impact --entry <func_name>`, deduplicate mapped tests, and run them when below `regression.max_impact_tests` (default 50). Log `"Regression: IMPACT-BASED — {N} test files based on call graph analysis"`; missing functions, failures, or threshold overflow fall through to Decision Tree.

### Step 2: Decision Tree (Safe-by-Default)
Run full regression by default. Incremental requires a fresh `code_graph.mmd`, ≤3 source files, mappings from `LANG_PROFILES[stack].test_map_pattern`, no test-infra changes, and no file with 3+ importers; missing graph or fast suite (<500 tests) means full.

### Step 2.3: Decision Logging (MUST)
After evaluating the decision tree, log the decision with format: `"Regression: {TYPE} — {reason}"` (e.g., SKIP, STORY-ONLY, FULL, IMPACT-BASED, INCREMENTAL).

### Step 2.5: Coverage Verification (Conditional)
Run `pactkit coverage-gate <changed-files>` to verify coverage on changed source files.
- ≥80% PASS; 50–79% WARN with file/coverage; <50% BLOCK for confirmation. If unavailable, run equivalent `pytest --cov`; report results.

### Step 2.7: Smart Lint Gate (STORY-030)
If Act already verified lint with no later source/test change, log `"Lint: SKIP — Act already passed lint, no new changes"`. Otherwise run `pactkit lint` (or `LANG_PROFILES[stack].lint_command`); honor `auto_fix` and `lint_blocking`, and report non-blocking warnings. No configured command means skip.

### Step 3: Gate
- If any test fails, do not commit or archive. Classify the failure and report the evidence.
- Do not guess at a pre-existing test's intent. A user-authorized repair may continue after reading its governing Spec/Test Case; otherwise leave that failure unchanged and disclose it.
- The agent MUST NOT assume it understands pre-existing test intent — the project may have adopted PDCA mid-way and there is no Spec for older features.
- Report the failure to the user with: which test failed, what it appears to test, and which change likely caused it.
- Proceed to commit/archive only if all required tests and blocking lint checks are green. Safe diagnosis and repair remain available.

## 🎬 Phase 3: Hygiene Check & Fix
1.  **Verify**: Are tasks for this Story marked `[x]`?
2.  **Auto-Fix**:
    - If tests are GREEN but tasks are `[ ]`, **Ask the user**: "Tests passed but tasks are unchecked. Mark as done?"
    - If user agrees, run `pactkit board complete-task {STORY_ID} "<exact task>"` for each task.
3.  **Lessons Auto-append (MUST)**: Run `pactkit lesson-append --story {STORY_ID} --text "lesson text" [--context "file.py:func"]`.
    - The command checks specificity (references concrete file/function?) and dedup (different from last 5 entries?).
    - If both pass: appends row using format `{LESSONS_ROW_FORMAT}` where date=YYYY-MM-DD, context={STORY_ID}
    - If either fails: skip with log from command output.
    - If `pactkit lesson-append` is unavailable, stop and request a Core upgrade; never write a shared Lesson projection manually.
4.  **Invariants Refresh (MUST)**: Run `pactkit invariants-refresh --test-count {N}` where {N} is the actual count from the most recent test run.
    - The command updates `docs/architecture/governance/rules.md` invariant "All {N}+ tests must pass".
    - If `pactkit invariants-refresh` is unavailable, fall back to manual: read rules.md, find the pattern, replace the number.
5.  **Document Validators (Non-blocking)**: Run document structure checks as warnings:
    - `pactkit context --stdout` — validates generation from Story/Lesson facts without writing tracked files
    - `pactkit board render --check` — validates the optional Board projection
    - These are non-blocking: report warnings but do not stop the Done flow.
6.  **Spec Status Update (MUST)**: Run `pactkit spec-status docs/specs/{STORY_ID}.md Done` to update `| Status | Draft |` to `| Status | Done |` in the spec file (accepted values: Draft, In Progress, Done). If `pactkit spec-status` is unavailable, manually edit the spec file.
7.  **Archive Honesty Gate (CRITICAL — STORY-slim-136)**: Run `pactkit done-verify {STORY_ID}` — it mechanically verifies requirement→test evidence, checkbox↔case honesty, and status consistency (Spec Done + Board `[x]` + archive).
    - **Any FAIL (exit ≠ 0)**: Print the evidence lines and do not archive or commit. Continue safe diagnosis or repair when it is within the user's request. WARN-only: print and proceed. CLI too old: warn that the gate was skipped, then proceed.
8.  **Memory MCP (Conditional)**: IF Memory MCP is available, use add_observations to record lessons learned (patterns, pitfalls, key files) on the `{STORY_ID}` entity.
9.  **Harness Audit Refresh (Conditional)**: Run `pactkit audit --append --if-needed {STORY_ID}`. Only refreshes when `harness_audit.json` exists AND its `story_id` matches `{STORY_ID}` (this story owns the audit). Silently skips if no audit was ever run or if the audit belongs to a different story. If it runs and `ready` changed from `true` to `false`, WARN the user.

## 🎬 Phase 3.5: Archive (Optional)
1.  **Check**: Are all tasks for the current Story marked `[x]`?
2.  **Action**: If yes, run `{BOARD_CMD} archive`.
3.  **Result**: Completed stories are moved to `docs/product/archive/archive_YYYYMM.md`.

## 🎬 Phase 3.5.5: Issue Tracker Verification (BUG/HOTFIX Only)
> **Purpose**: Verify GitHub Issue exists for BUG/HOTFIX items; STORY items are NOT synced to protect IP.
1.  Run `pactkit issue-sync {ITEM_ID}` to handle the full issue lifecycle:
    - STORY items: skipped automatically (IP protection).
    - BUG/HOTFIX items: searches for existing issue, backfill-creates if missing, returns issue URL.
2.  If `pactkit issue-sync` returns a URL, update the Sprint Board entry to include `[#{number}]({url})`.
3.  If `pactkit issue-sync` is unavailable, fall back to manual `gh` CLI commands:
    a. **CLI Check**: Run `gh --version`. If unavailable, print warning and proceed to Phase 3.6.
    b. **Search**: Run `gh issue list --search "{ITEM_ID}" --state all --json number,title,url`.
    c. **If not found**: Create issue via `gh issue create`.
    d. **If any gh command fails**: Print warning, continue to Phase 3.6.

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
0.5.  **Deployment Verification (self-dev only)**: Only when developing PactKit itself (`pyproject.toml` name == "pactkit"):
    - First perform the deployment smoke-check in a temporary target directory; do not write a real host configuration as part of Done.
    - If validating the installed host is needed, describe the exact update and ask for explicit authorization before running `pactkit update`.
    - Smoke-check: for each AC that references prompt/deployed file content, inspect 1-2 key assertions in the temporary generated files.
    - Report: `Deploy verification: PASS ({N} assertions checked)` or `FAIL (details)`.
    - If FAIL, fix the deployment issue before committing.
    - **If NOT self-dev**: Skip this step silently.
1.  **Format**: `feat(scope): <title from spec>`
2.  **Execute**: Run the git commit command.
3.  **Post-Commit Prompts**:
    - **Version bump?** If `pyproject.toml` version was changed in this Story: "ℹ️ Version bump detected. Run `/project-release` to create snapshot and git tag."
    - **Feature branch?** If current branch is not `main`/`master`: "ℹ️ Working on a feature branch. Run `/project-pr` to push and create a pull request."
    - **CI Status Check (Conditional)**: If `ci.provider` is `github` in `pactkit.yaml` and `gh` CLI is available:
      1. After push, run `gh run list --limit 1 --json status,name,databaseId` to check the latest workflow run.
      2. Report: `CI: [pass/fail/pending] — {workflow_name} #{run_id}`
      3. If CI fails, print a warning but do NOT block the Done flow.
      4. If `gh` CLI is unavailable or command fails, skip silently.

## 🎬 Phase 4.5: Session Context Update
1.  Run `pactkit context` to refresh ignored local `.pactkit/context.md`. This clears its Agent Continuation section because no `--continuation` flag is passed.
2.  **Never Commit Context**: `.pactkit/context.md` is a local cache; do not stage, commit, or amend it.
""",
    "project-clarify.md": """---
description: "Standalone requirement clarification before planning"
allowed-tools: [Read, Bash, Glob, Grep]
---

# Command: Clarify (v1.1.0)
- **Usage**: `/project-clarify "$ARGUMENTS"`
- **Agent**: System Architect

> **PURPOSE**: Standalone requirement clarification. Run before `/project-plan` to surface ambiguities and assess risks upfront.

## Phase 1: Ambiguity Analysis
1.  Analyze `$ARGUMENTS` against the AMBIGUITY_SIGNALS checklist (same as Plan Phase 0.7).
2.  Generate 3–6 structured questions (Scope, Users, Constraints, Scale, Edge Cases, Non-Goals).
3.  Ask questions in the user's language.

## Phase 2: Pre-mortem Risk Probe
> **PURPOSE**: Reverse thinking — identify how the plan could fail before it starts.
1.  Based on `$ARGUMENTS` and Phase 1 findings, generate 1–2 pre-mortem questions (pick the most relevant):
    - "If this feature is deemed a failure 1 month after launch, what is the most likely reason?"
    - "What assumptions does this plan rely on? Which assumption is the most fragile?"
    - "What will the person maintaining this code in 6 months complain about the most?"
    - "What is the most likely integration point to break?"
2.  Ask in the user's language, together with Phase 1 questions.
3.  Total questions across Phase 1 + Phase 2 MUST NOT exceed 6. If Phase 1 already has 5–6, pick only 1 pre-mortem question. If Phase 1 has ≤ 4, pick up to 2.

## Phase 3: Clarified Brief Output
1.  After user responses, produce a **Clarified Brief**:
    ```markdown
    ## Clarified Brief: {feature name}
    - **Scope**: {confirmed operations}
    - **Users**: {confirmed target users / roles}
    - **Constraints**: {technical constraints}
    - **Scale**: {performance expectations}
    - **Edge Cases**: {failure scenarios and expected behavior}
    - **Non-Goals**: {explicitly excluded}
    - **Risks**: {top 1-2 identified risks from pre-mortem}
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

## 🧠 Phase 0: The Thinking Process
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
> **NOTE**: This playbook is pre-rendered per-format during deployment. All paths below are already resolved for **{DISPLAY_NAME}** (`{FORMAT_NAME}`). No runtime IDE detection needed.
1.  **Check CLI Availability**: Run `pactkit version` to check if CLI is available.
    - **If available**: Proceed to Step 2.
    - **If NOT available** (command fails): Print warning: "⚠️ pactkit CLI not found. Install with: `pip install pactkit`". Then manually create a minimal `pactkit.yaml` in `{PROJECT_CONFIG_DIR}/` with `stack: <detected>`, `root: .`, `developer: ""` and skip to Step 3.
2.  **Generate Config**: Check if `{PACTKIT_YAML}` exists.
    - **If missing**: Run `pactkit init --format {FORMAT_NAME}`
    - **If exists**: Run `pactkit update --format {FORMAT_NAME}`
3.  **Stack Detection** (config-first, then file-based fallback):
    - **Config-first**: If `{PACTKIT_YAML}` exists and has a `stack` value set (including `auto`), use that value and skip file-based detection.
    - **File-based detection** (only if no config value):
      - Valid values: `python`, `node`, `go`, `java`, `auto`
      - If `pyproject.toml` or `requirements.txt` or `setup.py` exists → `stack: python`
      - If `package.json` exists → `stack: node`
      - If `go.mod` exists → `stack: go`
      - If `pom.xml` or `build.gradle` exists → `stack: java`
    - **Safe fallback**: If none match and no config exists, default to `stack: auto` and print warning: "⚠️ No stack detected, defaulting to auto. You can set `stack:` in `{PACTKIT_YAML}` later."
    - Do NOT block on user input for stack selection mid-flow.
4.  **Project Instructions File**: Check/Create `./{PROJECT_CONFIG_DIR}/{INSTRUCTIONS_FILE}` if missing (do NOT overwrite).
    - Use the directory name as the project name. Fill test_runner and lint_command from the detected language stack in LANG_PROFILES.
    - Include: venv instructions, dev commands, and `pactkit context` as the cold-start bootstrap; do not `@import` generated Context.

## 🔌 Phase 1.5: External Dependencies (STORY-slim-137)
> Runs BEFORE Phase 3 — Discovery (codegraph) depends on these tools.
1.  Run `pactkit deps check`. If all present, skip silently.
2.  If anything is missing, list items + purposes and ask the user: "Install now?"
3.  On explicit yes: run `pactkit deps install`. NEVER improvise install commands — the CLI owns the registry.
4.  If declined/failed/refused (`enterprise.no_external`): print the manual commands and continue — MUST NOT block init.

## 🎬 Phase 2: Architecture Governance
1.  **Scaffold**: Run `{VISUALIZE_CMD} init_arch`.
    - *Result*: Folders created. Placeholders (`system_design.mmd`) created.
2.  **Ensure**: `mkdir -p docs/product docs/specs docs/test_cases tests/e2e/api tests/e2e/browser tests/unit`.

## 🎬 Phase 3: Discovery (Reverse Engineering)
1.  **Scan Reality**: Run `{VISUALIZE_CMD} visualize`.
    - *Goal*: If this is an existing project, overwrite the empty `code_graph.mmd` with the REAL class structure immediately.
2.  **Class Scan**: Run `{VISUALIZE_CMD} visualize --mode class`.
3.  **Module Scan**: Run `{VISUALIZE_CMD} visualize --mode module` to generate module-level overview for multi-module projects.
4.  **Verify**: Read `docs/architecture/graphs/code_graph.mmd` and `class_graph.mmd`.
    - *Check*: Is it still "No code yet"? If files exist in src, this graph MUST contain classes.

## 🎬 Phase 4: Project Skeleton
1.  **Story Facts**: Create `docs/product/stories/`. Do not create a writable Board; render one explicitly with `pactkit board render` only when configured. For an existing aggregate project, preview `pactkit governance migrate`, then ask before applying `pactkit governance migrate --apply`.
    - This ensures the board has all three section headers: `## 📋 Backlog`, `## 🔄 In Progress`, `## ✅ Done`.

## 🎬 Phase 5: Knowledge Base (The Law)
1.  **Law**: Write `docs/architecture/governance/rules.md`.
2.  **History**: Create `docs/architecture/governance/lessons/`; every Lesson is a create-only record written by `pactkit lesson-append`.

## 🎬 Phase 6: Session Context Bootstrap
1.  **Generate Context**: Run `pactkit context` to generate ignored local `.pactkit/context.md`; never stage it.

## 🎬 Phase 7: Next Step
1.  **Output**: "✅ PactKit Initialized. Reality Graph captured. Knowledge Base ready."
2.  **Advice**: "⚠️ IMPORTANT: Continue with `/project-plan 'Reverse engineer'` in this session when requested; a new session is optional."
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
    - If no version change is detected: print "ℹ️ No version bump detected. Update `pyproject.toml` version before releasing." Do not tag, publish, or create a release; safe release diagnosis remains available.
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
    - If branch is `main` or `master`: print "Skipping PR: working on main branch" and do not push or create a PR.
2.  **Existing PR Check**:
    - Run `gh pr list --head <branch> --state open --json number` to check for existing PR
    - If PR exists: print "PR already open: <URL>" and do not create a duplicate.
    - If `gh` CLI is unavailable: print "⚠️ gh CLI not available — cannot create PR"; do not push solely for this command, but still provide the prepared title/body and diagnostics.
3.  **Story Detection**: Infer active Story ID from branch name (e.g., `feature/STORY-051-desc` → `STORY-051`).

## 🎬 Phase 1: Push Assurance
1.  **Check Remote**: If remote tracking branch does not exist, run `git push -u origin <branch>`.
2.  **If push fails**: Do not create the PR. Report the error and preserve the local branch for retry.

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

COMMANDS_CONTENT = dict(LEGACY_COMMANDS_CONTENT)

# Register additional prompts into COMMANDS_CONTENT
COMMANDS_CONTENT["project-sprint.md"] = SPRINT_PROMPT
COMMANDS_CONTENT["project-hotfix.md"] = HOTFIX_PROMPT
COMMANDS_CONTENT["project-design.md"] = DESIGN_PROMPT
COMMANDS_CONTENT["project-debug.md"] = DEBUG_PROMPT
def get_deployable_commands() -> dict[str, str]:
    """Return native current-host/current-session command playbooks.

    Workflow/runner APIs are explicit integrations and never alter these
    current-host/current-session command playbooks.
    """
    return dict(COMMANDS_CONTENT)

# Exported prompt constants are canonical rendered command bodies too.
SPRINT_PROMPT = COMMANDS_CONTENT["project-sprint.md"]
HOTFIX_PROMPT = COMMANDS_CONTENT["project-hotfix.md"]
DESIGN_PROMPT = COMMANDS_CONTENT["project-design.md"]
DEBUG_PROMPT = COMMANDS_CONTENT["project-debug.md"]
