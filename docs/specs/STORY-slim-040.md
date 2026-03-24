# STORY-slim-040: TopologyParser ABC + Auto-Detect

| Field | Value |
|-------|-------|
| ID | STORY-slim-040 |
| Status | Done |
| Priority | P1 — Impact 5, Effort 3 |
| Release | 2.3.7 |

## Background

The current workflow graph system is hardcoded for PactKit's PDCA topology (commands→agents→skills→files). To support microservice and frontend architectures, we need a `TopologyParser` abstraction that decouples parsing logic from the `build_workflow_graph()` orchestrator.

The key design constraint (per user requirement): topology type MUST be auto-detected from project file markers — **zero manual pactkit.yaml configuration**. This follows the same pattern as `_STACK_MARKERS` for language detection.

## Requirements

### R1: TopologyParser abstract base class (MUST)

A `TopologyParser` ABC MUST be defined in `visualize.py` with:
- A `markers` class attribute (`list[str]`) — file/directory markers for this topology (default empty)
- `detect(root: Path) -> bool` — **concrete default** that returns True if any `markers` entry exists under root. Subclasses MAY override for custom logic.
- `parse(root: Path) -> WorkflowGraph` — **abstract method** that parses the project and returns a WorkflowGraph

### R2: _TOPOLOGY_MARKERS constant (MUST)

A `_TOPOLOGY_MARKERS` dict MUST map topology names to lists of file/directory markers:
- `'pdca'`: `['.claude/commands/', 'pactkit.yaml']`
- `'service'`: `['docker-compose.yml', 'docker-compose.yaml', 'kubernetes/', 'k8s/', 'openapi.yaml', 'swagger.json']`
- `'frontend'`: `['next.config.js', 'next.config.ts', 'nuxt.config.ts', 'vite.config.ts', 'app/layout.tsx', 'pages/_app.tsx', 'src/router/', 'src/store/']`

### R3: detect_topology() dispatcher (MUST)

A `detect_topology(root: Path) -> list[str]` function MUST scan the project root against `_TOPOLOGY_MARKERS` and return a list of matching topology names. A project MAY match multiple topologies (e.g., monorepo with both service and frontend).

### R4: _TOPOLOGY_PARSERS registry (MUST)

A `_TOPOLOGY_PARSERS` dict MUST map topology names to `TopologyParser` subclass instances. `build_workflow_graph()` MUST use `detect_topology()` + `_TOPOLOGY_PARSERS` to select and invoke the appropriate parsers.

### R5: Backward-compatible build_workflow_graph() (MUST)

After STORY-slim-041 refactors `build_workflow_graph()` to use this registry, the output MUST remain identical for PactKit projects (excluding new sequence edges from STORY-slim-039). Existing tests for STORY-slim-035~038 MUST pass without modification.

### R6: Multi-topology merge (SHOULD)

When `detect_topology()` returns multiple matches, `build_workflow_graph()` SHOULD invoke all matching parsers and merge the resulting graphs (union of nodes and edges).

### R7: Zero pactkit.yaml configuration (MUST)

Topology detection MUST NOT require any manual entries in `pactkit.yaml`. The `_TOPOLOGY_MARKERS` scan is the sole detection mechanism.

## Acceptance Criteria

### AC1: TopologyParser ABC is abstract (R1)

- **Given** the `TopologyParser` class
- **When** attempting to instantiate it directly
- **Then** a `TypeError` is raised because `detect()` and `parse()` are abstract

### AC2: detect_topology identifies PDCA (R2, R3)

- **Given** a project root containing `.claude/commands/` directory
- **When** calling `detect_topology(root)`
- **Then** the result includes `'pdca'`

### AC3: detect_topology identifies service (R2, R3)

- **Given** a project root containing `docker-compose.yml`
- **When** calling `detect_topology(root)`
- **Then** the result includes `'service'`

### AC4: detect_topology identifies frontend (R2, R3)

- **Given** a project root containing `next.config.js`
- **When** calling `detect_topology(root)`
- **Then** the result includes `'frontend'`

### AC5: detect_topology returns empty for unknown (R3)

- **Given** a project root with no matching marker files
- **When** calling `detect_topology(root)`
- **Then** the result is an empty list

### AC6: Multi-topology detection (R3, R6)

- **Given** a project root containing both `docker-compose.yml` and `next.config.js`
- **When** calling `detect_topology(root)`
- **Then** the result includes both `'service'` and `'frontend'`

### AC7: build_workflow_graph backward compat (R4, R5)

- **Given** a PactKit project with commands, skills, rules
- **When** running `build_workflow_graph(root)` after STORY-slim-041 refactors it to use the registry
- **Then** the output graph has the same nodes and edges as the pre-refactor version (excluding sequence edges from STORY-slim-039)

### AC8: No pactkit.yaml required (R7)

- **Given** a project with no `pactkit.yaml` but with `.claude/commands/`
- **When** calling `detect_topology(root)` and `build_workflow_graph(root)`
- **Then** PDCA topology is detected and the workflow graph is built successfully

## Target Call Chain

```
build_workflow_graph(root)
  → detect_topology(root)                         # NEW — scan _TOPOLOGY_MARKERS
  → for topology in detected:
      parser = _TOPOLOGY_PARSERS[topology]
      graph.merge(parser.parse(root))             # Each parser returns WorkflowGraph
  → return merged_graph

detect_topology(root)
  → for name, markers in _TOPOLOGY_MARKERS.items():
      if any marker file/dir exists in root:
        matched.append(name)
  → return matched
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim040.py` | TDD: tests for TopologyParser ABC, detect_topology, registry | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Define `TopologyParser` ABC with `detect()` + `parse()` | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | Add `_TOPOLOGY_MARKERS` constant | None | Low |
| 4 | `src/pactkit/skills/visualize.py` | Implement `detect_topology()` function | Step 3 | Low |
| 5 | `src/pactkit/skills/visualize.py` | Add `_TOPOLOGY_PARSERS` registry (empty dict, populated by subclass stories) | Steps 2-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Scans directory structure only (os.path.exists) |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- ServiceParser implementation (STORY-slim-042)
- FrontendParser implementation (STORY-slim-045)
- Actual micro-service/frontend parsing logic
- Manual topology override in pactkit.yaml
