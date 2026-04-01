# STORY-slim-078: Multi-language module resolution for file-mode dependency graph

| Field | Value |
|-------|-------|
| ID | STORY-slim-078 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.12 |

## Background

The file-mode dependency graph (`code_graph.mmd`) produces nodes for Go, TS, and Java files but **zero edges** because `module_index` keys use Python-style dot-separated relative paths (`backend.internal.ui.auth`) while each language's `extract_imports()` returns its own format:

| Language | `extract_imports` returns | `module_index` key | Resolves? |
|----------|--------------------------|-------------------|-----------|
| Python | `pactkit.config` | `pactkit.config` | YES |
| Go | `github.com/foo/backend/internal/ui` | `backend.internal.ui.auth` | NO |
| TS/JS | `./lib/utils`, `@scope/pkg` | `src.lib.utils` | NO |
| Java | `com.example.Foo` | `src.main.java.com.example.Foo` | NO |

Additionally, `_build_file_graph()` accepts only one analyzer — in multi-stack projects the first stack's analyzer is used for all files, causing Go/Java files to be silently skipped when the primary stack is Python/Node.

Finally, `_scan_files()` line 298 has a hardcoded `.replace('.py', '')` for the src-strip secondary key, which leaves Go/TS/Java extensions in the key (e.g., `internal.api.handler.go`).

## Requirements

### R0: Split visualize.py into modular analyzer files (MUST)

`visualize.py` (3213 lines) MUST be split into a main framework file and per-language analyzer modules:

```
src/pactkit/skills/
  visualize.py              # main: scan, graph build, CLI entry (~1500 lines)
  analyzers/
    __init__.py             # registry + LanguageAnalyzer ABC
    python_analyzer.py      # PythonAnalyzer
    go_analyzer.py          # GoAnalyzer + tree-sitter queries
    ts_analyzer.py          # TSAnalyzer + tree-sitter queries
    java_analyzer.py        # JavaAnalyzer + tree-sitter queries
```

`load_script()` in `skills/__init__.py` MUST be extended to support multi-file merging: when deploying `visualize.py`, it MUST also inline the contents of `analyzers/*.py` so the deployed standalone script remains a single file. New languages only require adding a new analyzer file + registering it.

### R1: Per-language module index keys (MUST)

Each `LanguageAnalyzer` MUST provide a `build_module_keys(rel_path, root)` method that returns the list of module_index keys to register for a given file. This replaces the one-size-fits-all Python-style key generation in `_scan_files()`.

- **Python**: `["pactkit.config", "src.pactkit.config"]` (current behavior)
- **Go**: `["backend/internal/ui/auth", "internal/ui/auth"]` (slash-separated, with/without top-level dir)
- **TS/JS**: `["./src/lib/utils", "./lib/utils", "src/lib/utils"]` (relative path variants)
- **Java**: `["com.example.Foo", "src.main.java.com.example.Foo"]` (qualified name + full path)

### R2: Per-language import normalization (MUST)

Each `LanguageAnalyzer` MUST provide a `normalize_import(import_str, consumer_path, root)` method that converts the raw import string to match `module_index` keys. This is called in `_build_file_graph()` before the index lookup.

- **Python**: return as-is (already matches)
- **Go**: strip module prefix, return slash-separated relative path (e.g., `github.com/foo/backend/internal/ui` → `backend/internal/ui`)
- **TS/JS**: resolve relative imports against consumer path, return normalized relative (e.g., `./lib/utils` from `src/app/page.ts` → `src/lib/utils`)
- **Java**: return as-is (dot-separated qualified name, should now match R1 keys)

### R3: Multi-analyzer file graph (MUST)

`_build_file_graph()` MUST accept `analyzer_file_groups` (list of `(stack, analyzer, files)` tuples) and use each stack's analyzer for its own files, instead of using a single analyzer for all files.

### R4: Fix src-strip hardcoded .py (MUST)

`_scan_files()` line 298 `.replace('.py', '')` MUST be replaced with a generic suffix strip using `with_suffix('')` so Go/TS/Java src-strip keys are correctly generated.

### R5: Go module prefix detection (SHOULD)

For Go projects, the Go module prefix (from `go.mod` line `module github.com/foo/bar`) SHOULD be read and used to strip external-looking local imports down to relative paths for index matching.

### R6: Backward compatibility (MUST)

Python-only projects MUST produce identical `code_graph.mmd` output as before. No behavioral change for existing Python file-mode graphs.

## Acceptance Criteria

### AC1: Go file edges in code_graph (R1, R2, R3)

- **Given** a Go project with `internal/api/handler.go` importing `internal/db/store`
- **When** `pactkit visualize` runs in file mode
- **Then** `code_graph.mmd` contains an edge `internal_api_handler_go --> internal_db_store_go`

### AC2: TS file edges with relative imports (R1, R2, R3)

