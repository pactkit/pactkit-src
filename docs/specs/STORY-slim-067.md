# STORY-slim-067: Call graph nested subgraph with fan-in/fan-out

| Field | Value |
|-------|-------|
| ID | STORY-slim-067 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.3 |

## Background

`visualize --mode call --entry <func>` currently outputs a flat Mermaid `graph TD` where all nodes appear at the same level. For call chains with 3+ levels of nesting, the flat layout makes it hard to understand call depth and identify hot functions. Inspired by LangSmith's nested trace tree, this story enhances the call graph rendering to use depth-based Mermaid subgraphs with fan-in/fan-out annotations on each node.

## Requirements

### R1: Depth-tracking BFS (MUST)

The forward BFS in `_build_call_graph()` MUST record each node's depth (distance from entry) and parent node, in addition to the existing `visited` set and `reachable_edges` list. Data structure: `depth_map: dict[str, int]` mapping function name → BFS depth.

### R2: Nested subgraph rendering (MUST)

When `--entry` is provided, the Mermaid output MUST group nodes into `subgraph "Depth N"` blocks based on their BFS depth. Depth 0 = entry function. Each depth level is a separate subgraph. Direction remains `graph TD`.

### R3: Fan-in / fan-out annotation (MUST)

Each node label MUST include fan-in (↑N) and fan-out (↓M) counts. Fan-in = number of callers within the reachable set. Fan-out = number of callees within the reachable set. Format: `func_name [↑2 ↓3]`.

### R4: Reverse graph nested rendering (SHOULD)

The reverse BFS rendering (lines 1034-1043) SHOULD also use nested subgraphs by reverse depth (depth 0 = target function, increasing depth = callers further away).

### R5: No `--entry` unchanged (MUST)

When `--entry` is NOT provided (full call graph mode), the output MUST remain unchanged (flat Mermaid graph). Nesting only applies when a specific entry point is given.

### R6: Cycle detection annotation (SHOULD)

If a BFS encounters a node already visited (recursive/circular call), the edge SHOULD be rendered with a `↻` label and dotted arrow (`-.->|↻|`) instead of being silently skipped.

## Acceptance Criteria

### AC1: Nested subgraph output (R1, R2)

- **Given** a Python project with `main() → process() → helper() → util()`
- **When** `visualize --mode call --entry main` is run
- **Then** the Mermaid output contains `subgraph "Depth 0"` with `main`, `subgraph "Depth 1"` with `process`, `subgraph "Depth 2"` with `helper`, `subgraph "Depth 3"` with `util`

### AC2: Fan-in/fan-out labels (R3)

- **Given** `main → helper`, `process → helper` (helper has fan-in=2, fan-out=0)
- **When** `visualize --mode call --entry main` is run
- **Then** the node label for `helper` contains `↑2 ↓0`

### AC3: Full graph unchanged (R5)

- **Given** any project
- **When** `visualize --mode call` (no `--entry`) is run
- **Then** output is identical to pre-change behavior (flat `graph TD`, no subgraphs)

### AC4: Reverse graph nested (R4)

- **Given** `a → b → c` call chain
- **When** `visualize --mode call --entry c --reverse` is run
- **Then** output contains depth-based subgraphs (depth 0 = `c`, depth 1 = `b`, depth 2 = `a`)

### AC5: Cycle annotation (R6)

- **Given** `a → b → a` circular call
- **When** `visualize --mode call --entry a` is run
- **Then** the edge `b → a` uses dotted arrow with `↻` label

## Target Call Chain

```
visualize(mode='call', entry=X)
  → _build_call_graph(root, all_files, focus, entry)  [line 730]
      → BFS loop [line 757-769] ← ADD depth_map tracking
      → Mermaid rendering [line 771-776] ← REPLACE with nested subgraph + fan-in/fan-out
  → reverse path [line 1030-1043] ← REPLACE with nested subgraph
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py:757-776` | Modify forward BFS to record `depth_map` + compute fan-in/fan-out; render as nested subgraphs | None | Low |
| 2 | `src/pactkit/skills/visualize.py:1034-1043` | Modify reverse BFS rendering to use nested subgraphs | Step 1 (shared helper) | Low |
| 3 | `tests/unit/test_visualize_call_nested.py` | New test file: AC1-AC5 tests | Step 1-2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 through SEC-8 | N/A | Rendering-only change, no I/O, auth, or external interaction |

## Out of Scope

- Runtime tracing / timing data (LangSmith-style spans)
- Token/cost statistics
- New output file formats (still `.mmd`)
- Changes to AST parsing or callee resolution logic
- Changes to full call graph (no `--entry`) rendering
