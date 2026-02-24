# Safe markdown helper
M = '```'

# ==============================================================================
# TRACE PROMPT
# ==============================================================================
TRACE_PROMPT = f"""---
description: "Deep code tracing and execution flow analysis"
allowed-tools: [Read, Bash, Grep, Glob]
---

# Skill: Trace (v16.2 Code Explorer)
- **Usage**: Invoked as `pactkit-trace` skill
- **Agent**: Code Explorer

## 🕵️‍♂️ Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block before using any tools.
1.  **Strategy**: Am I tracing a Data Flow (Model -> DB) or Control Flow (API -> Service)?
2.  **Boundaries**: Define the stop condition (e.g., "Stop at Database Layer").

## 🧠 Phase 1: Feature Discovery
1.  **Entry Point**: Use `grep` or `find` to locate the trigger (API route, CLI arg, UI Event).
    - *Tool*: `grep -r "$ARGUMENTS" src/`
2.  **Map Files**: List the core files involved. Don't read everything yet.

## 🔗 Phase 1.5: Call Graph Analysis (Auto-Trace)
1.  **Auto-Trace**: Run `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize --mode call --entry <function_name>`.
    - *Result*: BFS transitive closure from entry function → `call_graph.mmd`.
2.  **Read Graph**: Read `docs/architecture/graphs/call_graph.mmd` to see all reachable functions.
3.  **Scope**: Use this to narrow down Phase 2 tracing targets.

## 🧵 Phase 2: Deep Tracing (The Thread)
1.  **Follow the Call**:
    - If `main()` calls `init_app()`, read `init_app`.
    - If `service.login()` is called, grep for `def login` to find the definition.
2.  **Data Spy**: Note how data structures change (e.g., `dict` -> `UserObj` -> `JSON`).

## 🏗️ Phase 3: Visual Synthesis (MANDATORY)
You must output a **Mermaid Sequence Diagram** to visualize the flow.

{M}mermaid
sequenceDiagram
    participant Entry as API/CLI
    participant Logic as DomainLogic
    participant Data as Persistence

    Entry->>Logic: Trigger Action
    Logic->>Data: Query
    Data-->>Logic: Result
    Logic-->>Entry: Response
{M}

## 📝 Phase 4: Archaeologist Report
- **Patterns**: Identify Design Patterns used.
- **Debt**: Flag hardcoded values, complex logic, or lack of tests.
- **Key Files**: List the top 3 files critical to this feature.
"""

# ==============================================================================
# 3b. LANGUAGE PROFILES (STORY-025)
# ==============================================================================

LANG_PROFILES = {
    'python': {
        'test_runner': 'pytest',
        'test_dir': 'tests/',
        'file_ext': '.py',
        'cleanup': ['__pycache__', '.pytest_cache', '*.pyc'],
        'package_file': 'pyproject.toml',
        'e2e_test_pattern': 'test_{ID}.py',
        'test_map_pattern': 'tests/unit/test_{module}.py',
        'lint_command': 'ruff check src/ tests/',
    },
    'node': {
        'test_runner': 'npx jest',
        'test_dir': '__tests__/',
        'file_ext': '.ts',
        'cleanup': ['node_modules/.cache', '.next', 'dist', 'coverage'],
        'package_file': 'package.json',
        'e2e_test_pattern': '{ID}.test.ts',
        'test_map_pattern': '__tests__/{module}.test.ts',
        'lint_command': 'npx eslint .',
    },
    'go': {
        'test_runner': 'go test ./...',
        'test_dir': '*_test.go',
        'file_ext': '.go',
        'cleanup': ['cover.out', 'cover.html'],
        'package_file': 'go.mod',
        'e2e_test_pattern': '{ID}_test.go',
        'test_map_pattern': '{package}/{module}_test.go',
        'lint_command': 'golangci-lint run',
    },
    'java': {
        'test_runner': 'mvn test',
        'test_dir': 'src/test/java/',
        'file_ext': '.java',
        'cleanup': ['target/', 'build/', '.gradle/'],
        'package_file': 'pom.xml',
        'e2e_test_pattern': '{ID}Test.java',
        'test_map_pattern': 'src/test/java/{package}/{module}Test.java',
        'lint_command': 'mvn checkstyle:check',
    },
}

