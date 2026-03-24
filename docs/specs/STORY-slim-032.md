# STORY-slim-032: TreeSitterAnalyzer base class + Go adapter

| Field | Value |
|-------|-------|
| ID | STORY-slim-032 |
| Status | Done |
| Priority | P1 — Impact 4, Effort 3 |
| Release | 2.3.7 |

## Background

After STORY-slim-030 establishes the `LanguageAnalyzer` interface with `PythonAnalyzer` (using stdlib `ast`), Go/Java/TS projects still get empty call graphs. Rather than writing fragile regex parsers per language (~60-80% coverage), we use **tree-sitter** — a universal parser generator with Python bindings that produces real ASTs for 100+ languages. This gives near-100% accuracy with a unified parsing engine.

This story introduces the `TreeSitterAnalyzer` shared base class and the first concrete adapter (`GoAnalyzer`). STORY-slim-033 (Java) and STORY-slim-034 (TS/JS) will reuse the base class with different grammars and queries.

## Architecture

```
LanguageAnalyzer (ABC)                    # STORY-slim-030
  ├── PythonAnalyzer                      # stdlib ast — zero deps
  └── TreeSitterAnalyzer (new base)       # THIS STORY
        ├── GoAnalyzer                    # THIS STORY
        ├── JavaAnalyzer                  # STORY-slim-033
        └── TSAnalyzer                    # STORY-slim-034
```

`PythonAnalyzer` keeps using `ast` (stdlib, 100% accurate, zero deps). All other languages share `TreeSitterAnalyzer`, which handles parser init, file reading, error handling, and query execution. Subclasses only provide: language grammar, import query, function query, call query.

## Requirements

### R1: tree-sitter optional dependency (MUST)

`pyproject.toml` MUST add `tree-sitter` and `tree-sitter-go` as optional dependencies under an `[optional-dependencies]` group (e.g., `multilang`). The standalone script MUST guard imports with `try/except ImportError` and degrade gracefully (return empty results) if tree-sitter is not installed.

### R2: TreeSitterAnalyzer base class (MUST)

`TreeSitterAnalyzer(LanguageAnalyzer)` MUST provide a concrete base class that:
- Accepts `language`, `import_query`, `func_query`, `call_query` in `__init__`
- Implements `extract_imports()` by parsing the file and running `import_query`
- Implements `extract_functions_and_calls()` by parsing the file and running `func_query` + `call_query`
- Handles all error cases: `FileNotFoundError`, `UnicodeDecodeError`, tree-sitter parse errors → return empty results
- Is defined in `src/pactkit/skills/visualize.py` after `PythonAnalyzer`

### R3: GoAnalyzer subclass (MUST)

`GoAnalyzer(TreeSitterAnalyzer)` MUST configure:
- Language: `tree_sitter_go.language()`
- Import query: extract `import_spec` path strings from Go source
- Function query: extract `function_declaration` and method `(receiver) func` declarations
- Call query: extract `call_expression` function/method calls

### R4: Go import extraction (MUST)

`GoAnalyzer.extract_imports()` MUST extract:
- Single imports: `import "fmt"`
- Block imports: `import ( "fmt" "net/http" )`
- Named imports: `import alias "path"` (return the path, not the alias)

### R5: Go function and call extraction (MUST)

`GoAnalyzer.extract_functions_and_calls()` MUST extract:
- Top-level functions: `func FuncName(` → registered as `FuncName`
- Methods with receivers: `func (s *Server) HandleRequest(` → registered as `Server.HandleRequest`
- Function calls: `FuncName(` and `pkg.FuncName(`
- Method calls: `s.HandleRequest(` → resolved to `Server.HandleRequest` where possible

### R6: Auto-selected for Go projects (MUST)

When `_detect_stack()` returns `"go"`, `visualize()` MUST auto-select `GoAnalyzer()`. If tree-sitter is not installed, it MUST fall back to `PythonAnalyzer()` with a stderr warning.

### R7: Analyzer selection function (MUST)

A `_select_analyzer(stack)` function MUST be added to centralize analyzer selection logic. This function returns the appropriate `LanguageAnalyzer` instance for the given stack, with fallback to `PythonAnalyzer()`. All call sites (`visualize()`, `impact()`) MUST use this function instead of hardcoding `PythonAnalyzer()`.

## Acceptance Criteria

### AC1: Go file graph non-empty (R3, R4)

- **Given** a Go project with `go.mod` and multiple `.go` files with imports
- **When** running `pactkit visualize`
- **Then** `code_graph.mmd` contains import relationship edges between Go packages

### AC2: Go call graph non-empty (R3, R5)

- **Given** a Go project with functions calling each other
- **When** running `pactkit visualize --mode call`
- **Then** `call_graph.mmd` contains function→function edges

### AC3: Go methods extracted (R5)

- **Given** a Go file with `func (s *Server) HandleRequest(` calling `s.validateInput(`
- **When** extracting functions and calls
- **Then** `Server.HandleRequest` appears with callee `validateInput`

### AC4: Auto-detection works (R6, R7)

- **Given** a project with `go.mod`
- **When** running `pactkit visualize --mode call`
- **Then** `GoAnalyzer` is used automatically

### AC5: Graceful degradation without tree-sitter (R1)

- **Given** tree-sitter is NOT installed
- **When** running `pactkit visualize` on a Go project
- **Then** falls back to `PythonAnalyzer` with a warning, no crash

