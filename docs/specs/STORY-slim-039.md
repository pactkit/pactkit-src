# STORY-slim-039: PDCA Sequence Parser

| Field | Value |
|-------|-------|
| ID | STORY-slim-039 |
| Status | Done |
| Priority | P2 — Impact 4, Effort 2 |
| Release | 2.3.7 |

## Background

Epic 1 (STORY-slim-035~038) built the workflow dependency graph with command→agent→skill→file vertical edges. Missing are the **horizontal** command→command sequence edges that represent the PDCA execution flow: Plan→Act→Check→Done. This sequence is defined in `project-sprint.md` as the orchestration order.

Without these edges, `workflow_impact` cannot answer: "If `/project-plan` breaks, does `/project-act` also fail?" because there is no edge connecting them.

## Requirements

### R1: Parse PDCA sequence from project-sprint.md (MUST)

A `_parse_pdca_sequence(commands_dir, graph)` function MUST parse `project-sprint.md` (or equivalent sprint orchestration file) and extract the command execution sequence. It MUST identify ordered pairs like (project-plan → project-act → project-check → project-done) and create `sequence` edges between them.

### R2: Sequence edge type (MUST)

`WorkflowEdge.relation` MUST accept `"sequence"` as a valid relation type. This represents "command A flows into command B" in the PDCA lifecycle.

### R3: Dashed edge rendering in to_mermaid() (MUST)

`WorkflowGraph.to_mermaid()` MUST render `sequence` edges as dashed arrows (`-.->`) instead of solid arrows (`-->`). All other relation types MUST continue to use solid arrows.

### R4: Integration into build_workflow_graph() (MUST)

`build_workflow_graph()` MUST call `_parse_pdca_sequence()` after the existing parsers, so the sequence edges appear in the generated `workflow_graph.mmd`.

### R5: Backward compatibility (MUST)

Existing edges (invokes, depends_on, contains) MUST NOT change rendering or behavior. Existing tests for STORY-slim-035~038 MUST continue to pass.

## Acceptance Criteria

### AC1: Sequence edges extracted from sprint file (R1)

- **Given** a commands directory containing `project-sprint.md` with PDCA orchestration steps (Plan→Act→Check→Done)
- **When** running `_parse_pdca_sequence(commands_dir, graph)`
- **Then** the graph contains `sequence` edges: project-plan→project-act, project-act→project-check, project-check→project-done

### AC2: Dashed rendering in Mermaid (R2, R3)

- **Given** a `WorkflowGraph` with both `invokes` and `sequence` edges
- **When** calling `to_mermaid()`
- **Then** `invokes` edges render as `-->|invokes|` and `sequence` edges render as `-.->|sequence|`

### AC3: Sequence edges in full workflow graph (R4)

- **Given** a PactKit installation with commands, skills, rules
- **When** running `build_workflow_graph(root)`
- **Then** the resulting graph contains ≥ 3 `sequence` edges connecting PDCA commands

### AC4: Existing edge types unchanged (R5)

- **Given** the updated `to_mermaid()` function
- **When** rendering a graph with only `invokes`/`depends_on`/`contains` edges (no `sequence`)
- **Then** the output is identical to the pre-change format (solid arrows only)

## Target Call Chain

```
build_workflow_graph(root)
  → _parse_commands(commands_dir, graph)          # existing
  → _parse_routing_table(rules_dir, graph)        # existing
  → _scan_skill_files(skills_dir, graph)          # existing
  → _parse_pdca_sequence(commands_dir, graph)     # NEW — extracts Plan→Act→Check→Done
  → return graph

WorkflowGraph.to_mermaid()
  → for e in edges:
       if e.relation == 'sequence': use '-.->|sequence|'
       else: use '-->|{relation}|'
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim039.py` | TDD: tests for sequence parsing and dashed rendering | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Add `_parse_pdca_sequence()` function | None | Medium |
| 3 | `src/pactkit/skills/visualize.py` | Modify `to_mermaid()` to render dashed edges for `sequence` | None | Low |
| 4 | `src/pactkit/skills/visualize.py` | Call `_parse_pdca_sequence()` in `build_workflow_graph()` | Steps 2-3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Parses local markdown files read-only |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- Parsing arbitrary orchestration formats (only project-sprint.md)
- Conditional/branching sequence edges (only linear PDCA flow)
- TopologyParser abstraction (STORY-slim-040)
- Non-PDCA command sequences (e.g., microservice deploy pipelines)
