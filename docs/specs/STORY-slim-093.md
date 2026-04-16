# STORY-slim-093: Audit: Multi-Signal Hotspots + Suggested Tasks Generation

| Field | Value |
|-------|-------|
| ID | STORY-slim-093 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.0 |

## Background

STORY-slim-092 将 audit findings 聚合为文件级 hotspots，但仍只有 3 个信号维度（complexity_avg, fan_in, blast_pct）。对代码质量好的项目全是 "Monitor" — 不够有用。

同时，audit 发现的问题没有进入 PDCA 闭环 — 用户需要手动决定做什么、手动创建 Spec、手动跑命令。

本 Story 做两件事：
1. **信号维度扩展** — 增加测试覆盖、文档覆盖、代码异味、架构层违规、依赖健康 5 个新维度
2. **Suggested Tasks 生成** — audit 自动 scaffold BUG/HOTFIX Spec，写入 `harness_audit.json` 的 `suggested_tasks` 字段。前端读 JSON 展示给用户，用户点 Accept → Claude Code headless 执行 command

完整闭环：`audit → JSON → 前端展示 → 用户确认 → headless PDCA 执行`

## Requirements

### R1: Test Coverage Signal (MUST)

Per source file, check if a corresponding test file exists:
- Use `_resolve_test_path(root, stem, source_file, stack)` from visualize.py
- Fallback: glob `tests/**/test_{stem}.*`
- Output field: `has_test: bool`

### R2: Docstring Coverage Signal (MUST)

Per Python source file, count percentage of functions with docstrings:
- Use `ast.get_docstring(func_node)` during AST traversal
- For tree-sitter languages: count functions with leading comment block (best-effort)
- Output field: `docstring_pct: int` (0-100)

### R3: Code Smell Signal (MUST)

Per file, detect:
- **Long functions**: functions >50 source lines (AST end_lineno - lineno)
- **Deep nesting**: functions with >4 nested control flow levels (count nested If/For/While/With)
- Output fields: `long_funcs: int`, `deep_nesting: int`

### R4: Layer Violation Signal (MUST)

Per file, count how many layer violations this file participates in as importer:
- Reuse `_classify_file()` + file-level edges already built by `_compute_hotspots()`
- Output field: `layer_violations: int`

### R5: Dependency Health (SHOULD)

Project-level (not per-file) vulnerability check:
- Python: `pip audit --format json` (if installed)
- Node: `npm audit --json` (if `package-lock.json` exists)
- Output: top-level `dependency_health` field in audit JSON: `{vulns: int, critical: int, details: [{name, version, severity}]}`
- Graceful: tool not installed → `{vulns: -1, error: "pip-audit not installed"}`
- Timeout: 10s max to avoid blocking audit

### R6: Updated Hotspot Score Formula (MUST)

Weighted multi-dimensional score replacing simple `complexity × blast × fan_in`:
```
score = (
    complexity_avg * 0.25
    + (1 - docstring_pct/100) * 10 * 0.15
    + (long_funcs + deep_nesting) * 3 * 0.15
    + layer_violations * 5 * 0.10
    + (0 if has_test else 10) * 0.20
    + blast_pct/100 * max(fan_in, 1) * 10 * 0.15
)
```
Normalize to 0-100. Weights defined as module-level constants for tunability.

### R7: Updated Action Suggestions (MUST)

`_suggest_action()` priority order (combine top 2):
1. `has_test=false` → "Add tests"
2. `complexity_avg > 30` → "Split"
3. `long_funcs > 0 or deep_nesting > 0` → "Refactor"
4. `layer_violations > 0` → "Fix layers"
5. `docstring_pct < 30` → "Document"
6. `fan_in >= 5` → "Stabilize"
7. `blast_pct > 50` → "Isolate"

### R8: Suggested Tasks Generation (MUST)

After computing hotspots, generate `suggested_tasks` array:
- For each hotspot with `score > 0` OR `has_test=false`:
  - Determine type: `score >= 15` or `layer_violations > 0` → BUG (needs Spec + TDD); otherwise → HOTFIX
  - Auto-scaffold Spec file using `scaffold.py create_spec` with generated ID (BUG-{dev}-{NNN} or HOTFIX-{dev}-{NNN})
  - Fill Spec Background with hotspot signals, Requirements with specific fix actions
  - Each task entry contains: `type`, `severity`, `title`, `file`, `signals` (dict of relevant signal values), `spec` (path to scaffolded spec), `command` (executable PDCA command)
