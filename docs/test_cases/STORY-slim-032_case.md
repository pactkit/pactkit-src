# Test Cases: STORY-slim-032 — TreeSitterAnalyzer base class + Go adapter

| Field | Value |
|-------|-------|
| Story | STORY-slim-032 |
| Level | API (unit) — standalone script function calls via exec(VISUALIZE_SOURCE) |
| Generated | 2026-03-24 |
| Verdict | QA PASS |

---

## AC1: Go file graph non-empty (R3, R4)

```gherkin
Feature: GoAnalyzer extracts import edges for Go source files

  Scenario: Single import statement
    Given a temporary Go file containing "import \"fmt\""
    When GoAnalyzer().extract_imports(file) is called
    Then the result contains "fmt"
    And the result is a list

  Scenario: Block import with multiple packages
    Given a temporary Go file containing a block import of "fmt", "net/http", "os"
    When GoAnalyzer().extract_imports(file) is called
    Then the result contains "fmt"
    And the result contains "net/http"
    And the result contains "os"

  Scenario: Named import returns path, not alias
    Given a temporary Go file containing "import alias \"path/filepath\""
    When GoAnalyzer().extract_imports(file) is called
    Then the result contains "path/filepath"
    And the result does NOT contain "alias"

  Scenario: File with no imports
    Given a temporary Go file "package main\n\nfunc main() {}"
    When GoAnalyzer().extract_imports(file) is called
    Then the result is a list
    And "fmt" is not in the result

  Scenario: Block import drives _build_file_graph via GoAnalyzer
    Given a temporary directory with a .go file containing block imports ("fmt", "net/http", "os")
    When GoAnalyzer().extract_imports(file) is called
    Then at least 3 items are returned (fmt, net/http, os)
```

---

## AC2: Go call graph non-empty (R3, R5)

```gherkin
Feature: GoAnalyzer drives _build_call_graph with Go function call edges

  Scenario: Top-level functions with call relationships
    Given a temporary Go file with "func main()" calling "helper()" and "func helper()"
    When _build_call_graph(root, [file], focus=None, entry=None, analyzer=GoAnalyzer()) is called
    Then the result content contains "graph TD"
    And the result content contains "main"
    And the result content contains "helper"

  Scenario: extract_functions_and_calls returns a 2-tuple
    Given any Go file
    When GoAnalyzer().extract_functions_and_calls(file) is called
    Then the return value is a tuple of length 2

  Scenario: Top-level functions registered
    Given a Go file with "func main()" and "func helper()"
    When GoAnalyzer().extract_functions_and_calls(file) is called
    Then "main" is in func_registry
    And "helper" is in func_registry

  Scenario: Plain function call extracted
    Given a Go file where "func main()" calls "helper()"
    When GoAnalyzer().extract_functions_and_calls(file) is called
    Then call_edges["main"] contains "helper"
```

---

## AC3: Go methods extracted (R5)

```gherkin
Feature: GoAnalyzer extracts method receivers as ClassName.MethodName

  Scenario: Method with pointer receiver registered
    Given a Go file with "func (s *Server) HandleRequest()"
    When GoAnalyzer().extract_functions_and_calls(file) is called
    Then "Server.HandleRequest" is in func_registry

  Scenario: Method call from receiver body extracted
    Given a Go file where "func (s *Server) HandleRequest()" calls "s.validateInput()"
    When GoAnalyzer().extract_functions_and_calls(file) is called
    Then call_edges["Server.HandleRequest"] contains a callee matching "validateInput"

  Scenario: func_registry values equal the file stem
    Given a temporary Go file named "myservice.go" with func main() and func helper()
    When GoAnalyzer().extract_functions_and_calls(file) is called
    Then func_registry["main"] == "myservice"
    And func_registry["helper"] == "myservice"
```

---

## AC4: Auto-detection works (R6, R7)

```gherkin
Feature: _select_analyzer auto-selects GoAnalyzer for Go projects

  Scenario: _select_analyzer("go") returns GoAnalyzer instance
    Given tree-sitter and tree-sitter-go are installed
    When _select_analyzer("go") is called
    Then the return value is an instance of GoAnalyzer

  Scenario: _HAS_TREE_SITTER is True when tree-sitter is installed
    Given tree-sitter is importable in the environment
    When the _HAS_TREE_SITTER flag is checked
    Then _HAS_TREE_SITTER is True

  Scenario: Python project uses PythonAnalyzer via _detect_stack + _select_analyzer
    Given a temporary directory with "pyproject.toml"
    When _detect_stack(root) is called
    Then it returns "python"
    When _select_analyzer("python") is called
    Then the return value is an instance of PythonAnalyzer
```

---

## AC5: Graceful degradation without tree-sitter (R1)

```gherkin
Feature: _select_analyzer falls back to PythonAnalyzer when tree-sitter is absent

  Scenario: Unknown stack always falls back to PythonAnalyzer
    Given _select_analyzer is available
    When _select_analyzer("ruby") is called
    Then the return value is an instance of PythonAnalyzer

  Scenario: _select_analyzer always returns a LanguageAnalyzer
    Given _select_analyzer is available
    When _select_analyzer is called with each of: "python", "go", "java", "node", "unknown"
    Then every return value is an instance of LanguageAnalyzer

  Scenario: tree-sitter optional deps in pyproject.toml
    Given pyproject.toml in the project root
    When reading [project.optional-dependencies]
    Then a "multilang" group exists containing "tree-sitter>=0.25" and "tree-sitter-go>=0.25"

  Scenario: Guard import prevents crash when tree-sitter is missing
    Given visualize.py wraps tree-sitter imports in try/except ImportError
    When tree-sitter is not installed
    Then _HAS_TREE_SITTER is False
    And _select_analyzer("go") returns PythonAnalyzer with a stderr warning
    And no ImportError propagates to the caller
```

