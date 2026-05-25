# STORY-slim-120: Improve Call Graph Coverage: Test Files, Scripts, and Locality-Based Callee Resolution

| Field | Value |
|-------|-------|
| ID | STORY-slim-120 |
| Status | Done |
| Priority | P1 |
| Release | 2.14.0 |

## Background

After STORY-slim-119 improved Python call graph coverage (R1: non-self attribute calls, R2: function references, R3: nested functions), pactkit produces 3,561 call edges on pactsearch (src/ only) vs codegraph's 2,327 src-only edges — pactkit now leads by 53% on the fair apples-to-apples comparison.

The remaining apparent gap (codegraph total: 6,571) is entirely explained by scan scope: codegraph indexes `tests/` (3,793 edges) and `scripts/`+`alembic/` (271 edges) which pactkit excludes via `SCAN_EXCLUDES`. Scanning test files is strategically valuable because `pactkit test-map` and `pactkit regression` use the call graph to map source changes to test files — more test call edges means higher-precision test selection.

Two additional improvements are identified:
1. **Scan tests/ directory** (high value): Adds ~3,793 edges on pactsearch. Directly improves `pactkit test-map` accuracy by making test→source call relationships visible.
2. **Scan scripts/ and alembic/ directories** (medium value): Adds ~271 edges. Makes utility scripts and DB migrations visible in the call graph.
3. **Locality-based callee resolution** (quality improvement): When `_resolve_callee` finds multiple candidates via suffix match, it currently picks the first alphabetically. Using caller file path proximity to prefer same-module or same-package candidates reduces false edges from name collisions.

## Requirements

### R1: Scan Test Files in Call Graph Mode (MUST)

`pactkit visualize --mode call` MUST scan the `tests/` directory (and any configured test directories) when building the call graph. Test files MUST be scanned with the same `PythonAnalyzer.extract_functions_and_calls` logic as source files. The `tests` entry MUST be removed from `SCAN_EXCLUDES` for call graph mode only — file dependency graph (`--mode file`) and class graph (`--mode class`) MUST remain unchanged (tests excluded there).

**Implementation note**: `SCAN_EXCLUDES` is currently a module-level constant shared across all graph modes. The fix is to pass an `extra_excludes` parameter to `_scan_files` / `_build_call_graph` that adds `tests` back for file/class modes but not for call mode.

### R2: Scan scripts/ and alembic/ Directories (SHOULD)

`pactkit visualize --mode call` SHOULD scan `scripts/` and `alembic/` directories (and similar utility directories at project root level) in call graph mode. These directories are currently excluded via `SCAN_EXCLUDES` implicitly (only source dirs are scanned). Add an opt-in mechanism: if a `scripts/` or `alembic/` directory exists at project root and contains `.py` files, include it in the call graph scan.

**Noise control**: Only scan directories at project root level (depth 1), not recursively from arbitrary paths. Do NOT add `scripts` or `alembic` to `SCAN_EXCLUDES`.

### R3: Locality-Based Callee Resolution (SHOULD)

`_resolve_callee` MUST prefer candidates that share the same file path as the caller when multiple suffix matches exist. Current behavior: `suffix_index[callee]` returns a list and `candidates[0]` is used (arbitrary ordering). New behavior: if `len(candidates) > 1`, sort by file-path locality — candidates from the same file first, then same package, then alphabetical fallback.

**Signature change**: `_resolve_callee(callee, all_func_names, suffix_index=None, caller_file=None)` — `caller_file` is the `rel` value from `func_registry[caller]`.

### R4: No Regression on Existing Tests (MUST NOT)

The changes MUST NOT break any existing test. The call graph format (Mermaid `graph TD`) and node ID scheme MUST remain unchanged. The `--mode file` and `--mode class` graph outputs MUST be identical before and after (tests/ still excluded in those modes).

## Acceptance Criteria

### AC1: Test File Calls Appear in Call Graph (R1)

- **Given** a project with `tests/unit/test_foo.py` containing `def test_something(): foo_func()`
- **When** `pactkit visualize --mode call` is run
- **Then** `test_something --> foo_func` appears as an edge in `call_graph.mmd`

### AC2: File and Class Graphs Unchanged (R1)

