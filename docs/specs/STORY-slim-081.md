# STORY-slim-081: Two-tier module graph with scoped focus for large codebases

| Field | Value |
|-------|-------|
| ID | STORY-slim-081 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.12 |

## Background

When `pactkit visualize` runs on large codebases (Dubbo: 4000+ Java files, FastAPI: 1100+ Python files), the scan is truncated at `MAX_SCAN_FILES=500`. The resulting graph is incomplete, and even if the limit were raised, a 500+ node Mermaid graph is unreadable.

The root cause is architectural: the current design produces a single flat file-level graph for any project size. Large projects need a **two-tier approach**:

1. **Module Graph** (Level 1): Each directory containing a build/config marker file (`pom.xml`, `go.mod`, `package.json`, `pyproject.toml`) is a "module" node. Edges are aggregated cross-module imports with weight labels. This graph is always small (typically 5-50 nodes) and readable for any project size.

2. **Scoped File Graph** (Level 2): `--focus <module>` scans only files within the focused module directory, not the entire repo. This avoids truncation because individual modules are typically 50-200 files.

The module graph also serves as a **navigation map**: its nodes are the valid `--focus` targets.

Validated on real projects:
- **Dubbo** (Apache): 4040 Java files, 119 pom.xml modules, depth-16 — needs module graph
- **FastAPI**: 1118 Python files — truncated at 500
- **phase-smith**: 88 files (Go+TS) — no truncation, but module graph still useful for overview
- **Spring PetClinic**: 47 Java files — small enough for file graph, no module graph needed

## Requirements

### R1: Module boundary detection (MUST)

Detect module boundaries by scanning for marker files (`_STACK_MARKERS`) via `rglob`. Each directory containing a marker file defines a module. Return a list of `(module_name, module_dir, stack)` tuples.

- Module name = directory path relative to root (e.g., `dubbo-common`, `backend`, `frontend`)
- Root-level marker → module name is the project name (from `pyproject.toml`/`pom.xml`) or `.` 
- MUST respect `SCAN_EXCLUDES` (skip `node_modules`, `.venv`, `vendor`, etc.)
- MUST reuse existing `_STACK_MARKERS` as the canonical marker list

### R2: Module-level graph generation (MUST)

New `--mode module` that produces a Mermaid graph where:
- Each node = one module (from R1)
- Each edge = at least one cross-module import exists between source and target module
- Edge labels show the import count (e.g., `-->|87|`)
- Output file: `docs/architecture/graphs/module_graph.mmd`
- Node click links to the module directory (e.g., `click dubbo_common href "dubbo-common/"`)

### R3: Auto-degradation to module graph (MUST)

When `--mode file` detects total files > `MAX_SCAN_FILES`:
- Instead of truncating, auto-generate the module graph (R2)
- Print: `"⚠️ {N} files exceed limit ({MAX_SCAN_FILES}). Generating module graph. Use --focus <module> for file-level detail."`
- The file-level `code_graph.mmd` is NOT generated (no truncated partial graph)
- Class and call graphs that also exceed the limit follow the same behavior: skip with a message

### R4: Scoped focus scan (MUST)

When `--focus <module_name>` is provided:
- Resolve `module_name` to a directory path using the module boundary detection (R1)
- Scan ONLY files within that directory (not the entire repo), then build file-level graph
- This bypasses `MAX_SCAN_FILES` truncation because the scan scope is limited
- If `module_name` does not match any detected module, print error and list available modules

### R5: .tsx/.jsx extension support (MUST)

Node stack scanning MUST include `.tsx` and `.jsx` extensions in addition to `.ts` and `.js`. This is already implemented in STORY-slim-080 but needs a test to prevent regression.

### R6: Backward compatibility (MUST)

- Projects with < `MAX_SCAN_FILES` files: `--mode file` behaves exactly as before (file-level graph)
- `--mode module` is always available regardless of project size
- `--focus` continues to work for class and call modes as before

## Acceptance Criteria

### AC1: Module boundary detection on Java monorepo (R1)

- **Given** a directory with `dubbo-common/pom.xml`, `dubbo-config/pom.xml`, `dubbo-registry/dubbo-registry-api/pom.xml`
- **When** `_detect_modules(root)` is called
- **Then** returns modules including `dubbo-common`, `dubbo-config`, `dubbo-registry/dubbo-registry-api` with stack `java`

### AC2: Module boundary detection on multi-stack monorepo (R1)

- **Given** a directory with `backend/go.mod`, `frontend/package.json`, `gateway/go.mod`
- **When** `_detect_modules(root)` is called
- **Then** returns 3 modules: `(backend, go)`, `(frontend, node)`, `(gateway, go)`