DRAW_REF_STYLES = """## Enterprise Style Dictionary
> **CRITICAL RULE**: Every style string MUST include `html=1;whiteSpace=wrap;`.

### Node Styles

| Role | Shape | Style String |
|------|-------|-------------|
| **Input/Start** (Green) | Rounded Rect | `rounded=1;whiteSpace=wrap;html=1;fillColor=#2ecc71;strokeColor=#27ae60;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;` |
| **Process/Service** (Blue) | Rounded Rect | `rounded=1;whiteSpace=wrap;html=1;fillColor=#1f497d;strokeColor=#c7c7c7;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;` |
| **Decision/Logic** (Orange) | Rhombus | `rhombus;whiteSpace=wrap;html=1;fillColor=#f39c12;strokeColor=#e67e22;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;` |
| **Output/End** (Red) | Rounded Rect | `rounded=1;whiteSpace=wrap;html=1;fillColor=#e74c3c;strokeColor=#c0392b;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;` |
| **Storage/DB** (Purple) | Cylinder | `shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#8e44ad;strokeColor=#7d3c98;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;` |
| **Container/Group** (Light Gray) | Dashed Rect | `rounded=1;whiteSpace=wrap;html=1;container=1;collapsible=0;fillColor=#f5f5f5;strokeColor=#666666;dashed=1;fontStyle=1;fontFamily=Helvetica;verticalAlign=top;` |
| **External System** (Dark Gray) | Rounded Rect | `rounded=1;whiteSpace=wrap;html=1;fillColor=#636363;strokeColor=#424242;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;` |
| **Queue/MessageBus** (Teal) | Parallelogram | `shape=parallelogram;whiteSpace=wrap;html=1;fillColor=#16a085;strokeColor=#0e6655;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;` |
| **Actor/User** (Blue) | Person | `shape=mxgraph.basic.person;whiteSpace=wrap;html=1;fillColor=#3498db;strokeColor=#2980b9;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;` |
| **Note/Annotation** (Yellow) | Note | `shape=note;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontColor=#333333;fontStyle=0;fontFamily=Helvetica;size=15;` |

### Edge Styles

| Type | Style String |
|------|-------------|
| **Standard** (Sync) | `edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#e67e22;strokeWidth=2;html=1;fontFamily=Helvetica;fontSize=10;` |
| **Async/Return** (Dashed) | `edgeStyle=orthogonalEdgeStyle;dashed=1;rounded=1;strokeColor=#8e44ad;strokeWidth=2;html=1;fontFamily=Helvetica;fontSize=10;` |

> **Edge Labels**: Set the `value` attribute on edge `mxCell` to the protocol name (e.g., `value="REST"`, `value="gRPC"`, `value="Event"`).
"""

DRAW_REF_LAYOUTS = """## Layout Patterns

### Architecture (Top -> Bottom)
- **Layer 0** (y=40): Client / Actor / External
- **Layer 1** (y=200): Gateway / API / Load Balancer
- **Layer 2** (y=360): Service / Business Logic
- **Layer 3** (y=520): Storage / Database / Cache
- **Horizontal spacing**: dx=220 within each layer
- **Node size**: width=160, height=60

### Dataflow (Left -> Right)
- **Zone 0** (x=40): Source / Input
- **Zone 1** (x=300): Processing / Transform
- **Zone 2** (x=560): Output / Sink
- **Vertical spacing**: dy=120 within each zone
- **Node size**: width=160, height=60

### Deployment (Grouped)
- Use **Container** nodes as parent groups (width=400+, height=auto)
- Place child nodes inside containers (set `parent` attribute to Container id)
- **Container spacing**: dx=450 between groups
- **Inner spacing**: dx=40, dy=80 inside container
"""

DRAW_REF_ANTI_BUGS = """## Anti-Bug Rules (Mandatory)
- **Anti-Bug 1**: `mxGeometry` MUST be a child element of `mxCell`, never self-closing `mxCell`.
- **Anti-Bug 2**: Labels with special chars MUST be XML-escaped (e.g., `&lt;br&gt;`, `&amp;`).
- **Anti-Bug 3**: Every `id` MUST be unique across the entire diagram. Use prefixes like `n_`, `e_`, `c_` for nodes, edges, containers.
- **Anti-Bug 4**: Edge `mxCell` MUST have valid `source` and `target` attributes pointing to existing node ids.
- **Anti-Bug 5**: Child nodes inside a Container MUST set `parent="<container_id>"`, not `parent="1"`.
- **Anti-Bug 6**: The root `mxCell` with `id="0"` and layer `mxCell` with `id="1" parent="0"` are mandatory boilerplate. Never omit them.
- **Anti-Bug 7**: Container nodes MUST include `container=1` in their style. Otherwise children won't nest properly.
"""

# --- Main Draw Prompt (STORY-024 R4-R5) ---

