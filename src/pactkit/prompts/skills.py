from pactkit.skills import load_script

# ==============================================================================
# SKILL SOURCE CODE (loaded from pactkit/skills/)
# ==============================================================================

VISUALIZE_SOURCE = load_script("visualize.py")
BOARD_SOURCE = load_script("board.py")
SCAFFOLD_SOURCE = load_script("scaffold.py")
REPORT_SOURCE = load_script("report.py")

# --- Backward-compatible combined source (for old tests) ---
TOOLS_SOURCE = VISUALIZE_SOURCE + "\n" + BOARD_SOURCE + "\n" + SCAFFOLD_SOURCE
TOOLS_CONTENT = TOOLS_SOURCE.split("\n")

# ==============================================================================
# SKILL.md TEMPLATES (Frontmatter + Documentation)
# ==============================================================================
SKILL_VISUALIZE_MD = """---
name: pactkit-visualize
description: "Generate project code dependency graph (Mermaid), supporting file-level, class-level, function-level, and module-level analysis"
model: haiku
---

# PactKit Visualize

Generate project code relationship graphs (Mermaid format), supporting four analysis modes.

> **Script location**: Use the base directory from the skill invocation header to resolve script paths.

## Prerequisites
- The project must have Python source files (`.py`) to generate meaningful graphs
- The `docs/architecture/graphs/` directory is automatically created by `init_arch`

## Command Reference

### visualize -- Generate code dependency graph
```
{VISUALIZE_CMD} visualize [--mode file|class|call|module] [--entry <func>] [--focus <module>]
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--mode file` | File-level dependency graph (inter-module import relationships) | Default |
| `--mode class` | Class diagram (including inheritance) | - |
| `--mode call` | Function-level call graph | - |
| `--mode module` | Module-level dependency graph with weighted cross-module edges | - |
| `--entry <func>` | BFS transitive chain tracing from specified function (requires `--mode call`) | - |
| `--focus <module>` | Scope scan to a specific module directory. **MUST** be an exact module name from the project (e.g., `pactkit`, `app`), not a keyword or concept. Run without `--focus` first to see available modules. | - |

### init_arch -- Initialize architecture directory
```
{VISUALIZE_CMD} init_arch
```
- Creates `docs/architecture/graphs/` and `docs/architecture/governance/`
- Generates placeholder file `system_design.mmd`

### list_rules -- List governance rules
```
{VISUALIZE_CMD} list_rules
```
- Outputs the list of rule files under `docs/architecture/governance/`

## Output Files

| Mode | Output Path | Mermaid Type |
|------|-------------|-------------|
| `--mode file` | `docs/architecture/graphs/code_graph.mmd` | graph TD |
| `--mode class` | `docs/architecture/graphs/class_graph.mmd` | classDiagram |
| `--mode call` | `docs/architecture/graphs/call_graph.mmd` | graph TD |
| `--mode module` | `docs/architecture/graphs/module_graph.mmd` | graph TD |
| `--focus` (file) | `docs/architecture/graphs/focus_file_graph.mmd` | graph TD |
| `--focus` (class) | `docs/architecture/graphs/focus_class_graph.mmd` | classDiagram |
| `--focus` (call) | `docs/architecture/graphs/focus_call_graph.mmd` | graph TD |

## Usage Scenarios
- `project-plan`, `project-act`, and `pactkit-trace` use `pactkit query --json --explain` for analysis.
- Use `visualize` only to explicitly regenerate derived Mermaid projections.
- `pactkit-doctor` checks graph-provider health and derived graph status.

## Graph Query Protocol

> **MUST NOT `Read` a full `.mmd` graph file** — graph files are large (50K–120K, 1000–2000+ lines). Full reads waste tokens before any work begins.

### Unified Query Router

```bash
pactkit query --callers atomic_write --json --explain
pactkit query --callees deploy --json --explain
pactkit query --chain atomic_write --json --explain
pactkit query --chain deploy --down --json --explain
pactkit query --explore deployer --json --explain
pactkit query --impact deploy --json --explain
```

The router owns Codegraph health, bounded sync, and provider selection. Configured Codegraph fails closed. Only an explicit `--allow-fallback` may select `builtin_graph` and then `text_search`; a healthy empty result never triggers fallback.
"""

