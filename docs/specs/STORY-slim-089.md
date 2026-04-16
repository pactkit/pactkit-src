# STORY-slim-089: Enterprise Code Analysis: Blast Radius, Cyclomatic Complexity, Layer Violations

| Field | Value |
|-------|-------|
| ID | STORY-slim-089 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.0 |

## Background

PactKit is expanding to enterprise adoption. Enterprise codebases require deeper static analysis beyond dependency graphs:
1. **Blast Radius** — When a file or function changes, engineers need to know the full impact scope (all affected files and their depth) to assess risk before committing. The current `impact()` function only maps source→test files; it does not provide a general-purpose blast radius across the dependency graph.
2. **Cyclomatic Complexity** — Enterprise code review requires identifying overly complex functions (high branch count) for refactoring prioritization. The current AST traversal in all 4 analyzers already visits the relevant nodes but does not count complexity.
3. **Layer Violation Detection** — Large codebases have implicit architectural layers (UI → Services → Data → Config → Utils). Detecting reverse dependencies (lower layers importing upper layers) prevents architectural erosion over time.

All three features operate as **post-processing on existing data structures** — the file graph `adjacency`/`edges`, the function-level `call_edges`/`func_registry`, and the per-file AST already parsed by `extract_functions_and_calls()`. No additional file scanning or AST parsing passes are required.

**Reference**: CodeFlow project (github.com/braedonsaunders/codeflow) implements similar features in a browser-based single-file architecture. PactKit's implementation adapts these concepts to its multi-language analyzer registry + Mermaid output pipeline.

## Requirements

### R1: Blast Radius — File-Level (MUST)

Add a `blast_radius` CLI subcommand and Python function that, given a target file path, computes the full set of affected files via bidirectional BFS on the file dependency graph.
- Input: `--target <file_path>` (relative to project root)
- Output: JSON to stdout with fields: `target`, `affected_files` (list of relative paths), `depth` (max BFS depth reached), `total_count`
- Algorithm: Reuse `_build_file_graph()`'s `edges` list. Build forward adjacency (files that import target) and backward adjacency (files target imports). BFS in both directions. Union of visited sets = blast radius.
- MUST support `--depth <N>` to limit BFS hops (0 = unlimited, default)
- MUST NOT trigger additional file scanning — reuse `_scan_files()` result

### R2: Blast Radius — Function-Level (SHOULD)

Extend `blast_radius` to accept `--entry <function_name>` for function-level analysis.
- Reuse `_scan_call_edges()` and `_build_reverse_graph()` infrastructure
- When `--entry` is provided, compute affected functions (not files) via bidirectional BFS on `call_edges`
- Output: JSON with `entry`, `affected_functions` (list), `affected_files` (list of unique files containing affected functions), `depth`, `total_count`

### R3: Cyclomatic Complexity (MUST)

Add cyclomatic complexity calculation to all 4 language analyzers.
- For each function extracted by `extract_functions_and_calls()`, count decision points: `if`, `elif`/`else if`, `for`, `while`, `and`, `or`, `except`/`catch`, `case`/`match`, ternary expressions. Base complexity = 1 + count.
- Return type change: `extract_functions_and_calls()` currently returns `(func_registry, call_edges)`. Add a third element: `complexity_map: dict[str, int]` mapping function qualified name → complexity score.
- **Backward compatibility**: Existing callers that unpack 2 values MUST NOT break. Use a wrapper or sentinel to maintain the 2-tuple interface, with an opt-in parameter `include_complexity=False` on `extract_functions_and_calls()`.
- Classification thresholds (for reporting): low (1-10), medium (11-20), high (21-30), critical (>30)

### R4: Complexity Report Subcommand (MUST)

Add a `complexity` CLI subcommand that scans all source files and outputs a sorted report.
- Output: table to stdout (function name, file, complexity, classification)
- Default: sort by complexity descending, show top 20
- Flags: `--threshold <N>` (only show functions with complexity >= N), `--format {table,json}`, `--all` (show all, not just top 20)
- Reuse existing `_scan_files()` + analyzer `extract_functions_and_calls(include_complexity=True)`

### R5: Layer Violation Detection (MUST)

