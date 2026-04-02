# STORY-slim-031: Unified impact test mapping via LANG_PROFILES

| Field | Value |
|-------|-------|
| ID | STORY-slim-031 |
| Status | Done |
| Priority | P0 — Impact 5, Effort 2 |
| Release | 2.3.7 |

## Background

`impact()` hardcodes `test_path = root / 'tests' / 'unit' / f'test_{stem}.py'` — only works for Python projects following a specific convention. `LANG_PROFILES` already defines `test_map_pattern` for each language:
- Python: `tests/unit/test_{module}.py`
- Go: `{package}/{module}_test.go`
- Java: `src/test/java/{package}/{module}Test.java`
- Node: `__tests__/{module}.test.ts`

`impact()` should read this pattern instead of hardcoding, while falling back to the current logic for backward compatibility.

## Requirements

### R1: impact reads test_map_pattern from LANG_PROFILES (MUST)

`impact()` MUST resolve test file paths using `LANG_PROFILES[stack].test_map_pattern` with `{module}` replaced by the source file stem and `{package}` by the relative directory path.

### R2: Fallback to current hardcoded logic (MUST)

If the LANG_PROFILES pattern produces no matches (file doesn't exist), `impact()` MUST fall back to the current `test_{stem}.py` lookup. This ensures existing Python projects see no behavior change even if the pattern resolution differs slightly.

### R3: Stack auto-detection (MUST)

`impact()` MUST auto-detect the stack via `_detect_stack()` (a new helper that returns the stack name string, e.g., "python", "go") or accept it as a parameter. No manual configuration required.

### R4: Inline test_map_pattern data (MUST)

Since `visualize.py` is a standalone script that cannot import from pactkit, the `test_map_pattern` data MUST be inlined as a module-level dict (like `_LANG_FILE_EXT`), with a comment pointing to the canonical source in `LANG_PROFILES`.

### R5: Package path resolution from source file (MUST)

For patterns containing `{package}` (Go, Java), `impact()` MUST derive the package path from the source file's actual path in `func_registry`. The `func_registry` currently stores only `stem` (filename without extension); `impact()` MUST additionally track the source file's relative directory to resolve `{package}`. This MAY be achieved by storing `(stem, relative_dir)` tuples or by building a separate `stem_to_path` index from `all_files`.

## Acceptance Criteria

### AC1: Python impact unchanged (R2, R3)

- **Given** a Python project with `tests/unit/test_config.py`
- **When** running `impact --entry load_config`
- **Then** returns `tests/unit/test_config.py` (same as current behavior)

### AC2: Go test mapping works (R1, R5)

- **Given** a Go project with `internal/config/config.go` and `internal/config/config_test.go`
- **When** running `impact --entry LoadConfig`
- **Then** returns `internal/config/config_test.go`

### AC3: Java test mapping works (R1, R5)

- **Given** a Java project with `src/main/java/com/app/Config.java` and `src/test/java/com/app/ConfigTest.java`
- **When** running `impact --entry loadConfig`
- **Then** returns `src/test/java/com/app/ConfigTest.java`

### AC4: Node test mapping works (R1)

- **Given** a Node project with `src/utils.ts` and `__tests__/utils.test.ts`
- **When** running `impact --entry parseConfig`
- **Then** returns `__tests__/utils.test.ts`

### AC5: Fallback when pattern misses (R2)

- **Given** a Python project where LANG_PROFILES pattern resolves to a non-existent path
- **When** running `impact --entry some_func`
- **Then** falls back to `tests/unit/test_{stem}.py` check

### AC6: _detect_stack returns stack name (R3)

- **Given** a project root with `pyproject.toml`
- **When** calling `_detect_stack(root)`
- **Then** returns `"python"` (string, not the file extension)

### AC7: Inlined test_map_patterns match LANG_PROFILES (R4)

- **Given** the `_TEST_MAP_PATTERNS` dict in `visualize.py`
- **When** compared against `LANG_PROFILES[*].test_map_pattern` in `workflows.py`
- **Then** all 4 entries match exactly

## Design

### Key Constraint

`visualize.py` is a standalone script (cannot import pactkit). All new data MUST be inlined with canonical-source comments, following the established pattern of `_STACK_MARKERS` and `_LANG_FILE_EXT`.

### New Inline Data

```python
# Canonical: src/pactkit/prompts/workflows.py LANG_PROFILES[*].test_map_pattern
_TEST_MAP_PATTERNS = {
    "python": "tests/unit/test_{module}.py",
    "node": "__tests__/{module}.test.ts",
    "go": "{package}/{module}_test.go",
    "java": "src/test/java/{package}/{module}Test.java",
}
```

### New Helper: `_detect_stack(root)`

Refactored from `_detect_file_ext()`. Returns the stack name string (e.g., "python"), not the extension. `_detect_file_ext()` becomes a thin wrapper: `return _LANG_FILE_EXT.get(_detect_stack(root), '.py')`.

Priority order (same as current `_detect_file_ext`):
1. `pactkit.yaml` `stack` field (if not 'auto' and known)
2. Marker-file detection via `_STACK_MARKERS`
3. Default: `"python"`

### New Helper: `_resolve_test_path(root, stem, source_file, stack)`

```
pattern = _TEST_MAP_PATTERNS.get(stack, "tests/unit/test_{module}.py")
module = stem                     # e.g., "config"
package = str(source_file.parent.relative_to(root))  # e.g., "internal/config"
test_path = root / pattern.replace("{module}", module).replace("{package}", package)
return test_path if test_path.exists() else None
```

### Source File Lookup

`func_registry` maps `func_name -> stem`. To get the full source path for `{package}` resolution, build `stem_to_file` index from `all_files`: `{file.stem: file for file in all_files}`. When multiple files share the same stem, prefer the one whose stem matches `func_registry[func_name]`.

### Target Call Chain

```
impact(entry="load_config")
  -> _detect_stack(root) -> "python"
  -> _scan_call_edges() -> func_registry, call_edges
  -> _build_reverse_graph() -> visited functions
  -> for each visited func:
       stem = func_registry[func_name]
       source_file = stem_to_file[stem]
       test_path = _resolve_test_path(root, stem, source_file, stack)
       if test_path: add to results
       else: fallback -> root / 'tests' / 'unit' / f'test_{stem}.py'
```

### Fallback Chain

1. Pattern from `_TEST_MAP_PATTERNS[stack]` with `{module}` and `{package}` resolved
2. Hardcoded `tests/unit/test_{stem}.py` (current behavior, backward compat)
3. Skip (no test file found for this function)

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim031.py` | Tests for `_detect_stack`, `_resolve_test_path`, multi-language `impact()` | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Add `_TEST_MAP_PATTERNS` inline dict | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | Extract `_detect_stack()` from `_detect_file_ext()` | Step 2 | Low |
| 4 | `src/pactkit/skills/visualize.py` | Add `_resolve_test_path()` helper | Step 3 | Medium |
| 5 | `src/pactkit/skills/visualize.py` | Refactor `impact()` to use new helpers + fallback chain | Steps 3, 4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 through SEC-8 | N/A | Only changes test file path resolution logic |

## Out of Scope

- Call graph parsing for non-Python languages (STORY-slim-030 + language adapters)
- test_map_pattern format changes in LANG_PROFILES (existing patterns are sufficient)