SKILL_BOARD_MD = """---
name: pactkit-board
description: "Sprint Board atomic operations: add Story, update Task, archive completed Stories"
model: haiku
---

# PactKit Board

Atomic operations tool for sharded Story facts (`docs/product/stories/{ITEM_ID}.yaml`). `docs/product/sprint_board.md` is an optional read-only projection.

> **Script location**: Use the base directory from the skill invocation header to resolve script paths.

## Prerequisites
- PactKit Core must provide the `StoryRepository` schema used by every adapter.
- Commands modify one Story record only. Run `render` explicitly to update the optional projection.

## Command Reference

### add_story -- Add a work item (Story, Hotfix, or Bug)
```
{BOARD_CMD} add_story ITEM-ID "Title" "Task A|Task B"
```
- `ITEM-ID`: Work item identifier, e.g. `STORY-001`, `HOTFIX-001`, `BUG-001`
- `Title`: Item title
- `Task A|Task B`: Task list, use `|` as separator for multiple tasks
- Output: `✅ Story ITEM-ID added` or `❌` error message

### update_task -- Update Task status
```
{BOARD_CMD} update_task ITEM-ID "Task Name"
```
- `Task Name`: Must be an exact match with the task name in the Board
- Changes only the matching task in the Story YAML record.
- Output: `✅ Task updated` or `❌ Task not found`

### archive -- Archive completed Stories
```
{BOARD_CMD} archive
```
- Marks completed Story records as `archived`; no shared archive file is appended.

### list_stories -- View current Stories
```
{BOARD_CMD} list_stories
```

### render -- Explicitly generate/check Board projection
```
{BOARD_CMD} render
{BOARD_CMD} render --check
```

### snapshot -- Architecture snapshot
```
{BOARD_CMD} snapshot "v1.0.0"
```
- Saves current architecture graphs to `docs/architecture/snapshots/{version}_*.mmd`

### fix_board -- Relocate misplaced stories to correct sections
```
{BOARD_CMD} fix_board
```
- Rebuilds the deterministic projection from Story records; it never parses the projection as facts.

## Usage Scenarios
- `/project-plan`: Use `add_story` to create a Story
- `/project-act`: Use `update_task` to mark completed tasks
- `/project-done`: Use `archive` to archive completed Stories
- `pactkit-release` skill: Use `snapshot` to archive architecture graphs during release
- `pactkit-doctor` skill: Use `fix_board` to repair misplaced stories
"""

SKILL_SCAFFOLD_MD = """---
name: pactkit-scaffold
description: "File scaffolding: create Spec, test files, E2E tests, Git branches, Skills"
model: haiku
---

# PactKit Scaffold

Project file scaffolding tool for quickly creating standardized project files.

> **Script location**: Use the base directory from the skill invocation header to resolve script paths.

## Prerequisites
- `docs/specs/` directory must exist (required by `create_spec`)
- `tests/unit/` and `tests/e2e/` directories must exist (required by test scaffolding)
- Git repository must be initialized (required by `git_start`)

## Command Reference

### create_spec -- Create a Spec file
```
{SCAFFOLD_CMD} create_spec ITEM-ID "Title"
```
- `ITEM-ID`: Work item identifier, e.g. `STORY-001`, `HOTFIX-001`, `BUG-001`
- `Title`: Spec title
- Output: `docs/specs/{ITEM-ID}.md` (with template structure)

### create_test_file -- Create a unit test
```
{SCAFFOLD_CMD} create_test_file src/module.py
```
- Automatically generates the corresponding test file based on the source file path
- Output: `tests/unit/test_module.py`

### create_e2e_test -- Create an E2E test
```
{SCAFFOLD_CMD} create_e2e_test ITEM-ID "scenario_name"
```
- Output: `tests/e2e/test_{ITEM-ID}_{scenario}.py`

### git_start -- Create a Git branch
```
{SCAFFOLD_CMD} git_start ITEM-ID
```
- Branch prefix is inferred from the item type:
  - `STORY-*` → `feature/STORY-*`
  - `HOTFIX-*` → `fix/HOTFIX-*`
  - `BUG-*` → `fix/BUG-*`

### create_skill -- Create a Skill directory scaffold
```
{SCAFFOLD_CMD} create_skill skill-name "Description of the skill"
```
- `skill-name`: Skill identifier (must start with lowercase letter: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`)
- `Description`: Brief description for SKILL.md frontmatter
- Output: `{SKILLS_ROOT}/{skill-name}/` with `SKILL.md`, `scripts/{clean_name}.py`, `references/.gitkeep`
- Refuses to overwrite if the skill directory already exists

### create_board -- Initialize Story Facts
```
{SCAFFOLD_CMD} create_board
```
- Creates `docs/product/stories/`; use `pactkit board render` only for an explicit projection
- Output: Standard board with `## 📋 Backlog`, `## 🔄 In Progress`, `## ✅ Done` sections
- Refuses to overwrite if the board already exists

## Usage Scenarios
- `/project-init`: Use `create_board` to initialize Story facts (Phase 4)
- `/project-plan`: Use `create_spec` to create a Spec template
- `/project-act`: Use `create_test_file` to create test scaffolding
- `/project-check`: Use `create_e2e_test` to create E2E tests
- Ad-hoc: Use `create_skill` to scaffold a new reusable skill
"""

