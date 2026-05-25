# STORY-slim-119: Improve Python Call Graph Coverage: Non-self Attribute Calls, Function References, and Nested Functions

| Field | Value |
|-------|-------|
| ID | STORY-slim-119 |
| Status | Draft |
| Priority | P1 |
| Release | 2.14.0 |

## Background

`pactkit-visualize` generates call graphs by parsing Python source via `ast`. Comparative analysis against `codegraph` (tree-sitter-based) on the same codebase (pactsearch, 184 Python files) revealed that pactkit produces 1,349 call edges while codegraph produces 6,571 — a 4.9x gap.

Root cause analysis identified three specific deficiencies in `_extract_calls` (visualize.py:432) and `PythonAnalyzer.extract_functions_and_calls` (visualize.py:280):

1. **Non-self attribute calls silently dropped** — `engine.run()`, `registry.get()`, `client.post()` etc. are filtered by a `self`-only guard at line 444. Only `self.method()` is captured.
2. **Function references not captured** — `ALL_TOOLS = [web_search, deep_research]` or `callback=my_func` stores function objects without calling them. These are `ast.Name` nodes in list/assignment context, never `ast.Call`, so they're invisible to the current scanner.
3. **Nested functions and class bodies only scanned one level deep** — `ast.iter_child_nodes(tree)` at line 294 only visits top-level nodes. Nested functions (`def inner():` inside a method), inner classes, and decorated factory functions are missed.

These gaps cause the call graph to miss entire call chains (e.g., `chat_tools.py:deep_research → research_agent.run` never appears), reducing the value of `pactkit regression`, `blast_radius`, and `impact` commands.

## Requirements

### R1: Capture Non-self Attribute Method Calls (MUST)

`_extract_calls` MUST capture `obj.method()` calls where `obj` is any local variable (not just `self`). The attribute name (`.method`) MUST be appended as a callee candidate. Standard library and builtin method names that appear in `_BUILTIN_CALLEES` MUST still be excluded.

**Current** (line 444): only captures `self.method()`.  
**Target**: also captures `engine.run()`, `client.get()`, `registry.get()`, etc. as `run`, `get`, etc.

**Noise control**: do NOT attempt to qualify `obj.method` with the class name of `obj` — the type of local variables cannot be resolved without a type system. Emit the bare method name (`run`, `get`, `search`) as callee. `_resolve_callee` already handles suffix matching to find the canonical qualified name.

### R2: Capture Function References in Assignments and Collections (MUST)

`_extract_calls` (or `extract_functions_and_calls`) MUST also capture function name references that appear as `ast.Name` values in:
- List/tuple literals that are assigned to a name (e.g., `TOOLS = [web_search, deep_research]`)
- Keyword arguments where value is a bare name (e.g., `callback=my_handler`)
- Direct assignment of a function to a variable (e.g., `handler = process_event`)

These MUST be treated as "references" — emitted as callee edges from the enclosing function/module-level context. Exclusions: names already in `_BUILTIN_CALLEES`, names that are clearly non-function (single-char names, all-caps constants like `MAX`, `None`, `True`, `False`).

### R3: Scan Nested Functions (MUST)

`extract_functions_and_calls` MUST register and extract calls from nested functions (functions defined inside other functions or methods). The current `ast.iter_child_nodes(tree)` + `node.body` loop MUST be replaced or supplemented with `ast.walk(tree)` to find all `FunctionDef`/`AsyncFunctionDef` nodes at any depth. Nested function qualified name format: `OuterClass.outer_method.<locals>.inner_func` or simply `outer_func.inner_func` — use the immediately enclosing function name as prefix.

### R4: No Regression on Existing Tests (MUST NOT)

The changes MUST NOT break any existing test in `tests/unit/test_visualize_chain_fix.py`, `test_story_slim032.py`, `test_story_slim033.py`, `test_story_slim034.py`, `test_blast_radius.py`, or `test_smart_regression.py`. The call graph format (Mermaid `graph TD`) and node ID scheme (`ClassName_method`) MUST remain unchanged.

### R5: Noise Budget — False Positive Rate (SHOULD)

The changes SHOULD NOT increase false-positive call edges (edges where the callee does not exist in `func_registry`) by more than 15% compared to baseline. `_resolve_callee` already filters unresolvable callees; this provides automatic noise control. Monitor with: `grep " --> " call_graph.mmd | wc -l` before and after.

## Acceptance Criteria

### AC1: Non-self Attribute Calls Captured (R1)

- **Given** a Python file containing `async def web_search(): engine = _get_web_engine(); result = await engine.run(query)`
- **When** `_extract_calls` is run on the `web_search` function node
- **Then** `run` appears in the returned callee list

### AC2: Self-only Calls Still Work (R1)

- **Given** a class method containing `self.validate()` and `other.process()`
- **When** `_extract_calls` is run with `current_class="MyClass"`
- **Then** both `MyClass.validate` and `process` appear in the callee list (qualified for self, bare name for other)

### AC3: Function References in Lists Captured (R2)

- **Given** a Python file containing `ALL_TOOLS = [web_search, deep_research]` at module or function level
- **When** `extract_functions_and_calls` scans the file
- **Then** `web_search` and `deep_research` appear as callee edges from the enclosing context (module-level assignment → treated as references from a synthetic `__module__` caller, or from the enclosing function if inside one)

### AC4: Nested Functions Registered (R3)

- **Given** a Python file with `def outer(): def inner(): pass`
- **When** `extract_functions_and_calls` scans the file
- **Then** `inner` (or `outer.inner`) appears in `func_registry` and its calls appear in `call_edges`

### AC5: Existing Tests Pass (R4)

