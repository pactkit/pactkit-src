# Test Cases: STORY-slim-034 — TS/JS LanguageAnalyzer adapter

| Field | Value |
|-------|-------|
| Story | STORY-slim-034 |
| Level | API (unit) — standalone script function calls via importlib.util.spec_from_file_location("visualize", vis_path) |
| Generated | 2026-03-24 |
| Verdict | QA PASS |

---

## AC1: TS file graph non-empty (R2, R3)

```gherkin
Feature: TSAnalyzer extracts import edges for TypeScript and JavaScript source files

  Scenario: ES module named import
    Given a temporary .ts file containing 'import { Config } from "./config";'
    When TSAnalyzer().extract_imports(file) is called
    Then the result contains "./config"
    And the result is a list

  Scenario: Default import
    Given a temporary .ts file containing 'import express from "express";'
    When TSAnalyzer().extract_imports(file) is called
    Then the result contains "express"

  Scenario: Re-export from another module
    Given a temporary .ts file containing 'export { handler } from "./handler";'
    When TSAnalyzer().extract_imports(file) is called
    Then the result contains "./handler"

  Scenario: Multiple imports all returned
    Given a .ts file with 'import { A } from "./a";' and 'import { B } from "./b";'
    When TSAnalyzer().extract_imports(file) is called
    Then len(result) >= 2

  Scenario: File with no imports returns empty list
    Given a .ts file containing only 'const x = 1;'
    When TSAnalyzer().extract_imports(file) is called
    Then the result is []

  Scenario: extract_imports always returns a list
    Given any .ts file
    When TSAnalyzer().extract_imports(file) is called
    Then the return type is list

  Scenario: tree-sitter-typescript package is importable
    Given the project's multilang optional deps include "tree-sitter-typescript>=0.23"
    When "import tree_sitter_typescript" is executed
    Then no ImportError is raised
```

---

## AC2: TS call graph non-empty (R2, R4)

```gherkin
Feature: TSAnalyzer extracts function definitions and call edges

  Scenario: extract_functions_and_calls returns a 2-tuple
    Given any .ts file
    When TSAnalyzer().extract_functions_and_calls(file) is called
    Then the return value is a tuple of length 2

  Scenario: Named function registered in func_registry
    Given a .ts file with 'function handleRequest(req: Request) { validate(req); }'
    When TSAnalyzer().extract_functions_and_calls(file) is called
    Then "handleRequest" is in func_registry

  Scenario: Call inside named function extracted
    Given a .ts file where handleRequest() calls validate()
    When TSAnalyzer().extract_functions_and_calls(file) is called
    Then call_edges["handleRequest"] contains a callee matching "validate"

  Scenario: Method call (obj.method) extracted as callee
    Given a .ts file with 'function run() { console.log("hi"); }'
    When TSAnalyzer().extract_functions_and_calls(file) is called
    Then call_edges["run"] contains a callee matching "console.log"

  Scenario: func_registry values equal the file stem
    Given a .ts file named "myModule.ts" containing 'function foo() {}'
    When TSAnalyzer().extract_functions_and_calls(file) is called
    Then func_registry["foo"] == "myModule"
```

---

## AC3: Arrow functions extracted (R4)

```gherkin
Feature: TSAnalyzer extracts arrow function definitions and their call edges

  Scenario: Exported async arrow function registered
    Given a .ts file with 'export const handler = async (req: Request) => { validateInput(req); };'
    When TSAnalyzer().extract_functions_and_calls(file) is called
    Then "handler" is in func_registry

  Scenario: Callee inside arrow function extracted
    Given a .ts file with handler arrow function calling validateInput
    When TSAnalyzer().extract_functions_and_calls(file) is called
    Then call_edges["handler"] contains a callee matching "validateInput"
```

---

## AC4: CommonJS require extracted (R3)

```gherkin
Feature: TSAnalyzer extracts CommonJS require() calls as imports

  Scenario: require() call treated as import
    Given a .js file with 'const path = require("path");'
    When TSAnalyzer().extract_imports(file) is called
    Then the result contains "path"
```

---

## AC5: Auto-detection works (R6)

```gherkin
Feature: _select_analyzer auto-selects TSAnalyzer for Node projects

  Scenario: _select_analyzer("node") returns TSAnalyzer instance
    Given tree-sitter and tree-sitter-typescript are installed
    When _select_analyzer("node") is called
    Then the return value is an instance of TSAnalyzer

  Scenario: _select_analyzer("node") returns a LanguageAnalyzer
    Given tree-sitter and tree-sitter-typescript are installed
    When _select_analyzer("node") is called
    Then the return value is an instance of LanguageAnalyzer

  Scenario: package.json project detected as node stack
    Given a temporary directory with only "package.json"
    When _detect_stack(root) is called
    Then it returns "node"
```