# ==============================================================================
# PROMPT-ONLY SKILL TEMPLATES (v1.3.0 — STORY-011)
# These skills have no executable script; they provide instruction context
# that is embedded into PDCA commands.
# ==============================================================================

SKILL_TRACE_MD = """---
name: pactkit-trace
description: "Deep code tracing and execution flow analysis"
model: sonnet
---

## Provider Routing (MUST)
Start every callers, callees, chain, explore or impact trace with `pactkit query ... --json --explain`. When `graph_provider: codegraph` is configured, Codegraph is mandatory and failures are closed by default. Never select Mermaid or grep yourself; only use `--allow-fallback` when the caller explicitly authorizes degradation, and retain the provider decision as evidence. A healthy empty result is `valid_empty`, not a fallback signal.

# PactKit Trace

Deep code analysis and execution path tracing via static analysis.

## When Invoked
- **Plan Phase 1** (Archaeology): Trace existing logic before designing changes.
- **Act Phase 1** (Precision Targeting): Confirm call sites before touching code.

## Protocol

### 1. Feature Discovery
- Use `pactkit query --explore <target> --json --explain` to locate entry points.
- Map core files involved — don't read everything yet.

### 2. Call Graph Analysis
- Run `pactkit query --chain <function_name> --json --explain` to obtain call chains.
- Query callers/callees through the same router; never select Codegraph, Mermaid, SQLite, or text search directly.

### 3. Deep Tracing
- Follow call chain file by file, recording data transformations.
- Note how data structures change (e.g., `dict` -> `UserObj` -> `JSON`).

#### Layered Output: Interface Summary vs Full Implementation

| Module Role | Output Level | How |
|-------------|-------------|-----|
| Target (to be modified) | Full implementation | `Read <file>` |
| Related (dependency, not modified) | Interface summary | `pactkit interface-summary <file>` |

For related (non-target) modules, run `pactkit interface-summary <file>` instead of reading full source. This CLI command uses AST parsing to output only signatures + types + docstrings — function bodies are excluded by code, not by prompt instruction.

If `pactkit` is not on `$PATH`, use `python3 -m pactkit interface-summary <file>`.

### 4. Visual Synthesis
Output a **Mermaid Sequence Diagram** to visualize the flow.

### 5. Topology-Aware Trace (Conditional)
If `detect_topology(root)` returns topologies beyond PDCA/Service:

**Frontend API Topology** (if `api_call` detected):
- Run `api_convention_summary(root)` to get path prefixes, fetch function names, total call count.
- Include conventions in output so downstream code uses the correct API path prefix (e.g., `/api/v1/`) and fetch wrapper (e.g., `apiFetch`).
- Flag any dynamic paths (`[dynamic]` markers) that may need special handling.

**Agent Topology** (if `agent` detected):
- AgentParser extracts orchestration from: LangGraph `StateGraph` (stdlib ast), YAML agent definitions, MCP server configs.
- Include agent nodes and `orchestrates` edges in the report.
- Flag multi-strategy merge results — agents may appear in multiple sources but are deduplicated.

### 6. Archaeologist Report
- **Patterns**: Design Patterns used.
- **Debt**: Hardcoded values, complex logic, lack of tests.
- **Key Files**: Top 3 files critical to this feature.
- **API Conventions** (if frontend): Path prefixes, fetch functions, call count.
- **Agent Flow** (if agents): Orchestration graph, delegation chains.
"""