- **Given** the full test suite in `tests/unit/`
- **When** `pytest tests/unit/ -q` is run after implementing R1–R3
- **Then** all 3937+ tests pass with 0 failures

### AC6: Edge Count Increase in pactsearch (R5)

- **Given** `pactkit visualize --mode call` run on pactsearch before and after this change
- **When** edge counts are compared
- **Then** `grep " --> " call_graph.mmd | wc -l` shows an increase of at least 20% (current: 1,349 edges)

## Target Call Chain

```
pactkit visualize --mode call
  └── _build_call_graph(root, all_files, ...)           visualize.py:2115
        └── PythonAnalyzer.extract_functions_and_calls  visualize.py:280
              └── _extract_calls(func_node, ...)        visualize.py:432  ← R1, R2 change here
                   ast.walk(func_node)                  ← currently only captures ast.Name + self.attr
        └── (loop over class body items)                visualize.py:303  ← R3 change here (replace with ast.walk)
```

**Source file**: `src/pactkit/skills/visualize.py` (deployed copy: `~/.claude/skills/pactkit-visualize/scripts/visualize.py`).  
Changes MUST be made to the source file — `pactkit update` redeploys to the skills directory.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py` | Extend `_extract_calls`: remove `self`-only guard; emit `node.func.attr` for all `ast.Attribute` calls not in `_BUILTIN_CALLEES` | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Extend `_extract_calls`: scan `ast.walk(func_node)` for `ast.Name` nodes in `ast.List`, `ast.Tuple`, `ast.keyword` contexts; emit non-builtin names as callee references | Step 1 | Medium |
| 3 | `src/pactkit/skills/visualize.py` | Extend `extract_functions_and_calls`: replace `ast.iter_child_nodes(tree)` + manual class body loop with `ast.walk(tree)` to capture nested functions; track enclosing function name for qname prefixing | Steps 1-2 | Medium |
| 4 | `tests/unit/test_story_slim119.py` | Write TDD tests for AC1–AC4 before implementing | None | Low |
| 5 | Run `pactkit update` | Redeploy visualize.py to `~/.claude/skills/pactkit-visualize/scripts/` | Steps 1-3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Input Validation) | Yes | `_extract_calls` processes AST nodes from user source files — `ast.parse()` can raise `SyntaxError`; already handled by `except (SyntaxError, UnicodeDecodeError, ValueError)`. No change needed. |
| SEC-2 (Auth) | N/A | no auth changes |
| SEC-3 (SQL Injection) | N/A | no SQL |
| SEC-4 (Path Traversal) | N/A | file reads already guarded by `MAX_FILE_BYTES` check |
| SEC-5 (Secret Leakage) | N/A | no credentials |
| SEC-6 (Dependency) | N/A | no new dependencies — stdlib `ast` only |
| SEC-7 (Error Handling) | Yes | new code paths in `_extract_calls` MUST be wrapped in try/except consistent with existing pattern — attribute access on AST nodes can raise `AttributeError` if tree is malformed |
| SEC-8 (XSS) | N/A | no web UI |

## Technical Design

### Lateral Scan Results

- Operation: `_extract_calls` — call extraction from AST nodes
- Existing implementations: 1 (`visualize.py:432`)
- Tree-sitter analyzers (`GoAnalyzer`, `TSAnalyzer`, `JavaAnalyzer`) have their own `_extract_calls_from_body` methods — these are NOT changed by this story (Python-only scope)
- Assessment: Modify existing `_extract_calls` and `extract_functions_and_calls` — no new abstraction needed

### R1 Design — Non-self Attribute Calls

```python
# Current (line 441–446):
elif isinstance(node.func, ast.Attribute):
    if isinstance(node.func.value, ast.Name):
        if node.func.value.id == 'self' and current_class:
            callees.append(f'{current_class}.{node.func.attr}')
        # Skip non-self ...

# New:
elif isinstance(node.func, ast.Attribute):
    attr = node.func.attr
    if attr not in _BUILTIN_CALLEES:
        if isinstance(node.func.value, ast.Name):
            if node.func.value.id == 'self' and current_class:
                callees.append(f'{current_class}.{attr}')
            else:
                callees.append(attr)  # bare method name; _resolve_callee handles suffix match
        else:
            callees.append(attr)  # chained calls e.g. foo().bar()
```

### R2 Design — Function References

Scan occurs inside `_extract_calls` via an additional `ast.walk` pass looking for `ast.Name` nodes that are:
- Direct elements of `ast.List` or `ast.Tuple` (list/tuple literals)
- `ast.keyword.value` in function calls (keyword args)
- RHS of `ast.Assign` when the value is a bare `ast.Name`

Filter: name not in `_BUILTIN_CALLEES`, name is not a single char, name is not all-uppercase (constants), name != `None`/`True`/`False`.

### R3 Design — Nested Functions

Replace the top-level loop:
```python
# Current:
for node in ast.iter_child_nodes(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): ...
    elif isinstance(node, ast.ClassDef):
        for item in node.body: ...

# New: use ast.walk to collect all function defs, track parent chain for qname
```

Use `ast.walk(tree)` to find all `FunctionDef`/`AsyncFunctionDef` nodes. Track parent via a pre-pass that builds a `{child_id: parent_node}` dict using `ast.walk`. Construct qname as `ClassName.method.inner_name` for nested functions.

## Out of Scope

- Go/TypeScript/Java analyzer improvements (separate story if needed)
- Type inference to qualify `obj.method()` with `obj`'s class type (requires type system, out of scope)
- Capturing `**kwargs` dispatch patterns (too dynamic, high false-positive risk)
- Changing Mermaid node ID format (breaking change)