---

## AC6: TreeSitterAnalyzer reusable (R2)

```gherkin
Feature: TreeSitterAnalyzer is an open base class — subclasses only need grammar + queries

  Scenario: GoAnalyzer is a subclass of LanguageAnalyzer
    Given GoAnalyzer is defined in visualize.py
    When checking issubclass(GoAnalyzer, LanguageAnalyzer)
    Then the result is True

  Scenario: TreeSitterAnalyzer is a subclass of LanguageAnalyzer
    Given TreeSitterAnalyzer is defined in visualize.py
    When checking issubclass(TreeSitterAnalyzer, LanguageAnalyzer)
    Then the result is True

  Scenario: GoAnalyzer instantiates without error
    Given tree-sitter and tree-sitter-go are installed
    When GoAnalyzer() is called with no arguments
    Then no exception is raised
    And the instance is not None

  Scenario: A hypothetical JavaAnalyzer(TreeSitterAnalyzer) would not require modifying TreeSitterAnalyzer
    Given TreeSitterAnalyzer provides __init__, _captures, _matches, extract_imports, extract_functions_and_calls
    When a new subclass overrides only _extract_funcs_and_calls with Java-specific logic
    Then it inherits all shared infrastructure without modification
    # (Verified structurally: _extract_funcs_and_calls is a hook method returning ({}, {}))
```

---

## AC7: Python output unchanged (R7)

```gherkin
Feature: Adding _select_analyzer does not alter Python project behavior

  Scenario: _select_analyzer("python") returns PythonAnalyzer
    Given _select_analyzer is defined
    When _select_analyzer("python") is called
    Then the return value is an instance of PythonAnalyzer
    And type(analyzer).__name__ == "PythonAnalyzer"

  Scenario: PythonAnalyzer still extracts Python functions and calls correctly
    Given a Python file with "def foo(): bar()" and "def bar(): pass"
    And _select_analyzer is used to obtain the analyzer
    When analyzer.extract_functions_and_calls(file) is called via _select_analyzer("python")
    Then "foo" is in func_registry
    And "bar" is in func_registry
    And "bar" is in call_edges["foo"]

  Scenario: visualize() and impact() use _select_analyzer (not hardcoded PythonAnalyzer)
    Given src/pactkit/skills/visualize.py (via VISUALIZE_SOURCE)
    When scanning the source for the string "_select_analyzer"
    Then "_select_analyzer" is present in the source
    And visualize() calls _select_analyzer(_detect_stack(root))
    And impact() calls _select_analyzer(stack)
```

---

## Error Handling

```gherkin
Feature: GoAnalyzer handles file errors gracefully

  Scenario: extract_imports on missing file
    Given a Path pointing to a nonexistent Go file
    When GoAnalyzer().extract_imports(file) is called
    Then the return value is []
    And no exception is raised

  Scenario: extract_functions_and_calls on missing file
    Given a Path pointing to a nonexistent Go file
    When GoAnalyzer().extract_functions_and_calls(file) is called
    Then func_registry == {}
    And call_edges == {}
    And no exception is raised
```

---

## Test Suite Coverage Matrix

| Test Class | Tests | ACs Covered |
|------------|-------|-------------|
| TestTreeSitterAnalyzerCreation | 4 | AC6 |
| TestGoAnalyzerExtractImports | 5 | AC1 |
| TestGoAnalyzerExtractFunctionsAndCalls | 6 | AC2, AC3 |
| TestGoAnalyzerErrorHandling | 2 | AC5 (error path) |
| TestSelectAnalyzerGo | 2 | AC4, AC5 |
| TestSelectAnalyzerPython | 2 | AC7 |
| TestSelectAnalyzerFallback | 2 | AC5 |
| TestPythonOutputUnchanged | 3 | AC4, AC7 |
| TestGoAnalyzerInCallGraph | 2 | AC1, AC2 |
| **Total** | **28** | **AC1–AC7** |

---

## OWASP Security Assessment

| Check | Finding |
|-------|---------|
| Path Traversal | `file_path.read_bytes()` reads user-supplied paths. `Path(target).resolve()` normalizes the scan root. tree-sitter parses source bytes in memory — no shell execution. Risk: LOW. |
| Code Injection | tree-sitter queries are hardcoded constants (`_GO_IMPORT_QUERY`, etc.). No user input reaches Query() construction. Risk: N/A. |
| Dependency Safety | `tree-sitter` and `tree-sitter-go` are official packages. Grammar packages are sandboxed C parsers with no network access. Risk: LOW. |
| Secrets | No credentials or tokens involved. Risk: N/A. |
| Denial of Service | `MAX_SCAN_FILES = 500` ceiling already in place. tree-sitter parse is bounded by file size. Risk: LOW. |
| Import Guard | `try/except ImportError` on tree-sitter import prevents crash in restricted environments. Risk: MITIGATED. |

---

## Issues

None. All 28 tests pass. All 7 ACs are covered by at least one test. Implementation is consistent with the Spec.