SKILL_DRAW_MD = """---
name: pactkit-draw
description: "Generate Draw.io XML architecture diagrams"
model: haiku
---

# PactKit Draw

Generate system architecture diagrams using Draw.io XML.

## Enterprise Style Dictionary

Copy these style strings exactly — do NOT improvise styles:

| Role | Style String |
|------|-------------|
| **Input** | `rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;` |
| **Process** | `rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;` |
| **Decision** | `rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;` |
| **Output** | `rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;` |
| **Storage** | `shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#e1d5e7;strokeColor=#9673a6;` |
| **Container** | `swimlane;whiteSpace=wrap;html=1;container=1;collapsible=0;recursiveResize=0;fillColor=#f5f5f5;strokeColor=#666666;` |
| **External** | `rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#ffe6cc;strokeColor=#d79b00;` |
| **Edge** | `edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;` |

## XML Template

```xml
<mxfile host="app.diagrams.net" type="device">
  <diagram name="Page-1" id="diag_1">
    <mxGraphModel dx="1000" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- NODES HERE: id="n_1", id="n_2", ... -->
        <!-- EDGES HERE: id="e_1", id="e_2", ... -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## Node Template

```xml
<mxCell id="n_1" value="Label" style="STYLE_STRING" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
</mxCell>
```

## Edge Template

```xml
<mxCell id="e_1" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;" edge="1" parent="1" source="n_1" target="n_2">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

## Protocol

1. **Detect Type**: architecture (top→bottom), dataflow (left→right), deployment (grouped)
2. **List Components**: Name each, assign Role from style dictionary
3. **Layout**: Place nodes on grid (x/y multiples of 20), connect with edges
4. **Write File**: Output complete XML to `.drawio` file

## Anti-Bug Rules

- Every style MUST end with `html=1;` (already in dictionary)
- Every `id` MUST be unique: `n_` prefix for nodes, `e_` for edges, `c_` for containers
- Edge `source` and `target` MUST reference existing node IDs
- Container children: set `parent="c_1"` (container ID), not `parent="1"`

## MCP Mode

IF `open_drawio_xml` tool available:
1. Write `.drawio` file
2. Call `open_drawio_xml` with XML content for instant preview
3. Optionally call `open_drawio_mermaid` to open existing `.mmd` files in Draw.io

IF MCP tools NOT available:
- Fallback to file write only (no editor preview)
"""

SKILL_STATUS_MD = """---
name: pactkit-status
description: "Project state overview for cold-start orientation"
model: haiku
---

# PactKit Status

Read-only project state report. Provides sprint board summary, git state, and health indicators.

## When Invoked
- **Init Phase 6** (Session Context): Bootstrap initial context.
- **Cold-start detection**: Auto-invoked when session needs orientation.

## Protocol

### 1. Gather Data
- Check if `docs/product/stories/` exists; accept legacy `docs/product/sprint_board.md` only with a migration warning.
- If yes: extract story counts by section (Backlog / In Progress / Done).
- Count Specs in `docs/specs/*.md` vs total board stories.
- Check architecture graph freshness.

### 2. Git State
- Current branch, uncommitted changes, active feature branches.

### 3. Output Report
```
## Project Status Report
### Sprint Board
- Backlog: {N} stories
- In Progress: {N} stories
- Done: {N} stories
### Git State
- Branch: {current}
- Uncommitted: {Y/N}
### Health Indicators
- Architecture graphs: {fresh/stale/missing}
- Specs coverage: {N/N}
### Recommended Next Action
{Decision tree}
```

> **CONSTRAINT**: This skill is read-only. It does not modify any files.
"""

