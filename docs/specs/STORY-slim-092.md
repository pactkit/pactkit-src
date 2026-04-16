# STORY-slim-092: Audit Findings: File-Level Hotspot Aggregation

| Field | Value |
|-------|-------|
| ID | STORY-slim-092 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.0 |

## Background

STORY-slim-091 实现了 `pactkit audit`，但 findings 输出存在两个问题：

1. **数据倾泻** — 每个高复杂度 function 独立一条 finding，PactKit 自身就有 141 条。用户拿到这个列表无法行动（"先改哪个？"）。
2. **JSON 文件膨胀** — `harness_audit.json` 达到 1006 行，包含完整 findings + insights 明细。committed 文件应该精简。

**解决方案**：从 per-function 原始数据聚合到**文件级热点排序**。

核心公式：
```
hotspot_score = complexity_avg × blast_radius_pct × fan_in_count
```

每个文件一行，包含多维度信号合成的综合风险评分 + 可操作建议（Split / Extract / Reduce）。141 条 → ~10 条 top hotspots。

**同时精简 `harness_audit.json`**：
- committed 文件只存 scorecard（layers level/name）+ top 10 hotspots 摘要
- findings/insights 完整明细不落盘，仅在 stdout 或 `--verbose` 时展示
- 文件从 1006 行降至 ~50 行

## Requirements

### R1: File-Level Hotspot Aggregation (MUST)

Replace per-function findings with file-level hotspots. For each source file, compute:
- `complexity_avg`: 该文件所有函数的平均 cyclomatic complexity
- `blast_pct`: blast radius 占项目总文件数的百分比 (0-100)
- `fan_in`: 被其他文件 import 的次数
- `hotspot_score`: `complexity_avg × (blast_pct / 100) × max(fan_in, 1)`，归一化到 0-100

Output top 10 hotspots sorted by `hotspot_score` descending.

### R2: Actionable Suggestion per Hotspot (MUST)

Each hotspot MUST include a human-readable `action` string based on the dominant risk signal:
- `complexity_avg > 30` → "Split: extract high-complexity functions into sub-modules"
- `fan_in >= 5` → "Stabilize: changes to this file affect {fan_in} dependents"
- `blast_pct > 50` → "Isolate: blast radius covers {blast_pct}% of project"
- `function_count > 15` → "Decompose: {function_count} functions suggest god object"
- Multiple signals → combine the top 2 most severe

### R3: Slim harness_audit.json (MUST)

Reduce `harness_audit.json` to scorecard + hotspot summary only:
```json
{
  "timestamp": "...",
  "commit": "...",
  "score": 52,
  "ready": true,
  "weakest": null,
  "layers": {
    "H1": {"level": 1, "name": "Basic"},
    ...
  },
  "hotspots": [
    {"file": "visualize.py", "score": 85, "complexity_avg": 52, "blast_pct": 89, "fan_in": 7, "action": "Split + Stabilize"},
    ...
  ]
}
```
- `layers` 只含 `level` 和 `name`，不含 `checks` 明细
- `hotspots` 最多 10 条
- 不含 `findings` 和 `insights` 字段
- 目标：文件 ≤ 50 行

### R4: Verbose Mode for Full Details (MUST)

`pactkit audit --verbose` 输出完整明细（与 STORY-slim-091 当前行为一致）：
- 所有 per-function complexity 条目
- 完整 layer violation 列表
- 完整 circular deps / god objects / fan-in 列表
- 仅在 stdout 展示，不写入 `harness_audit.json`

默认 `pactkit audit`（无 `--verbose`）只输出 scorecard + top 10 hotspots。

### R5: Backward Compatibility for --json (MUST)

`pactkit audit --json` 输出与 `harness_audit.json` 相同的精简格式（scorecard + hotspots）。
`pactkit audit --json --verbose` 输出包含完整 findings + insights 的全量 JSON（供 `pactkit-report --overlay` 或外部工具消费）。

## Acceptance Criteria

### AC1: Hotspot Aggregation (R1)

- **Given** a project with 50 source files, some having high complexity and high fan-in
- **When** `pactkit audit`
- **Then** output shows ≤10 hotspots, each with file name, score, complexity_avg, blast_pct, fan_in

