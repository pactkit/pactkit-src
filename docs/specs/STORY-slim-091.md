# STORY-slim-091: Harness Audit Skill: H1-H7 AI Readiness Assessment

| Field | Value |
|-------|-------|
| ID | STORY-slim-091 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.0 |

## Background

企业在引入 AI Coding 工具（Claude Code, OpenCode, Codex 等）时，缺乏一个标准化的**就绪度评估**。项目方不知道自己的代码库是否"AI Ready"，也不知道哪些维度需要补齐。

基于 AI Coding Harness 7 层成熟度模型（H1-H7），创建 `pactkit-audit` skill，自动扫描项目并输出：
1. **Compliance**: 每层 L0-L3 评级 + 综合 Harness Score (0-100)
2. **AI Readiness**: min(H1..H7) ≥ L1 即为 Ready（短板决定论）
3. **Findings**: 架构/代码/安全维度的 suggestions，按 severity 排序
4. **Insights**: 调用链分析 — 高扇入文件、爆炸半径 top 10、循环依赖

审计结果写入 `docs/architecture/governance/harness_audit.json`（单文件覆写，git 管历史），每次 `/project-done` 自动更新。`/project-plan` 可选读取，`ready: false` 时 WARN 用户。

**Harness 7 层模型**:

| Layer | Name | What It Measures | Detection |
|-------|------|-----------------|-----------|
| H1 | Prompt Engineering | System prompts, rules, agent roles | Auto-scan |
| H2 | Context Engineering | Project context, memory, hierarchy of truth | Auto-scan |
| H3 | Process Governance | PDCA workflow, TDD, quality gates | Auto-scan |
| H4 | Tool Governance | MCP config, permissions, tool whitelist | Manual input |
| H5 | Safety & Guardrails | .gitignore, safety rules, hooks | Auto-scan |
| H6 | Observability | Logging, cost tracking, lessons, self-audit | Manual input |
| H7 | Evolution | Version management, changelog, automation | Auto-scan |

**评分模型**: Each layer L0-L3 (None → Basic → Structured → Advanced). Harness Score = sum(all 7) / 21 × 100.
**AI Ready** = min(H1..H7) ≥ L1 (任何一层 L0 = Not Ready)

## Requirements

### R1: H1 Prompt Engineering Check (MUST)

Auto-scan 检测项:
- L1: CLAUDE.md (或等效指令文件) 存在
- L2: rules/ 目录存在且有 ≥1 个规则文件；agents/ 目录存在且有 ≥1 个 agent 定义
- L3: commands/ 目录存在且有 ≥3 个 playbook；Signal Strength Convention 规则存在

### R2: H2 Context Engineering Check (MUST)

Auto-scan 检测项:
- L1: docs/product/context.md 存在
- L2: docs/specs/ 目录存在且有 ≥1 个 Spec 文件；hierarchy-of-truth 规则存在
- L3: context.md 更新日期 ≤7 天；memory 配置存在（Memory MCP 或 MEMORY.md）

### R3: H3 Process Governance Check (MUST)

Auto-scan 检测项:
- L1: docs/product/sprint_board.md 存在
- L2: tests/ 目录存在且有 ≥1 个测试文件；CI 配置存在（.github/workflows/ 或类似）
- L3: Spec→Test 映射完整（每个 Done Spec 有对应测试）；spec-lint 规则存在；quality gate 配置（pactkit.yaml lint_blocking）

### R4: H4 Tool Governance Check (MUST)

Manual input + partial auto-scan:
- L1: pactkit.yaml 存在
- L2: settings.json (或等效) 存在且有 permissions 配置
- L3: MCP servers 配置存在；tool whitelist 定义
- H4 的 L2/L3 检测项需要用户确认（`--manual-input` 参数或 `harness_audit.json` 中 `manual` 字段），auto-scan 只能检测文件是否存在

### R5: H5 Safety & Guardrails Check (MUST)

Auto-scan 检测项:
- L1: .gitignore 存在
- L2: safety rules 存在（规则文件中包含 secrets/data-loss 相关关键词）；hooks 配置存在
- L3: SEC-1~SEC-8 在最近的 Spec 中全部覆盖；pre-commit hooks 配置

### R6: H6 Observability Check (MUST)

Manual input + partial auto-scan:
- L1: docs/architecture/governance/lessons.md 存在
- L2: self-audit 规则存在（operational-discipline 规则）
- L3: cost tracking 配置；logging 配置；retro 历史存在
- 同 H4，L2/L3 部分需要用户确认

### R7: H7 Evolution Check (MUST)

Auto-scan 检测项:
- L1: 版本管理文件存在（pyproject.toml/package.json 含 version 字段）
- L2: CHANGELOG.md 存在；git tags 存在（≥1 个 tag）
- L3: CI/CD pipeline 配置完整（publish/release workflow）；自动化脚本存在