- **Given** a TS project with `src/app/page.ts` importing `../lib/utils`
- **When** `pactkit visualize` runs in file mode
- **Then** `code_graph.mmd` contains an edge `src_app_page_ts --> src_lib_utils_ts`

### AC3: Java file edges with package imports (R1, R2, R3)

- **Given** a Java project with `src/main/java/com/example/App.java` importing `com.example.Service`
- **When** `pactkit visualize` runs in file mode
- **Then** `code_graph.mmd` contains an edge from App to Service

### AC4: Multi-stack analyzer dispatch (R3)

- **Given** a project with both `.py` and `.go` files
- **When** `_build_file_graph` processes the file list
- **Then** PythonAnalyzer extracts imports for `.py` files and GoAnalyzer for `.go` files (not one analyzer for all)

### AC5: Go module prefix stripping (R5)

- **Given** a Go project with `go.mod` containing `module github.com/slim/phase-smith`
- **When** a `.go` file imports `github.com/slim/phase-smith/backend/internal/ui`
- **Then** the import resolves to `backend/internal/ui` and matches the local file

### AC6: src-strip key fix (R4)

- **Given** a file at `src/lib/utils.ts`
- **When** `_scan_files` builds module_index
- **Then** the secondary src-strip key is `lib.utils` (not `lib.utils.ts`)

### AC7: Python backward compatibility (R6)

- **Given** a Python-only project
- **When** `pactkit visualize` runs in file mode
- **Then** output is identical to pre-change behavior (same nodes and edges)

### AC8: External imports ignored (R2)

- **Given** Go `import "fmt"`, TS `import "react"`, Java `import java.util.List`
- **When** file graph processes these imports
- **Then** they are silently skipped (no crash, no phantom edge)

## Target Call Chain

```
_scan_files(root, file_ext)
  → for each file: analyzer.build_module_keys(rel_path, root)  [NEW]
  →   register each key in module_index

_build_file_graph(root, all_files, module_index, file_to_node, focus, analyzer_file_groups)  [CHANGED]
  → for each (stack, analyzer, files) in analyzer_file_groups:
    → for p in files:
      → for import_str in analyzer.extract_imports(p):
        → normalized = analyzer.normalize_import(import_str, p, root)  [NEW]
        → candidates = module_index.get(normalized)
        → fallback prefix match

visualize(target, mode='file')
  → stacks = _detect_stacks(root)
  → per-stack _scan_files + analyzer_file_groups
  → _build_file_graph(..., analyzer_file_groups=analyzer_file_groups)  [CHANGED]
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 0a | `skills/analyzers/__init__.py` | Extract `LanguageAnalyzer` ABC + registry + `_select_analyzer` | None | Med |
| 0b | `skills/analyzers/python_analyzer.py` | Extract `PythonAnalyzer` | 0a | Low |
| 0c | `skills/analyzers/go_analyzer.py` | Extract `GoAnalyzer` + queries | 0a | Low |
| 0d | `skills/analyzers/ts_analyzer.py` | Extract `TSAnalyzer` + queries | 0a | Low |
| 0e | `skills/analyzers/java_analyzer.py` | Extract `JavaAnalyzer` + queries | 0a | Low |
| 0f | `skills/__init__.py` | Extend `load_script()` to merge analyzer files | 0a-0e | Med |
| 0g | `skills/visualize.py` | Remove extracted code, import from analyzers | 0a-0e | Med |
| 1 | `analyzers/*.py` | Add `build_module_keys()` to ABC + each analyzer | 0a-0e | Med |
| 2 | `analyzers/*.py` | Add `normalize_import()` to ABC + each analyzer | 0a-0e | Med |
| 3 | `visualize.py` | Refactor `_scan_files()` to use `build_module_keys()`, fix src-strip | 1 | Med |
| 4 | `visualize.py` | Refactor `_build_file_graph()` to accept `analyzer_file_groups` | 2 | Med |
| 5 | `visualize.py` | Update `visualize()` entry to pass `analyzer_file_groups` to file mode | 3-4 | Low |
| 6 | `analyzers/go_analyzer.py` | Add `_read_go_module_prefix(root)` for R5 | None | Low |
| 7 | `tests/unit/test_story_slim078.py` | Tests for AC1–AC9 | 0-6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 User Input | N/A | No user input — reads source files |
| SEC-2 Auth | N/A | Local CLI only |
| SEC-3 Data Storage | N/A | Only writes mmd files |
| SEC-4 Secrets | N/A | No secrets involved |
| SEC-5 Network | N/A | No network access |
| SEC-6 File Ops | Low | Reads go.mod for module prefix — bounded, local only |
| SEC-7 Dependencies | N/A | No new dependencies |
| SEC-8 Logging | N/A | No sensitive data logged |

## Out of Scope

- Resolving transitive dependencies (only direct imports)
- Resolving dynamic imports (`importlib.import_module`, `require(variable)`)
- NPM package resolution (node_modules lookup) — only local project files
- Go vendored module resolution
- Call-mode multi-analyzer dispatch (file-mode only in this story)