- **Done-completed filter**: If a suggested task's Spec file already exists AND its status is `Done`, exclude it from `suggested_tasks`. This ensures fixed issues don't reappear.
- **Idempotent Spec generation**: If a Spec file for the same file+type already exists and is NOT `Done`, reuse it instead of creating a new one. Avoid duplicate Specs for the same hotspot.

### R9: Command Format (MUST)

Every suggested task MUST have a `command` field usable by headless Claude Code:
- BUG: `"/project-act BUG-{dev}-{NNN} {description}"`
- HOTFIX: `"/project-hotfix HOTFIX-{dev}-{NNN} {description}"`
- Description derived from the dominant signal in the hotspot

### R10: Updated JSON Schema (MUST)

`harness_audit.json` gains:
- Per-hotspot: new fields `has_test`, `docstring_pct`, `long_funcs`, `deep_nesting`, `layer_violations`
- Top-level: `dependency_health` object (R5)
- Top-level: `suggested_tasks` array (R8)
- All existing fields preserved (backward compatible)

### R11: Full Re-Audit on Done (MUST)

`pactkit audit --append` (called by Done Phase 3.8) MUST run the complete audit including hotspot recalculation and suggested_tasks refresh — not just H1-H7 layer scoring. This ensures:
- Score reflects actual project state after each fix
- Fixed hotspots drop out of `suggested_tasks` (via Done-completed filter in R8)
- New hotspots from code changes are detected

Performance budget: full re-audit SHOULD complete within 10s for projects with ≤500 source files.

## Acceptance Criteria

### AC1: Test Coverage Detection (R1)

- **Given** a file `src/foo.py` with no corresponding test
- **When** `pactkit audit`
- **Then** hotspot has `has_test: false`; a file `src/bar.py` with `tests/unit/test_bar.py` has `has_test: true`

### AC2: Docstring Coverage (R2)

- **Given** a file with 4 functions, 1 has a docstring
- **When** `pactkit audit`
- **Then** hotspot has `docstring_pct: 25`

### AC3: Code Smell Detection (R3)

- **Given** a file with a 60-line function and a 5-level nested function
- **When** `pactkit audit`
- **Then** hotspot has `long_funcs >= 1` and `deep_nesting >= 1`

### AC4: Layer Violation Count (R4)

- **Given** a file in `utils/` importing from `services/`
- **When** `pactkit audit`
- **Then** hotspot has `layer_violations >= 1`

### AC5: Dependency Health (R5)

- **Given** a Python project
- **When** `pactkit audit`
- **Then** audit JSON has `dependency_health` field with `vulns` count (or error if tool not installed)

### AC6: Weighted Score (R6)

- **Given** file A (no test, low docstring, high complexity) and file B (has test, good docstring, low complexity)
- **When** `pactkit audit`
- **Then** file A has higher hotspot score than file B

### AC7: Action Priority (R7)

- **Given** a file with `has_test=false` and `complexity_avg=35`
- **When** `pactkit audit`
- **Then** action starts with "Add tests" (priority 1), not "Split"

### AC8: Suggested Tasks Generated (R8, R9)

- **Given** a project with hotspots having `score > 0`
- **When** `pactkit audit`
- **Then** `harness_audit.json` contains `suggested_tasks` array; each entry has `type`, `severity`, `title`, `file`, `signals`, `spec`, `command`

### AC9: Spec Auto-Scaffolded (R8)

- **Given** a hotspot that triggers a BUG task
- **When** `pactkit audit`
- **Then** a Spec file `docs/specs/BUG-{dev}-{NNN}.md` exists with Background filled from hotspot data

### AC10: Command Executable (R9)

- **Given** a suggested task with command `"/project-act BUG-slim-094 Refactor config.py"`
- **When** the command is passed to Claude Code headless
- **Then** Act finds the Spec, reads it, and proceeds with implementation

### AC11: Backward Compatible JSON (R10)

- **Given** existing consumers of `harness_audit.json`
- **When** new fields added
- **Then** old fields (score, complexity_avg, blast_pct, fan_in, function_count, action) still present

### AC12: Done-Completed Filter (R8, R11)

- **Given** a previous audit generated BUG-slim-094 for config.py; user fixed it via /project-act + /project-done (Spec status=Done)
- **When** `pactkit audit` runs again (via Done --append or manual)
- **Then** BUG-slim-094 is NOT in `suggested_tasks`; hotspot score for config.py reflects improved state

### AC13: Re-Audit Updates Score (R11)

