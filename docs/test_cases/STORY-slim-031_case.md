# Test Cases: STORY-slim-031 — Unified impact test mapping via LANG_PROFILES

| Field | Value |
|-------|-------|
| Story | STORY-slim-031 |
| Level | API (unit) — standalone script function calls via exec(VISUALIZE_SOURCE) |
| Generated | 2026-03-24 |
| Verdict | QA PASS |

---

## AC1: Python impact unchanged (R2, R3)

```gherkin
Feature: Python project impact() returns the same result as before

  Scenario: Python project with load_config function and matching test file
    Given a temporary project directory
    And "pyproject.toml" exists (Python marker)
    And "src/config.py" contains "def load_config(): return {}"
    And "tests/unit/test_config.py" exists
    When impact(target, entry="load_config") is called
    Then the result contains "tests/unit/test_config.py"
    And the result is a space-separated string

  Scenario: Python project with no test file
    Given a temporary project directory
    And "pyproject.toml" exists
    And "src/config.py" contains "def load_config(): return {}"
    And no test file exists
    When impact(target, entry="load_config") is called
    Then the result is an empty string ""

  Scenario: impact() with no entry parameter
    Given any project directory
    When impact(target, entry=None) is called
    Then the result is an empty string ""

  Scenario: impact() always returns a string
    Given a Python project directory
    When impact(target, entry="nonexistent_func") is called
    Then the result is a str instance
```

---

## AC2: Go test mapping works (R1, R5)

```gherkin
Feature: Go project _resolve_test_path maps source to _test.go file

  Scenario: Go source file resolves to co-located _test.go
    Given a temporary project directory
    And "internal/config/config.go" exists with "package config"
    And "internal/config/config_test.go" exists with "package config"
    When _resolve_test_path(root, "config", source_file, "go") is called
      Where source_file = root / "internal/config/config.go"
    Then the result is a Path pointing to "internal/config/config_test.go"

  Scenario: Go test file does not exist
    Given a temporary project directory
    And "internal/config/config.go" exists
    And no config_test.go exists
    When _resolve_test_path(root, "config", source_file, "go") is called
    Then the result is None
```

---

## AC3: Java test mapping works (R1, R5)

```gherkin
Feature: Java project _resolve_test_path maps source to Test.java file

  Scenario: Java source file resolves to matching Test.java
    Given a temporary project directory
    And "com/app/Config.java" exists
    And "src/test/java/com/app/ConfigTest.java" exists
    When _resolve_test_path(root, "Config", source_file, "java") is called
      Where source_file = root / "com/app/Config.java"
    Then the result is a Path pointing to "src/test/java/com/app/ConfigTest.java"

  Scenario: Java test file does not exist
    Given a temporary project directory
    And "src/main/java/com/app/Config.java" exists
    And no ConfigTest.java exists
    When _resolve_test_path(root, "Config", source_file, "java") is called
    Then the result is None
```

---

## AC4: Node test mapping works (R1)

```gherkin
Feature: Node project _resolve_test_path maps source to .test.ts file

  Scenario: Node source file resolves to __tests__/utils.test.ts
    Given a temporary project directory
    And "src/utils.ts" exists
    And "__tests__/utils.test.ts" exists
    When _resolve_test_path(root, "utils", source_file, "node") is called
      Where source_file = root / "src/utils.ts"
    Then the result is a Path pointing to "__tests__/utils.test.ts"

  Scenario: Node test file does not exist
    Given a temporary project directory
    And "src/utils.ts" exists
    And no __tests__/utils.test.ts exists
    When _resolve_test_path(root, "utils", source_file, "node") is called
    Then the result is None
```

---

## AC5: Fallback when pattern misses (R2)

```gherkin
Feature: impact() falls back to hardcoded path when pattern resolves to nothing

  Scenario: Pattern resolves to existing file — no fallback needed
    Given a Python project directory with "pyproject.toml"
    And "src/config.py" contains "def load_config(): pass"
    And "tests/unit/test_config.py" exists (Python pattern and fallback are identical)
    When impact(target, entry="load_config") is called
    Then "test_config.py" is in the result (via pattern or fallback, same path)

  Scenario: Neither pattern path nor fallback path exists
    Given a Python project directory with "pyproject.toml"
    And "src/config.py" contains "def load_config(): pass"
    And no test file exists at any location
    When impact(target, entry="load_config") is called
    Then the result is an empty string ""

  Scenario: _resolve_test_path returns None for missing test file
    Given any project directory
    And source_file exists but corresponding test file does not
    When _resolve_test_path(root, stem, source_file, stack) is called
    Then it returns None
    And impact() falls through to the fallback path check
```

---

## AC6: _detect_stack returns stack name (R3)