- **Given** the same project
- **When** `pactkit visualize --mode file` or `--mode class` is run
- **Then** `tests/` content does NOT appear in the output (behavior identical to pre-change)

### AC3: Scripts Directory Scanned (R2)

- **Given** a project with a `scripts/` directory containing `.py` files with function calls
- **When** `pactkit visualize --mode call` is run
- **Then** functions from `scripts/*.py` appear as nodes and their call edges appear in `call_graph.mmd`

### AC4: Locality Preference Reduces False Edges (R3)

- **Given** two functions named `process` in different modules, and a caller in the same module as one of them
- **When** `_resolve_callee('process', all_func_names, suffix_index, caller_file='module_a')` is called
- **Then** the candidate from `module_a` is returned (not the one from `module_b`)

### AC5: Existing Tests Pass (R4)

- **Given** the full test suite in `tests/unit/`
- **When** `pytest tests/unit/ -q` is run after implementing R1–R3
- **Then** all 3916+ tests pass with 0 failures

### AC6: Edge Count Increase on pactsearch (R1+R2)

- **Given** `pactkit visualize --mode call` run on pactsearch before and after this change
- **When** edge counts are compared
- **Then** `grep " --> " call_graph.mmd | wc -l` shows an increase of at least 50% from the STORY-slim-119 baseline (3,561 → expected ≥5,000)

## Target Call Chain

```
pactkit visualize --mode call
  └── _build_call_graph(root, all_files, ...)           visualize.py:~2115
        └── _scan_files(root, scan_excludes, ...)       visualize.py:1886  ← R1/R2: pass mode-specific excludes
              └── PythonAnalyzer.extract_functions_and_calls  python_analyzer.py:36
        └── _build_call_graph (loop over call_edges)    visualize.py:~2240
              └── _resolve_callee(callee, ..., caller_file)   visualize.py:2297  ← R3: add caller_file param
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim120.py` | Write TDD tests for AC1–AC4 before implementing | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | R1: In `_build_call_graph`, compute `call_mode_excludes = SCAN_EXCLUDES - {'tests'}` and pass to `_scan_files`. Keep existing excludes for file/class modes. | None | Low |
| 3 | `src/pactkit/skills/visualize.py` | R2: In `_build_call_graph`, after computing `call_mode_excludes`, detect root-level `scripts/` and `alembic/` dirs containing `.py` files and include them in the scan. | Step 2 | Low |
| 4 | `src/pactkit/skills/visualize.py` | R3: Add `caller_file=None` param to `_resolve_callee`. If `len(candidates) > 1`, sort by: same file first, then same package prefix, then alphabetical. Update all 4 call sites to pass `caller_file`. | None | Medium |
| 5 | Run `pactkit update` | Redeploy visualize.py to `~/.claude/skills/pactkit-visualize/scripts/` | Steps 2–4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Input Validation) | Yes | `_scan_files` processes file paths from user project directories — path traversal already guarded by `MAX_FILE_BYTES` check and `ast.parse()` exception handling. No change needed. |
| SEC-2 (Auth) | N/A | no auth changes |
| SEC-3 (SQL Injection) | N/A | no SQL |
| SEC-4 (Path Traversal) | N/A | new directory scanning (`tests/`, `scripts/`) uses same `_scan_files` guard which resolves paths relative to `root` — parent traversal already blocked |
| SEC-5 (Secret Leakage) | N/A | no credentials |
| SEC-6 (Dependency) | N/A | no new dependencies |
| SEC-7 (Error Handling) | Yes | `_resolve_callee` locality sort must handle `caller_file=None` gracefully; `_scan_files` additions must use same `try/except (SyntaxError, UnicodeDecodeError, ValueError)` pattern |
| SEC-8 (XSS) | N/A | no web UI |

## Out of Scope

- Go/TypeScript/Java analyzer improvements (separate story if needed)
- Scanning arbitrary user-specified directories via CLI flag (too broad, out of scope)
- Changing `--mode file` or `--mode class` behavior (tests/ stays excluded there)
- Full type-inference for callee resolution (requires type system, out of scope)
- codegraph `references` edge kind (import/usage tracking) — pactkit tracks this separately via file dependency graph
