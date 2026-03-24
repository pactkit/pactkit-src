# STORY-slim-037: Workflow Impact Analysis

| Field | Value |
|-------|-------|
| ID | STORY-slim-037 |
| Status | Done |
| Priority | P1 — Impact 5, Effort 3 |
| Release | TBD |

## Background

PactKit already supports code-level impact analysis: given a changed function, `impact --entry <func>` traces the call graph to find affected tests. This story extends the same concept to the logical/workflow dimension: given a changed skill or file, `impact --mode workflow --entry <skill>` traces the `WorkflowGraph` backward to find all commands and agents that depend on it.

This is critical for answering: "I changed `pactkit-board` — which PDCA commands will break?" Without this, developers must manually trace command→skill dependencies through markdown files.

## Requirements

### R1: Reverse traversal on WorkflowGraph (MUST)

A `WorkflowGraph.reverse_reach(entry_id)` method MUST perform a reverse BFS/DFS from the given node ID, following edges backward (target→source), and return all reachable node IDs.

### R2: `impact --mode workflow` CLI integration (MUST)

The `impact()` function in `src/pactkit/skills/visualize.py` MUST accept `mode="workflow"` and `entry=<node_id>`. It MUST:
1. Call `build_workflow_graph(root)` to build the full graph
2. Call `graph.reverse_reach(entry)` to find affected nodes
3. Output the list of affected commands/agents/skills/files grouped by `kind`

### R3: Output format (MUST)

The impact output MUST list affected nodes grouped by kind:
```
Workflow Impact for "pactkit-board":
  Commands: project-done, project-sprint, project-act
  Agents: repo-maintainer, senior-developer
  Files: board.py, sprint_board.md
```

### R4: Entry node validation (MUST)

If the `--entry` node ID does not exist in the `WorkflowGraph`, the function MUST print an error message listing available node IDs and return a non-zero exit code (or empty result for programmatic use).

### R5: Multiple entry points (SHOULD)

`impact --mode workflow --entry <id1> --entry <id2>` SHOULD accept multiple entry points and return the union of affected nodes.

## Acceptance Criteria

### AC1: Reverse reach finds commands (R1)

- **Given** a `WorkflowGraph` where command A invokes skill B, and skill B depends on file C
- **When** calling `reverse_reach("C")`
- **Then** the result includes both skill B and command A

### AC2: Impact CLI outputs affected commands (R2, R3)

- **Given** a PactKit installation with full workflow graph
- **When** running `impact(root, mode="workflow", entry="pactkit-board")`
- **Then** output lists all commands that directly or transitively depend on `pactkit-board`

### AC3: Invalid entry handled (R4)

- **Given** a `WorkflowGraph` with known nodes
- **When** calling `impact(root, mode="workflow", entry="nonexistent-skill")`
- **Then** an error message is printed with a list of valid node IDs

### AC4: Multiple entries union (R5)

- **Given** a `WorkflowGraph`
- **When** calling `reverse_reach` for both `pactkit-board` and `pactkit-trace`
- **Then** the result is the union of both reverse reach sets

## Target Call Chain

```
impact(root, mode="workflow", entry="pactkit-board")
  → build_workflow_graph(root)
  → graph.reverse_reach("pactkit-board")
    → BFS backward through edges
  → format and print affected nodes by kind
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim037.py` | Tests for reverse_reach and workflow impact | STORY-slim-035 | Low |
| 2 | `src/pactkit/skills/visualize.py` | Implement `WorkflowGraph.reverse_reach()` | STORY-slim-035 | Low |
| 3 | `src/pactkit/skills/visualize.py` | Add `mode="workflow"` branch in `impact()` | Step 2 | Medium |
| 4 | `src/pactkit/skills/visualize.py` | Entry validation and error messaging | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Entry node ID is a string lookup in a dict; no injection risk |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- Code-level + workflow-level combined impact (STORY-slim-042 Unified Graph)
- Automatic regression test selection based on workflow impact
- Cross-service impact analysis (STORY-slim-040)
- Weighted or probabilistic impact scoring
