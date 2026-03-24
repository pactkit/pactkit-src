# STORY-slim-042: ServiceParser

| Field | Value |
|-------|-------|
| ID | STORY-slim-042 |
| Status | Draft |
| Priority | P1 — Impact 5, Effort 4 |
| Release | 2.4.0 |

## Background

STORY-slim-040 introduces the `TopologyParser` ABC. This story implements `ServiceParser(TopologyParser)` — the first non-PDCA topology parser, targeting microservice architectures. It parses `docker-compose.yml`, `openapi.yaml`/`swagger.json`, and `*.proto` files to extract service→service, service→api, and service→grpc dependency edges.

This enables developers to run `visualize --mode workflow` on a microservice project and see the cross-service dependency graph without any manual configuration.

## Requirements

### R1: ServiceParser class (MUST)

A `ServiceParser(TopologyParser)` class MUST be defined with:
- `detect(root) -> bool`: Returns True if any of `docker-compose.yml`, `docker-compose.yaml`, `openapi.yaml`, `swagger.json` exist under root
- `parse(root) -> WorkflowGraph`: Parses service manifests and returns a WorkflowGraph with `service`, `api` node kinds and `calls_api`, `depends_on` edge relations

### R2: docker-compose parsing (MUST)

`ServiceParser` MUST parse `docker-compose.yml`/`docker-compose.yaml` using YAML `safe_load` and extract:
- Service names as `service` nodes
- `depends_on` entries as `depends_on` edges between services
- `links` entries (if present) as `depends_on` edges

### R3: OpenAPI/Swagger parsing (SHOULD)

`ServiceParser` SHOULD parse `openapi.yaml` or `swagger.json` and extract:
- API paths as `api` nodes (e.g., `GET /users`, `POST /orders`)
- Service name from `info.title` as the owning `service` node
- `calls_api` edges from service to its API endpoints

### R4: Proto file parsing (SHOULD)

`ServiceParser` SHOULD scan `*.proto` files using regex and extract:
- `service` declarations as `service` nodes
- `rpc` declarations as `api` nodes
- Edges from service to its RPC methods

### R5: Registered in _TOPOLOGY_PARSERS (MUST)

`ServiceParser` MUST be registered as `_TOPOLOGY_PARSERS['service'] = ServiceParser()`.

### R6: YAML safe_load only (MUST)

All YAML parsing MUST use `yaml.safe_load()`. If `pyyaml` is not available, parsing MUST fail gracefully with an empty graph (not crash).

## Acceptance Criteria

### AC1: ServiceParser detects docker-compose (R1)

- **Given** a project root containing `docker-compose.yml`
- **When** calling `ServiceParser().detect(root)`
- **Then** returns True

### AC2: docker-compose services extracted (R2)

- **Given** a `docker-compose.yml` with services `web`, `db`, `redis` where `web` depends_on `db` and `redis`
- **When** calling `ServiceParser().parse(root)`
- **Then** the graph contains 3 service nodes and 2 depends_on edges (web→db, web→redis)

### AC3: OpenAPI paths extracted (R3)

- **Given** an `openapi.yaml` with `info.title: "User Service"` and paths `/users` (GET, POST)
- **When** calling `ServiceParser().parse(root)`
- **Then** the graph contains a `service` node "User Service" and `api` nodes for the paths

### AC4: Proto services extracted (R4)

- **Given** a `user.proto` with `service UserService { rpc GetUser(...); rpc CreateUser(...); }`
- **When** calling `ServiceParser().parse(root)`
- **Then** the graph contains a `service` node "UserService" and `api` nodes for each rpc

### AC5: Graceful fallback without pyyaml (R6)

- **Given** an environment where `pyyaml` is not installed
- **When** calling `ServiceParser().parse(root)` on a project with `docker-compose.yml`
- **Then** an empty WorkflowGraph is returned (no crash)

### AC6: ServiceParser registered (R5)

- **Given** the `_TOPOLOGY_PARSERS` registry
- **When** looking up `_TOPOLOGY_PARSERS['service']`
- **Then** it is an instance of `ServiceParser`

## Target Call Chain

```
ServiceParser.parse(root)
  → _parse_docker_compose(root, graph)     # docker-compose.yml → service nodes + edges
  → _parse_openapi(root, graph)            # openapi.yaml → api nodes + edges
  → _parse_proto_files(root, graph)        # *.proto → service/rpc nodes + edges
  → return graph
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim042.py` | TDD: tests for ServiceParser with fixture files | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Implement `_parse_docker_compose()` | None | Medium |
| 3 | `src/pactkit/skills/visualize.py` | Implement `_parse_openapi()` | None | Medium |
| 4 | `src/pactkit/skills/visualize.py` | Implement `_parse_proto_files()` | None | Medium |
| 5 | `src/pactkit/skills/visualize.py` | Implement `ServiceParser` class + register | Steps 2-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Medium | Parses YAML/JSON files — must use safe_load, no eval |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | Low | Optional pyyaml dependency (already in project) |

## Out of Scope

- Source code scanning for HTTP client calls (future enhancement)
- MQ topic parsing (STORY-slim-044)
- Cross-service impact analysis (STORY-slim-043)
- Runtime dependency detection from logs/traces