### R8: Harness Score Calculation (MUST)

- 每层独立评 L0/L1/L2/L3（取该层最高满足等级）
- Harness Score = sum(H1..H7 levels) / 21 × 100，精确到整数
- AI Ready = min(H1..H7) ≥ L1
- 输出包含: score (int 0-100), ready (bool), layers (dict H1-H7 各含 level/name/checks)

### R9: Findings — Multi-Dimensional Suggestions (MUST)

聚合现有检测能力生成分类建议：
- **Architecture**: 复用 `layers()` 违规 + `doctor.py` module drift
- **Code**: 复用 `garden.py` dead code + `complexity()` 高复杂度函数 (>20)
- **Security**: 复用 `sec_scope.py` 检测未覆盖的 SEC 项
- 每条 finding 含: severity (critical/high/medium/low), category (architecture/code/security), message, file (optional)
- 按 severity 降序排列

### R10: Insights — Call Chain Analysis (MUST)

基于 call_graph 和 code_graph 数据生成代码洞察:
- **High fan-in files**: 被 ≥5 个文件 import 的文件（变更风险高）
- **Blast radius top 10**: 爆炸半径最大的 10 个文件
- **Circular dependencies**: 文件级循环依赖检测（DFS on file edges）
- **God objects**: 函数数量 >15 的文件
- 输出: insights 对象含 high_fan_in[], blast_top10[], circular_deps[], god_objects[]

### R11: Audit Result File (MUST)

- 路径: `docs/architecture/governance/harness_audit.json`
- 格式: 单个 JSON 文件，每次 audit 完整覆写
- 内容: `{timestamp, commit, score, ready, layers: {H1..H7}, findings: [], insights: {}}`
- 历史: 由 git 管理，`git log -p harness_audit.json` 可追溯所有变更

### R12: Done Phase Integration (MUST)

在 `/project-done` Phase 3 (Hygiene) 中新增一步：
- 运行 `pactkit audit --append` 更新 `harness_audit.json`
- 将文件 `git add` 随 commit 一起提交
- 如果 `ready` 从 `true` 变为 `false`，WARN 用户

### R13: Plan Phase Integration (SHOULD)

在 `/project-plan` Phase 1 (Archaeology) 中可选读取 `harness_audit.json`：
- 如果文件存在且 `ready: false`，WARN: "Harness audit shows project is NOT AI Ready. Weakest layer: {layer}."
- 不阻塞 Plan 流程

### R14: Skill Entry Point (MUST)

创建 `pactkit-audit` skill，入口为 `pactkit audit` CLI 子命令：
- `pactkit audit` → 运行全部 H1-H7 检查，输出人类可读报告 + 写入 JSON 文件
- `pactkit audit --json` → 仅输出 JSON 到 stdout（供 pactkit-report --overlay 使用）
- `pactkit audit --layer H3` → 仅检查指定层
- `pactkit audit --append` → 静默更新 JSON 文件（Done 集成用）

## Acceptance Criteria

### AC1: Full Audit on Initialized Project (R1, R2, R3, R5, R7, R8)

- **Given** a project with pactkit.yaml, CLAUDE.md, rules/, specs/, tests/, sprint_board.md
- **When** `pactkit audit`
- **Then** output shows H1-H7 each with L0/L1/L2/L3 level, Harness Score, and AI Ready status

### AC2: AI Ready Detection (R8)

- **Given** a project where H1=L2, H2=L1, H3=L2, H4=L1, H5=L1, H6=L1, H7=L1
- **When** `pactkit audit`
- **Then** `ready: true` because min(all layers) ≥ L1; score = (2+1+2+1+1+1+1)/21×100 = 43

### AC3: Not Ready — One Layer L0 (R8)

- **Given** a project where H6=L0 (no lessons.md)
- **When** `pactkit audit`
- **Then** `ready: false` regardless of other layers' scores; output highlights H6 as the blocker

### AC4: Findings Output (R9)

- **Given** a project with 2 layer violations and 3 high-complexity functions
- **When** `pactkit audit`
- **Then** findings list contains ≥5 entries; architecture findings include layer violations; code findings include high-complexity functions

### AC5: Insights — Circular Dependency (R10)

- **Given** a project where file A imports B and B imports A
- **When** `pactkit audit`
- **Then** insights.circular_deps contains the cycle [A, B]

### AC6: JSON File Written (R11)

- **Given** a successful audit run
- **When** `pactkit audit`
- **Then** `docs/architecture/governance/harness_audit.json` exists with valid JSON containing timestamp, score, ready, layers

### AC7: Done Integration (R12)

- **Given** an existing harness_audit.json
- **When** `/project-done` runs
- **Then** harness_audit.json is updated with new timestamp and included in the commit

### AC8: Plan Reads Audit (R13)