Add a `layers` CLI subcommand that detects architectural layer violations.
- **Layer model**: Configurable via `pactkit.yaml` under `visualize.layers` key. Format:
  ```yaml
  visualize:
    layers:
      - name: ui
        patterns: ["*/ui/*", "*/views/*", "*/pages/*", "*/components/*"]
      - name: services
        patterns: ["*/service/*", "*/services/*", "*/api/*"]
      - name: data
        patterns: ["*/data/*", "*/models/*", "*/db/*", "*/repositories/*"]
      - name: config
        patterns: ["*/config/*", "*/settings/*"]
      - name: utils
        patterns: ["*/util/*", "*/utils/*", "*/helpers/*", "*/lib/*"]
  ```
- **Default layers**: If `visualize.layers` is not configured, use the 5-layer model above as built-in default.
- **Layer ordering**: The list order defines the hierarchy — earlier layers are "higher". Higher layers MAY import lower layers. Lower layers importing higher layers = violation.
- **Detection**: Iterate file-level `edges`. For each edge `(importer, importee)`, classify both files by layer (first matching pattern wins). If importer's layer index > importee's layer index (lower imports higher), flag as violation.
- **Output**: JSON with `violations` (list of `{importer, importee, importer_layer, importee_layer}`), `total_count`, `layer_summary` (files per layer)
- Files not matching any layer pattern are classified as "unclassified" and excluded from violation checks.

### R6: Layer Violation Mermaid Annotation (SHOULD)

When `--mode file` is used with `--layers` flag, annotate the file graph with layer violations:
- Add `style` lines to highlight violation edges in red
- Add a legend subgraph showing the layer model

## Acceptance Criteria

### AC1: Blast Radius — Single File (R1)

- **Given** a Python project with files A→B→C dependency chain (A imports B, B imports C)
- **When** `visualize.py blast_radius --target B.py`
- **Then** output JSON includes `affected_files: ["A.py", "C.py"]` with `depth: 1` and `total_count: 2`

### AC2: Blast Radius — Depth Limit (R1)

- **Given** a project with chain A→B→C→D
- **When** `visualize.py blast_radius --target B.py --depth 1`
- **Then** output includes A.py and C.py but NOT D.py (D is 2 hops from B via C)

### AC3: Blast Radius — Function-Level (R2)

- **Given** a project where `func_a()` calls `func_b()` which calls `func_c()`
- **When** `visualize.py blast_radius --entry func_b`
- **Then** output includes `affected_functions: ["func_a", "func_c"]` and `affected_files` lists unique files

### AC4: Cyclomatic Complexity — Python (R3)

- **Given** a Python function with 3 `if` statements and 1 `for` loop
- **When** `extract_functions_and_calls(file, include_complexity=True)` is called
- **Then** `complexity_map` contains the function with complexity = 5 (1 base + 3 if + 1 for)

### AC5: Cyclomatic Complexity — Backward Compatibility (R3)

- **Given** existing code that calls `analyzer.extract_functions_and_calls(path)` and unpacks as `(fr, ce) = ...`
- **When** the new implementation is deployed
- **Then** the 2-tuple unpacking still works without error (default `include_complexity=False`)

### AC6: Complexity Report (R4)

- **Given** a project with 50 functions of varying complexity
- **When** `visualize.py complexity --threshold 10 --format json`
- **Then** output contains only functions with complexity >= 10, sorted descending

### AC7: Layer Violation — Default Model (R5)

- **Given** a project where `utils/helper.py` imports `services/api.py`
- **When** `visualize.py layers`
- **Then** output flags `{importer: "utils/helper.py", importee: "services/api.py", importer_layer: "utils", importee_layer: "services"}` as a violation

### AC8: Layer Violation — Custom Config (R5)

- **Given** a `pactkit.yaml` with custom `visualize.layers` defining 3 layers
- **When** `visualize.py layers`
- **Then** violations are detected according to the custom layer model, not the default

### AC9: Layer Violation — No Config (R5)

- **Given** a project without `visualize.layers` in pactkit.yaml
- **When** `visualize.py layers`
- **Then** the 5-layer built-in default is used

### AC10: Layer Violation Mermaid Annotation (R6)

- **Given** a project with a layer violation (utils importing services)
- **When** `visualize.py visualize --mode file --layers`
- **Then** the output `code_graph.mmd` contains `style` lines marking violation edges in red and a legend subgraph showing the layer model

