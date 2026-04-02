# STORY-053: Impact-Based Regression via Call Graph Analysis

| Field | Value |
|-------|-------|
| ID | STORY-053 |
| Status | Draft |
| Priority | P1 |
| Author | System Architect |
| Created | 2026-02-27 |
| Release | 1.4.0 |

## Background

当前的 Regression 决策树条件过于严格，实际上很难触发增量测试，导致几乎每次都跑全量测试：

```
Run incremental tests only if ALL of the following:
- code_graph.mmd exists AND recently updated
- Changed source files ≤ 3
- Has direct test mapping
- NO changed file imported by 3+ modules  ← 常见函数很容易不满足
- NO test infrastructure files changed
- NO version change
```

用户观察：`call_graph.mmd` 已经记录了函数级调用关系，可以利用它做**反向依赖分析**，只测试受影响的功能点。

## Target Call Chain

```
visualize.py
  └── _build_call_graph()      # 现有：正向 BFS (entry → callees)
  └── _build_reverse_callers() # 新增：反向 BFS (entry ← callers)
  └── get_impacted_tests()     # 新增：映射到测试文件

project-done.md / project-act.md
  └── Regression Gate
      └── Impact Analysis (新策略)
```

## Requirements

### R1: Add Reverse Caller Analysis to visualize.py
`visualize.py` MUST support a new `--reverse` flag combined with `--entry`:
```bash
python3 visualize.py visualize --mode call --entry validate_config --reverse
```
- Parse `call_graph.mmd` (or rebuild from source)
- Build reverse adjacency list: `{callee: [callers]}`
- BFS from entry to find all **reverse reachable** functions
- Output: list of impacted functions

### R2: Add Test Mapping Function
`visualize.py` SHOULD provide a `--test-map` flag to output impacted test files:
```bash
python3 visualize.py impact --entry validate_config
```
- Find all reverse callers (R1)
- Map each caller to its test file using `test_map_pattern`:
  - `src/pactkit/config.py:validate_config` → `tests/unit/test_config.py`
  - `src/pactkit/deployer.py:_deploy_classic` → `tests/unit/test_deployer.py`
- Output: space-separated list of test file paths (for pytest)

### R3: Update Regression Decision Tree
`project-done.md` Phase 2.5 Decision Tree SHOULD be simplified:
- **New Rule**: If `call_graph.mmd` exists AND `impact` command returns < 50 test files:
  - Run `pytest {impacted_test_files}` instead of full suite
  - Log: `"Regression: IMPACT-BASED — {N} test files based on call graph analysis"`
- **Fallback**: If `impact` fails or returns ≥ 50 files: run full regression

### R4: Configuration Option
`pactkit.yaml` MAY support a `regression` config section:
```yaml
regression:
  strategy: impact  # or 'full' (default: impact)
  max_impact_tests: 50  # fallback threshold
```

### R5: Release Gate (Full Regression Override)
Impact-based regression MUST be disabled when releasing:
- **Detection**: If `git diff HEAD~1 pyproject.toml | grep version` shows version change
- **Action**: Force full regression, ignore impact analysis
- **Log**: `"Regression: FULL — version bump detected, release requires full test suite"`
- **Rationale**: Release is a safety checkpoint; cannot risk missing regressions

## Acceptance Criteria

### AC1: Reverse Caller Works
**Given** `call_graph.mmd` contains `deploy --> _deploy_classic --> validate_config`
**When** `visualize.py visualize --mode call --entry validate_config --reverse`
**Then** output MUST include `_deploy_classic` and `deploy`

### AC2: Test Mapping Works
**Given** changed function `validate_config` in `config.py`
**When** `visualize.py impact --entry validate_config`
**Then** output MUST include `tests/unit/test_config.py`

### AC3: Regression Uses Impact Analysis
**Given** a Story modifies `config.py:validate_config`
**When** `/project-done` runs Regression Gate
**Then** it SHOULD run only impacted tests (not full suite) if < 50 files

### AC4: Fallback to Full Regression
**Given** impact analysis returns ≥ 50 test files (or fails)
**When** `/project-done` runs Regression Gate
**Then** it MUST fallback to full regression with log message

### AC5: Release Forces Full Regression
**Given** `pyproject.toml` version was changed (e.g., 1.4.0 → 1.4.1)
**When** `/project-done` runs Regression Gate
**Then** it MUST run full regression regardless of impact analysis result
**And** log: `"Regression: FULL — version bump detected, release requires full test suite"`

## Non-Goals

- Cross-file import analysis (already handled by `code_graph.mmd`)
- Dynamic call analysis (runtime reflection, eval)
- Test prioritization/ordering within impacted set

## Algorithm

```
Input: changed_functions = [validate_config, load_config]

1. Parse call_graph.mmd → edges = [(caller, callee), ...]
2. Build reverse_map = {callee: [callers]}
3. For each changed_func:
     impacted = BFS(reverse_map, start=changed_func)
4. Map impacted → test files using test_map_pattern
5. Dedupe and return test file list
```

## Files to Modify

| File | Change |
|------|--------|
| `src/pactkit/skills/visualize.py` | Add `--reverse` flag, `impact` subcommand |
| `~/.claude/commands/project-done.md` | Update Regression Gate to use impact analysis |
| `~/.claude/commands/project-act.md` | Update Regression Check to use impact analysis |
| `src/pactkit/prompts/commands.py` | Sync templates |
| `src/pactkit/config.py` | Add `regression` config section (optional) |
| `tests/unit/test_visualize_modes.py` | Add tests for reverse caller and impact |
