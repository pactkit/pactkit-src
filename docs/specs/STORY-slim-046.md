# STORY-slim-046: FrontendParser — Hook & Store

| Field | Value |
|-------|-------|
| ID | STORY-slim-046 |
| Status | Done |
| Priority | P3 — Impact 3, Effort 3 |
| Release | 2.4.0 |

## Background

STORY-slim-045 implements page→component dependencies in `FrontendParser`. This story extends it to cover the deeper dependency chain: component→hook→store. Hooks (React `use*`, Vue `composables`) and state stores (Redux slices, Zustand stores, Pinia stores) are the invisible connective tissue of frontend apps — changes to them can silently break many pages.

## Requirements

### R1: Hook node kind and uses_hook edge (MUST)

The WorkflowGraph MUST support:
- `hook` as a valid node kind (e.g., `useAuth`, `useCart`, `useI18n`)
- `uses_hook` as a valid edge relation (component → hook)

### R2: Store node kind and reads_store edge (MUST)

The WorkflowGraph MUST support:
- `store` as a valid node kind (e.g., `authSlice`, `cartStore`, `userStore`)
- `reads_store` as a valid edge relation (hook → store or component → store)

### R3: Hook detection from source files (MUST)

`FrontendParser` MUST detect custom hooks:
- React: files in `src/hooks/` or files exporting `use*` functions
- Vue: files in `composables/` or `src/composables/`
- Usage: components importing and calling `use*` functions

### R4: Store detection from source files (MUST)

`FrontendParser` MUST detect state stores:
- Redux: files using `createSlice()` in `src/store/` or `src/slices/`
- Zustand: files using `create()` from `zustand`
- Pinia: files using `defineStore()` in `src/stores/`

### R5: Component→hook→store chain (MUST)

The parser MUST create the full chain: if `LoginPage` imports `useAuth` which imports `authStore`, then edges MUST exist: `LoginPage --uses_hook--> useAuth --reads_store--> authStore`.

## Acceptance Criteria

### AC1: Hook nodes from hooks directory (R1, R3)

- **Given** a project with `src/hooks/useAuth.ts` exporting `useAuth`
- **When** calling `FrontendParser().parse(root)`
- **Then** the graph contains a `hook` node `useAuth`

### AC2: Component→hook edge (R1, R3)

- **Given** a component `LoginForm.tsx` importing `useAuth` from `../hooks/useAuth`
- **When** parsing imports
- **Then** a `uses_hook` edge exists: `LoginForm → useAuth`

### AC3: Store nodes from store directory (R2, R4)

- **Given** a project with `src/store/authSlice.ts` using `createSlice()`
- **When** calling `FrontendParser().parse(root)`
- **Then** the graph contains a `store` node `authSlice`

### AC4: Hook→store edge (R2, R5)

- **Given** `useAuth.ts` importing from `../store/authSlice`
- **When** parsing imports
- **Then** a `reads_store` edge exists: `useAuth → authSlice`

### AC5: Full chain traversal (R5)

- **Given** a graph with `LoginPage --renders--> LoginForm --uses_hook--> useAuth --reads_store--> authSlice`
- **When** calling `reverse_reach("authSlice")`
- **Then** the result includes `useAuth`, `LoginForm`, and `LoginPage`

## Target Call Chain

```
FrontendParser.parse(root)
  → ... (page/component from STORY-slim-045)
  → _scan_hooks(root, graph)                # src/hooks/, composables/ → hook nodes
  → _scan_stores(root, graph)               # src/store/, src/stores/ → store nodes
  → _parse_hook_store_imports(graph)         # component→hook, hook→store edges
  → return graph
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim046.py` | TDD: tests for hook/store detection and edge creation | STORY-slim-045 | Low |
| 2 | `src/pactkit/skills/visualize.py` | Implement `_scan_hooks()` | STORY-slim-045 | Medium |
| 3 | `src/pactkit/skills/visualize.py` | Implement `_scan_stores()` | STORY-slim-045 | Medium |
| 4 | `src/pactkit/skills/visualize.py` | Implement `_parse_hook_store_imports()` | Steps 2-3 | Medium |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Reads local source files — regex/tree-sitter only |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies beyond STORY-slim-045 |

## Out of Scope

- Runtime state tracking
- Computed/derived state analysis
- Zustand middleware chain analysis
- Redux saga/thunk dependency tracking
- Frontend impact analysis (STORY-slim-047)
