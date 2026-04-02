# Test Cases: STORY-slim-033 — Java LanguageAnalyzer adapter

| Field | Value |
|-------|-------|
| Story | STORY-slim-033 |
| Level | API (unit) — standalone script function calls via exec(VISUALIZE_SOURCE) |
| Generated | 2026-03-24 |
| Verdict | QA PASS |

---

## AC1: Java file graph non-empty (R2, R3)

```gherkin
Feature: JavaAnalyzer extracts import edges for Java source files

  Scenario: Regular import statement
    Given a temporary Java file containing "import com.app.Config;"
    When JavaAnalyzer().extract_imports(file) is called
    Then the result contains "com.app.Config"
    And the result is a list

  Scenario: Multiple regular imports
    Given a temporary Java file with "import com.app.Config;" and "import com.app.utils.Helper;"
    When JavaAnalyzer().extract_imports(file) is called
    Then the result contains "com.app.Config"
    And the result contains "com.app.utils.Helper"

  Scenario: Static import returns class-level path
    Given a temporary Java file with "import static com.app.Config.load;"
    When JavaAnalyzer().extract_imports(file) is called
    Then the result contains at least one item with "com.app" in it

  Scenario: Wildcard import
    Given a temporary Java file with "import com.app.*;"
    When JavaAnalyzer().extract_imports(file) is called
    Then the result contains at least one item with "com.app" in it

  Scenario: File with no imports
    Given a temporary Java file "package com.app;\n\npublic class App {}\n"
    When JavaAnalyzer().extract_imports(file) is called
    Then the return value is a list
    And the list may be empty (no crash)

  Scenario: tree-sitter-java package is importable
    Given the project's multilang optional deps include "tree-sitter-java>=0.23"
    When "import tree_sitter_java" is executed
    Then no ImportError is raised
```

---

## AC2: Java call graph non-empty (R2, R4)

```gherkin
Feature: JavaAnalyzer extracts method call edges for Java source files

  Scenario: extract_functions_and_calls returns a 2-tuple
    Given any Java file
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then the return value is a tuple of length 2

  Scenario: Instance method registered with class context
    Given a Java file with "public void handleRequest()" in class "Service"
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then "Service.handleRequest" is in func_registry

  Scenario: Method call extracted from body
    Given a Java file where "handleRequest()" calls "processData()"
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then call_edges["Service.handleRequest"] contains a callee matching "processData"

  Scenario: Object method call extracted
    Given a Java file where "handleRequest()" calls "service.process()"
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then call_edges["Controller.handleRequest"] contains a callee matching "process"

  Scenario: func_registry values equal the file stem
    Given a temporary Java file named "MyService.java" with methods
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then every value in func_registry equals "MyService"
```

---

## AC3: Static methods extracted (R4)

```gherkin
Feature: JavaAnalyzer extracts static methods and static call targets

  Scenario: Static method registered with class context
    Given a Java file with "public static void main(String[] args)" in class "Main"
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then "Main.main" is in func_registry

  Scenario: Static call target extracted from body
    Given a Java file where "main()" calls "Config.load()"
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then call_edges["Main.main"] contains a callee matching "load"

  Scenario: Constructor registered as ClassName.ClassName
    Given a Java file with "public Config()" constructor in class "Config"
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then "Config.Config" is in func_registry

  Scenario: Constructor call targets extracted
    Given a Java file where "Config()" constructor calls "init()"
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then call_edges["Config.Config"] contains a callee matching "init"
```

---

## AC4: Auto-detection works (R5)

```gherkin
Feature: _select_analyzer auto-selects JavaAnalyzer for Java projects

  Scenario: _select_analyzer("java") returns JavaAnalyzer instance
    Given tree-sitter and tree-sitter-java are installed
    When _select_analyzer("java") is called
    Then the return value is an instance of JavaAnalyzer

  Scenario: _select_analyzer("java") returns a LanguageAnalyzer
    Given tree-sitter and tree-sitter-java are installed
    When _select_analyzer("java") is called
    Then the return value is an instance of LanguageAnalyzer

  Scenario: pom.xml project detected as java stack
    Given a temporary directory with "pom.xml"
    When _detect_stack(root) is called
    Then it returns "java"

  Scenario: build.gradle project detected as java stack
    Given a temporary directory with "build.gradle"
    When _detect_stack(root) is called
    Then it returns "java"
```