SKILL_DOCTOR_MD = """---
name: pactkit-doctor
description: "Diagnose project health status"
model: haiku
---

# PactKit Doctor

Diagnostic tool for project health — config drift, missing files, stale graphs, orphaned specs.

## When Invoked
- **Init** (auto-check): Verify project structure after initialization.
- Standalone diagnostic when project health is in question.

## Severity Levels
| Level | Meaning |
|-------|---------|
| INFO | Informational, no action required |
| WARN | Potential issue, should be addressed |
| ERROR | Critical mismatch, must be fixed |

## Protocol

### 1. Run Deterministic Checks
Run `pactkit doctor` to perform automated diagnostics:
- **Orphaned/Missing Specs**: Cross-references `docs/specs/` vs board + archive.
- **Config Drift**: Compares `pactkit.yaml` items vs deployed files.
- **Stale Graphs**: Checks `docs/architecture/graphs/*.mmd` mtimes vs source files.

### 2. Structural Health (Manual)
- Run `visualize` to check architecture graph generation.
- Run `visualize --mode class` for class diagram verification.
- Check `docs/test_cases/` existence.

### 3. Infrastructure & Data
- Verify `pactkit.yaml` exists (at `{PACTKIT_YAML}`) and is valid.
- Check if `tests/e2e/` is empty.

### 4. Report
Output a structured health report grouped by category:

| Category | Check Item | Severity | Description |
|----------|------------|:--------:|-------------|
| Architecture | Graph Freshness | INFO/WARN | Stale if > 7 days |
| Specs | Orphaned Specs | INFO | Specs without board entries |
| Specs | Missing Specs | WARN | Board stories without specs |
| Config | Drift Detection | ERROR | pactkit.yaml vs deployed |
| Tests | Test Suite | INFO/WARN | Test runner status |

End with overall status: "Health: OK" (no WARN/ERROR) or "Health: NEEDS ATTENTION" (WARN/ERROR found).
"""

SKILL_GARDEN_MD = """---
name: pactkit-garden
description: "Codebase quality patrol — detect dead code, stale docs, pattern duplication"
model: sonnet
---

# PactKit Garden

Codebase entropy detection — scans for dead code, stale documentation, and pattern duplication.

## When Invoked
- Periodically (weekly) to prevent codebase entropy accumulation.
- Before release to ensure cleanup.
- As part of Sprint QA flow.

## Protocol

### 1. Run Garden Scan
Run `pactkit garden` to perform automated quality checks:
- **Dead Imports**: Unused Python imports (F401-equivalent).
- **Empty Except**: Bare `except: pass` blocks.
- **Stale Docs**: Done specs referencing deleted files, orphaned test cases, stale context.md.
- **Duplicate Functions**: Same function signature in multiple modules.
- **Stale Canonical Copies**: Inline copies that diverged from their canonical source.

### 2. Interpret Results
- Exit 0: No findings — codebase is clean.
- Exit 1: Findings detected — review and address.

### 3. Options
- `pactkit garden --json` — machine-readable output for CI integration.
- `pactkit garden --scope <path>` — scan specific directory only.
"""

SKILL_REVIEW_MD = """---
name: pactkit-review
description: "PR Code Review with structured SOLID, security, and quality checklists"
model: sonnet
---

# PactKit Review

Structured PR code review with severity-ranked findings.

## When Invoked
- **Check Phase 4** (PR variant): When `/project-check` is given a PR number/URL.
- **Sprint Stage B**: As part of automated QA in Sprint orchestration.

## Severity Levels
| Level | Name | Action |
|-------|------|--------|
| **P0** | Critical | Must block merge |
| **P1** | High | Should fix before merge |
| **P2** | Medium | Fix in PR or follow-up |
| **P3** | Low | Optional improvement |

## Protocol

### 1. PR Information
- Fetch PR metadata: `gh pr view $ARG --json title,body,author,baseRefName,headRefName,files`
- Fetch PR diff: `gh pr diff $ARG`
- Extract STORY-ID from title/body if present.

### 2. Review Checklists
- **SOLID**: SRP, OCP, LSP, ISP, DIP analysis on changed files.
- **Security**: OWASP baseline (injection, auth, secrets, XSS, SSRF).
- **Quality**: Error handling, performance, boundary conditions, logic correctness.

### 3. Report
```
## Code Review: PR $ARG
**Result**: APPROVE / REQUEST_CHANGES
### Issues
- [P0] [file:line] Description
- [P1] [file:line] Description
### Spec Alignment
- [x] R1: Implemented
- [ ] R2: Missing
```

> **CONSTRAINT**: This skill is read-only. Do not modify code files.
"""