```gherkin
Feature: _detect_stack() returns the stack identifier string

  Scenario: pyproject.toml present → "python"
    Given a temporary project directory
    And "pyproject.toml" exists
    When _detect_stack(root) is called
    Then it returns the string "python"

  Scenario: setup.py present → "python"
    Given a temporary project directory
    And "setup.py" exists
    When _detect_stack(root) is called
    Then it returns the string "python"

  Scenario: go.mod present → "go"
    Given a temporary project directory
    And "go.mod" exists
    When _detect_stack(root) is called
    Then it returns the string "go"

  Scenario: pom.xml present → "java"
    Given a temporary project directory
    And "pom.xml" exists
    When _detect_stack(root) is called
    Then it returns the string "java"

  Scenario: package.json present → "node"
    Given a temporary project directory
    And "package.json" exists
    When _detect_stack(root) is called
    Then it returns the string "node"

  Scenario: No marker files → defaults to "python"
    Given a temporary project directory with no marker files
    When _detect_stack(root) is called
    Then it returns the string "python"

  Scenario: _detect_stack always returns a string
    Given any project directory
    When _detect_stack(root) is called
    Then the return value is a str instance (never None)

  Scenario: _detect_file_ext() remains backward compatible after refactor
    Given a Python project directory with "pyproject.toml"
    When _detect_file_ext(root) is called
    Then it returns ".py" (delegates to _detect_stack())

  Scenario: _detect_file_ext() for Go project
    Given a Go project directory with "go.mod"
    When _detect_file_ext(root) is called
    Then it returns ".go"
```

---

## AC7: Inlined test_map_patterns match LANG_PROFILES (R4)

```gherkin
Feature: _TEST_MAP_PATTERNS in visualize.py matches canonical LANG_PROFILES

  Scenario: All four stacks are present in _TEST_MAP_PATTERNS
    Given the _TEST_MAP_PATTERNS dict in visualize.py (via VISUALIZE_SOURCE)
    When checking for keys "python", "node", "go", "java"
    Then all four keys exist

  Scenario: Python pattern matches canonical source
    Given LANG_PROFILES["python"]["test_map_pattern"] in workflows.py
    And _TEST_MAP_PATTERNS["python"] in visualize.py
    When comparing the two values
    Then they are exactly equal: "tests/unit/test_{module}.py"

  Scenario: Node pattern matches canonical source
    Given LANG_PROFILES["node"]["test_map_pattern"] = "__tests__/{module}.test.ts"
    And _TEST_MAP_PATTERNS["node"] in visualize.py
    When comparing the two values
    Then they are exactly equal

  Scenario: Go pattern matches canonical source
    Given LANG_PROFILES["go"]["test_map_pattern"] = "{package}/{module}_test.go"
    And _TEST_MAP_PATTERNS["go"] in visualize.py
    When comparing the two values
    Then they are exactly equal

  Scenario: Java pattern matches canonical source
    Given LANG_PROFILES["java"]["test_map_pattern"] = "src/test/java/{package}/{module}Test.java"
    And _TEST_MAP_PATTERNS["java"] in visualize.py
    When comparing the two values
    Then they are exactly equal

  Scenario: Canonical-source comment is present in visualize.py
    Given src/pactkit/skills/visualize.py
    When reading the line above _TEST_MAP_PATTERNS declaration
    Then it contains a comment: "# Canonical: src/pactkit/prompts/workflows.py LANG_PROFILES[*].test_map_pattern"
```

---

## Implementation Verification

```gherkin
Feature: impact() call chain uses new helpers

  Scenario: impact() calls _detect_stack before reverse BFS
    Given src/pactkit/skills/visualize.py
    When reviewing the impact() function body
    Then stack = _detect_stack(root) is called
    And _resolve_test_path(root, stem, source_file, stack) is called per visited function
    And fallback to root / "tests" / "unit" / f"test_{stem}.py" is executed when _resolve_test_path returns None

  Scenario: _resolve_test_path uses _TEST_MAP_PATTERNS with {module} and {package} substitution
    Given src/pactkit/skills/visualize.py
    When reviewing _resolve_test_path(root, stem, source_file, stack)
    Then pattern is retrieved from _TEST_MAP_PATTERNS.get(stack, "tests/unit/test_{module}.py")
    And {module} is replaced with stem
    And {package} is replaced with source_file.parent.relative_to(root)
    And the result is returned only if the path exists, else None

  Scenario: stem_to_file index built from all_files for {package} resolution
    Given src/pactkit/skills/visualize.py
    When reviewing the impact() function body
    Then stem_to_file = {f.stem: f for f in all_files} is built (with setdefault)
    And source_file = stem_to_file.get(stem) is used to derive the package path
```

---

## OWASP Security Assessment

| Check | Finding |
|-------|---------|
| Path Traversal | `source_file.parent.relative_to(root)` raises ValueError if source_file escapes root; `Path(target).resolve()` normalizes the entry point. Risk: LOW. |
| Code Injection | No exec of user-supplied strings. `entry` parameter is used as a function name lookup key only (dict.get). Risk: N/A. |
| Secrets | No credentials or tokens involved. Risk: N/A. |
| Denial of Service | `MAX_SCAN_FILES = 500` ceiling already in place from STORY-060. Risk: LOW. |
| File Read | Only reads files within `root` via rglob with excludes. Risk: LOW. |
