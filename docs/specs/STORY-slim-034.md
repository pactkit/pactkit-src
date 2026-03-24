# STORY-slim-034: TS/JS LanguageAnalyzer adapter

| Field | Value |
|-------|-------|
| ID | STORY-slim-034 |
| Status | Done |
| Priority | P2 — Impact 3, Effort 2 |
| Release | 2.3.7 |

## Background

After STORY-slim-032 (TreeSitterAnalyzer + Go) and STORY-slim-033 (Java), TypeScript/JavaScript projects still get empty call graphs. `TSAnalyzer` is the third tree-sitter adapter. TS/JS was previously estimated at ~60-70% regex coverage due to syntax variety (ES modules, CommonJS, arrow functions, class methods). With tree-sitter, coverage reaches near-100% because the parser handles the full grammar. Effort is reduced from 3 to 2 because the `TreeSitterAnalyzer` base class handles all infrastructure.

The main unique challenge for TS/JS is **multi-extension support**: `.ts`, `.tsx`, `.js`, `.jsx` all need to be scanned, whereas other languages have a single extension.

## Requirements

### R1: tree-sitter-typescript dependency (MUST)

`pyproject.toml` MUST add `tree-sitter-typescript` to the `multilang` optional dependency group. This package provides both TypeScript and TSX grammars. For plain JS files, the TypeScript grammar MUST be used (TypeScript is a superset of JavaScript).

### R2: TSAnalyzer subclass (MUST)

`TSAnalyzer(TreeSitterAnalyzer)` MUST configure:
- Language: `tree_sitter_typescript.language_typescript()` (handles both TS and JS)
- Import query: extract ES module imports and CommonJS require calls
- Function query: extract function declarations, arrow functions, class methods
- Call query: extract function calls and method invocations

### R3: Import extraction (MUST)

`TSAnalyzer.extract_imports()` MUST extract:
- ES module imports: `import { Name } from 'module'` → `"module"`
- Default imports: `import Name from 'module'` → `"module"`
- CommonJS: `const Name = require('module')` → `"module"`
- Re-exports: `export { Name } from 'module'` → `"module"`

### R4: Function and call extraction (MUST)

`TSAnalyzer.extract_functions_and_calls()` MUST extract:
- Named functions: `function funcName(` and `export function funcName(`
- Arrow functions: `const funcName = (` and `export const funcName = (`
- Async variants: `async function`, `const fn = async (`
- Class methods: `methodName(` inside class bodies → `ClassName.methodName`
- Calls: `funcName(`, `obj.methodName(`, `await funcName(`

### R5: Multi-extension scanning (MUST)

When `_detect_stack()` returns `"node"`, the file discovery MUST scan for both `.ts` and `.js` files. This MAY be achieved by:
- Running `_scan_files()` twice (once per extension) and merging results, OR
- Extending `_scan_files()` to accept a list of extensions, OR
- Using `_scan_files()` with `.ts` (from `_LANG_FILE_EXT`) and adding a secondary scan for `.js`

The chosen approach MUST NOT break existing single-extension behavior for Python/Go/Java.

### R6: Auto-selected for Node projects (MUST)

When `_detect_stack()` returns `"node"`, `_select_analyzer()` MUST return `TSAnalyzer()`. If `tree-sitter-typescript` is not installed, MUST fall back to `PythonAnalyzer()` with a warning.

## Acceptance Criteria

### AC1: TS file graph non-empty (R2, R3)

- **Given** a Node project with `package.json` and `.ts` files with imports
- **When** running `pactkit visualize`
- **Then** `code_graph.mmd` contains import relationship edges

### AC2: TS call graph non-empty (R2, R4)

- **Given** a TS project with functions calling each other
- **When** running `pactkit visualize --mode call`
- **Then** `call_graph.mmd` contains function→function edges

### AC3: Arrow functions extracted (R4)

