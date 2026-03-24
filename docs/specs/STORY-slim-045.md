# STORY-slim-045: FrontendParser — Route & Page

| Field | Value |
|-------|-------|
| ID | STORY-slim-045 |
| Status | Done |
| Priority | P2 — Impact 4, Effort 3 |
| Release | 2.4.0 |

## Background

STORY-slim-040 introduces the `TopologyParser` ABC. This story implements `FrontendParser(TopologyParser)` — the first phase, focusing on route configuration and page→component dependencies. It targets Next.js, Nuxt, and Vue Router projects, extracting the page/route structure and which components each page renders.

## Requirements

### R1: FrontendParser class (MUST)

A `FrontendParser(TopologyParser)` class MUST be defined with:
- `markers = ['next.config.js', 'next.config.ts', 'nuxt.config.ts', 'vite.config.ts', 'app/layout.tsx', 'pages/_app.tsx', 'src/router/']` — inherits default `detect()` from `TopologyParser` (STORY-slim-040 R1)
- `parse(root) -> WorkflowGraph`: Parses route config and component imports, returns WorkflowGraph with `page` and `component` node kinds

### R2: Next.js App Router detection (MUST)

For Next.js App Router projects (`app/` directory with `page.tsx`/`page.jsx` files):
- Each `app/**/page.tsx` MUST become a `page` node with route path derived from directory structure
- Import statements in page files MUST be parsed to create `page → component` edges with `renders` relation

### R3: Next.js Pages Router detection (SHOULD)

For Next.js Pages Router projects (`pages/` directory):
- Each `pages/**/*.tsx` (except `_app.tsx`, `_document.tsx`) MUST become a `page` node
- Import statements MUST be parsed for component dependencies

### R4: Vue Router detection (SHOULD)

For Vue/Nuxt projects with `src/router/index.ts` or `nuxt.config.ts`:
- Route definitions SHOULD be parsed to extract page→component mappings
- Each route's `component` import SHOULD create a `renders` edge

### R5: Component import parsing via tree-sitter (MUST)

Import statements in page/component files MUST be parsed using tree-sitter (if available) or regex fallback to extract:
- Named imports: `import { Button } from './components/Button'`
- Default imports: `import Layout from '@/components/Layout'`
- Only local project imports are tracked (skip `node_modules` packages)

### R6: Registered in _TOPOLOGY_PARSERS (MUST)

`FrontendParser` MUST be registered as `_TOPOLOGY_PARSERS['frontend'] = FrontendParser()`.

## Acceptance Criteria

### AC1: FrontendParser detects Next.js (R1)

- **Given** a project root containing `next.config.js`
- **When** calling `FrontendParser().detect(root)`
- **Then** returns True

### AC2: App Router pages extracted (R2)

- **Given** a Next.js App Router project with `app/dashboard/page.tsx` importing `<DashboardChart />`
- **When** calling `FrontendParser().parse(root)`
- **Then** the graph contains a `page` node `/dashboard` and a `component` node `DashboardChart` with a `renders` edge

### AC3: Pages Router pages extracted (R3)

- **Given** a Next.js Pages Router project with `pages/about.tsx`
- **When** calling `FrontendParser().parse(root)`
- **Then** the graph contains a `page` node `/about`

### AC4: Vue Router routes extracted (R4)

- **Given** a Vue project with `src/router/index.ts` defining route `{ path: '/login', component: LoginPage }`
- **When** calling `FrontendParser().parse(root)`
- **Then** the graph contains a `page` node `/login` and a `component` node `LoginPage`

### AC5: Only local imports tracked (R5)

- **Given** a page file importing `react` (npm) and `./components/Header` (local)
- **When** parsing imports
- **Then** only `Header` creates a `component` node; `react` is ignored

### AC6: FrontendParser registered (R6)

- **Given** the `_TOPOLOGY_PARSERS` registry
- **When** looking up `_TOPOLOGY_PARSERS['frontend']`
- **Then** it is an instance of `FrontendParser`

## Target Call Chain

```
FrontendParser.parse(root)
  → _detect_frontend_framework(root)           # next/nuxt/vue/vite
  → _parse_app_router_pages(root, graph)       # app/**/page.tsx → page nodes
  → _parse_pages_router(root, graph)           # pages/**/*.tsx → page nodes
  → _parse_vue_routes(root, graph)             # src/router/index.ts → page nodes
  → _parse_component_imports(page_files, graph) # import analysis → component edges
  → return graph
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim045.py` | TDD: tests with fixture frontend project structures | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Implement `_detect_frontend_framework()` | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | Implement `_parse_app_router_pages()` + `_parse_pages_router()` | None | Medium |
| 4 | `src/pactkit/skills/visualize.py` | Implement `_parse_component_imports()` using tree-sitter/regex | None | High |
| 5 | `src/pactkit/skills/visualize.py` | Implement `FrontendParser` class + register | Steps 2-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Reads local source files — no eval/exec |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | Low | Optional tree-sitter dependency for import parsing |

## Out of Scope

- Hook and store dependency analysis (STORY-slim-046)
- Dynamic imports / code splitting analysis
- CSS/style dependencies
- Server component vs client component distinction (Next.js 13+)
