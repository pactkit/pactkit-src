# STORY-020: Visualize Horizon Limit (--depth flag)

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.2.0 |

## Context

The `visualize` skill generates full dependency graphs with no size limit. For small projects (10-30 files), this works well. For medium/large projects (100+ files), the Mermaid output can reach thousands of lines, causing "Lost in the Middle" attention dilution when injected into the LLM context window.

The `--focus` flag exists but only filters by module name in call mode. There is no general-purpose depth limiter that works across all three modes (file, class, call).

Additionally, there is no node count cap — a 200-file project would produce a 200+ node graph that provides diminishing returns to the AI agent.

## Target Call Chain

```
visualize.py
  → _build_file_graph()     ← scans ALL .py files, no depth limit
  → _build_class_graph()    ← scans ALL classes, no depth limit
  → _build_call_graph()     ← BFS with no depth limit
  → _write_mermaid()        ← writes full graph, no truncation
```

## Requirements

### R1: --depth Parameter
- `visualize` MUST accept a `--depth N` parameter (integer, default: unlimited).
- When `--depth` is set, graph traversal MUST stop after N levels from the entry point or focus module.
- For `--mode file`: depth is measured as import hops from the root/focus module.
- For `--mode call`: depth is measured as call hops from the `--entry` function.
- For `--mode class`: depth is measured as inheritance levels.

### R2: Node Count Cap
- `visualize` SHOULD accept a `--max-nodes N` parameter (default: 80).
- When the node count exceeds the cap, the graph MUST be truncated with a note: `NOTE["... and N more nodes (use --max-nodes to adjust)"]`.
- This protects the LLM context window from oversized graphs.

### R3: Prompt Guidance
- The `project-plan` and `project-act` command prompts SHOULD be updated to recommend `--focus <module> --depth 2` for large codebases.
- The prompt SHOULD include a heuristic: "If the project has more than 50 source files, use `--focus` with `--depth 2` instead of a full graph."

### R4: Backward Compatibility
- Default behavior (no flags) MUST remain unchanged for existing users.
- The truncation note MUST be visible in the Mermaid output so the agent knows the graph is incomplete.

## Acceptance Criteria

### Scenario 1: --depth limits file graph
- **Given** a project with modules A→B→C→D (chain of 4)
- **When** `visualize --mode file --depth 2` is run with A as root
- **Then** graph contains A, B, C but NOT D (2 hops from A)

### Scenario 2: --max-nodes truncates large graph
- **Given** a project with 150 Python files
- **When** `visualize --max-nodes 50` is run
- **Then** graph contains 50 nodes + a NOTE node saying "... and 100 more nodes"

### Scenario 3: Default behavior unchanged
- **Given** a project with 20 files
- **When** `visualize` is run with no flags
- **Then** all 20 files appear in the graph (same as current behavior)

### Scenario 4: Prompt recommends focus for large projects
- **Given** `project-plan` is invoked on a project with 80+ source files
- **When** the agent reads the Plan prompt
- **Then** the prompt instructs: "use `--focus <module> --depth 2`" for large codebases
