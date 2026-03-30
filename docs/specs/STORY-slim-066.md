# STORY-slim-066: PactKit Trace Multi-Topology Extension

| Field | Value |
|-------|-------|
| ID | STORY-slim-066 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.0 |

## Background

PactKit's `TopologyParser` system currently supports 3 topologies: PDCA, Service, and Frontend. The Frontend parser extracts page/component/hook/store nodes but does NOT trace API call patterns (e.g., `apiFetch("/api/v1/rulesets")`) or multi-agent orchestration relationships. This gap caused avoidable bugs in PactGuard STORY-012: the `ScanInputForm` component called `apiFetch("/rulesets")` instead of `apiFetch("/api/v1/rulesets")` because the implementation phase did not analyze existing API call conventions.

Additionally, Plan Phase 1 and Act Phase 1 reference `pactkit-trace` generically but have no frontend/agent-specific gate — when a frontend or agent topology is detected, the workflow does not enforce API convention analysis or agent dependency tracing.

This story adds two new `TopologyParser` subclasses (`ApiCallParser`, `AgentParser`) and a workflow enforcement gate to ensure trace output is consumed before implementation.

## Requirements

### R1: ApiCallParser — tree-sitter based (MUST)

New `TopologyParser` subclass that extracts API call nodes and edges from frontend source files using the existing `tree-sitter-typescript` infrastructure (`TSAnalyzer`, `TreeSitterAnalyzer` base class). MUST:
- Detect projects with frontend markers (same as `FrontendParser`) AND at least one file containing a fetch-like call (`apiFetch`, `fetch`, `axios`, `useQuery`, `useSWR`, `useMutation`).
- Parse all `.ts`/`.tsx`/`.js`/`.jsx` files using `tree-sitter-typescript` AST (reuse existing `_TSParser`, `_TSQuery`, `_TSQueryCursor` from `visualize.py`). Do NOT use regex for call extraction.
- Define tree-sitter queries to match:
  - Direct fetch calls: `apiFetch("/api/v1/rulesets")` → `(call_expression function: (identifier) @callee arguments: (arguments (string) @api_path))`
  - Method-style calls: `axios.get("/path")`, `axios.post("/path")` → `(call_expression function: (member_expression object: (_) @obj property: (property_identifier) @method) arguments: (arguments (string) @api_path))`
  - Template literal paths: `` apiFetch(`/api/v1/${x}`) `` → `(call_expression function: (identifier) @callee arguments: (arguments (template_string) @dynamic_path))`
- For each API call, create a `WorkflowNode` with `kind='api_call'` and label containing the HTTP method + path (e.g., `GET /api/v1/rulesets`).
- Create `WorkflowEdge` with `relation='fetches'` from the containing page/component/hook node to the `api_call` node. Use tree-sitter parent traversal to identify the enclosing function/component.
- Mark template-literal paths as `[dynamic]` in the node label — do not attempt to resolve variables.
- Support user-configurable fetch function names via `pactkit.yaml` key `trace.fetch_functions` (list of strings, default: `["fetch", "apiFetch", "axios", "useQuery", "useSWR", "useMutation"]`).
- Graceful fallback: if `tree-sitter-typescript` is not installed, skip `ApiCallParser` silently (consistent with existing `_HAS_TREE_SITTER` guard pattern).

### R2: AgentParser — multi-strategy (MUST)

New `TopologyParser` subclass that extracts multi-agent orchestration topology using a prioritized multi-strategy approach. No existing agent parsing infrastructure exists — current `kind='agent'` nodes in `PdcaParser` represent PDCA roles (e.g., "Senior Developer"), not orchestrable agent definitions. MUST:

**Strategy 1 — LangGraph/LangChain (tree-sitter Python, highest priority)**:
- Detect: scan Python files for `StateGraph`, `MessageGraph`, or `from langgraph` imports.
- Parse `add_node("name", callable)` calls → `WorkflowNode(kind='agent_def')`.
- Parse `add_edge("from", "to")` → `WorkflowEdge(relation='orchestrates')`.
- Parse `add_conditional_edges("from", route_fn, {"key": "target"})` → conditional `orchestrates` edges with the routing key as edge label.
- Reuse existing `tree-sitter` + `tree-sitter-python` (Python AST is already used via `PythonAnalyzer`; tree-sitter queries provide more precise matching for `add_node`/`add_edge` patterns).