SKILL_ANALYZE_MD = """---
name: pactkit-analyze
description: "Cross-artifact consistency check: Spec ↔ Board ↔ Test Cases"
model: sonnet
---
# Skill: pactkit-analyze

Run a consistency check between Spec, Sprint Board, and Test Cases for a given Story.

## Usage
```
/pactkit-analyze STORY-XXX
```

## What It Checks
1. **Spec ↔ Board**: Every Requirement (`R{N}`) has a matching Board Task, and every Task traces to a Requirement.
2. **Spec AC ↔ Test Case**: Every Acceptance Criteria item has a corresponding Scenario in the Test Case file.

## Output
Prints an alignment matrix and coverage report. Non-blocking — advisory only.
"""

SKILL_REPORT_MD = """---
name: pactkit-report
description: "Interactive HTML dashboard from Mermaid .mmd architecture graphs"
model: haiku
---

# PactKit Report

Generate interactive D3 force-directed HTML dashboards from Mermaid `.mmd` graph files.

> **Script location**: Use the base directory from the skill invocation header to resolve script paths.

## Prerequisites
- Architecture graphs must exist in `docs/architecture/graphs/*.mmd` (generated by `visualize`)

## Command Reference

### generate -- Generate HTML report from .mmd
```
{REPORT_CMD} generate --input <file.mmd> [--output <file.html>] [--overlay <overlay.json>]
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--input` | Input `.mmd` file path | Required (unless `--all`) |
| `--output` | Output `.html` file path | Same name as input with `.html` |
| `--all` | Convert all `.mmd` files in `docs/architecture/graphs/` | - |
| `--overlay` | Overlay JSON with complexity/blast_radius/layers data | - |

## Supported Graph Types

| Type | Auto-detected From | Visualization |
|------|-------------------|---------------|
| File dependency | `code_graph.mmd` | Force-directed node graph |
| Class diagram | `class_graph.mmd` | Inheritance hierarchy |
| Call graph | `call_graph.mmd` | Function call chains |
| Module graph | `module_graph.mmd` | Cross-module dependencies |

## Output
- Single self-contained HTML file with embedded D3.js
- Interactive: zoom, pan, hover tooltips, click-to-highlight
- Overlay mode: nodes colored by complexity/blast radius

## Usage Scenarios
- `/project-done`: Generate HTML reports for architecture review.
- Sprint review: `generate --all` to create dashboard of entire codebase.
- CI integration: Generate reports as build artifacts.
- Frontend dashboard: Call `/pactkit-report` via headless mode for on-demand visualization.
"""

SKILL_AUDIT_MD = """---
name: pactkit-audit
description: "H1-H7 AI Readiness Assessment — harness audit scoring and hotspot analysis"
model: sonnet
---

# PactKit Audit

H1-H7 AI Coding Harness readiness assessment. Scans project structure against a 7-layer model, produces a Harness Score (0-100), and identifies code hotspots.

## When Invoked
- **Done Phase 8** (Harness Audit Refresh): Auto-invoked via `pactkit audit --append`.
- **Standalone**: Ad-hoc project health assessment.
- **Headless / Frontend integration**: Called as `/pactkit-audit` via Claude Code headless mode.

## The 7 Layers

| Layer | Name | What It Checks |
|-------|------|----------------|
| H1 | Prompt Engineering | CLAUDE.md, rules, agents, commands |
| H2 | Context Engineering | Specs, test cases, architecture graphs |
| H3 | Process Governance | Sprint board, PDCA workflow artifacts |
| H4 | Tool Governance | Skills, CLI tools, MCP integration |
| H5 | Safety & Guardrails | Pre-commit hooks, security rules, credential guards |
| H6 | Observability | Logging, cost tracking, lessons, self-audit rules |
| H7 | Evolution | Version management, changelog, CI/CD publish |

## Scoring
- Each layer scores **L0-L3** (None → Basic → Structured → Advanced).
- **Harness Score** = sum(all 7 levels) / 21 × 100.
- **AI Ready** = min(all 7 levels) ≥ L1.

## Protocol

### 1. Run Audit
```bash
pactkit audit
```
- Outputs: scorecard + top hotspots (concise by default).
- Output file: `docs/architecture/governance/harness_audit.json`.

### 2. Options
| Flag | Purpose |
|------|---------|
| `--json` | JSON output only (machine-readable) |
| `--layer H1-H7` | Check a single layer |
| `--append` | Silent update for `/project-done` integration |
| `--if-needed STORY_ID` | Only refresh when `harness_audit.json` exists and its `story_id` matches; skips otherwise |
| `--verbose` | Full detail: findings + insights + hotspots |

### 3. Interpret Results
- **Score < 50**: Major gaps — address weakest layer first.
- **Score 50-80**: Functional but room for improvement.
- **Score > 80**: Strong harness — focus on hotspot refinement.
- **Hotspots**: Files ranked by composite score (complexity, blast radius, fan-in, test coverage, smells).

### 4. Suggested Tasks
When hotspots are detected and `developer` is configured in `pactkit.yaml`, the audit generates suggested task entries that can be added to the sprint board.

## Usage Scenarios
- `/project-done`: Run `pactkit audit --append --if-needed {STORY_ID}` — only refreshes if the audit belongs to this story; silently skips otherwise.
- Sprint planning: Run `pactkit audit --verbose` to identify technical debt priorities.
- CI integration: Run `pactkit audit --json` for machine-readable pipeline checks.
- Frontend dashboard: Call `/pactkit-audit` via headless mode for real-time project health.
"""

