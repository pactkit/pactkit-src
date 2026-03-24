# STORY-slim-030: LanguageAnalyzer interface + Python adapter

| Field | Value |
|-------|-------|
| ID | STORY-slim-030 |
| Status | Done |
| Priority | P0 — Impact 5, Effort 3 |
| Release | 2.3.7 |

## Background

`_build_call_graph()` and `_build_file_graph()` use Python's `ast.parse` directly — tightly coupled to Python. To support Go, Java, and TS/JS, we need an adapter interface that each language implements. The Python adapter wraps the existing `ast.parse` logic with zero behavior change. Future language adapters (STORY-slim-032, 033, 034) implement the same interface using regex.

Additionally, `_scan_call_edges()` (STORY-053) duplicates the same ast parsing logic as `_build_call_graph()`. This refactor consolidates both into the shared `PythonAnalyzer`.

## Requirements

### R1: LanguageAnalyzer abstract interface (MUST)

Define a `LanguageAnalyzer` base class (using `abc.ABC` + `abc.abstractmethod`) with two methods:
- `extract_imports(file_path: Path) -> list[str]` — returns a list of imported module name strings (e.g., `["src.models", "os.path"]`)
- `extract_functions_and_calls(file_path: Path) -> tuple[dict[str, str], dict[str, list[str]]]` — returns `(func_registry, call_edges)` where `func_registry` is `{qualified_name: file_stem}` and `call_edges` is `{caller_qualified: [callee_names]}`

The class MUST be defined in `src/pactkit/skills/visualize.py`, near the top after imports and constants, before existing `_build_*` functions.

### R2: PythonAnalyzer wraps existing ast logic (MUST)

`PythonAnalyzer(LanguageAnalyzer)` MUST implement both interface methods by extracting the existing `ast.parse` logic:

- `extract_imports()` MUST extract the import-walking logic from `_build_file_graph()` lines 158-183 (the inner loop that collects `imported_modules` from `ast.Import` and `ast.ImportFrom` nodes). It MUST return a `list[str]` of module names.
- `extract_functions_and_calls()` MUST extract the per-file ast parsing logic from `_build_call_graph()` lines 315-336 (the loop that builds `func_registry` and `call_edges` via `_extract_calls()`). It MUST accept a single file path and return `(func_registry_fragment, call_edges_fragment)` for that file.

The existing `_extract_calls()` helper and `_BUILTIN_CALLEES` set MUST remain as module-level functions/constants (they are not part of the interface — they are Python-specific implementation details used by `PythonAnalyzer`).

Error handling: each method MUST catch `(SyntaxError, UnicodeDecodeError, ValueError)` and return empty results, matching current behavior.

### R3: _build_call_graph uses analyzer (MUST)

`_build_call_graph()` MUST accept an optional `analyzer: LanguageAnalyzer = None` parameter. When `None`, it MUST default to `PythonAnalyzer()`. The per-file parsing loop MUST be replaced with a call to `analyzer.extract_functions_and_calls(file_path)`, with results merged into the aggregate `func_registry` and `call_edges` dicts.

### R4: _build_file_graph uses analyzer (MUST)

`_build_file_graph()` MUST accept an optional `analyzer: LanguageAnalyzer = None` parameter. When `None`, it MUST default to `PythonAnalyzer()`. The import extraction loop (lines 158-183) MUST be replaced with a call to `analyzer.extract_imports(file_path)`.

### R5: _scan_call_edges consolidation (MUST)

`_scan_call_edges()` MUST be refactored to accept an optional `analyzer: LanguageAnalyzer = None` parameter and delegate to `analyzer.extract_functions_and_calls()` instead of duplicating the ast parsing logic. This eliminates the code duplication between `_scan_call_edges` and `_build_call_graph`.

### R6: Analyzer selection via detect_stack (SHOULD)

`visualize()` SHOULD instantiate the analyzer based on `_detect_file_ext()` result. For now, only `PythonAnalyzer` exists. All stacks SHOULD fall back to `PythonAnalyzer` with a comment indicating where future analyzers will be selected.

### R7: _build_class_graph excluded from refactor (MAY)