### AC6: TreeSitterAnalyzer reusable (R2)

- **Given** `TreeSitterAnalyzer` base class exists
- **When** creating `JavaAnalyzer(TreeSitterAnalyzer)` with Java grammar and queries
- **Then** it works without modifying `TreeSitterAnalyzer` or `_build_*` functions

### AC7: Python output unchanged (R7)

- **Given** a Python project
- **When** running `pactkit visualize` after adding `_select_analyzer`
- **Then** output is identical to pre-change (PythonAnalyzer still used)

## Design

### tree-sitter Query Pattern

tree-sitter uses S-expression queries to match AST nodes:

```python
# Go import query
IMPORT_QUERY = '(import_spec path: (interpreted_string_literal) @import)'

# Go function query
FUNC_QUERY = '''[
  (function_declaration name: (identifier) @name)
  (method_declaration
    receiver: (parameter_list (parameter_declaration type: (_) @receiver_type))
    name: (field_identifier) @name)
]'''

# Go call query
CALL_QUERY = '''[
  (call_expression function: (identifier) @callee)
  (call_expression function: (selector_expression
    operand: (_) @obj
    field: (field_identifier) @method))
]'''
```

### TreeSitterAnalyzer Base Class (tree-sitter v0.25 API)

**CRITICAL**: tree-sitter v0.25 changed the query API. Use `Query(lang, str)` + `QueryCursor(query)` + `cursor.captures(node)`. The `captures()` method returns `dict[str, list[Node]]` (capture name to list of nodes). `Node.text` returns `bytes`.

```python
class TreeSitterAnalyzer(LanguageAnalyzer):
    def __init__(self, language, import_query, func_query, call_query):
        from tree_sitter import Language, Parser, Query
        self._lang = Language(language)
        self._parser = Parser(self._lang)
        self._import_query = Query(self._lang, import_query)
        self._func_query = Query(self._lang, func_query)
        self._call_query = Query(self._lang, call_query)

    def _captures(self, query, node):
        """Run a query against a node, return dict[str, list[Node]]."""
        from tree_sitter import QueryCursor
        cursor = QueryCursor(query)
        return cursor.captures(node)  # dict[str, list[Node]]

    def extract_imports(self, file_path):
        tree = self._parser.parse(file_path.read_bytes())
        captures = self._captures(self._import_query, tree.root_node)
        return [n.text.decode().strip('"\'') for n in captures.get("import", [])]

    def extract_functions_and_calls(self, file_path):
        tree = self._parser.parse(file_path.read_bytes())
        # ... run func_query + call_query via self._captures(), build func_registry + call_edges
```

### _select_analyzer Function

```python
def _select_analyzer(stack):
    if stack == 'python':
        return PythonAnalyzer()
    try:
        if stack == 'go':
            return GoAnalyzer()
        # Future: java, node
    except ImportError:
        import sys
        print(f"tree-sitter not installed; falling back to PythonAnalyzer for {stack}", file=sys.stderr)
    return PythonAnalyzer()
```

## Target Call Chain

```
visualize(target='.', mode='call')
  -> _detect_stack(root) -> "go"
  -> _select_analyzer("go") -> GoAnalyzer()
       GoAnalyzer.__init__()
         -> Language(tree_sitter_go.language())
         -> Parser(lang)
         -> Query(lang, IMPORT_QUERY), Query(lang, FUNC_QUERY), Query(lang, CALL_QUERY)
  -> _build_call_graph(root, all_files, focus, entry, analyzer=GoAnalyzer())
       -> for file in all_files:
            fr, ce = analyzer.extract_functions_and_calls(file)
              -> parser.parse(file.read_bytes())
              -> QueryCursor(func_query).captures(root_node) -> {"name": [...], "receiver_type": [...]}
              -> QueryCursor(call_query).captures(root_node) -> {"callee": [...], "obj": [...], "method": [...]}
            func_registry.update(fr)
            call_edges.update(ce)

_select_analyzer("go")  [when tree-sitter NOT installed]
  -> GoAnalyzer() raises ImportError
  -> fallback: PythonAnalyzer() + stderr warning
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `pyproject.toml` | Add `tree-sitter`, `tree-sitter-go` to optional deps | None | Low |
| 2 | `tests/unit/test_story_slim032.py` | Tests for TreeSitterAnalyzer, GoAnalyzer, _select_analyzer, graceful degradation | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | Implement `TreeSitterAnalyzer` base class | Step 1 | Medium |
| 4 | `src/pactkit/skills/visualize.py` | Implement `GoAnalyzer(TreeSitterAnalyzer)` with Go queries | Step 3 | Medium |
| 5 | `src/pactkit/skills/visualize.py` | Add `_select_analyzer(stack)` function | Step 4 | Low |
| 6 | `src/pactkit/skills/visualize.py` | Update `visualize()` and `impact()` to use `_select_analyzer()` | Step 5 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | tree-sitter parses source files read-only, no code execution |
| SEC-8 Dependencies | Low | tree-sitter is a widely-used C library with Python bindings; grammar packages are official |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |

## Out of Scope

- Go interface resolution (static analysis limitation)
- Go module vendoring analysis
- Go generics type parameter parsing
- Replacing PythonAnalyzer with tree-sitter (stdlib ast is optimal for Python)
