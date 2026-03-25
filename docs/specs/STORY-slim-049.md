# STORY-slim-049: Split unified graph: full graph for AI + focused sub-graphs for humans

| Field | Value |
|-------|-------|
| ID | STORY-slim-049 |
| Status | Done |
| Priority | P1 |
| Release | 2.5.0 |

## Background

The current `build_unified_graph()` enforces `MAX_WORKFLOW_NODES=500` truncation, which silently drops nodes beyond that limit. This causes two problems:

1. **AI impact analysis loses accuracy**: `reverse_reach()` operates on the in-memory graph object, so truncated nodes are invisible to impact analysis queries.
2. **Human Mermaid readability**: Even without truncation, a 500+ node .mmd file is unreadable when rendered as a Mermaid diagram.

**Solution**: Split the unified graph into two outputs:
- **Full graph** (no truncation): Used by AI for `reverse_reach()` impact analysis. The full graph object stays in memory; the .mmd is a reference artifact.
- **Focused sub-graphs**: Per-entry-point .mmd files (one per first-level command/service/page) generated via `reverse_reach()` extraction. Each sub-graph contains <50 nodes — human-readable in Mermaid renderers.

## Requirements

### R1: Remove MAX_WORKFLOW_NODES truncation from build_unified_graph (MUST)

`build_unified_graph()` MUST return the complete graph without truncation. The `MAX_WORKFLOW_NODES` constant MAY be retained for backward compatibility but MUST NOT be enforced in `build_unified_graph()`. The full graph is the source of truth for `reverse_reach()` impact analysis.

### R2: Add export_focus_graphs function (MUST)

A new function `export_focus_graphs(graph: WorkflowGraph, output_dir: Path) -> list[Path]` MUST:
- Identify first-level entry points: nodes of kind `command`, `service`, or `page` (the top-level anchors of each topology dimension).
- For each entry point, call `reverse_reach(entry_id)` to extract the reachable sub-graph.
- Render each sub-graph as a standalone .mmd file: `{output_dir}/focus_{sanitized_entry_id}.mmd`.
- Return the list of written file paths.

### R3: Add max_render_nodes parameter to to_mermaid (SHOULD)

`to_mermaid(max_render_nodes: int = 0)` SHOULD accept an optional parameter. When `max_render_nodes > 0` and the graph exceeds that count, render only the first N nodes and append a `NOTE` node indicating truncation. Default `0` means no limit (render all).

### R4: CLI integration — unified mode with --split flag (MUST)

`pactkit visualize --mode unified` MUST:
- Call `build_unified_graph(root)` (full, no truncation).
- Write the full graph to `docs/architecture/graphs/unified_graph.mmd`.
- If `--split` flag is provided, also call `export_focus_graphs()` to generate per-entry-point files in `docs/architecture/graphs/focus/`.

### R5: Backward compatibility (MUST)

- Existing `visualize --mode workflow` behavior MUST NOT change.
- Existing `MAX_WORKFLOW_NODES` constant MUST remain defined (tests reference it).
- `reverse_reach()` API MUST NOT change.

## Acceptance Criteria

### AC1: Full graph contains all nodes without truncation (R1)

- **Given** a project with 600+ functions and topology nodes (exceeding MAX_WORKFLOW_NODES)
- **When** `build_unified_graph(root)` is called
- **Then** the returned graph contains all nodes (no truncation warning emitted)

### AC2: Focused sub-graphs generated per entry point (R2)

- **Given** a unified graph with 3 commands (`project-act`, `project-plan`, `project-done`) and 2 services (`order-service`, `payment-service`)
- **When** `export_focus_graphs(graph, output_dir)` is called
- **Then** 5 .mmd files are created in `output_dir/`, one per entry point, each containing only nodes reachable via `reverse_reach()`

### AC3: Each focused sub-graph is self-contained Mermaid (R2)

- **Given** a focused sub-graph .mmd file
- **When** the file is opened in a Mermaid renderer
- **Then** it starts with `graph TD`, contains valid node and edge definitions, and renders without errors

### AC4: to_mermaid with max_render_nodes truncates rendering (R3)

