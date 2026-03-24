# STORY-slim-041: PdcaParser Refactor

| Field | Value |
|-------|-------|
| ID | STORY-slim-041 |
| Status | Draft |
| Priority | P2 — Impact 3, Effort 2 |
| Release | 2.3.7 |

## Background

STORY-slim-035 implemented `_parse_commands()`, `_parse_routing_table()`, `_scan_skill_files()` as standalone functions called by `build_workflow_graph()`. STORY-slim-040 introduces the `TopologyParser` ABC. This story wraps the existing PDCA parsing logic into a `PdcaParser(TopologyParser)` subclass, making it the first concrete implementation of the abstraction.

This is a **refactor-only** story — no new parsing logic is added. The sequence parsing from STORY-slim-039 is also included in PdcaParser's `parse()` method.

## Requirements

### R1: PdcaParser class (MUST)

A `PdcaParser(TopologyParser)` class MUST be defined with:
- `detect(root) -> bool`: Returns True if `.claude/commands/` or `commands/` directory exists under root, OR if `pactkit.yaml` exists under `.claude/` or `.opencode/`
- `parse(root) -> WorkflowGraph`: Calls existing `_parse_commands()`, `_parse_routing_table()`, `_scan_skill_files()`, and `_parse_pdca_sequence()` (from STORY-slim-039), returning the combined WorkflowGraph

### R2: Registered in _TOPOLOGY_PARSERS (MUST)

`PdcaParser` MUST be registered as `_TOPOLOGY_PARSERS['pdca'] = PdcaParser()`.

### R3: Directory discovery encapsulated (MUST)

The commands/rules/skills directory discovery logic currently in `build_workflow_graph()` MUST be moved into `PdcaParser.parse()`. The `build_workflow_graph()` function MUST delegate to parsers via the registry, not contain PDCA-specific path logic.

### R4: Explicit dir parameters preserved (MUST)

`build_workflow_graph()` MUST continue to accept `commands_dir`, `rules_dir`, `skills_dir` keyword arguments for testing purposes. When explicit dirs are provided, they MUST be passed through to `PdcaParser.parse()` (bypassing auto-detection).

### R5: Output equivalence (MUST)

For any PactKit project root, `build_workflow_graph(root)` MUST produce a graph with identical nodes and edges as the pre-refactor implementation (minus any new sequence edges from STORY-slim-039). All existing tests for STORY-slim-035~038 MUST pass.

### R6: Dynamic kind_order and kind_labels in to_mermaid() and workflow_impact() (MUST)

The hardcoded `kind_order` and `kind_labels` in `to_mermaid()` and `workflow_impact()` MUST be replaced with a dynamic mechanism. Each `TopologyParser` subclass MUST declare its supported node kinds and labels via class attributes (e.g., `kind_order = ['command', 'agent', 'skill', 'file']` and `kind_labels = {'command': 'Commands', ...}`). `to_mermaid()` and `workflow_impact()` MUST discover kinds from the graph's actual node kinds, falling back to parser-declared labels when available.

## Acceptance Criteria

### AC1: PdcaParser detects PDCA projects (R1)

- **Given** a project root with `.claude/commands/` directory
- **When** calling `PdcaParser().detect(root)`
- **Then** returns True

### AC2: PdcaParser returns complete graph (R1)

- **Given** a PactKit project with commands, skills, rules
- **When** calling `PdcaParser().parse(root)`
- **Then** the returned WorkflowGraph contains command, agent, skill, and file nodes with proper edges

### AC3: PdcaParser registered (R2)

- **Given** the `_TOPOLOGY_PARSERS` registry
- **When** looking up `_TOPOLOGY_PARSERS['pdca']`
- **Then** it is an instance of `PdcaParser`

### AC4: build_workflow_graph delegates to registry (R3)

- **Given** the refactored `build_workflow_graph()`
- **When** inspecting the function body
- **Then** it uses `detect_topology()` + `_TOPOLOGY_PARSERS` instead of directly calling `_parse_commands()` etc.

### AC5: Explicit dirs still work (R4)

- **Given** explicit `commands_dir`, `rules_dir`, `skills_dir` parameters
- **When** calling `build_workflow_graph(commands_dir=..., rules_dir=..., skills_dir=...)`
- **Then** the graph is built using those directories (same as pre-refactor behavior)

### AC6: Output equivalence verified (R5)

- **Given** a PactKit project root
- **When** comparing pre-refactor and post-refactor `build_workflow_graph(root)` output
- **Then** the same command/agent/skill/file nodes and invokes/depends_on/contains edges exist

### AC7: Dynamic kind_order in to_mermaid (R6)

- **Given** a WorkflowGraph containing nodes with kinds `service` and `api` (not in PDCA's kind_order)
- **When** calling `to_mermaid()`
- **Then** the output contains subgraph sections for "Services" and "APIs" (auto-discovered from node kinds)

## Target Call Chain

```
build_workflow_graph(root, commands_dir=None, rules_dir=None, skills_dir=None)
  → if explicit dirs provided:
      pdca = PdcaParser()
      return pdca.parse(root, commands_dir=..., rules_dir=..., skills_dir=...)
  → else:
      detect_topology(root)
      for topology in detected:
          parser = _TOPOLOGY_PARSERS[topology]
          sub_graph = parser.parse(root)
          merged_graph.merge(sub_graph)
      return merged_graph

PdcaParser.parse(root)
  → discover commands_dir, rules_dir, skills_dir
  → _parse_commands(commands_dir, graph)
  → _parse_routing_table(rules_dir, graph)
  → _scan_skill_files(skills_dir, graph)
  → _parse_pdca_sequence(commands_dir, graph)   # from STORY-slim-039
  → return graph
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim041.py` | TDD: tests for PdcaParser.detect(), PdcaParser.parse(), registry lookup | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Implement `PdcaParser(TopologyParser)` wrapping existing parsers | STORY-slim-039, STORY-slim-040 | Medium |
| 3 | `src/pactkit/skills/visualize.py` | Register `PdcaParser` in `_TOPOLOGY_PARSERS` | Step 2 | Low |
| 4 | `src/pactkit/skills/visualize.py` | Refactor `build_workflow_graph()` to delegate via registry | Steps 2-3 | Medium |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Same directory scanning as before — no new input vectors |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- New parsing logic (this is refactor-only + wiring STORY-slim-039)
- ServiceParser or FrontendParser (STORY-slim-042, 045)
- Multi-topology merge testing with real service/frontend projects
- WorkflowGraph.merge() method (simple node/edge union via add_node/add_edge is sufficient)
