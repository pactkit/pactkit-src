# STORY-slim-080: Deep monorepo scanning: nearest-ancestor config discovery for all analyzers

| Field | Value |
|-------|-------|
| ID | STORY-slim-080 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.12 |

## Background

STORY-slim-078 added multi-language file-mode dependency graphs, and STORY-slim-079 added TS path alias resolution via `tsconfig.json`. Both work correctly in flat projects and depth-1 monorepos (e.g., `frontend/tsconfig.json`). However, two systemic gaps remain:

**1. Config discovery is inconsistent across analyzers:**
- **TS** `_load_tsconfig_paths`: searches root + depth-1 subdirs (STORY-slim-079)
- **Go** `_read_go_module_prefix`: searches root then walks **upward** via `root.parents` — never searches child subdirs
- **Java/Python**: no config file needed currently (no gap)

**2. `_detect_stacks` only scans depth-1 subdirectories:**
The monorepo stack detection (STORY-slim-077) checks `root/` and `root/*/` for marker files (`go.mod`, `package.json`, etc.). In deeper layouts like Turborepo (`packages/web/`), Nx (`apps/frontend/`), or pnpm workspaces (`services/api/`), stacks at depth-2+ are invisible — their files are never scanned, producing zero edges.

**Note**: `_scan_files` already uses `rglob` and finds source files at **any depth**. The problem is not file discovery — it's that (a) stacks aren't detected if their marker is deeper than depth-1, and (b) each scanned file can't find its language-specific config (tsconfig, go.mod) because discovery doesn't walk upward from the file's location.

**Correct approach — nearest-ancestor pattern**: For each source file found by `rglob`, walk upward from its parent directory to `root`, looking for the nearest config file. This mirrors how real toolchains work (`tsc` walks up for `tsconfig.json`, `go` walks up for `go.mod`). Multiple configs at different levels are correctly associated with their respective files.

Verified on `~/workspaces/phase-smith`: Go 37 + TS 4 edges. The 4 TS edges exist only because STORY-slim-079 added depth-1 subdir search. A Turborepo layout (`packages/web/tsconfig.json`) would still produce 0 TS edges.

## Requirements

### R1: Extend `_detect_stacks` to scan all depths (MUST)

`_detect_stacks(root)` MUST search for stack marker files (`go.mod`, `package.json`, `tsconfig.json`, `pom.xml`, `pyproject.toml`, etc.) at **all directory depths** under `root`, not just depth-0 and depth-1. The search MUST respect `SCAN_EXCLUDES` (skip `node_modules`, `.venv`, `vendor`, etc.) to avoid false positives from dependency directories.

### R2: Nearest-ancestor config discovery for TS (MUST)

`TSAnalyzer._load_tsconfig_paths` MUST be refactored to use a **nearest-ancestor** pattern:
1. Accept the **source file path** (not just root) as context
2. Walk from the source file's parent directory upward to `root`, looking for `tsconfig.json` or `jsconfig.json`
3. Use the **nearest** config found for that file
4. Cache results per **config file path** (not per root) to avoid redundant reads
5. Multiple tsconfigs at different levels (e.g., `frontend/tsconfig.json` and `packages/ui/tsconfig.json`) MUST each be used for their respective files

### R3: Nearest-ancestor config discovery for Go (MUST)

`GoAnalyzer._read_go_module_prefix` MUST be refactored to use the same nearest-ancestor pattern:
1. Accept the **source file path** as context
2. Walk from the source file's parent directory upward to `root`, looking for `go.mod`
3. Use the nearest `go.mod` found — its `module` line defines the import prefix for that file's package
4. Cache results per **go.mod path**
5. Multiple go.mod files in a multi-module monorepo (e.g., `backend/go.mod` and `gateway/go.mod`) MUST each be used for their respective files

### R4: Plumb source file path through normalize_import (MUST)

`normalize_import(import_str, consumer_path, root)` already receives `consumer_path`. The analyzer's internal config discovery methods MUST use `consumer_path` (the importing file) to find the nearest ancestor config, rather than searching from `root` downward.

### R5: Backward compatibility (MUST)

- Flat projects (single `tsconfig.json` or `go.mod` at root) MUST produce identical results
- Projects without config files MUST degrade gracefully (empty aliases, None module prefix)
- `_scan_files` behavior MUST NOT change (already correct — uses `rglob`)
- Python and Java analyzers MUST NOT be affected (no config discovery needed)

## Acceptance Criteria

### AC1: Depth-2 stack detection (R1)

- **Given** a monorepo with `packages/web/package.json` and `packages/api/go.mod` (depth-2)
- **When** `_detect_stacks(root)` is called
- **Then** it returns `['node', 'go']` (both stacks detected)

### AC2: TS nearest-ancestor tsconfig (R2, R4)

- **Given** a monorepo with `apps/frontend/tsconfig.json` containing `"paths": {"@/*": ["./src/*"]}` and source file `apps/frontend/src/app/page.ts` importing `@/lib/utils`
- **When** `normalize_import('@/lib/utils', apps/frontend/src/app/page.ts, root)` is called
- **Then** it returns `'apps/frontend/src/lib/utils'`