**Strategy 2 — Declarative configs (YAML/JSON parsing)**:
- Detect: `agents/` directory, `*.agent.yaml`, `crew.yaml`, or files containing `agents:` top-level key.
- Parse CrewAI-style: `agents:` list → agent nodes; `tasks:` with `agent:` references → orchestration edges.
- Parse Claude Code `AGENTS.md` → agent sections with tool/delegation references.
- Parse PactKit's own format (`agents.py` role definitions, `SKILL.md` embedded-in references).

**Strategy 3 — MCP config (JSON parsing)**:
- Detect: `.claude/settings.json`, `mcp_servers` config, or `mcp.json`.
- Parse MCP server definitions → `WorkflowNode(kind='agent_def')` per server.
- Extract tool-use relationships: agent → MCP server → tools → `WorkflowEdge(relation='uses_tool')`.

**Strategy 4 — A2A Agent Card (optional, runtime discovery)**:
- Detect: `a2a.json`, `.well-known/agent.json`, or `agent_card` config in project files.
- Parse Agent Card JSON for `name`, `skills`, `capabilities`.
- This strategy is opt-in: only triggered when A2A config files exist locally. Does NOT make HTTP requests during static analysis.

**Common rules across all strategies**:
- Use `kind='agent_def'` (not `kind='agent'`) to avoid collision with PdcaParser's existing role-based nodes.
- Multiple strategies may fire for the same project — results are merged into a single `WorkflowGraph`, deduplicating agent nodes by name.
- `AgentParser.detect()` returns `True` if ANY strategy detects markers.
- Graceful fallback: if `tree-sitter` is not installed, skip Strategy 1 silently; Strategies 2-4 still work (pure YAML/JSON/markdown parsing).

### R3: Dimension Registration (MUST)

Register new node kinds in `_KIND_TO_DIMENSION`:
- `api_call` → `API Topology`
- `agent_def` → `Agent Topology`

New dimensions MUST appear in the unified graph's Mermaid output when the corresponding parser detects nodes.

### R4: Workflow Enforcement Gate (MUST)

Update `pactkit-trace` skill protocol and Plan/Act command prompts to include a mandatory convention check when frontend or agent topology is detected:
- **Plan Phase 1**: When `detect_topology(root)` includes `frontend`, the trace MUST output an "API Convention Summary" section listing all unique API path prefixes, fetch function names, and base URL patterns found in the project.
- **Act Phase 1**: When implementing new frontend code, the trace MUST verify that the new code's API calls conform to the existing convention (same prefix, same fetch wrapper). If a discrepancy is detected, WARN before proceeding.
- **Agent topology**: When `detect_topology(root)` includes `agent`, trace MUST output an "Agent Dependency Map" listing all agents and their orchestration relationships.

### R5: pactkit.yaml Configuration (SHOULD)

Add optional `trace` section to `pactkit.yaml` schema:
```yaml
trace:
  fetch_functions: ["apiFetch", "fetch"]  # Custom fetch function names for ApiCallParser
  agent_strategies: ["langgraph", "declarative", "mcp", "a2a"]  # Enable/disable strategies
  agent_markers: ["agents/", "*.agent.yaml"]  # Extra marker paths for declarative strategy
```

Defaults MUST work without any configuration — the `trace` section is entirely optional. All 4 strategies are enabled by default.

## Acceptance Criteria

### AC1: ApiCallParser detects fetch calls in Next.js project (R1, R3)

- **Given** a Next.js project with files containing `apiFetch("/api/v1/rulesets")` and `apiFetch("/api/v1/scan-git", { method: "POST" })`
- **When** `ApiCallParser.parse(root)` is called
- **Then** the resulting `WorkflowGraph` contains:
  - `api_call` nodes with labels `GET /api/v1/rulesets` and `POST /api/v1/scan-git`
  - `fetches` edges from the containing page/component to each `api_call` node
- **Then** `_KIND_TO_DIMENSION` maps `api_call` to `API Topology`

### AC2: ApiCallParser handles wrapper functions (R1)

- **Given** a file `lib/api-client.ts` exporting `apiFetch` and a page file calling `apiFetch("/api/v1/health")`
- **When** `ApiCallParser.parse(root)` is called
- **Then** the `fetches` edge source is the page node (not the utility module)

### AC3: ApiCallParser marks dynamic paths (R1)