- **Given** a WorkflowGraph with 100 nodes
- **When** `to_mermaid(max_render_nodes=50)` is called
- **Then** the output contains exactly 50 node definitions plus a NOTE node indicating "... and 50 more nodes"

### AC5: CLI unified mode writes full graph (R4)

- **Given** a PactKit project
- **When** `pactkit visualize --mode unified` is run
- **Then** `docs/architecture/graphs/unified_graph.mmd` is created with the full layered graph

### AC6: CLI --split flag generates focus directory (R4)

- **Given** a PactKit project
- **When** `pactkit visualize --mode unified --split` is run
- **Then** `docs/architecture/graphs/focus/` directory contains per-entry-point .mmd files

### AC7: Existing workflow mode unchanged (R5)

- **Given** a PactKit project
- **When** `pactkit visualize --mode workflow` is run
- **Then** output is identical to pre-change behavior (same file path, same content format)

## Target Call Chain

```
build_unified_graph(root)                    # visualize.py:1962 — MODIFY: remove truncation
  → build_workflow_graph(root)               # visualize.py:1872 — unchanged
  → _load_code_graph(root)                   # visualize.py:1902 — unchanged
  → _build_bridge_edges(...)                 # visualize.py:1944 — unchanged
  → [REMOVE] MAX_WORKFLOW_NODES truncation   # visualize.py:1990-1998

export_focus_graphs(graph, output_dir)       # NEW function
  → graph.reverse_reach(entry_id)            # visualize.py:1054 — unchanged
  → WorkflowGraph.to_mermaid()               # visualize.py:1009 — MODIFY: add max_render_nodes

visualize(mode='unified', split=False)       # visualize.py:878 — MODIFY: add unified mode
  → build_unified_graph(root)
  → export_focus_graphs(graph, output_dir)   # only if split=True

CLI: pactkit visualize --mode unified --split  # visualize.py:2004+ — MODIFY: add mode/flag
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py` | Remove MAX_WORKFLOW_NODES truncation block (lines 1990-1998) from `build_unified_graph()` | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Add `max_render_nodes` parameter to `to_mermaid()`. When >0, truncate node output and append NOTE. | Step 1 | Low |
| 3 | `src/pactkit/skills/visualize.py` | Implement `export_focus_graphs(graph, output_dir)` — iterate entry-point kinds, call `reverse_reach()`, build sub-graph, write .mmd | Step 2 | Medium |
| 4 | `src/pactkit/skills/visualize.py` | Add `mode='unified'` handling in `visualize()` function — call `build_unified_graph`, write full .mmd, optionally call `export_focus_graphs` | Step 3 | Low |
| 5 | `src/pactkit/skills/visualize.py` | Update CLI argparse: add `'unified'` to `--mode` choices, add `--split` flag | Step 4 | Low |
| 6 | `tests/unit/test_story_slim049.py` | Write tests for R1-R5: no truncation, focus graph generation, max_render_nodes, CLI integration | Steps 1-5 | Low |
| 7 | `tests/unit/test_story_slim048.py` | Update existing truncation test to verify MAX_WORKFLOW_NODES constant still exists but is not enforced | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | Internal function APIs, no user-supplied strings beyond file paths already validated by Path() |
| SEC-2 Authentication | N/A | CLI tool, no auth required |
| SEC-3 Authorization | N/A | Local file operations only |
| SEC-4 Data Exposure | N/A | Graph data is project structure, not secrets |
| SEC-5 Injection | N/A | Mermaid node IDs sanitized via existing `_sanitize_id()` |
| SEC-6 Path Traversal | N/A | Output paths constructed from `root / 'docs/...'`, no user-controlled path components |
| SEC-7 Dependencies | N/A | No new dependencies added |
| SEC-8 Logging | N/A | No sensitive data in graph output |

## Out of Scope

- Changing `reverse_reach()` algorithm or API
- Modifying existing `workflow`, `file`, `class`, `call` visualization modes
- Adding interactive Mermaid rendering (browser-based)
- Persisting the full graph object across sessions (it's rebuilt on demand)