SKILL_RELEASE_MD = """---
name: pactkit-release
description: "Version release: snapshot, archive, Git tag, and GitHub Release"
model: sonnet
---

# PactKit Release

Version release management — update versions, snapshot architecture, create Git tags, and publish GitHub Releases.

## When Invoked
- **`/project-release` command**: VERSION is passed explicitly from the command's pre-flight check.
- **Standalone / legacy path**: VERSION is not provided — auto-detected from `pyproject.toml`.

## Version Parameter
- If `VERSION` is provided (e.g., by `/project-release`): use it directly, skip auto-detection.
- If version is not provided: auto-detect by running `git diff HEAD~1 pyproject.toml | grep version` and extracting the new value.

## Protocol

### 1. Version Update
- Update the project's package manifest (e.g., `pyproject.toml`, `package.json`, `__init__.py`).
- Backfill Specs: run `pactkit backfill-release $VERSION` to replace `Release: TBD` in completed specs.

### 2. Architecture Snapshot
- Run `visualize` (all four modes: file, class, call, module).
- Run `snapshot "$VERSION"` via pactkit-board skill.
- Result: graphs saved to `docs/architecture/snapshots/{version}_*.mmd`.

### 2.5. Pre-Tag Gate (CRITICAL)
- Run lint: `pactkit lint` (falls back to `ruff check src/ tests/`).
- Run tests: `pactkit regression` (falls back to `pytest tests/ -q`).
- If either fails: **STOP. Do NOT tag.** Fix the issue, re-commit, then re-run this gate.
- Report: `Pre-tag gate: PASS` or `Pre-tag gate: FAIL (details)`.

### 3. Git Operations
- Run `archive` via pactkit-board skill.
- Commit: `git commit -am "chore(release): $VERSION"`.
- Tag: `git tag $VERSION`.

### 4. GitHub Release (Conditional)
- **Check config**: Read `pactkit.yaml` for `release.github_release`.
  - If `release.github_release: true`: proceed with GitHub Release creation.
  - If `release.github_release: false` or section missing: log "GitHub Release: SKIP — not configured" and stop.
- Extract the `[$VERSION]` section from `CHANGELOG.md` as release notes.
- Create a GitHub Release: `gh release create $VERSION --title "$VERSION" --notes "$NOTES"`.
- Verify: `gh release view $VERSION` confirms the release exists and is marked Latest.
"""


# ---------------------------------------------------------------------------
# SKILL_MANIFEST — single source of truth for skill deployment (STORY-slim-139 R1)
#
# Every deployer (core classic/plugin AND external adapters like pactkit-codex)
# MUST iterate this manifest via get_skill_manifest(). Adding a skill = adding
# one entry here. script_name=None means prompt-only (SKILL.md only).
# ---------------------------------------------------------------------------