- **Given** a file containing `` apiFetch(`/api/v1/rulesets/${name}`) ``
- **When** `ApiCallParser.parse(root)` is called
- **Then** the `api_call` node label includes `[dynamic]` marker

### AC4: AgentParser Strategy 1 — LangGraph (R2, R3)

- **Given** a Python project with `graph = StateGraph(State)`, `graph.add_node("researcher", research_fn)`, `graph.add_node("writer", write_fn)`, `graph.add_edge("researcher", "writer")`
- **When** `AgentParser.parse(root)` is called
- **Then** the resulting `WorkflowGraph` contains:
  - `agent_def` nodes: `researcher`, `writer`
  - `orchestrates` edge from `researcher` to `writer`
- **Then** `_KIND_TO_DIMENSION` maps `agent_def` to `Agent Topology`

### AC4b: AgentParser Strategy 2 — Declarative YAML (R2)

- **Given** a project with `agents/crew.yaml` containing `agents:` list with two agents, one delegating to the other
- **When** `AgentParser.parse(root)` is called
- **Then** the resulting `WorkflowGraph` contains `agent_def` nodes for each agent
- **Then** delegation edges (`orchestrates`) connect the delegating agent to its target

### AC4c: AgentParser Strategy 3 — MCP config (R2)

- **Given** a project with `.claude/settings.json` containing `mcpServers` with 2 server definitions
- **When** `AgentParser.parse(root)` is called
- **Then** the resulting `WorkflowGraph` contains `agent_def` nodes for each MCP server

### AC4d: AgentParser multi-strategy merge (R2)

- **Given** a project with both LangGraph code AND a `crew.yaml`
- **When** `AgentParser.parse(root)` is called
- **Then** agent nodes with the same name are deduplicated
- **Then** edges from both strategies are merged into one graph

### AC5: Workflow gate outputs API convention summary (R4)

- **Given** a project where `detect_topology(root)` returns `['frontend']`
- **When** Plan Phase 1 trace is executed
- **Then** output includes an "API Convention Summary" with:
  - Unique path prefixes (e.g., `/api/v1/`)
  - Fetch function names used (e.g., `apiFetch`)
  - Total API call count per prefix

### AC6: Custom fetch function names via config (R5)

- **Given** `pactkit.yaml` contains `trace.fetch_functions: ["customFetch", "apiCall"]`
- **When** `ApiCallParser` initializes
- **Then** it scans for `customFetch` and `apiCall` instead of the defaults

## Target Call Chain