DRAW_PROMPT_TEMPLATE = f"""---
description: "Generate Draw.io XML architecture diagrams (supporting multiple diagram types)"
allowed-tools: [Read, Write]
---

# Skill: Draw (v22.0 Enterprise)
- **Usage**: Invoked as `pactkit-draw` skill
- **Agent**: Visual Architect

## Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block before using any tools.

### Step 1: Detect Diagram Type
Classify the user request into one of these types:

| Type | Trigger Keywords | Layout |
|------|-----------------|--------|
| **architecture** | architecture, system, layered, microservice, layers | Top -> Bottom (vertical layers) |
| **dataflow** | dataflow, process, pipeline, ETL, flow | Left -> Right (horizontal) |
| **deployment** | deployment, infra, cloud, k8s, docker, VPC | Grouped (nested containers) |

### Step 2: Identify Components
- Classify each component from user input into a style role (see Style Dictionary below).
- For each pair of components, identify the connection type (sync/async) and protocol label.

### Step 3: Plan Layout
- **Architecture**: Arrange in horizontal layers. Top = Client/User, Middle = Service, Bottom = Data.
- **Dataflow**: Arrange left to right. Source -> Process -> Sink.
- **Deployment**: Use Container nodes to group related services. Nest child nodes inside containers.

{DRAW_REF_STYLES}

{DRAW_REF_LAYOUTS}

{DRAW_REF_ANTI_BUGS}

## Legend (Optional)
Only add a Legend when the user explicitly requests one, or when the diagram uses more than 4 distinct node types. If needed, place it at the bottom-right corner of the diagram to avoid overlapping content nodes.

## Execution Protocol
1. **Classify**: Detect diagram type (architecture / dataflow / deployment).
2. **Component List**: Extract components, assign style roles.
3. **Layout**: Choose the matching layout pattern and compute (x, y) for each node.
4. **Generate XML**: Write the final `.drawio` file using the template below.
5. **MCP Preview (Conditional)**: IF `open_drawio_xml` tool is available (Draw.io MCP), call it with the generated XML content to open the diagram in Draw.io editor for instant visual verification. IF Draw.io MCP is not available, skip this step — the `.drawio` file on disk is the sole output.

## XML Template (Landscape, No Legend)
{M}xml
<mxfile host="Electron" agent="PactKit-v20.0" version="26.2.2">
  <diagram name="Architecture" id="PACTKIT_ARCH">
    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="827" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- Add nodes and edges here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
{M}

## 📝 Few-shot Example (4-Node Architecture with Container and Edge Labels)

Below is a complete example of a simple API architecture diagram:

{M}xml
<mxfile host="Electron" agent="PactKit-v20.0" version="26.2.2">
  <diagram name="Example" id="EXAMPLE_001">
    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="827" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="n_user" value="User" style="shape=mxgraph.basic.person;whiteSpace=wrap;html=1;fillColor=#3498db;strokeColor=#2980b9;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;" vertex="1" parent="1">
          <mxGeometry x="100" y="40" width="80" height="80" as="geometry" />
        </mxCell>
        <mxCell id="c_backend" value="Backend Services" style="rounded=1;whiteSpace=wrap;html=1;container=1;collapsible=0;fillColor=#f5f5f5;strokeColor=#666666;dashed=1;fontStyle=1;fontFamily=Helvetica;verticalAlign=top;" vertex="1" parent="1">
          <mxGeometry x="40" y="200" width="400" height="180" as="geometry" />
        </mxCell>
        <mxCell id="n_api" value="API Gateway" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#2ecc71;strokeColor=#27ae60;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;" vertex="1" parent="c_backend">
          <mxGeometry x="20" y="50" width="160" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n_svc" value="Auth Service" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1f497d;strokeColor=#c7c7c7;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;" vertex="1" parent="c_backend">
          <mxGeometry x="220" y="50" width="160" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n_db" value="PostgreSQL" style="shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#8e44ad;strokeColor=#7d3c98;fontColor=#ffffff;fontStyle=1;fontFamily=Helvetica;" vertex="1" parent="1">
          <mxGeometry x="260" y="460" width="160" height="80" as="geometry" />
        </mxCell>
        <mxCell id="e_user_api" value="HTTPS" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#e67e22;strokeWidth=2;html=1;fontFamily=Helvetica;fontSize=10;" edge="1" source="n_user" target="n_api" parent="1">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e_api_svc" value="gRPC" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#e67e22;strokeWidth=2;html=1;fontFamily=Helvetica;fontSize=10;" edge="1" source="n_api" target="n_svc" parent="1">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e_svc_db" value="SQL" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#e67e22;strokeWidth=2;html=1;fontFamily=Helvetica;fontSize=10;" edge="1" source="n_svc" target="n_db" parent="1">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
{M}

This example demonstrates: Container grouping (`c_backend`), Actor node (`n_user`), edge labels (`HTTPS`, `gRPC`, `SQL`), unique id prefixes, proper parent nesting, and landscape canvas.
"""

