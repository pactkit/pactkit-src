# STORY-slim-029: Multi-language file discovery via LANG_PROFILES

| Field | Value |
|-------|-------|
| ID | STORY-slim-029 |
| Status | Done |
| Priority | P0 — Impact 5, Effort 2 |
| Release | 2.3.7 |

## Background

`_scan_files()` hardcodes `root.rglob('*.py')` — only Python files are discovered. `LANG_PROFILES` already defines `file_ext` for Python (`.py`), Go (`.go`), Java (`.java`), and Node (`.ts`), but `visualize.py` ignores it entirely. A Go project running `pactkit visualize` gets an empty graph because no `.go` files are found.

## Requirements

### R1: _scan_files reads file_ext from LANG_PROFILES (MUST)

`_scan_files()` MUST use `LANG_PROFILES[stack].file_ext` to determine the glob pattern (e.g., `*.go` for Go). The stack MUST be auto-detected via `detect_stack()` or read from `pactkit.yaml`.

### R2: Fallback to *.py (MUST)

If `detect_stack()` returns an unknown stack or `LANG_PROFILES` has no entry, `_scan_files()` MUST fall back to `*.py` (current behavior). This ensures zero regression for projects where detection fails.

### R3: Full rglob scan preserved (MUST)

`_scan_files()` MUST NOT restrict scanning to `source_dirs`. It MUST continue to use `root.rglob()` over the entire project tree (minus excludes). `source_dirs` is informational metadata for test mapping, not a scan filter.

## Acceptance Criteria

### AC1: Python project unchanged (R2)

- **Given** a project with `pyproject.toml`
- **When** running `pactkit visualize`
- **Then** scans `*.py` files, output identical to current behavior

### AC2: Go project discovers .go files (R1)

- **Given** a project with `go.mod`
- **When** running `pactkit visualize`
- **Then** `_scan_files()` finds `*.go` files

### AC3: Java project discovers .java files (R1)

- **Given** a project with `pom.xml`
- **When** running `pactkit visualize`
- **Then** `_scan_files()` finds `*.java` files

### AC4: Unknown stack falls back to *.py (R2)

- **Given** a project with no recognized marker files
- **When** running `pactkit visualize`
- **Then** scans `*.py` files (default)

### AC5: Full tree scanned, not restricted to source_dirs (R3)

- **Given** a Go project with .go files in both `cmd/` and `internal/`
- **When** running `pactkit visualize`
- **Then** files from both directories appear in the graph

## Target Call Chain

```
pactkit visualize (CLI)
  → lazy_visualize.py → subprocess → visualize.py visualize
  → visualize(target='.', ...)
    → _detect_file_ext(root)                   # NEW — inline stack detection
      → reads pactkit.yaml stack field (if not "auto")
      → else: marker-file detection (go.mod→go, pom.xml→java, ...)
      → maps stack → file_ext via _LANG_FILE_EXT dict
      → returns ".go" (or ".py" default)
    → _scan_files(root, scan_excludes=..., file_ext=".go")
      → root.rglob("*.go")                    # CHANGED from hardcoded "*.py"
```

## Design Decision: Inline Detection (Option A)

`visualize.py` is a standalone script (cannot import from pactkit). Two options were evaluated:

- **Option A (chosen)**: Inline lightweight stack detection and file_ext mapping directly in `visualize.py`. Consistent with STORY-slim-028 pattern (`_load_scan_excludes` inlines yaml reading).
- **Option B (rejected)**: Pass `--file-ext` from `lazy_visualize.py`. Would work but splits the logic across two files, and direct invocation by AI agents would bypass it.

The inline data to replicate is minimal:
- 7 marker-file entries from `cleaners.py _STACK_MARKERS`
- 4 ext entries from `workflows.py LANG_PROFILES[*].file_ext`

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim029.py` | RED: Tests for `_detect_file_ext()` (4 stacks + unknown fallback) and `_scan_files()` with `file_ext` param | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Add `_STACK_MARKERS` list and `_LANG_FILE_EXT` dict (inline, with canonical-source comments) near line 26 | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | Add `_detect_file_ext(root)` function: reads `pactkit.yaml` `stack` field, falls back to marker-file detection, maps to ext via `_LANG_FILE_EXT`, defaults to `.py` | Step 2 | Low |
| 4 | `src/pactkit/skills/visualize.py` | Modify `_scan_files()` signature: add `file_ext='.py'` param; change `root.rglob('*.py')` to `root.rglob(f'*{file_ext}')` at line 68 | None | Low |
| 5 | `src/pactkit/skills/visualize.py` | Modify `visualize()` (line 470): call `file_ext = _detect_file_ext(root)` and pass to `_scan_files(root, scan_excludes=scan_excludes, file_ext=file_ext)` | Steps 3-4 | Low |
| 6 | `src/pactkit/skills/visualize.py` | Modify `impact()` (line 445): same pattern as Step 5 | Steps 3-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 through SEC-8 | N/A | Only changes file glob pattern from hardcoded to config-driven |

## Out of Scope

- Call graph parsing for non-Python languages (STORY-slim-030 adapter interface)
- source_dirs as scan filter (explicitly NOT doing this — R3)