- **Given** harness_audit.json shows score=52 before a fix
- **When** user fixes a hotspot file and `/project-done` triggers `pactkit audit --append`
- **Then** harness_audit.json score changes to reflect the fix (may increase or stay same)

### AC14: Idempotent Spec Generation (R8)

- **Given** a previous audit already created BUG-slim-094.md (status=Draft, not yet acted on)
- **When** `pactkit audit` runs again
- **Then** the same BUG-slim-094.md is reused in suggested_tasks; no duplicate BUG-slim-095.md is created for the same file

## Target Call Chain

```
audit(root)
  ├── _check_h1..h7(root)                               → EXISTING
  ├── _compute_score(layers)                             → EXISTING
  ├── _compute_hotspots(root)                            → MODIFIED
  │     ├── complexity per file                          → EXISTING
  │     ├── fan_in from code_graph.mmd                   → EXISTING
  │     ├── blast_pct                                    → EXISTING
  │     ├── _check_test_coverage(root, file, stack)      → NEW (R1)
  │     │     └── _resolve_test_path()                   → REUSE (visualize.py)
  │     ├── _check_docstring_coverage(file)              → NEW (R2)
  │     │     └── ast.get_docstring() per function       → stdlib
  │     ├── _check_code_smells(file)                     → NEW (R3)
  │     │     └── AST line count + nesting depth
  │     ├── _count_layer_violations(file, edges, config) → NEW (R4)
  │     │     └── _classify_file()                       → REUSE (visualize.py)
  │     └── _weighted_score(hotspot)                     → NEW (R6)
  ├── _check_dependency_health(root)                     → NEW (R5)
  │     └── subprocess: pip audit / npm audit
  ├── _generate_suggested_tasks(root, hotspots, dev)     → NEW (R8)
  │     ├── _determine_task_type(hotspot)                → NEW
  │     ├── id_generator.next_story_id()                 → REUSE
  │     └── scaffold.create_spec()                       → REUSE
  └── _write_audit_json(result)                          → MODIFIED (add suggested_tasks + dependency_health)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/audit.py` | Add `_check_test_coverage()` — per file test existence via `_resolve_test_path` | None | Low |
| 2 | `src/pactkit/audit.py` | Add `_check_docstring_coverage()` — AST docstring counting per file | None | Low |
| 3 | `src/pactkit/audit.py` | Add `_check_code_smells()` — long functions (>50 lines) + deep nesting (>4 levels) | None | Low |
| 4 | `src/pactkit/audit.py` | Add `_count_layer_violations()` — per-file violation count from edges + layer config | None | Low |
| 5 | `src/pactkit/audit.py` | Add `_check_dependency_health()` — pip audit / npm audit subprocess with timeout | None | Medium |
| 6 | `src/pactkit/audit.py` | Update `_compute_hotspots()` — integrate all 5 new signals into hotspot dict | Steps 1-4 | Low |
| 7 | `src/pactkit/audit.py` | Add `_weighted_score()` — new formula replacing simple multiplication | Step 6 | Low |
| 8 | `src/pactkit/audit.py` | Update `_suggest_action()` — new priority order with 7 signal types | Step 6 | Low |
| 9 | `src/pactkit/audit.py` | Add `_generate_suggested_tasks()` — scaffold Specs + build task entries | Steps 6-8 | Medium |
| 10 | `src/pactkit/audit.py` | Update `audit()` + `_write_audit_json()` — integrate tasks + dep health | Steps 5, 9 | Low |
| 11 | `tests/unit/test_audit.py` | Add tests for all new signals, weighted score, task generation, spec scaffolding | Steps 1-10 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code — subprocess calls (pip audit/npm audit) need input sanitization |
| SEC-2 | No | No new user-facing input params |
| SEC-3 | No | No database |
| SEC-4 | No | No HTML output |
| SEC-5 | No | No auth |
| SEC-6 | No | No API |
| SEC-7 | Yes | Error handling — missing pip-audit, subprocess timeout, malformed AST |
| SEC-8 | No | No new pip dependencies (pip-audit is optional, not required) |

## Out of Scope

- 修改现有 PDCA skill（Plan/Act/Check/Done 等 playbook 不改）
- 前端 UI（本 Story 只负责写 JSON，前端另做）
- 自动执行 suggested tasks（只生成、不执行）
- pip-audit / npm audit 作为硬依赖（缺失时 graceful degradation）
- Tree-sitter 语言的精确 docstring 检测（best-effort 用注释块近似）