### AC3: Go nearest-ancestor go.mod (R3, R4)

- **Given** a monorepo with `services/api/go.mod` (module `github.com/org/api`) and source file `services/api/internal/handler.go` importing `github.com/org/api/internal/db`
- **When** `normalize_import('github.com/org/api/internal/db', services/api/internal/handler.go, root)` is called
- **Then** it returns `services/api/internal/db`

### AC4: Multiple tsconfigs at different levels (R2)

- **Given** `frontend/tsconfig.json` with `"@/*": ["./src/*"]` AND `packages/ui/tsconfig.json` with `"@ui/*": ["./components/*"]`
- **When** a file in `frontend/src/` imports `@/lib/utils` and a file in `packages/ui/src/` imports `@ui/Button`
- **Then** each resolves using its nearest tsconfig: `frontend/src/lib/utils` and `packages/ui/components/Button`

### AC5: Multiple go.mod files (R3)

- **Given** `backend/go.mod` (module `backend`) and `gateway/go.mod` (module `gateway`)
- **When** `backend/cmd/main.go` imports `backend/internal/db` and `gateway/cmd/main.go` imports `gateway/routes`
- **Then** each strips its respective module prefix correctly

### AC6: Flat project unchanged (R5)

- **Given** a project with `tsconfig.json` at root containing `"@/*": ["./src/*"]`
- **When** `normalize_import('@/lib/utils', src/app/page.ts, root)` is called
- **Then** it returns `'src/lib/utils'` (identical to STORY-slim-079)

### AC7: No config graceful degradation (R5)

- **Given** a TS project with no `tsconfig.json` at any level
- **When** `normalize_import('@/lib/utils', ...)` is called
- **Then** it returns `None`

### AC8: SCAN_EXCLUDES respected in stack detection (R1)

- **Given** a project with `node_modules/some-pkg/go.mod`
- **When** `_detect_stacks(root)` is called
- **Then** it does NOT detect `go` from node_modules (excluded directory)

### AC9: Deeply nested stacks (R1)

- **Given** a monorepo with `services/billing/api/go.mod` (depth-3)
- **When** `_detect_stacks(root)` is called
- **Then** it detects `go`

## Target Call Chain

```
visualize(root, mode='file')
  → _detect_stacks(root)                                  [CHANGED: rglob for markers, respect SCAN_EXCLUDES]
    → yields stack names (e.g. ['go', 'node'])
  → for stk in stacks:
      _scan_files(root, file_ext=ext, analyzer=stk_analyzer)  [UNCHANGED: already uses rglob]
        → for p in scan_root.rglob('*.ts'):
            analyzer.build_module_keys(rel_path, root)

  → _build_file_graph(root, all_files, module_index, ...)
      → for p in all_files:
          a.normalize_import(imported_module, p, root)
            → TSAnalyzer: _find_nearest_tsconfig(p, root)    [NEW: walk p.parent→root for tsconfig.json]
              → _load_tsconfig_paths(tsconfig_path)           [CHANGED: keyed by tsconfig path, not root]
              → match alias → return resolved path
            → GoAnalyzer: _find_nearest_go_mod(p, root)      [NEW: walk p.parent→root for go.mod]
              → _read_go_module_prefix(go_mod_path)           [CHANGED: keyed by go.mod path]
              → strip module prefix → return relative path
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim080.py` | TDD: tests for AC1–AC9 | None | Low |
| 2 | `skills/visualize.py` | Refactor `_detect_stacks` — rglob for markers with SCAN_EXCLUDES | None | Medium |
| 3 | `skills/analyzers/ts_analyzer.py` | Add `_find_nearest_tsconfig(file_path, root)` — ancestor walk; refactor `_load_tsconfig_paths` to key by tsconfig path | Step 2 | Low |
| 4 | `skills/analyzers/go_analyzer.py` | Add `_find_nearest_go_mod(file_path, root)` — ancestor walk; refactor `_read_go_module_prefix` to key by go.mod path | Step 2 | Low |
| 5 | `skills/__init__.py` | Verify deployed script inlining still works with refactored methods | Steps 3–4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 User Input | N/A | No user input — reads config files from project tree |
| SEC-2 Auth | N/A | Local CLI only |
| SEC-3 Data Storage | N/A | Only reads JSON/text config, no writes |
| SEC-4 Secrets | N/A | Config files contain no secrets |
| SEC-5 Network | N/A | No network access |
| SEC-6 File Ops | Low | Reads tsconfig.json/go.mod — bounded by SCAN_EXCLUDES, local only |
| SEC-7 Error Handling | Low | JSON/text parse errors must be caught gracefully |
| SEC-8 Dependencies | N/A | Uses stdlib `json` and `re` only |

## Out of Scope

- `tsconfig.json` `extends` field (config inheritance chains — separate story)
- Vite/Webpack/Rollup `resolve.alias` (non-tsconfig alias systems)
- Automatic `pactkit.yaml` `stacks` list update when deeper stacks detected
- Java Gradle/Maven multi-module config discovery (Java has package-based imports, no path rewriting needed)
- Python virtualenv detection (already handled by SCAN_EXCLUDES)
- Symlink following (could cause infinite loops)