- **Given** harness_audit.json with `ready: false`
- **When** `/project-plan` runs
- **Then** output includes a WARN about not AI Ready, but Plan proceeds normally

### AC9: Layer-Specific Check (R14)

- **Given** a project
- **When** `pactkit audit --layer H5`
- **Then** only H5 (Safety & Guardrails) checks are run and reported

### AC10: Manual Input Layers (R4, R6)

- **Given** H4 and H6 have manual-input checks
- **When** `pactkit audit` and no `--manual-input` provided
- **Then** H4/H6 auto-scannable items are checked; manual items default to L0 with note "requires manual verification"

## Target Call Chain

```
pactkit audit (CLI entry in cli.py)
  └── audit(root, layer?, json_only?, append?)           → NEW
        ├── _check_h1(root) → {level, checks}            → NEW (auto-scan)
        │     └── Glob for CLAUDE.md, rules/, agents/, commands/
        ├── _check_h2(root) → {level, checks}            → NEW (auto-scan)
        │     └── Glob for context.md, specs/, hierarchy-of-truth
        │     └── doctor.py stale check                   → REUSE
        ├── _check_h3(root) → {level, checks}            → NEW (auto-scan)
        │     └── guards.py board check                   → REUSE
        │     └── Glob for tests/, CI configs
        ├── _check_h4(root, manual?) → {level, checks}   → NEW (partial auto)
        │     └── Glob for pactkit.yaml, settings.json
        ├── _check_h5(root) → {level, checks}            → NEW (auto-scan)
        │     └── sec_scope.py                            → REUSE
        │     └── Glob for .gitignore, hooks, safety rules
        ├── _check_h6(root, manual?) → {level, checks}   → NEW (partial auto)
        │     └── Glob for lessons.md, retro files
        ├── _check_h7(root) → {level, checks}            → NEW (auto-scan)
        │     └── Glob for CHANGELOG.md, pyproject.toml version, git tags
        ├── _compute_score(layers) → {score, ready}       → NEW
        ├── _collect_findings(root)                        → NEW (aggregator)
        │     ├── layers() violations                     → REUSE (visualize.py)
        │     ├── garden.py dead code                     → REUSE
        │     ├── complexity() high functions             → REUSE (visualize.py)
        │     └── sec_scope.py gaps                       → REUSE
        ├── _collect_insights(root)                        → NEW (aggregator)
        │     ├── fan-in analysis from code_graph.mmd     → NEW
        │     ├── blast_radius() top 10                   → REUSE (visualize.py)
        │     ├── circular dependency DFS                 → NEW
        │     └── god object detection                    → NEW
        └── _write_audit_json(result, root)               → NEW
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/audit.py` | Implement `_check_h1()` through `_check_h7()` — each returns `{level, name, checks}` | None | Low |
| 2 | `src/pactkit/audit.py` | Implement `_compute_score(layers)` — sum/21×100 + min≥L1 ready check | Step 1 | Low |
| 3 | `src/pactkit/audit.py` | Implement `_collect_findings(root)` — aggregate layers/garden/complexity/sec_scope | None | Medium |
| 4 | `src/pactkit/audit.py` | Implement `_collect_insights(root)` — fan-in, blast_top10, circular deps, god objects | None | Medium |
| 5 | `src/pactkit/audit.py` | Implement `audit()` entry point + `_write_audit_json()` | Steps 1-4 | Low |
| 6 | `src/pactkit/cli.py` | Register `pactkit audit` subcommand with `--json`, `--layer`, `--append` flags | Step 5 | Low |
| 7 | `commands/project-done.md` | Add Phase 3.x: `pactkit audit --append` + git add | Step 5 | Low |
| 8 | `commands/project-plan.md` | Add Phase 1 optional read of harness_audit.json + WARN if not ready | None | Low |
| 9 | `tests/unit/test_audit.py` | Unit tests: H1-H7 checks, scoring, findings, insights, file output | Steps 1-5 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code — audit checks read project files, ensure no code execution from scanned content |
| SEC-2 | Yes | Input handling — `--layer` and `--manual-input` CLI args need validation |
| SEC-3 | No | No database |
| SEC-4 | No | No HTML output (JSON file only; HTML via pactkit-report overlay) |
| SEC-5 | No | No auth |
| SEC-6 | No | No API |
| SEC-7 | Yes | Error handling — missing files, malformed pactkit.yaml, absent git tags |
| SEC-8 | No | No new dependencies |

## Out of Scope

- 修改现有 PDCA skill 的核心逻辑（仅在 Done/Plan playbook 中增加一步调用）
- HTML 报告输出（由 pactkit-report `--overlay harness_audit.json` 负责）
- H4/H6 的完整自动检测（需要 manual input，超出文件扫描范围）
- 代码自动修复（audit 只诊断不修复）
- 跨仓库审计（仅当前 project root）
