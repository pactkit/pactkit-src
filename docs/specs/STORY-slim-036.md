# STORY-slim-036: visualize --mode workflow

| Field | Value |
|-------|-------|
| ID | STORY-slim-036 |
| Status | Done |
| Priority | P2 — Impact 4, Effort 2 |
| Release | TBD |

## Background

STORY-slim-035 builds the `WorkflowGraph` data model and parsers that extract command→agent→skill→file dependencies from PactKit's markdown files. This story adds the `--mode workflow` flag to the `visualize` command, which invokes `build_workflow_graph()` and writes `workflow_graph.mmd` — a Mermaid diagram showing the logical dependency graph of PactKit's PDCA workflow.

This is the "view" layer for the workflow parser: it connects the data model to the CLI and produces a visual artifact alongside the existing `code_graph.mmd`, `class_graph.mmd`, and `call_graph.mmd`.

## Requirements

### R1: `--mode workflow` CLI flag (MUST)

The `visualize()` function in `src/pactkit/skills/visualize.py` MUST accept `mode="workflow"` as a valid option. When `mode="workflow"` is specified, it MUST call `build_workflow_graph(root)` and write the result to `docs/architecture/graphs/workflow_graph.mmd`.

### R2: Mermaid output format (MUST)

The `WorkflowGraph.to_mermaid()` method (from STORY-slim-035) MUST produce a valid `graph TD` Mermaid diagram with:
- Subgraphs grouping nodes by `kind` (commands, agents, skills, files)
- Edges labeled with the `relation` type (invokes, depends_on, reads, writes)
- Node IDs sanitized for Mermaid compatibility (no dots, slashes, or spaces)

### R3: Lazy generation support (MUST)

When `--lazy` flag is active, `workflow_graph.mmd` MUST only be regenerated if any command/skill/rule markdown file has changed since the last generation. This MUST use the same staleness check pattern as the existing file/class/call modes.

### R4: CLI integration via pactkit-visualize skill (MUST)

The `pactkit-visualize` skill script MUST pass the `mode` parameter through to `visualize()`. Running `python3 ~/.claude/skills/pactkit-visualize/scripts/visualize.py visualize --mode workflow` MUST produce `workflow_graph.mmd`.

### R5: Backward compatibility (MUST)

Adding `--mode workflow` MUST NOT change the behavior of existing modes (`file`, `class`, `call`). The default mode MUST remain `file`.

## Acceptance Criteria

### AC1: workflow_graph.mmd generated (R1, R2)

- **Given** a PactKit installation with commands, skills, and rules directories
- **When** running `visualize(root, mode="workflow")`
- **Then** `docs/architecture/graphs/workflow_graph.mmd` is created with valid Mermaid `graph TD` syntax

### AC2: Subgraphs by kind (R2)

- **Given** a generated `workflow_graph.mmd`
- **When** inspecting the content
- **Then** nodes are grouped into subgraphs: `Commands`, `Agents`, `Skills`, `Files`

### AC3: Edge labels present (R2)

- **Given** a generated `workflow_graph.mmd`
- **When** inspecting edges
- **Then** edges include relation labels like `invokes`, `depends_on`, `reads`, `writes`

### AC4: Lazy skip when unchanged (R3)

- **Given** `workflow_graph.mmd` already exists and no command/skill/rule files have changed
- **When** running `visualize(root, mode="workflow", lazy=True)`
- **Then** the file is NOT regenerated and a skip message is logged

### AC5: CLI skill script passes mode (R4)

- **Given** the pactkit-visualize skill script
- **When** running `python3 scripts/visualize.py visualize --mode workflow`
- **Then** `workflow_graph.mmd` is produced in the graphs directory

### AC6: Existing modes unaffected (R5)

- **Given** the updated `visualize()` function
- **When** running `visualize(root, mode="file")` (or `class`, `call`)
- **Then** behavior is identical to before this change

## Target Call Chain

```
visualize(root, mode="workflow")
  → build_workflow_graph(root)          # STORY-slim-035
    → _parse_commands(commands_dir)
    → _parse_routing_table(rules_dir)
    → _scan_skill_files(skills_dir)
  → WorkflowGraph.to_mermaid()
  → write workflow_graph.mmd
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim036.py` | Tests for workflow mode integration | STORY-slim-035 | Low |
| 2 | `src/pactkit/skills/visualize.py` | Add `mode="workflow"` branch in `visualize()` | STORY-slim-035 | Low |
| 3 | `src/pactkit/skills/visualize.py` | Implement lazy check for workflow mode | Step 2 | Low |
| 4 | `src/pactkit/skills/visualize.py` | Ensure `to_mermaid()` produces subgraphs | STORY-slim-035 | Medium |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Reads local markdown files only |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- Workflow impact analysis (STORY-slim-037)
- Interactive filtering or focus on specific nodes
- Service dependency graph (STORY-slim-039)
- HTML/SVG rendering of the Mermaid diagram