---

## AC6: JS files also scanned (R5)

```gherkin
Feature: _scan_files discovers both .ts and .js files in Node projects

  Scenario: Node project stack detected when package.json present
    Given a directory with package.json, app.ts, and helper.js
    When _detect_stack(root) is called
    Then it returns "node"

  Scenario: .ts files discovered by _scan_files with file_ext=".ts"
    Given a Node project directory with app.ts
    When _scan_files(root, file_ext=".ts") is called
    Then "app.ts" is in the returned file list

  Scenario: .js files discovered by _scan_files with file_ext=".js"
    Given a Node project directory with helper.js
    When _scan_files(root, file_ext=".js") is called
    Then "helper.js" is in the returned file list
```

---

## AC7: Graceful degradation (R1, R6)

```gherkin
Feature: _select_analyzer falls back gracefully when tree-sitter-typescript is absent

  Scenario: _select_analyzer always returns a LanguageAnalyzer for any stack
    Given _select_analyzer is available
    When _select_analyzer is called with each of: "python", "go", "java", "node", "unknown"
    Then every return value is an instance of LanguageAnalyzer
    And no ImportError propagates to the caller

  Scenario: TSAnalyzer construction guarded by try/except ImportError in _select_analyzer
    Given visualize.py wraps TSAnalyzer() construction in try/except ImportError
    When tree-sitter-typescript is not installed
    Then _select_analyzer("node") returns PythonAnalyzer with a stderr warning
    And no crash occurs
```

---

## Error Handling

```gherkin
Feature: TSAnalyzer handles file errors gracefully

  Scenario: extract_imports on missing file
    Given a Path pointing to a nonexistent .ts file
    When TSAnalyzer().extract_imports(file) is called
    Then the return value is []
    And no exception is raised

  Scenario: extract_functions_and_calls on missing file
    Given a Path pointing to a nonexistent .ts file
    When TSAnalyzer().extract_functions_and_calls(file) is called
    Then func_registry == {}
    And call_edges == {}
    And no exception is raised

  Scenario: extract_imports on empty file
    Given a .ts file containing 0 bytes
    When TSAnalyzer().extract_imports(file) is called
    Then the return value is []
    And no exception is raised

  Scenario: extract_functions_and_calls on empty file
    Given a .ts file containing 0 bytes
    When TSAnalyzer().extract_functions_and_calls(file) is called
    Then func_registry == {}
    And call_edges == {}
    And no exception is raised
```

---

## Test Suite Coverage Matrix

| Test Class | Tests | ACs Covered |
|------------|-------|-------------|
| TestTSAnalyzerCreation | 4 | AC1 (dep), AC2, AC7 (type hierarchy) |
| TestTSAnalyzerExtractImports | 7 | AC1, AC4 |
| TestTSAnalyzerExtractFunctionsAndCalls | 6 | AC2, AC3 |
| TestTSAnalyzerErrorHandling | 4 | Error Handling |
| TestSelectAnalyzerNode | 2 | AC5 |
| TestSelectAnalyzerFallbackForTS | 1 | AC7 |
| TestMultiExtensionScanning | 2 | AC6 |
| TestDetectStackNode | 1 | AC5 |
| **Total** | **27** | **AC1–AC7** |

---

## OWASP Security Assessment

| Check | Finding |
|-------|---------|
| Path Traversal | `file_path.read_bytes()` reads user-supplied paths. `Path(target).resolve()` normalizes the scan root. tree-sitter parses source bytes in memory — no shell execution. Risk: LOW. |
| Code Injection | TS/JS tree-sitter queries are hardcoded constants in `TSAnalyzer`. No user input reaches query construction. Risk: N/A. |
| Dependency Safety | `tree-sitter-typescript` is the official tree-sitter grammar package. Grammar packages are sandboxed C parsers with no network access. Risk: LOW. |
| Secrets | No credentials or tokens involved. Risk: N/A. |
| Denial of Service | `MAX_SCAN_FILES = 500` ceiling already in place. tree-sitter parse is bounded by file size. Risk: LOW. |
| Import Guard | `try/except ImportError` in `_select_analyzer` prevents crash when `tree-sitter-typescript` is absent. Risk: MITIGATED. |

---

## Issues

None. All 27 tests pass. All 7 ACs are covered by at least one test. Implementation is consistent with the Spec.

**AC7 note**: The fallback path (absent `tree-sitter-typescript`) is validated structurally — `test_all_stacks_return_language_analyzer` confirms no crash and a `LanguageAnalyzer` is always returned. Direct simulation of the missing-package scenario is not feasible when the package is installed; the guard code path in `_select_analyzer` is confirmed present by code inspection.