```
build_unified_graph(root)
  → build_workflow_graph(root)
    → detect_topology(root)  # returns ['pdca', 'frontend', ...]
    → for name in topologies:
        _TOPOLOGY_PARSERS[name].parse(root)  # includes NEW ApiCallParser, AgentParser
    → merge all WorkflowGraph results
  → _load_code_graph(root)
  → _build_bridge_edges(...)
  → return unified WorkflowGraph (layered=True)

# New parsers:
ApiCallParser.parse(root)
  → scan .ts/.tsx/.js/.jsx files
  → tree-sitter-typescript AST parse (reuse _TSParser, _TSQuery)
  → custom queries: call_expression + string arg → api_call node
  → template_string arg → api_call node with [dynamic] marker
  → parent traversal → enclosing function/component → fetches edge
  → WorkflowNode(kind='api_call') + WorkflowEdge(relation='fetches')

AgentParser.parse(root)
  → Strategy 1: tree-sitter Python → StateGraph/add_node/add_edge/add_conditional_edges
  → Strategy 2: YAML/JSON → agents/ dir, crew.yaml, AGENTS.md, PactKit agents.py
  → Strategy 3: JSON → .claude/settings.json mcpServers, mcp.json
  → Strategy 4: JSON → a2a.json, .well-known/agent.json (local files only)
  → merge + deduplicate
  → WorkflowNode(kind='agent_def') + WorkflowEdge(relation='orchestrates'|'uses_tool')
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py` | Add `ApiCallParser` class using `tree-sitter-typescript` queries, `detect()`, `parse()`, register in `_TOPOLOGY_PARSERS['api_call']`. Reuse `_HAS_TREE_SITTER` guard, `_TSParser`, `_TSQuery`, `_TSQueryCursor`. | None | Low (AST-based, not regex) |
| 2a | `src/pactkit/skills/visualize.py` | Add `AgentParser` class with multi-strategy `detect()` + `parse()`, register in `_TOPOLOGY_PARSERS['agent']`. Strategy 1: tree-sitter Python queries for `StateGraph`/`add_node`/`add_edge`. | None | Low |
| 2b | `src/pactkit/skills/visualize.py` | AgentParser Strategy 2: YAML/JSON parsing for CrewAI, Claude AGENTS.md, PactKit agents.py | Step 2a | Low |
| 2c | `src/pactkit/skills/visualize.py` | AgentParser Strategy 3: MCP config parsing (`.claude/settings.json` mcpServers) | Step 2a | Low |
| 2d | `src/pactkit/skills/visualize.py` | AgentParser Strategy 4: A2A Agent Card local file parsing (opt-in) | Step 2a | Low |
| 3 | `src/pactkit/skills/visualize.py` | Update `_KIND_TO_DIMENSION` with `api_call` → `API Topology`, `agent_def` → `Agent Topology` | Steps 1-2 | Low |
| 4 | `src/pactkit/skills/visualize.py` | Add `api_convention_summary(root)` function that returns prefix/function/count analysis | Step 1 | Low |
| 5 | `src/pactkit/prompts/commands.py` | Update Plan Phase 1 and Act Phase 1 prompts with topology-aware trace gate | Step 4 | Low |
| 6 | `~/.claude/skills/pactkit-trace/SKILL.md` | Add frontend and agent trace protocols to skill definition | Step 5 | Low |
| 7 | `src/pactkit/schemas.py` | Add `TRACE_CONFIG_KEYS` for pactkit.yaml `trace` section validation | None | Low |
| 8 | `tests/unit/` | Tests for ApiCallParser, AgentParser, api_convention_summary, config loading | Steps 1-7 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Injection | N/A | No user input reaches shell/SQL — parsers read local files only |
| SEC-2 Auth | N/A | No auth changes |
| SEC-3 Data Exposure | N/A | No new data exposed — parsers analyze already-accessible local files |
| SEC-4 CSRF | N/A | No web endpoints |
| SEC-5 Dependency | N/A | No new dependencies — reuses existing tree-sitter-typescript (optional extra) |
| SEC-6 Secrets | N/A | No secrets handling |
| SEC-7 Logging | N/A | No logging changes |
| SEC-8 File Access | Low | Parsers read source files under project root — bounded by existing `scan_excludes` + `MAX_SCAN_FILES` |

## Out of Scope

- Runtime trace (instrumented execution)
- Third-party npm package internal call tracing
- Cross-language end-to-end trace (Python route ↔ TS fetch matching) — deferred to Phase 2
- A2A runtime HTTP discovery (querying live `/.well-known/agent.json` endpoints) — only local A2A config files are parsed
- OpenAI Assistants API / Swarm framework parsing — can be added as Strategy 5 later

## Notes

- **tree-sitter over regex**: ApiCallParser uses `tree-sitter-typescript` (already a project dependency for `TSAnalyzer`) for AST-accurate call extraction. This avoids the regex fragility risk identified in Clarify Q5-A. Falls back gracefully when tree-sitter is not installed (`_HAS_TREE_SITTER` guard).
- **kind collision avoidance**: AgentParser uses `kind='agent_def'` to distinguish orchestrable agent definitions from PdcaParser's existing `kind='agent'` (PDCA role nodes like "Senior Developer").
- **Backward compatibility**: New parsers are additive — existing `FrontendParser` behavior is unchanged. `ApiCallParser` adds `api_call` nodes alongside existing `page`/`component` nodes.
- **Config defaults**: `trace` section in `pactkit.yaml` is optional. All parsers work with sensible defaults when no config is present.
- **Test fixtures**: Each tree-sitter query MUST have corresponding fixture files in `tests/fixtures/` — `.tsx` for ApiCallParser (Next.js apiFetch, axios, dynamic paths, wrapper hooks), `.py` for AgentParser Strategy 1 (LangGraph StateGraph patterns), `.yaml` for Strategy 2 (CrewAI crew.yaml).
- **AgentParser strategy priority**: When multiple strategies detect agents, Strategy 1 (LangGraph AST) is most authoritative for orchestration edges. Strategy 2-4 provide supplementary nodes. Deduplication is by agent name — first strategy to create the node wins, later strategies only add edges.
- **New edge relation**: `uses_tool` is added for MCP config strategy (Strategy 3) where agents use MCP servers as tools, distinct from `orchestrates` which implies agent-to-agent delegation.