# ==============================================================================
# 5. EXPERT MODE CONTENT

SPRINT_PROMPT = """---
description: "Automated PDCA Sprint orchestration via Subagent Team (Slim Team)"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Command: Sprint (v22.0 Slim Team)
- **Usage**: `/project-sprint "$ARGUMENTS"`
- **Agent**: Team Lead (current session)

> **CORE PRINCIPLE**: Thin Orchestrator + File-Driven Context.
> The Lead does ZERO file reading — only Glob for STORY-ID, then dispatch.
> Each subagent reads `docs/specs/`, `commands/*.md`, and `docs/product/sprint_board.md` from disk.
> Do NOT relay context through conversation — pass STORY-ID and file paths via prompt.

## ⚠️ Model Requirement
> **IMPORTANT**: This command requires the **Opus 4.6** model to orchestrate the Subagent Team.
> If the current model is Sonnet 4, use the manual PDCA workflow instead:
> `/project-plan` → `/project-act` → `/project-check` → `/project-done`

## ⚠️ Model Tiering Prerequisite
> For Bedrock environments, ensure the sonnet model is configured:
> ```bash
> export ANTHROPIC_DEFAULT_SONNET_MODEL='claude-sonnet-4'
> ```
> This enables `model: "sonnet"` for cost-efficient subagents (QA, Security, Closer).

## 🧠 Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block.
> **CRITICAL**: Do NOT use the `Read` tool in this phase. Lead must stay thin.
1.  **Analyze**: Parse the requirement from `$ARGUMENTS`.
2.  **STORY-ID**: Determine next available ID by scanning `docs/specs/` using **Glob only** (not Read).
3.  **Strategy**: Plan the 3-stage Slim Team orchestration (Build → Check → Close).

## 🎬 Phase 1: Team Setup
1.  **Create Team**: `TeamCreate("sprint-{STORY_ID}")`.
2.  **Create Tasks**: Use `TaskCreate` for each phase:
    - Task: "Build — Plan + TDD Implementation" (no dependencies)
    - Task: "Check-QA — Spec Verification" (blockedBy: Build)
    - Task: "Check-Security — OWASP Audit" (blockedBy: Build)
    - Task: "Close — Archive & Commit" (blockedBy: Check-QA, Check-Security)

## 🎬 Phase 2: Slim PDCA Execution

### Stage A: Build (Plan + Act merged)
> **WHY MERGED**: The architect who designs the spec has the best codebase understanding.
> Keeping Plan+Act in one agent eliminates 1 context fork and 1 round-trip,
> while preserving continuity — the builder validates spec feasibility during implementation.

1.  **Launch**: `Task(subagent_type="system-architect")`
    - **prompt**:
      ```
      You are the Builder (System Architect + Senior Developer).
      STORY-ID: {STORY_ID}
      Requirement: {$ARGUMENTS}

      Execute TWO phases in sequence:
      1. PLAN: Read `commands/project-plan.md` and execute it. Create `docs/specs/{STORY_ID}.md`.
      2. ACT: Read `commands/project-act.md` and execute it. Implement with TDD. All tests must be GREEN.

      When done, write a summary to `docs/product/reports/{STORY_ID}-build.md` and
      report a single line: "BUILD PASS" or "BUILD FAIL: <reason>"
      ```
2.  **Wait**: For subagent completion.
3.  **Verify**: Confirm `docs/specs/{STORY_ID}.md` was created (Glob, not Read).
4.  **On Failure**: STOP orchestration. Report failure to user. Do NOT proceed.
5.  **Update**: `TaskUpdate(build_task, status=completed)`.

### Stage B: Check (PARALLEL)
> **CRITICAL**: Launch BOTH subagents in a SINGLE message (parallel tool calls).

1.  **Launch QA**: `Task(subagent_type="qa-engineer", model="sonnet")`
    - **prompt**:
      ```
      You are the QA Engineer.
      STORY-ID: {STORY_ID}
      Spec: `docs/specs/{STORY_ID}.md`

      Read `commands/project-check.md` and execute your full playbook.
      When done, write a report to `docs/product/reports/{STORY_ID}-qa.md` and
      report a single line: "QA PASS" or "QA FAIL: <reason>"
      ```
2.  **Launch Security** (same message): `Task(subagent_type="security-auditor", model="sonnet")`
    - **prompt**:
      ```
      You are the Security Auditor.
      STORY-ID: {STORY_ID}
      Spec: `docs/specs/{STORY_ID}.md`

      Audit all code related to {STORY_ID}. Focus on OWASP top 10 vulnerabilities.
      When done, write a report to `docs/product/reports/{STORY_ID}-security.md` and
      report a single line: "SECURITY PASS" or "SECURITY FAIL: <reason>"
      ```
3.  **Wait**: For BOTH subagents to complete.
4.  **On Failure**: If either reports FAIL, STOP. Report to user.
5.  **Update**: `TaskUpdate(check tasks, status=completed)`.

### Stage C: Close
1.  **Launch**: `Task(subagent_type="repo-maintainer", model="sonnet")`
    - **prompt**:
      ```
      You are the Repo Maintainer.
      STORY-ID: {STORY_ID}
      Spec: `docs/specs/{STORY_ID}.md`

      Read `commands/project-done.md` and execute your full playbook.
      Report a single line: "DONE PASS" or "DONE FAIL: <reason>"
      ```
2.  **Wait**: For subagent completion.
3.  **Update**: `TaskUpdate(close_task, status=completed)`.

## 🎬 Phase 3: Cleanup
1.  **Shutdown**: Send `SendMessage(type="shutdown_request")` to all teammates.
2.  **Delete Team**: `TeamDelete` to remove `~/.claude/tasks/sprint-{STORY_ID}/`.
3.  **Report**: Output final summary to user:
    - Spec path
    - Test results
    - Commit hash (if created)
    - Reports: `docs/product/reports/{STORY_ID}-*.md`

## ⚠️ Error Handling
- If ANY stage fails, **STOP immediately**. Do NOT proceed to the next stage.
- Report the failure phase, subagent output, and suggest manual intervention.
- Always run `TeamDelete` in cleanup, even on failure.

## 📋 Subagent Type Reference
| Phase | subagent_type | Model | Playbook |
|-------|--------------|-------|----------|
| Build (Plan+Act) | system-architect | default (Opus) | project-plan.md + project-act.md |
| Check-QA | qa-engineer | sonnet | project-check.md |
| Check-Security | security-auditor | sonnet | (inline OWASP audit) |
| Close | repo-maintainer | sonnet | project-done.md |

## 📊 Token Efficiency (vs v21.0)
| Metric | v21.0 (5 agents) | v22.0 Slim (4 agents) |
|--------|------------------|----------------------|
| Context forks | 5 | 4 |
| Lead context at fork | ~50-95K (growing) | ~15-17K (flat) |
| Duplication overhead | ~370K tokens | ~64K tokens |
| Parallelism | Check only | Check only (same) |
| Cost reduction | Baseline | ~83% overhead + sonnet tiering |
"""

