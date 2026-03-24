# STORY-slim-043: Cross-Service Impact

| Field | Value |
|-------|-------|
| ID | STORY-slim-043 |
| Status | Done |
| Priority | P1 — Impact 5, Effort 4 |
| Release | 2.4.0 |

## Background

STORY-slim-042 builds the `ServiceParser` that creates a WorkflowGraph of service→api dependencies. This story adds cross-service impact analysis: given a changed API endpoint or service, trace the dependency graph backward to find all upstream services that will be affected.

This is the microservice equivalent of STORY-slim-037's `workflow_impact()` — same `reverse_reach()` algorithm, applied to service topology.

## Requirements

### R1: Service impact via existing workflow_impact (MUST)

The existing `workflow_impact(target, entry)` function (from STORY-slim-037) MUST work with service topology graphs. Since `ServiceParser` produces a standard `WorkflowGraph`, `reverse_reach()` MUST traverse service→api→service edges correctly.

### R2: Service-specific output format (MUST)

When running impact analysis on a service graph, the output MUST group results by service-specific node kinds (leveraging dynamic kind_labels from STORY-slim-041 R6):
```
Workflow Impact for "user-service":
  Services: order-service, notification-service
  APIs: POST /orders, GET /notifications
```

### R3: Changed API endpoint matching (MUST)

The `regression_workflow_impact()` function MUST match changed source files against service nodes. When a file belonging to a known service is changed, it MUST report affected downstream services.

### R4: CLI integration (SHOULD)

Running `pactkit impact --mode workflow --entry user-service` on a microservice project SHOULD list all services that depend on `user-service`.

## Acceptance Criteria

### AC1: reverse_reach works on service graph (R1)

- **Given** a WorkflowGraph where `order-service` calls_api `user-service/GET /users`
- **When** calling `reverse_reach("user-service")`
- **Then** the result includes `order-service`

### AC2: Service-grouped output (R2)

- **Given** a service topology with 3 services and cross-dependencies
- **When** running `workflow_impact(root, entry="user-service")`
- **Then** output lists affected Services and APIs grouped by kind

### AC3: Regression gate detects service impact (R3)

- **Given** a changed file `services/user/handler.py` in a microservice project
- **When** running `regression_workflow_impact(target, changed_files)`
- **Then** output includes "Workflow Impact: user-service changed → affects: order-service, notification-service"

### AC4: CLI impact works (R4)

- **Given** a microservice project with ServiceParser-detected topology
- **When** running `pactkit impact --mode workflow --entry user-service`
- **Then** affected services are listed

## Target Call Chain

```
workflow_impact(root, entry="user-service")
  → build_workflow_graph(root)                # detect_topology → ServiceParser
  → graph.reverse_reach("user-service")       # existing algorithm
  → format and print by kind (service, api)   # existing grouping logic
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim043.py` | TDD: tests for service impact analysis | STORY-slim-042 | Low |
| 2 | `src/pactkit/skills/visualize.py` | Extend kind_labels in workflow_impact for service/api kinds | STORY-slim-042 | Low |
| 3 | `src/pactkit/skills/visualize.py` | Extend regression_workflow_impact file→service matching | STORY-slim-042 | Medium |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Same as existing workflow_impact — string lookup in dict |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- Automatic service-to-directory mapping (heuristic only)
- MQ topic impact (STORY-slim-044)
- Weighted impact scoring
- Slack/email notifications for cross-service impact
