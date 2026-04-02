# Test Cases: STORY-slim-029 — Multi-language file discovery via LANG_PROFILES

| Field | Value |
|-------|-------|
| Story | STORY-slim-029 |
| Level | API (unit) — standalone script function calls |
| Generated | 2026-03-24 |
| Verdict | QA PASS |

---

## AC1: Python project unchanged

```gherkin
Feature: Python project file discovery is unchanged

  Scenario: pyproject.toml marker detects Python stack
    Given a temporary project directory
    And a file "pyproject.toml" exists with content "[project]\nname = 'foo'\n"
    When _detect_file_ext(root) is called
    Then it returns ".py"

  Scenario: _scan_files defaults to *.py (backward compatibility)
    Given a temporary project directory
    And "module.py" exists in the root
    And "main.go" exists in the root
    When _scan_files(root) is called with no file_ext argument
    Then "module.py" appears in the result
    And "main.go" does not appear in the result

  Scenario: _scan_files with explicit file_ext='.py' matches default behavior
    Given a temporary project directory
    And "util.py" exists in the root
    When _scan_files(root) is called with no file_ext
    And _scan_files(root, file_ext='.py') is called explicitly
    Then both calls return the same file list
```

---

## AC2: Go project discovers .go files

```gherkin
Feature: Go project file discovery

  Scenario: go.mod marker detects Go stack
    Given a temporary project directory
    And a file "go.mod" exists
    When _detect_file_ext(root) is called
    Then it returns ".go"

  Scenario: _scan_files with file_ext='.go' finds .go files
    Given a temporary project directory
    And "main.go" exists in the root
    And "ignored.py" exists in the root
    When _scan_files(root, file_ext='.go') is called
    Then "main.go" appears in the result
    And "ignored.py" does not appear in the result

  Scenario: _scan_files with file_ext='.go' finds .go files in subdirectories
    Given a temporary project directory
    And "src/main/App.java" does not exist
    And "cmd/main.go" exists
    When _scan_files(root, file_ext='.go') is called
    Then "main.go" appears in the result
```

---

## AC3: Java project discovers .java files

```gherkin
Feature: Java project file discovery

  Scenario: pom.xml marker detects Java stack
    Given a temporary project directory
    And a file "pom.xml" exists with Maven XML content
    When _detect_file_ext(root) is called
    Then it returns ".java"

  Scenario: _scan_files with file_ext='.java' finds nested Java files
    Given a temporary project directory
    And directory "src/main/java/" exists
    And "src/main/java/App.java" exists
    When _scan_files(root, file_ext='.java') is called
    Then "App.java" appears in the result
```

---

## AC4: Unknown stack falls back to *.py

```gherkin
Feature: Unknown stack default fallback

  Scenario: No marker files present — defaults to .py
    Given a temporary empty project directory
    And no marker files exist (no pyproject.toml, go.mod, pom.xml, package.json, etc.)
    When _detect_file_ext(root) is called
    Then it returns ".py"
```

---

## AC5: Full tree scanned, not restricted to source_dirs

```gherkin
Feature: Full rglob scan not restricted to source_dirs

  Scenario: Go project with files in both cmd/ and internal/ are both discovered
    Given a temporary Go project directory
    And "go.mod" exists in root
    And "cmd/main.go" exists
    And "internal/server/server.go" exists
    When _scan_files(root, file_ext='.go') is called
    Then "main.go" appears in the result
    And "server.go" appears in the result
```

---

## Additional Scenarios (implementation coverage beyond ACs)

```gherkin
Feature: pactkit.yaml stack override

  Scenario: pactkit.yaml with explicit stack overrides marker detection
    Given a temporary project directory with no go.mod
    And ".claude/pactkit.yaml" exists with "stack: go"
    When _detect_file_ext(root) is called
    Then it returns ".go"

  Scenario: pactkit.yaml with stack: auto falls through to marker detection
    Given ".claude/pactkit.yaml" exists with "stack: auto"
    And "go.mod" exists in root
    When _detect_file_ext(root) is called
    Then it returns ".go"

Feature: Node project file discovery

  Scenario: package.json marker detects Node stack
    Given a temporary project directory
    And "package.json" exists
    When _detect_file_ext(root) is called
    Then it returns ".ts"
```

---

## Wiring Verification

```gherkin
Feature: visualize() and impact() wiring to _detect_file_ext

  Scenario: visualize() calls _detect_file_ext before _scan_files
    Given src/pactkit/skills/visualize.py
    When reviewing the visualize() function body
    Then file_ext = _detect_file_ext(root) is called before _scan_files
    And _scan_files is called with file_ext=file_ext

  Scenario: impact() calls _detect_file_ext before _scan_files
    Given src/pactkit/skills/visualize.py
    When reviewing the impact() function body
    Then file_ext = _detect_file_ext(root) is called before _scan_files
    And _scan_files is called with file_ext=file_ext
```