REVIEW_PROMPT = """---
description: "PR Code Review: structured review with SOLID, security, quality checklists"
allowed-tools: [Read, Bash, Grep, Glob]
---

# Skill: Review (v22.0 Deep Code Review)
- **Usage**: Invoked as `pactkit-review` skill
- **Agent**: QA Engineer

> **PRINCIPLE**: Review is a read-only operation; do not modify any code files.

## Severity Levels

| Level | Name | Action |
|-------|------|--------|
| **P0** | Critical | Must block merge — security vulnerability, data loss risk, correctness bug |
| **P1** | High | Should fix before merge — logic error, significant SOLID violation, performance regression |
| **P2** | Medium | Fix in this PR or create follow-up — code smell, maintainability concern |
| **P3** | Low | Optional improvement — style, naming, minor suggestion |

## Phase 0: PR Information Retrieval (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block.
1.  **Parse Input**: `$ARGUMENTS` can be a PR number (e.g. `123`) or a full URL.
2.  **Fetch PR Metadata**: Run `gh pr view $ARGUMENTS --json title,body,author,baseRefName,headRefName,files`.
3.  **Fetch PR Diff**: Run `gh pr diff $ARGUMENTS`.
4.  **Extract STORY-ID**: Extract the `STORY-\\d+` pattern from the PR title or body (if present).

**Edge cases:**
- **No changes**: If `gh pr diff` is empty, inform user and stop.
- **Large diff (>500 lines)**: Summarize by file first, then review in batches by module/feature area.
- **Mixed concerns**: Group findings by logical feature, not just file order.

## Phase 1: Context Loading
1.  **Spec Alignment** (if STORY-ID found):
    - Read `docs/specs/{STORY-ID}.md`
    - Extract Requirements and Acceptance Criteria
    - These become the **review checklist**
2.  **No Spec** (if no STORY-ID):
    - Review based on general best practices only
    - Note: "No associated Spec found. Reviewing against general standards."
3.  **Detect Stack from Diff**: Check changed file extensions:
    - `.tsx`/`.vue`/`.svelte`/`.css`/`.scss` → Also apply `DEV_REF_FRONTEND` (component, a11y, rendering perf)
    - `.py`/`.go`/`.java`/`.rs` → Also apply `DEV_REF_BACKEND` (API design, data layer, observability)
    - Mixed → Apply both

## Phase 2: SOLID + Architecture Analysis
Apply the SOLID checklist to all changed files:

- **SRP**: Does any changed file own unrelated concerns?
- **OCP**: Are there growing switch/if blocks that should use extension points?
- **LSP**: Do subclasses break parent expectations or require type checks?
- **ISP**: Are interfaces too wide with unused methods?
- **DIP**: Is high-level logic coupled to concrete implementations?

Also check for common code smells: long methods, feature envy, data clumps, primitive obsession, shotgun surgery, dead code, speculative generality, magic numbers.

When proposing refactors, explain *why* it improves cohesion/coupling. For non-trivial refactors, propose an incremental plan.

## Phase 3: Removal Candidates
Identify code that is unused, redundant, or feature-flagged off:

- Distinguish **safe delete now** vs **defer with plan**
- For each candidate, provide: location, rationale, evidence, impact, deletion steps
- Provide a follow-up plan with concrete steps and checkpoints

## Phase 4: Security & Reliability Scan (OWASP+)
Apply the Security checklist to all changed files:

- **Input/Output**: XSS, injection (SQL/NoSQL/command), SSRF, path traversal
- **AuthN/AuthZ**: Missing auth guards, tenant checks, IDOR
- **JWT & Tokens**: Algorithm confusion, weak secrets, missing expiry validation
- **Secrets & PII**: API keys in code/logs, excessive PII logging
- **Supply Chain**: Unpinned deps, dependency confusion, known CVEs
- **Runtime**: Unbounded loops, missing timeouts, resource exhaustion, ReDoS
- **Race Conditions**: TOCTOU, missing locks, concurrent read-modify-write
- **Crypto**: Weak algorithms, hardcoded IVs, encryption without authentication
- **Data Integrity**: Missing transactions, partial writes, missing idempotency

Call out both **exploitability** and **impact** for each finding.

## Phase 5: Code Quality Scan
Apply the Code Quality checklist to all changed files:

- **Error Handling**: Swallowed exceptions, overly broad catch, missing error handling, async errors
- **Performance**: N+1 queries, CPU hotspots in hot paths, missing cache, unbounded memory
- **Boundary Conditions**: Null handling, empty collections, numeric boundaries, off-by-one, unicode
- **Logic Correctness**: Does the change match stated intent? Are edge cases handled?

Flag issues that may cause silent failures or production incidents.

## Phase 6: Review Report
Output the following structured report:

```
## Code Review: PR $ARGUMENTS

### Summary
- **PR**: [title] by [author]
- **Branch**: [head] -> [base]
- **Files reviewed**: X files, Y lines changed
- **Spec**: [STORY-ID or "None"]
- **Overall assessment**: [APPROVE / REQUEST_CHANGES / COMMENT]

---

### P0 - Critical
(none or list with `[file:line]` format)

### P1 - High
- **[file:line]** Brief title
  - Description of issue
  - Suggested fix

### P2 - Medium
...

### P3 - Low
...

---

### Removal/Iteration Plan
(if applicable — use safe-delete vs defer format)

### Spec Alignment
- [x] R1: ... (Implemented)
- [ ] R2: ... (Missing)

### Verdict
**APPROVE** / **REQUEST_CHANGES**
[One-line justification]
```

**Clean review**: If no issues found, explicitly state what was checked and any areas not covered.

## Phase 7: Next Steps Confirmation

After presenting findings, ask user how to proceed:

```
---

## Next Steps

I found X issues (P0: _, P1: _, P2: _, P3: _).

**How would you like to proceed?**

1. **Fix all** — I'll implement all suggested fixes
2. **Fix P0/P1 only** — Address critical and high priority issues
3. **Fix specific items** — Tell me which issues to fix
4. **No changes** — Review complete, no implementation needed

Please choose an option or provide specific instructions.
```

**IMPORTANT**: Do NOT implement any changes until user explicitly confirms. This is a review-first workflow.

## Constraints
- This command is **read-only**. Do NOT modify any files.
- If `gh` CLI is not authenticated, report the error and suggest `gh auth login`.
- If the PR number is invalid, report clearly and stop.
"""