### AC2: Actionable Suggestions (R2)

- **Given** a file with complexity_avg=52 and fan_in=7
- **When** `pactkit audit`
- **Then** that file's hotspot includes action containing "Split" and "Stabilize"

### AC3: Slim JSON File (R3)

- **Given** a successful audit run
- **When** `harness_audit.json` is written
- **Then** the file has ≤ 50 lines; contains `layers` with only `level`/`name`; contains `hotspots` array with ≤ 10 entries; does NOT contain `findings` or `insights` keys

### AC4: Verbose Full Details (R4)

- **Given** a project with layer violations and high-complexity functions
- **When** `pactkit audit --verbose`
- **Then** stdout shows per-function complexity details, layer violations list, circular deps, god objects — all the detail from STORY-slim-091

### AC5: Default Is Concise (R1)

- **Given** a project that previously generated 141 findings
- **When** `pactkit audit` (no flags)
- **Then** stdout shows ≤ 10 hotspot lines + scorecard, not 141 per-function lines

### AC6: JSON Verbose Mode (R5)

- **Given** `pactkit audit --json --verbose`
- **When** output is captured
- **Then** JSON contains `findings` array and `insights` object (full detail)

### AC7: JSON Default Is Slim (R5)

- **Given** `pactkit audit --json` (no --verbose)
- **When** output is captured
- **Then** JSON matches `harness_audit.json` format — scorecard + hotspots only, no findings/insights

## Target Call Chain

```
audit(root, verbose=False)                        → MODIFIED
  ├── _check_h1..h7(root)                         → EXISTING (unchanged)
  ├── _compute_score(layers)                      → EXISTING (unchanged)
  ├── _compute_hotspots(root)                     → NEW (replaces _collect_findings + _collect_insights)
  │     ├── complexity() per file → avg           → REUSE (visualize.py)
  │     ├── blast_radius() per file → pct         → REUSE (visualize.py)
  │     ├── fan-in from code_graph.mmd            → REUSE (existing _collect_insights logic)
  │     ├── function_count per file               → from complexity data
  │     └── _suggest_action(hotspot) → string     → NEW
  ├── _write_audit_json(slim_result)              → MODIFIED (write scorecard + hotspots only)
  │
  ├── if verbose:
  │     ├── _collect_findings(root)               → EXISTING (moved to verbose-only)
  │     └── _collect_insights(root)               → EXISTING (moved to verbose-only)
  └── format output (concise or verbose)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/audit.py` | Add `_compute_hotspots(root)` — per-file aggregation of complexity_avg, blast_pct, fan_in, function_count → hotspot_score | None | Low |
| 2 | `src/pactkit/audit.py` | Add `_suggest_action(hotspot)` — generate actionable string from dominant signals | Step 1 | Low |
| 3 | `src/pactkit/audit.py` | Modify `_write_audit_json()` — slim output: scorecard + layers (level/name only) + hotspots top 10 | Steps 1-2 | Low |
| 4 | `src/pactkit/audit.py` | Modify `audit()` — add `verbose` param; default concise, verbose shows full findings/insights | Step 3 | Low |
| 5 | `src/pactkit/cli.py` | Add `--verbose` flag to audit subcommand | Step 4 | Low |
| 6 | `tests/unit/test_audit.py` | Update tests: hotspot aggregation, slim JSON, verbose mode, action suggestions | Steps 1-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | Modifying existing module, no new file types |
| SEC-2 | Yes | New `--verbose` CLI flag — validate input |
| SEC-3 | No | No database |
| SEC-4 | No | No HTML output |
| SEC-5 | No | No auth |
| SEC-6 | No | No API |
| SEC-7 | Yes | Error handling — missing graph files, empty projects |
| SEC-8 | No | No new dependencies |

## Out of Scope

- Per-function complexity 明细改动（保留在 `pactkit complexity` 子命令中，不受此 Story 影响）
- 新增分析维度（churn 分析、code duplication 等 — 未来 Story）
- Report HTML 可视化集成（由 pactkit-report `--overlay` 消费 JSON）
- 自动修复建议（audit 只诊断不修复）
