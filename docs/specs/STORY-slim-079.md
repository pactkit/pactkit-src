# STORY-slim-079: TS/JS path alias resolution for file-mode dependency graph

| Field | Value |
|-------|-------|
| ID | STORY-slim-079 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.12 |

## Background

STORY-slim-078 added multi-language module resolution for `code_graph.mmd`, enabling Go and Java file edges. However, TS/JS projects using **path aliases** (e.g., `@/lib/utils`) still produce zero edges because `TSAnalyzer.normalize_import()` treats any import not starting with `.` as a bare/external package and returns `None`.

Most modern TS/JS frameworks use path aliases configured in `tsconfig.json` (or `jsconfig.json`) `compilerOptions.paths`:

```json
{ "paths": { "@/*": ["./src/*"] } }
```

This is the default configuration for Next.js, and similar patterns are used in Vue CLI, Angular, and custom setups. The import `@/lib/supabase/server` should resolve to `src/lib/supabase/server` — matching the `module_index` key from `build_module_keys()`.

Verified on `~/workspaces/phase-smith`: after STORY-slim-078, Go edges went from 0→37, but TS frontend still has 0 edges despite 30+ `.ts` files with `@/` imports.

## Requirements

### R1: Read tsconfig/jsconfig paths (MUST)

`TSAnalyzer` MUST provide a `_load_tsconfig_paths(root)` method that:
1. Searches for `tsconfig.json` or `jsconfig.json` in `root` (and common subdirectories like `frontend/`, `web/`, `client/` for monorepos)
2. Parses `compilerOptions.paths` into a list of `(alias_prefix, replacement_prefix)` tuples
3. Respects `compilerOptions.baseUrl` if present (defaults to tsconfig's parent directory)
4. Caches the result per `root` (avoid re-reading on every import)
5. Returns an empty list if no tsconfig/paths found (graceful degradation)

### R2: Resolve alias imports in normalize_import (MUST)

`TSAnalyzer.normalize_import()` MUST, before returning `None` for non-`.`-prefixed imports:
1. Check if the import matches any alias prefix from R1
2. If matched, replace the alias prefix with the resolved replacement path
3. Return the resolved slash-separated path (matching `build_module_keys` format)
4. If no alias matches and the import is not relative, return `None` (existing behavior)

### R3: Wildcard alias patterns (MUST)

The resolver MUST handle the standard tsconfig `paths` wildcard syntax:
- `"@/*": ["./src/*"]` — wildcard capture/replace (most common)
- `"@components/*": ["./src/components/*"]` — multi-segment prefix
- `"@config": ["./src/config"]` — exact match (no wildcard)

### R4: Backward compatibility (MUST)

Projects without `tsconfig.json` or without `compilerOptions.paths` MUST produce identical results as before. Relative imports (`./foo`, `../bar`) MUST continue to be resolved by the existing logic.

## Acceptance Criteria

### AC1: Next.js @/ alias resolves to src/ (R1, R2, R3)

- **Given** a TS project with `tsconfig.json` containing `"paths": { "@/*": ["./src/*"] }`
- **When** `normalize_import('@/lib/supabase/server', consumer_path, root)` is called
- **Then** it returns `'src/lib/supabase/server'`

### AC2: Multi-segment alias prefix (R3)

- **Given** `tsconfig.json` with `"paths": { "@components/*": ["./src/components/*"] }`
- **When** `normalize_import('@components/Button', consumer_path, root)` is called
- **Then** it returns `'src/components/Button'`

### AC3: Exact match alias (R3)

- **Given** `tsconfig.json` with `"paths": { "@config": ["./src/config"] }`
- **When** `normalize_import('@config', consumer_path, root)` is called
- **Then** it returns `'src/config'`

### AC4: baseUrl respected (R1)

- **Given** `tsconfig.json` with `"baseUrl": "."` and `"paths": { "@/*": ["./*"] }` (no src/ prefix)
- **When** `normalize_import('@/lib/utils', consumer_path, root)` is called
- **Then** it returns `'lib/utils'`

### AC5: No tsconfig — graceful degradation (R4)

- **Given** a TS project with no `tsconfig.json`
- **When** `normalize_import('@/lib/utils', consumer_path, root)` is called
- **Then** it returns `None` (same as before)

### AC6: Relative imports unchanged (R4)

- **Given** any TS project (with or without tsconfig)
- **When** `normalize_import('../lib/utils', consumer_path, root)` is called
- **Then** it resolves via existing relative path logic (unchanged)

### AC7: Monorepo subdir tsconfig (R1)

- **Given** a monorepo with `frontend/tsconfig.json` containing `"paths": { "@/*": ["./src/*"] }`
- **When** visualize scans from the monorepo root with `stacks: [node:frontend]`
- **Then** the tsconfig in `frontend/` is found and aliases resolve correctly

### AC8: Bare module still ignored (R2)

- **Given** any TS project
- **When** `normalize_import('react', consumer_path, root)` is called
- **Then** it returns `None` (external package, not an alias)

## Target Call Chain

```
TSAnalyzer.normalize_import(import_str='@/lib/utils', consumer_path, root)
  → _load_tsconfig_paths(root)                              [NEW: read & cache tsconfig.json paths]
    → find tsconfig.json / jsconfig.json in root (or stack subdir)
    → parse compilerOptions.paths → dict[prefix, replacement]
  → match import_str against alias prefixes
  → replace prefix with resolved path (relative to tsconfig baseUrl or root)
  → return slash-separated key (e.g., 'src/lib/utils')

_build_file_graph(...)
  → ... a.normalize_import(imported_module, p, root) ...    [UNCHANGED: line 386 of visualize.py]
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim079.py` | TDD: tests for AC1–AC8 | None | Low |
| 2 | `skills/analyzers/ts_analyzer.py` | Add `_load_tsconfig_paths(root)` — read & cache tsconfig paths | None | Low |
| 3 | `skills/analyzers/ts_analyzer.py` | Modify `normalize_import()` — alias resolution before bare-module check | Step 2 | Low |
| 4 | `skills/__init__.py` | Verify deploy-time inlining includes new `json` import if needed | Step 2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 User Input | N/A | No user input — reads tsconfig.json from project root |
| SEC-2 Auth | N/A | Local CLI only |
| SEC-3 Data Storage | N/A | Only reads JSON config, no writes |
| SEC-4 Secrets | N/A | tsconfig.json contains no secrets |
| SEC-5 Network | N/A | No network access |
| SEC-6 File Ops | Low | Reads tsconfig.json/jsconfig.json — bounded, local only |
| SEC-7 Error Handling | Low | JSON parse errors must be caught gracefully |
| SEC-8 Dependencies | N/A | Uses stdlib `json` only |

## Out of Scope

- `extends` in tsconfig.json (following config inheritance chains)
- Vite `resolve.alias` configuration (non-tsconfig alias systems)
- Webpack `resolve.alias` configuration
- Non-wildcard complex patterns beyond `prefix*` → `replacement*`
- Runtime path resolution (node_modules, package.json exports)
- `~` Sass/SCSS alias (different mechanism)