# ==============================================================================
# 5d. HOTFIX FAST TRACK PROMPT (STORY-017)
# ==============================================================================
HOTFIX_PROMPT = """---
description: "Hotfix fast track: lightweight fix path that bypasses PDCA"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Command: Hotfix (v22.0 Traceable Fast Track)
- **Usage**: `/project-hotfix "$ARGUMENTS"`
- **Agent**: Senior Developer

> **PRINCIPLE**: This command is a lightweight fast-fix channel with traceability.
> Lightweight Spec + Board entry are auto-created. No TDD workflow required.
> Suitable for typos, configuration changes, style adjustments, obvious bugs, and other minor fixes.

## ⚠️ Scope of Application
- ✅ Fix typos / spelling errors
- ✅ Modify configuration files
- ✅ Adjust style / formatting
- ✅ Fix obvious small bugs (single file, clear logic)
- ❌ New feature development → use `/project-plan` + `/project-act`
- ❌ Multi-module refactoring → use `/project-plan` + `/project-act`

## 🧠 Phase 0: Locate & Register (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block.
1.  **Parse**: Understand what needs to be fixed from `$ARGUMENTS`.
2.  **Locate**: Use `Grep` or `Glob` to quickly locate the target file and code line.
3.  **Assess**: Confirm this is a minor fix (suitable for Hotfix), not a change requiring full PDCA.
    - If the assessment reveals a complex change, **proactively suggest the user switch to** `/project-plan`.
4.  **Assign HOTFIX- ID**: Scan `docs/specs/` for existing `HOTFIX-*.md` files, determine the next available number (e.g., `HOTFIX-001`, `HOTFIX-002`).
5.  **Create Spec**: Create a lightweight Spec at `docs/specs/HOTFIX-{NNN}.md` with:
    - Title, Background (one sentence), Target file/line, and what was fixed.
6.  **Add Board Entry**: Add the hotfix to the Board:
    - `python3 ~/.claude/skills/pactkit-board/scripts/board.py add_story HOTFIX-{NNN} "Short title" "Fix description"`

## 🔧 Phase 1: Fix
1.  **Fix**: Use `Edit` or `Write` to directly fix the target code.
2.  **Scope**: Keep the modification scope as small as possible — only change what must be changed, no extra optimization or refactoring.
3.  **No Side Effects**: Ensure the modification does not introduce new dependencies or change interface signatures.

## ✅ Phase 2: Verify
1.  **Run Tests (Incremental)**: Run only tests related to changed modules to confirm no existing functionality is broken.
    - **Identify changed modules**: `git diff --name-only HEAD` to list modified source files.
    - **Map to related tests**: Use `test_map_pattern` in `LANG_PROFILES` to find corresponding test files.
    - **Run incremental**: Execute only the mapped test files (e.g., `pytest tests/unit/test_foo.py -q`).
    - **Fallback**: If no mapping can be determined, fall back to the full test suite (`pytest tests/ -q`).
2.  **On Failure**: If tests fail:
    - Output the failing test name and error message
    - **Do not auto-rollback** — let the user decide whether to continue
    - Suggestion: check whether the fix is correct, or switch to `/project-act` for the full workflow

## 📦 Phase 3: Commit
1.  **Conventional Commit**: Generate a standardized commit message:
    - Format: `fix(scope): short description for HOTFIX-{NNN}`
    - Infer scope from the modified file path (e.g. `config`, `auth`, `ui`)
2.  **Confirm**: **Must ask the user for confirmation** before executing `git commit`.
    - Output: "Suggested commit: `fix(scope): description`. Confirm commit?"
3.  **Execute**: After user confirmation, execute git add + git commit.
4.  **Update Board**: Mark the hotfix task as done on the Board.

## 🚫 What This Command Does NOT Do
- Does not require writing tests before code (no TDD)
- Does not run `visualize` to update architecture graphs
"""