- **Given** a TS file with `export const handler = async (req: Request) => { validateInput(req) }`
- **When** extracting functions and calls
- **Then** `handler` appears with callee `validateInput`

### AC4: CommonJS require extracted (R3)

- **Given** a JS file with `const express = require('express')`
- **When** extracting imports
- **Then** `"express"` appears in the import list

### AC5: Auto-detection works (R6)

- **Given** a project with `package.json`
- **When** running `pactkit visualize --mode call`
- **Then** `TSAnalyzer` is used automatically

### AC6: JS files also scanned (R5)

- **Given** a Node project with both `.ts` and `.js` files
- **When** running `pactkit visualize`
- **Then** both `.ts` and `.js` files appear in the graph

### AC7: Graceful degradation (R1, R6)

- **Given** `tree-sitter-typescript` is NOT installed
- **When** running `pactkit visualize` on a Node project
- **Then** falls back to `PythonAnalyzer` with a warning, no crash

## Design

### tree-sitter Queries for TypeScript

```python
# TS/JS import query — covers ES modules, CommonJS, re-exports
IMPORT_QUERY = '''[
  (import_statement source: (string) @import)
  (export_statement source: (string) @import)
  (call_expression
    function: (identifier) @_func (#eq? @_func "require")
    arguments: (arguments (string) @import))
]'''

# TS/JS function query
FUNC_QUERY = '''[
  (function_declaration name: (identifier) @name)
  (method_definition name: (property_identifier) @name)
  (lexical_declaration
    (variable_declarator
      name: (identifier) @name
      value: [(arrow_function) (function_expression)]))
]'''

# TS/JS call query
CALL_QUERY = '''[
  (call_expression function: (identifier) @callee)
  (call_expression function: (member_expression
    object: (_) @obj
    property: (property_identifier) @method))
  (await_expression (call_expression function: (identifier) @callee))
]'''
```

### Multi-Extension Strategy

The simplest approach: `TSAnalyzer` overrides `extract_imports` and `extract_functions_and_calls` to handle any file that tree-sitter-typescript can parse. The file discovery change is in `_scan_files` or in `visualize()`:

```python
# In visualize() / impact(), for node stack:
if stack == 'node':
    # Scan .ts files (primary)
    files_ts, mi_ts, ftn_ts = _scan_files(root, scan_excludes=scan_excludes, file_ext='.ts')
    # Also scan .js files
    files_js, mi_js, ftn_js = _scan_files(root, scan_excludes=scan_excludes, file_ext='.js')
    all_files = files_ts + files_js
    module_index = {**mi_ts, **mi_js}
    file_to_node = {**ftn_ts, **ftn_js}
```

This approach keeps `_scan_files()` simple (single extension) and handles merging at the call site.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `pyproject.toml` | Add `tree-sitter-typescript` to `multilang` optional deps | STORY-slim-032 | Low |
| 2 | `tests/unit/test_story_slim034.py` | Tests with sample TS/JS source strings | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | Implement `TSAnalyzer(TreeSitterAnalyzer)` with TS queries | STORY-slim-032 | Low |
| 4 | `src/pactkit/skills/visualize.py` | Multi-extension scanning for Node projects | Step 3 | Medium |
| 5 | `src/pactkit/skills/visualize.py` | Register TSAnalyzer in `_select_analyzer()` | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-8 Dependencies | Low | `tree-sitter-typescript` is an official tree-sitter grammar package |
| SEC-1 through SEC-7 | N/A | Read-only AST parsing, no new input vectors |

## Out of Scope

- Dynamic imports (`import()` expressions) — tree-sitter can parse them but they resolve at runtime
- Decorator-based routing (e.g., NestJS `@Controller`) — framework-specific semantics
- JSX component call tracking (e.g., `<Component />` as function calls)
- TypeScript type resolution (generic constraints, conditional types)
- `.mjs` / `.cjs` extensions (rare; can be added later)
