# STORY-slim-047: Frontend Impact

| Field | Value |
|-------|-------|
| ID | STORY-slim-047 |
| Status | Draft |
| Priority | P2 — Impact 4, Effort 3 |
| Release | 2.4.0 |

## Background

STORY-slim-045 and 046 build the frontend topology graph (page→component→hook→store). This story adds frontend-specific impact analysis: given a changed hook or store, trace backward to find all affected pages and route guards. This is the frontend equivalent of STORY-slim-037's `workflow_impact()`.

## Requirements

### R1: Frontend impact via existing reverse_reach (MUST)

The existing `reverse_reach()` algorithm MUST work on frontend topology graphs. Since `FrontendParser` produces a standard `WorkflowGraph`, traversal through `page --renders--> component --uses_hook--> hook --reads_store--> store` chains MUST work without modification.

### R2: Frontend-specific kind labels (MUST)

The `workflow_impact()` output MUST include frontend-specific kind labels:
```
Workflow Impact for "useAuth":
  Pages: /login, /dashboard, /settings
  Components: LoginForm, AuthGuard, UserMenu
  Stores: authSlice
```

### R3: Route guard impact detection (MUST)

If a `guards` edge exists (page → hook used as route guard), changing the guard hook MUST surface all guarded pages in the impact output.

### R4: Regression gate integration (MUST)

`regression_workflow_impact()` MUST match changed `.tsx`/`.ts` files in `hooks/` or `store/` directories against frontend graph nodes and report affected pages.

## Acceptance Criteria

### AC1: reverse_reach through frontend chain (R1)

- **Given** a graph: `/dashboard --renders--> DashboardChart --uses_hook--> useData --reads_store--> dataSlice`
- **When** calling `reverse_reach("dataSlice")`
- **Then** result includes `useData`, `DashboardChart`, `/dashboard`

### AC2: Frontend kind labels in output (R2)

- **Given** a frontend topology graph
- **When** running `workflow_impact(root, entry="useAuth")`
- **Then** output groups results as Pages, Components, Hooks, Stores

### AC3: Guard impact surfaced (R3)

- **Given** a graph where `/admin --guards--> useAuth`
- **When** calling `reverse_reach("useAuth")`
- **Then** result includes `/admin`

### AC4: Regression detects hook change (R4)

- **Given** a changed file `src/hooks/useAuth.ts`
- **When** running `regression_workflow_impact(target, ["src/hooks/useAuth.ts"])`
- **Then** output includes affected pages

## Target Call Chain

```
workflow_impact(root, entry="useAuth")
  → build_workflow_graph(root)              # detect_topology → FrontendParser
  → graph.reverse_reach("useAuth")          # existing algorithm
  → format by kind (page, component, hook, store)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim047.py` | TDD: tests for frontend impact traversal and output | STORY-slim-046 | Low |
| 2 | `src/pactkit/skills/visualize.py` | Add frontend kind labels to `workflow_impact()` and `regression_workflow_impact()` | STORY-slim-046 | Low |
| 3 | `src/pactkit/skills/visualize.py` | Add `hooks/`/`store/` directory matching in regression_workflow_impact | STORY-slim-046 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Same as existing workflow_impact — string lookup |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- Visual diff of impacted UI pages
- Automated screenshot comparison
- Performance impact analysis (bundle size changes)
- Cross-topology impact (frontend + service combined — STORY-slim-048)