---

## AC5: Graceful degradation (R1, R5)

```gherkin
Feature: _select_analyzer falls back gracefully when tree-sitter-java is absent

  Scenario: _select_analyzer always returns a LanguageAnalyzer for any stack
    Given _select_analyzer is available
    When _select_analyzer is called with each of: "python", "go", "java", "node", "unknown"
    Then every return value is an instance of LanguageAnalyzer
    And no ImportError propagates to the caller

  Scenario: JavaAnalyzer construction guarded by try/except ImportError in _select_analyzer
    Given visualize.py wraps JavaAnalyzer() construction in try/except ImportError
    When tree-sitter-java is not installed
    Then _select_analyzer("java") returns PythonAnalyzer with a stderr warning
    And no crash occurs

  Scenario: tree-sitter-java in multilang optional deps
    Given pyproject.toml in the project root
    When reading [project.optional-dependencies]
    Then a "multilang" group exists containing "tree-sitter-java>=0.23"
```

---

## Error Handling

```gherkin
Feature: JavaAnalyzer handles file errors gracefully

  Scenario: extract_imports on missing file
    Given a Path pointing to a nonexistent Java file
    When JavaAnalyzer().extract_imports(file) is called
    Then the return value is []
    And no exception is raised

  Scenario: extract_functions_and_calls on missing file
    Given a Path pointing to a nonexistent Java file
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then func_registry == {}
    And call_edges == {}
    And no exception is raised

  Scenario: extract_imports on empty file
    Given a Java file containing 0 bytes
    When JavaAnalyzer().extract_imports(file) is called
    Then the return value is a list
    And no exception is raised

  Scenario: extract_functions_and_calls on empty file
    Given a Java file containing 0 bytes
    When JavaAnalyzer().extract_functions_and_calls(file) is called
    Then func_registry == {}
    And call_edges == {}
    And no exception is raised
```

---

## Test Suite Coverage Matrix

| Test Class | Tests | ACs Covered |
|------------|-------|-------------|
| TestJavaAnalyzerCreation | 4 | AC2, AC5 (type hierarchy) |
| TestJavaAnalyzerExtractImports | 6 | AC1 |
| TestJavaAnalyzerExtractFunctionsAndCalls | 8 | AC2, AC3 |
| TestJavaAnalyzerErrorHandling | 4 | Error Handling |
| TestSelectAnalyzerJava | 2 | AC4 |
| TestSelectAnalyzerFallbackForJava | 1 | AC5 |
| TestDetectStackJava | 2 | AC4 |
| **Total** | **28** | **AC1–AC5** |

---

## OWASP Security Assessment

| Check | Finding |
|-------|---------|
| Path Traversal | `file_path.read_bytes()` reads user-supplied paths. `Path(target).resolve()` normalizes the scan root. tree-sitter parses source bytes in memory — no shell execution. Risk: LOW. |
| Code Injection | Java tree-sitter queries are hardcoded constants (`_JAVA_IMPORT_QUERY`, `_JAVA_FUNC_QUERY`, etc.). No user input reaches `_TSQuery()` construction. Risk: N/A. |
| Dependency Safety | `tree-sitter-java` is the official tree-sitter grammar package. Grammar packages are sandboxed C parsers with no network access. Risk: LOW. |
| Secrets | No credentials or tokens involved. Risk: N/A. |
| Denial of Service | `MAX_SCAN_FILES = 500` ceiling already in place. tree-sitter parse is bounded by file size. Risk: LOW. |
| Import Guard | `try/except ImportError` in `_select_analyzer` prevents crash when `tree-sitter-java` is absent. Risk: MITIGATED. |

---

## Issues

None. All 28 tests pass. All 5 ACs are covered by at least one test. Implementation is consistent with the Spec.