`_build_class_graph()` MAY remain unchanged in this story. Class diagram parsing has a fundamentally different structure (extracting class definitions, bases, methods) that does not fit the `extract_imports`/`extract_functions_and_calls` interface. A separate `extract_classes()` method MAY be added to `LanguageAnalyzer` in a future story.

## Acceptance Criteria

### AC1: Python call graph output identical (R2, R3)

- **Given** an existing Python project with a known call_graph.mmd
- **When** running `visualize(mode='call')` after refactor
- **Then** the output MUST be byte-for-byte identical to the pre-refactor output

### AC2: Python file graph output identical (R2, R4)

- **Given** an existing Python project with a known code_graph.mmd
- **When** running `visualize(mode='file')` after refactor
- **Then** the output MUST be byte-for-byte identical to the pre-refactor output

### AC3: LanguageAnalyzer interface is extensible (R1)

- **Given** the `LanguageAnalyzer` interface exists
- **When** a new `GoAnalyzer(LanguageAnalyzer)` is created
- **Then** it can be passed to `_build_call_graph(analyzer=GoAnalyzer())` and `_build_file_graph(analyzer=GoAnalyzer())` without modifying those functions

### AC4: Default analyzer is PythonAnalyzer (R3, R4, R5, R6)

- **Given** no explicit analyzer is provided
- **When** calling `_build_call_graph(root, all_files, focus, entry)` or `_build_file_graph(...)` or `_scan_call_edges(...)` with the old signature
- **Then** `PythonAnalyzer` MUST be used (backward compat)

### AC5: Reverse BFS and impact use analyzer (R5)

- **Given** `_scan_call_edges` has been refactored
- **When** `impact(entry='some_func')` or `visualize(mode='call', reverse=True, entry='x')` is called
- **Then** the output MUST be identical to pre-refactor output

### AC6: All existing visualize tests pass (R2)

- **Given** the test file `tests/unit/test_visualize_modes.py` exists
- **When** running `pytest tests/unit/test_visualize_modes.py`
- **Then** all 12 existing tests MUST pass without modification

## Target Call Chain

```
visualize()
  -> _detect_file_ext(root) -> ".py"
  -> analyzer = PythonAnalyzer()
  -> _build_call_graph(root, all_files, focus, entry, analyzer=analyzer)
    -> for file in all_files:
        func_reg, call_edg = analyzer.extract_functions_and_calls(file)
        func_registry.update(func_reg)
        call_edges.update(call_edg)
  -> _build_file_graph(root, all_files, module_index, file_to_node, focus, analyzer=analyzer)
    -> for file in all_files:
        imports = analyzer.extract_imports(file)
        (resolve imports against module_index — same as before)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim030.py` | Snapshot tests: capture pre-refactor output for file/call/reverse modes using test project fixture, assert byte-for-byte match after refactor | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Define `LanguageAnalyzer` ABC with `extract_imports` and `extract_functions_and_calls` abstract methods | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | Implement `PythonAnalyzer` extracting ast logic from `_build_file_graph` and `_build_call_graph` | Step 2 | Medium |
| 4 | `src/pactkit/skills/visualize.py` | Refactor `_build_call_graph` to accept `analyzer` param and delegate parsing | Step 3 | Medium |
| 5 | `src/pactkit/skills/visualize.py` | Refactor `_build_file_graph` to accept `analyzer` param and delegate import extraction | Step 3 | Medium |
| 6 | `src/pactkit/skills/visualize.py` | Refactor `_scan_call_edges` to accept `analyzer` param and delegate | Step 3 | Low |
| 7 | `src/pactkit/skills/visualize.py` | Update `visualize()` to instantiate `PythonAnalyzer` and pass to all build functions | Steps 4-6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 through SEC-8 | N/A | Pure refactor, no new input vectors or behavior changes |

## Out of Scope

- Go/Java/TS analyzers (STORY-slim-032, 033, 034)
- Regex-based parsing strategies (deferred to language-specific stories)
- Any behavior change to graph output (this is a pure refactor)
- `_build_class_graph` refactoring (separate interface shape; may be future story)
- `module_index` building in `_scan_files` (Python-specific module resolution; stays as-is for now)