## Target Call Chain

```
CLI (__main__ argparse)
  ├── blast_radius(target, entry?, depth?) → NEW
  │     ├── _scan_files(root)             → EXISTING (reuse)
  │     ├── _build_file_graph(...)        → EXISTING (reuse edges/adjacency)
  │     ├── _bidirectional_bfs(adj, target, depth) → NEW
  │     └── _scan_call_edges(root, files) → EXISTING (reuse, if --entry)
  │
  ├── complexity(target, threshold?, format?) → NEW
  │     ├── _scan_files(root)             → EXISTING (reuse)
  │     └── analyzer.extract_functions_and_calls(path, include_complexity=True) → MODIFIED
  │           └── PythonAnalyzer: ast.walk() + count If/For/While/BoolOp/ExceptHandler
  │           └── TreeSitterAnalyzer: query for decision nodes per language
  │
  └── layers(target) → NEW
        ├── _scan_files(root)             → EXISTING (reuse)
        ├── _build_file_graph(...)        → EXISTING (reuse edges)
        ├── _load_layer_config(root)      → NEW (reads pactkit.yaml or uses default)
        └── _classify_file(path, layers)  → NEW (fnmatch against layer patterns)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/analyzers/__init__.py` | Add `include_complexity` param to `extract_functions_and_calls()` abstract method signature | None | Low |
| 2 | `src/pactkit/skills/analyzers/python_analyzer.py` | Implement complexity counting in `extract_functions_and_calls()` by counting `ast.If`, `ast.For`, `ast.While`, `ast.BoolOp`, `ast.ExceptHandler`, `ast.Match` nodes | Step 1 | Low |
| 3 | `src/pactkit/skills/analyzers/ts_analyzer.py` | Implement complexity counting via tree-sitter queries for `if_statement`, `for_statement`, `while_statement`, `catch_clause`, `ternary_expression` | Step 1 | Medium |
| 4 | `src/pactkit/skills/analyzers/go_analyzer.py` | Implement complexity counting via tree-sitter queries for Go decision nodes | Step 1 | Medium |
| 5 | `src/pactkit/skills/analyzers/java_analyzer.py` | Implement complexity counting via tree-sitter queries for Java decision nodes | Step 1 | Medium |
| 6 | `src/pactkit/skills/visualize.py` | Add `blast_radius()` function with bidirectional BFS on file graph adjacency | None | Low |
| 7 | `src/pactkit/skills/visualize.py` | Add `complexity()` function scanning all files with `include_complexity=True` | Step 2-5 | Low |
| 8 | `src/pactkit/skills/visualize.py` | Add `_load_layer_config()`, `_classify_file()`, `layers()` functions | None | Low |
| 9 | `src/pactkit/skills/visualize.py` | Add CLI subcommands: `blast_radius`, `complexity`, `layers` to argparse | Steps 6-8 | Low |
| 10 | `tests/unit/test_blast_radius.py` | Unit tests for blast_radius (file-level, function-level, depth limit) | Step 6 | Low |
| 11 | `tests/unit/test_complexity.py` | Unit tests for complexity counting across Python/TS/Go/Java + backward compat | Steps 2-5 | Low |
| 12 | `tests/unit/test_layer_violations.py` | Unit tests for layer detection (default model, custom config, edge cases) | Step 8 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code files modified — validate no arbitrary code execution via user-supplied paths |
| SEC-2 | Yes | Input handling: `--target`, `--entry`, `--threshold` CLI args + `pactkit.yaml` layer patterns — validate path traversal and type safety |
| SEC-3 | No | No database patterns |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth patterns |
| SEC-6 | No | No API/route files |
| SEC-7 | Yes | Error handling: file read failures, malformed YAML, missing tree-sitter grammars — ensure graceful degradation |
| SEC-8 | No | No new dependencies added |

## Out of Scope

- D3.js interactive visualization (Draw.io MCP covers interactive viewing)
- Git churn analysis (requires git log parsing, separate story)
- Code duplication detection (future story, extends pactkit-garden)
- Cross-language dependency tracking (e.g., Python calling Go via FFI)
- Layer violation auto-fix / refactoring suggestions
- Mermaid annotation for complexity (only layer violations get Mermaid annotation per R6)
