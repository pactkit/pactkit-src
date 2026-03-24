# STORY-slim-035: Workflow Parser

| Field | Value |
|-------|-------|
| ID | STORY-slim-035 |
| Status | Done |
| Priority | P1 — Impact 5, Effort 3 |
| Release | TBD |

## Background

PactKit has 11 commands, 11 skills, 7 rules, and multiple agent roles. These components form a dependency graph: `/project-sprint` invokes `system-architect` (Plan) → `senior-developer` (Act) → `qa-engineer` (Check) → `repo-maintainer` (Done). Each command references skills (e.g., `pactkit-board`, `pactkit-trace`), reads/writes files (e.g., `sprint_board.md`, `specs/*.md`), and is executed by a specific agent role.

Currently, these dependencies are implicit — embedded in markdown command files and routing tables. This story extracts them into a structured `WorkflowGraph` data model that can be queried and visualized.

## Requirements

### R1: WorkflowNode and WorkflowEdge data model (MUST)

A `WorkflowGraph` data structure MUST be defined in `src/pactkit/skills/visualize.py` with:
- `WorkflowNode(id, kind, label)` where `kind` is one of: `command`, `agent`, `skill`, `file`
- `WorkflowEdge(source, target, relation)` where `relation` is one of: `invokes`, `depends_on`, `reads`, `writes`
- `WorkflowGraph(nodes, edges)` with methods `add_node()`, `add_edge()`, and `to_mermaid()`

### R2: Command parser (MUST)

A `_parse_commands(commands_dir)` function MUST parse command markdown files and extract:
- Command name (from filename: `project-act.md` → `project-act`)
- Agent role (from `Role:` or `Agent:` line in the command header)
- Referenced skills (from `pactkit-*` mentions in the command body)
- Referenced artifact files (from `docs/specs/`, `docs/product/`, `tests/` path mentions)

### R3: Routing table parser (MUST)

A `_parse_routing_table(rules_dir)` function MUST parse `rules/04-routing-table.md` and extract the command→agent→playbook mapping from the structured tables.

### R4: Skill file scanner (MUST)

A `_scan_skill_files(skills_dir)` function MUST discover skill directories and their script files, creating skill→file edges.

### R5: Build complete workflow graph (MUST)

A `build_workflow_graph(root)` function MUST combine R2-R4 parsers to build a complete `WorkflowGraph` containing all commands, agents, skills, and files with their dependency edges.

### R6: Standalone script compatible (MUST)

All new code MUST work within `visualize.py` as a standalone script — no pactkit library imports allowed. Path discovery MUST use `pactkit.yaml` or well-known locations (`~/.claude/commands/`, `~/.claude/skills/`, `~/.claude/rules/`).

## Acceptance Criteria

### AC1: WorkflowGraph model works (R1)

- **Given** a `WorkflowGraph` instance
- **When** adding nodes and edges
- **Then** `to_mermaid()` produces valid Mermaid `graph TD` output

### AC2: Command parser extracts dependencies (R2)

- **Given** a directory with PactKit command files (e.g., `project-act.md`, `project-done.md`)
- **When** running `_parse_commands()`
- **Then** command nodes, agent nodes, skill edges, and file edges are extracted

### AC3: Routing table parsed (R3)

- **Given** `rules/04-routing-table.md` with the standard format
- **When** running `_parse_routing_table()`
- **Then** all 11 commands map to their agent roles

### AC4: Skill files discovered (R4)

- **Given** a skills directory with `pactkit-board/`, `pactkit-trace/`, etc.
- **When** running `_scan_skill_files()`
- **Then** skill→file edges are created for each script file

### AC5: Complete graph non-empty (R5)

- **Given** a PactKit installation with commands, skills, and rules
- **When** running `build_workflow_graph()`
- **Then** the graph contains ≥ 11 command nodes, ≥ 5 skill nodes, and ≥ 20 edges

### AC6: Standalone script works (R6)

- **Given** `visualize.py` running as a standalone script (no pactkit library imports)
- **When** calling `build_workflow_graph(root)` with a valid PactKit root
- **Then** the function discovers commands, skills, and rules via `pactkit.yaml` or well-known paths without import errors

## Target Call Chain

```
build_workflow_graph(root)
  → _parse_commands(commands_dir)       # command→agent, command→skill edges
  → _parse_routing_table(rules_dir)     # command→agent→playbook edges
  → _scan_skill_files(skills_dir)       # skill→file edges
  → WorkflowGraph.add_node() / .add_edge()
  → return WorkflowGraph
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim035.py` | Tests for WorkflowGraph model and parsers | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | WorkflowNode, WorkflowEdge, WorkflowGraph dataclasses | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | `_parse_commands()` with regex extraction | None | Medium |
| 4 | `src/pactkit/skills/visualize.py` | `_parse_routing_table()` table parser | None | Low |
| 5 | `src/pactkit/skills/visualize.py` | `_scan_skill_files()` directory scanner | None | Low |
| 6 | `src/pactkit/skills/visualize.py` | `build_workflow_graph()` combining all parsers | Steps 3-5 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Parses local markdown files read-only |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- Microservice/OpenAPI/gRPC parsing (PRD Epic 2, S8)
- Mermaid visualization output integration (STORY-slim-036)
- Impact analysis (STORY-slim-037)
- Dynamic dependency detection from runtime logs