# ==============================================================================
# 5e. PRODUCT DESIGN PROMPT (STORY-035)
# ==============================================================================
DESIGN_PROMPT = """---
description: "Product design for greenfield projects: PRD generation, story decomposition, board setup"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Command: Design (v22.0 Product Designer)
- **Usage**: `/project-design "$ARGUMENTS"`
- **Agent**: Product Designer

> **PURPOSE**: Transform a product vision into a comprehensive PRD, decompose it into
> implementable Specs, and populate the Sprint Board — bridging the gap between
> "I have an idea" and "I have a prioritized backlog ready for `/project-sprint`."

## 🧠 Phase 0: The Thinking Process (Mandatory)
> **INSTRUCTION**: Output a `<thinking>` block.
1.  **Parse Vision**: What is the core product idea? What problem does it solve?
2.  **Identify Domain**: E-commerce, SaaS, internal tool, mobile app, CLI, etc.
3.  **Detect Stack Hints**: Does the user mention specific technologies? (React, Python, Go, etc.)
4.  **Scope Assessment**: Is this a full product or a module within an existing system?

## 🎬 Phase 1: PRD Generation
> **Goal**: Create `docs/product/prd.md` — the single source of truth for the product.

1.  **Scaffold**: Run `python3 ~/.claude/skills/pactkit-scaffold/scripts/scaffold.py create_prd "{ProductName}"`.
2.  **Fill Sections** — Complete each section in the PRD:

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

### 1.6 API Design
- List endpoints: `METHOD /path → description`
- Define core data models (entity fields and relationships)
- Specify auth strategy (JWT, session, OAuth, API key)

### 1.7 Non-Functional Requirements
- **Performance**: Response time targets, throughput expectations
- **Security**: Auth model, data encryption, OWASP baseline
- **Scalability**: Expected user load, horizontal vs vertical scaling

### 1.8 Success Metrics
Define measurable KPIs per Epic:

| Epic | Metric | Target | How to Measure |
|------|--------|--------|----------------|
| ...  | ...    | ...    | ...            |

### 1.9 MVP Roadmap (Three-Horizon Framework)
Assign each Story to a horizon:

- **Now (Sprint 1-3)**: Core MVP — must-have features to validate the product
- **Next (Sprint 4-8)**: Differentiation — features that create competitive advantage
- **Later (Sprint 9+)**: Scale — platform expansion, optimization, advanced features

3.  **Write**: Save the completed PRD to `docs/product/prd.md`.

## 🎬 Phase 2: Architecture
1.  **Update HLD**: Write the architecture Mermaid diagram from Section 1.4 into `docs/architecture/graphs/system_design.mmd`.
2.  **Visualize** (if existing code): Run `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize`.

## 🎬 Phase 3: Story Decomposition
> **Goal**: Convert PRD Feature Breakdown into individual Specs.

1.  **Determine STORY IDs**: Scan `docs/specs/` to find the next available STORY-NNN number.
2.  **Sort**: Order stories by horizon (Now → Next → Later), then by Priority Score (descending).
3.  **For each Story**:
    - Run `python3 ~/.claude/skills/pactkit-scaffold/scripts/scaffold.py create_spec "STORY-{NNN}" "{title}"`.
    - Fill in the Spec:
      - `## Requirements` — using RFC 2119 keywords (MUST/SHOULD/MAY)
      - `## Acceptance Criteria` — Given/When/Then scenarios
      - Add Priority Score to the spec header: `- **Priority**: {score} (Impact {I} / Effort {E})`
4.  **Dependency Graph**: Add a Mermaid dependency graph at the end of the PRD showing Story execution order and critical path.

## 🎬 Phase 4: Board Setup
1.  **Add Stories**: For each Story (ordered by horizon → priority):
    - Run `python3 ~/.claude/skills/pactkit-board/scripts/board.py add_story "STORY-{NNN}" "{title}" "{task list}"`.
2.  **Verify**: Read `docs/product/sprint_board.md` to confirm all stories are listed.

## 🎬 Phase 5: Handover
1.  **Summary Table**: Output a table of all created artifacts:

| Artifact | Path | Count |
|----------|------|-------|
| PRD | `docs/product/prd.md` | 1 |
| Specs | `docs/specs/STORY-{NNN}.md` | N |
| Board Entries | `docs/product/sprint_board.md` | N |
| Architecture | `docs/architecture/graphs/system_design.mmd` | 1 |

2.  **Story Overview**: List stories grouped by horizon (Now/Next/Later) with priority scores.
3.  **Handover**: "PRD created. {N} stories ready for `/project-sprint`."

## ⚠️ What This Command Does NOT Do
- Does NOT write implementation code — only PRD, Specs, and architecture design
- Does NOT include market sizing (TAM/SAM/SOM) or pricing strategy — AI cannot produce reliable market data
- Does NOT generate UI wireframe images — page design is text-based component hierarchy
- Does NOT enforce a specific tech stack — recommendations only, not mandates
- Does NOT depend on WebSearch — works entirely from user input
"""
