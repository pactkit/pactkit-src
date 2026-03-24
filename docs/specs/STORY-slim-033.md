# STORY-slim-033: Java LanguageAnalyzer adapter

| Field | Value |
|-------|-------|
| ID | STORY-slim-033 |
| Status | Done |
| Priority | P1 — Impact 4, Effort 2 |
| Release | 2.3.7 |

## Background

After STORY-slim-032 establishes the `TreeSitterAnalyzer` base class with `GoAnalyzer`, Java projects still get empty call graphs. `JavaAnalyzer` is the second tree-sitter adapter — it reuses the base class, providing only Java-specific grammar and queries. Effort is reduced from 3 to 2 because the infrastructure (base class, `_select_analyzer`, optional deps pattern) is already in place.

## Requirements

### R1: tree-sitter-java dependency (MUST)

`pyproject.toml` MUST add `tree-sitter-java` to the `multilang` optional dependency group (alongside `tree-sitter` and `tree-sitter-go` from STORY-slim-032).

### R2: JavaAnalyzer subclass (MUST)

`JavaAnalyzer(TreeSitterAnalyzer)` MUST configure:
- Language: `tree_sitter_java.language()`
- Import query: extract `import_declaration` paths
- Function query: extract `method_declaration` and `constructor_declaration` names with enclosing class
- Call query: extract `method_invocation` calls

### R3: Java import extraction (MUST)

`JavaAnalyzer.extract_imports()` MUST extract:
- Regular imports: `import com.app.Config;` → `"com.app.Config"`
- Static imports: `import static com.app.Config.load;` → `"com.app.Config"`
- Wildcard imports: `import com.app.*;` → `"com.app"`

### R4: Java method and call extraction (MUST)

`JavaAnalyzer.extract_functions_and_calls()` MUST extract:
- Instance methods: `public void handleRequest(` → `ClassName.handleRequest`
- Static methods: `public static void main(` → `ClassName.main`
- Constructors: `public Config(` → `Config.Config`
- Method calls: `config.load(` and `Config.staticMethod(`

### R5: Auto-selected for Java projects (MUST)

When `_detect_stack()` returns `"java"`, `_select_analyzer()` MUST return `JavaAnalyzer()`. If `tree-sitter-java` is not installed, MUST fall back to `PythonAnalyzer()` with a warning.

## Acceptance Criteria

### AC1: Java file graph non-empty (R2, R3)

- **Given** a Java project with `pom.xml` and multiple `.java` files with imports
- **When** running `pactkit visualize`
- **Then** `code_graph.mmd` contains import relationship edges

### AC2: Java call graph non-empty (R2, R4)

- **Given** a Java project with methods calling each other
- **When** running `pactkit visualize --mode call`
- **Then** `call_graph.mmd` contains method→method edges

### AC3: Static methods extracted (R4)

- **Given** a Java file with `public static void main(String[] args)` calling `Config.load(`
- **When** extracting functions and calls
- **Then** `ClassName.main` appears with callee `Config.load`

### AC4: Auto-detection works (R5)

- **Given** a project with `pom.xml`
- **When** running `pactkit visualize --mode call`
- **Then** `JavaAnalyzer` is used automatically

### AC5: Graceful degradation (R1, R5)

- **Given** `tree-sitter-java` is NOT installed
- **When** running `pactkit visualize` on a Java project
- **Then** falls back to `PythonAnalyzer` with a warning, no crash

## Design

### tree-sitter Queries for Java

```python
# Java import query
IMPORT_QUERY = '(import_declaration (scoped_identifier) @import)'

# Java method query — captures class context + method name
FUNC_QUERY = '''[
  (method_declaration name: (identifier) @name)
  (constructor_declaration name: (identifier) @name)
]'''

# Java call query
CALL_QUERY = '''[
  (method_invocation name: (identifier) @callee)
  (method_invocation object: (_) @obj name: (identifier) @method)
]'''
```

### JavaAnalyzer Implementation

```python
class JavaAnalyzer(TreeSitterAnalyzer):
    def __init__(self):
        import tree_sitter_java
        super().__init__(
            language=tree_sitter_java.language(),
            import_query=JAVA_IMPORT_QUERY,
            func_query=JAVA_FUNC_QUERY,
            call_query=JAVA_CALL_QUERY,
        )
```

The `__init__` is the only code specific to Java. All parsing, error handling, and result formatting is inherited from `TreeSitterAnalyzer`.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `pyproject.toml` | Add `tree-sitter-java` to `multilang` optional deps | STORY-slim-032 | Low |
| 2 | `tests/unit/test_story_slim033.py` | Tests with sample Java source files | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | Implement `JavaAnalyzer(TreeSitterAnalyzer)` with Java queries | STORY-slim-032 | Low |
| 4 | `src/pactkit/skills/visualize.py` | Register JavaAnalyzer in `_select_analyzer()` | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-8 Dependencies | Low | `tree-sitter-java` is an official tree-sitter grammar package |
| SEC-1 through SEC-7 | N/A | Read-only AST parsing, no new input vectors |

## Out of Scope

- Java annotation processing (e.g., `@Override`, `@Bean`, `@Inject`)
- Inner class / anonymous class call resolution
- Lambda expression call tracking
- Gradle project support beyond `build.gradle` detection (already in `_detect_stack`)