### AC3: Module graph generation with weighted edges (R2)

- **Given** modules A and B where A has 5 files importing 12 symbols from B
- **When** `visualize --mode module` is run
- **Then** output contains `A -->|12| B` and output file is `module_graph.mmd`

### AC4: Auto-degradation when files exceed limit (R3)

- **Given** a project with 600+ source files across multiple modules
- **When** `pactkit visualize` (default file mode) is run
- **Then** `module_graph.mmd` is generated (not `code_graph.mmd`), and stderr contains the warning message with available focus targets

### AC5: Scoped focus scans only target module (R4)

- **Given** a monorepo with `backend/` (200 Go files) and `frontend/` (300 TS files)
- **When** `pactkit visualize --focus backend` is run
- **Then** only `backend/` files are scanned, no truncation warning, and `code_graph.mmd` contains only `backend/` nodes and edges

### AC6: Focus with invalid module name lists available modules (R4)

- **Given** a monorepo with modules `backend`, `frontend`, `gateway`
- **When** `pactkit visualize --focus nonexistent` is run
- **Then** error message includes "Available modules: backend, frontend, gateway"

### AC7: Small project unchanged (R6)

- **Given** a project with 50 Python files and no module markers beyond root
- **When** `pactkit visualize` is run
- **Then** `code_graph.mmd` is generated as before (file-level), no module graph

### AC8: .tsx files included in scan (R5)

- **Given** a monorepo with `frontend/package.json` and `.tsx` files under `frontend/src/`
- **When** file-mode visualize runs for node stack
- **Then** `.tsx` and `.jsx` files appear as nodes with resolved edges

### AC9: SCAN_EXCLUDES respected in module detection (R1)

- **Given** `node_modules/some-pkg/package.json` exists
- **When** `_detect_modules(root)` is called
- **Then** `node_modules/some-pkg` is NOT in the returned modules

### AC10: Module graph node click links (R2)

- **Given** module `backend` at path `backend/`
- **When** module graph is generated
- **Then** output contains `click backend href "backend/"`

## Target Call Chain

```
CLI (pactkit visualize --mode module)
  → visualize() in visualize.py:886
    → _detect_modules(root)          # NEW: R1
      → root.rglob('*') + _STACK_MARKERS filter
    → _build_module_graph(root, modules)  # NEW: R2
      → per-module _scan_files() + cross-module edge aggregation
      → Mermaid output with weighted edges
    → _atomic_mmd_write(dest, content)

CLI (pactkit visualize --focus backend)
  → visualize() in visualize.py:886
    → _detect_modules(root)          # R4: resolve focus name
    → _scan_files(module_dir, ...)   # R4: scoped scan
    → _build_file_graph(...)         # existing
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py` | Add `_detect_modules(root)` function | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Add `_build_module_graph(root, modules, ...)` function | Step 1 | Medium |
| 3 | `src/pactkit/skills/visualize.py` | Add `mode='module'` branch in `visualize()` | Steps 1-2 | Low |
| 4 | `src/pactkit/skills/visualize.py` | Implement auto-degradation in file mode when files > MAX_SCAN_FILES | Steps 1-3 | Medium |
| 5 | `src/pactkit/skills/visualize.py` | Implement scoped focus: resolve module name → directory, scan only that dir | Step 1 | Medium |
| 6 | `src/pactkit/cli.py` | Add `module` to `--mode` choices | Step 3 | Low |
| 7 | `tests/unit/test_story_slim081.py` | Tests for all ACs | Steps 1-6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Path Traversal | N/A | All paths are relative to root, using existing `_scan_files` safety |
| SEC-2 Injection | N/A | No user input in shell commands |
| SEC-3 Auth | N/A | Local CLI tool, no auth |
| SEC-4 Data Exposure | N/A | No sensitive data handling |
| SEC-5 Dependencies | N/A | No new dependencies |
| SEC-6 Config | N/A | No new config surface |
| SEC-7 Logging | N/A | No sensitive data in logs |
| SEC-8 Crypto | N/A | No cryptographic operations |

## Out of Scope

- Unified graph mode integration (STORY-slim-049) — module graph is separate from unified workflow graph
- Interactive module drill-down in IDE (future: click node → run focus)
- Cross-module call graph (aggregated function calls across modules) — only file-level imports are aggregated
- Raising `MAX_SCAN_FILES` beyond 500 — the two-tier design makes this unnecessary
- Module-level class graph — class mode stays file-level with focus