SKILL_MANIFEST: tuple[dict, ...] = (
    {"name": "pactkit-visualize", "skill_md": SKILL_VISUALIZE_MD, "script_name": "visualize.py"},
    {"name": "pactkit-board", "skill_md": SKILL_BOARD_MD, "script_name": "board.py"},
    {"name": "pactkit-scaffold", "skill_md": SKILL_SCAFFOLD_MD, "script_name": "scaffold.py"},
    {"name": "pactkit-report", "skill_md": SKILL_REPORT_MD, "script_name": "report.py"},
    {"name": "pactkit-trace", "skill_md": SKILL_TRACE_MD, "script_name": None},
    {"name": "pactkit-draw", "skill_md": SKILL_DRAW_MD, "script_name": None},
    {"name": "pactkit-status", "skill_md": SKILL_STATUS_MD, "script_name": None},
    {"name": "pactkit-doctor", "skill_md": SKILL_DOCTOR_MD, "script_name": None},
    {"name": "pactkit-garden", "skill_md": SKILL_GARDEN_MD, "script_name": None},
    {"name": "pactkit-review", "skill_md": SKILL_REVIEW_MD, "script_name": None},
    {"name": "pactkit-release", "skill_md": SKILL_RELEASE_MD, "script_name": None},
    {"name": "pactkit-analyze", "skill_md": SKILL_ANALYZE_MD, "script_name": None},
    {"name": "pactkit-audit", "skill_md": SKILL_AUDIT_MD, "script_name": None},
)

# STORY-slim-146: every deployed runtime skill must declare resume behavior.
# This is Core-owned so adapters cannot silently drift into unsafe replay rules.
SKILL_RECOVERY_CONTRACTS: dict[str, dict[str, str]] = {
    "pactkit-visualize": {"category": "derived_replayable", "recovery": "replay"},
    "pactkit-board": {
        "category": "local_write", "recovery": "idempotent_local_write",
        "safe_operations": "move_story,update_task",
        "manual_operations": "add_story,archive,snapshot",
    },
    "pactkit-scaffold": {"category": "create_only", "recovery": "manual_confirmation"},
    "pactkit-report": {"category": "derived_replayable", "recovery": "replay"},
    "pactkit-trace": {"category": "read_only", "recovery": "replay"},
    "pactkit-draw": {"category": "user_owned_write", "recovery": "manual_confirmation"},
    "pactkit-status": {"category": "read_only", "recovery": "replay"},
    "pactkit-doctor": {"category": "read_only", "recovery": "replay"},
    "pactkit-garden": {"category": "read_only", "recovery": "replay"},
    "pactkit-review": {"category": "external_read", "recovery": "replay"},
    "pactkit-release": {
        "category": "high_side_effect", "recovery": "manual_confirmation",
        "manual_operations": "release,tag,publish",
    },
    "pactkit-analyze": {"category": "read_only", "recovery": "replay"},
    "pactkit-audit": {
        "category": "derived_replayable", "recovery": "replay",
        "manual_operations": "--append",
    },
}


def validate_skill_recovery_contracts() -> list[str]:
    """Return manifest/contract drift errors without mutating deployment state."""
    names = [entry["name"] for entry in SKILL_MANIFEST]
    errors: list[str] = []
    if len(names) != len(set(names)):
        errors.append("duplicate skill in SKILL_MANIFEST")
    missing = set(names) - set(SKILL_RECOVERY_CONTRACTS)
    extra = set(SKILL_RECOVERY_CONTRACTS) - set(names)
    if missing:
        errors.append("missing recovery contracts: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("unknown recovery contracts: " + ", ".join(sorted(extra)))
    for name, contract in SKILL_RECOVERY_CONTRACTS.items():
        if not contract.get("category") or not contract.get("recovery"):
            errors.append(f"invalid recovery contract: {name}")
    return errors


def get_skill_manifest(*, include_portable_methods: bool = False) -> list[dict]:
    """Return default host skills, with script sources resolved.

    Public adapter contract (STORY-slim-139 R1): each entry has
    name / skill_md / script_name (None for prompt-only) and, for scripted
    skills, script_source. Adapters consume this instead of maintaining
    their own skill lists.
    """
    from pactkit.skills import load_script

    resolved = []
    entries = SKILL_MANIFEST
    if include_portable_methods:
        from pactkit.portable_methods import get_portable_methods

        entries = (*entries, *get_portable_methods())
    for entry in entries:
        item = dict(entry)
        if item["script_name"]:
            item["script_source"] = load_script(item["script_name"])
        resolved.append(item)
    return resolved
