# STORY-slim-094: Unified HTML Report — single aggregated dashboard from all .mmd graphs + audit data

| Field | Value |
|-------|-------|
| ID | STORY-slim-094 |
| Status | Draft |
| Priority | P1 |
| Release | 2.9.14 |

## Background

当前 `pactkit-report` 的 `--all` 模式为每个 `.mmd` 文件生成一个独立 `.html`（9 个 .mmd → 9 个 .html），没有聚合视图。用户需要逐个打开文件，无法一览全貌。

对比 CodeFlow (braedonsaunders/codeflow) 的 3 列 dashboard 设计（文件树 + 画布 + 详情面板、多视图切换、健康分 ring），pactkit-report 的交互质量有显著差距。

CodeFlow 本身是 4700 行的 React SPA，依赖 CDN（React/Babel/Acorn），且不接受 .mmd 输入，直接集成不可行。正确方向是：借鉴其 UI 设计模式，改进 pactkit-report 生成**单个聚合 HTML dashboard**，将所有 .mmd 图 + audit 数据合并为一份交互式报告。

## Requirements

### R1: Unified Single HTML Output (MUST)

`--all` 模式 MUST 生成单个 `report.html`（而非 N 个文件），内含所有 `.mmd` 图的 Tab 切换。

- 输出路径: `docs/architecture/graphs/report.html`
- 每个 .mmd 对应一个 Tab（以文件名 stem 命名：code_graph, class_graph, call_graph 等）
- 默认选中 `code_graph` Tab（如果存在）

### R2: Left Panel — Audit Dashboard (SHOULD)

左侧面板 SHOULD 展示项目健康概览，数据来自 `harness_audit.json`：

- Harness Score 环形图（0-100，颜色区间：红 < 50、黄 50-80、绿 > 80）
- H1-H7 层级条（L0-L3 进度条）
- AI Ready 状态标志（YES/NO）
- 如果 `harness_audit.json` 不存在，显示 "Run `pactkit audit` to generate health data"

### R3: Right Panel — Hotspot Details (SHOULD)

右侧面板 SHOULD 展示 hotspot 详情：

- 默认显示 Top 10 hotspots 列表（来自 `harness_audit.json` 的 `hotspots` 数组）
- 每个 hotspot 显示：文件名、composite score、complexity、blast radius、fan-in
- 点击图中节点时，右侧面板切换为该节点的详情

### R4: Single File Backward Compatibility (MUST)

`--input <file.mmd>` 单文件模式 MUST 保持向后兼容：

- 输出单个 `.html`（与当前行为相同）
- 不含 Tab 切换、不含 audit 数据面板
- 保持当前的 force-directed 图 + tooltip 交互

### R5: Self-Contained Offline HTML (MUST)

生成的 HTML MUST 完全自包含，可离线使用：

- D3.js 内联（不依赖 CDN）
- 所有 CSS 内联
- 所有数据以 JSON 内联嵌入
- 单文件可通过 `open report.html` 直接查看

### R6: Overlay Integration (SHOULD)

`--overlay <file.json>` SHOULD 支持将 `harness_audit.json` 作为 overlay 传入：

- 自动检测 overlay 格式（harness_audit vs 自定义）
- 从 harness_audit 提取 hotspots → 节点着色（按 composite score 从绿到红）
- 从 harness_audit 提取 layers → 左面板数据

### R7: CLI Convenience (SHOULD)

`pactkit report` CLI 子命令 SHOULD 提供便捷入口：

- `pactkit report` = `pactkit report --all --overlay auto`（自动发现 harness_audit.json）
- `pactkit report --input <file>` = 单文件模式
- 注册到 `cli.py` subparsers

## Acceptance Criteria

### AC1: Unified HTML Generated (R1)

- **Given** `docs/architecture/graphs/` 下有 code_graph.mmd, class_graph.mmd, call_graph.mmd
- **When** 运行 `pactkit-report generate --all`
- **Then** 生成单个 `docs/architecture/graphs/report.html`，不再生成每个 .mmd 对应的 .html

### AC2: Tab Switching Works (R1)

- **Given** report.html 包含 3 个图（code, class, call）
- **When** 用户点击 "class_graph" tab
- **Then** 中央画布切换为 class diagram 的 D3 可视化

### AC3: Audit Data Displayed (R2)

- **Given** `harness_audit.json` 存在且 score=76, ready=true
- **When** 打开 report.html
- **Then** 左侧面板显示 Harness Score 环形图（76/100，黄色），H1-H7 条形图，AI Ready: YES

### AC4: No Audit Graceful Fallback (R2)

- **Given** `harness_audit.json` 不存在
- **When** 打开 report.html
- **Then** 左侧面板显示 "Run `pactkit audit` to generate health data"，不报错

### AC5: Hotspot Click Interaction (R3)

- **Given** report.html 包含 hotspots 数据
- **When** 用户点击图中一个节点（文件）
- **Then** 右侧面板显示该文件的 complexity, blast radius, fan-in, test coverage

### AC6: Single File Mode Unchanged (R4)

- **Given** 运行 `pactkit-report generate --input code_graph.mmd`
- **When** 生成完成
- **Then** 输出 `code_graph.html`（单图，无 Tab，无 audit 面板），行为与旧版一致

### AC7: Offline Self-Contained (R5)

- **Given** 生成 report.html
- **When** 断网后 `open report.html`
- **Then** D3 图正常渲染，所有交互正常工作

### AC8: Overlay Auto-detect (R6)

- **Given** `harness_audit.json` 存在于 `docs/architecture/governance/`
- **When** 运行 `pactkit report`（无 --overlay 参数）
- **Then** 自动加载 harness_audit.json 作为 overlay，图中节点按 hotspot score 着色

### AC9: CLI Convenience Entry (R7)

- **Given** pactkit CLI 已注册 report 子命令
- **When** 运行 `pactkit report`
- **Then** 等价于 `pactkit-report generate --all --overlay auto`，生成 `report.html`

## Target Call Chain

```
CLI: pactkit report [--all|--input]
  → cli.py: args.command == "report"
    → report.py: generate(all_mode=True, overlay_file=auto)
      → _discover_mmds(root) → list[Path]
      → for each .mmd: _parse_mmd(content) → {nodes, edges, groups}
      → _load_audit_data(root) → {score, layers, hotspots} | None
      → _render_unified_html(graphs_dict, audit_data) → single HTML string
      → write report.html
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/report.py` | 新增 `_render_unified_html()` 函数，生成带 Tab 切换的聚合 HTML | None | Medium |
| 2 | `src/pactkit/skills/report.py` | 新增 `_load_audit_data()` 从 harness_audit.json 读取数据 | Step 1 | Low |
| 3 | `src/pactkit/skills/report.py` | 修改 `generate()` 的 `all_mode` 分支，改为调用 unified 渲染 | Step 1 | Low |
| 4 | `src/pactkit/cli.py` | 注册 `pactkit report` 子命令 | None | Low |
| 5 | `src/pactkit/prompts/skills.py` | 更新 SKILL_REPORT_MD 文档 | Step 3 | Low |
| 6 | `tests/unit/test_report.py` | 新增 unified 模式测试 | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | 输入为本地 .mmd 文件，非用户输入 |
| SEC-2 Output Encoding | Yes | HTML 输出 MUST 对节点 label 做 html.escape()（已有） |
| SEC-3 Auth | N/A | 纯本地文件操作 |
| SEC-4 XSS | Yes | JSON 数据内嵌 HTML，需确保无 script injection |
| SEC-5 Secrets | N/A | 不涉及 |
| SEC-6 Rate Limit | N/A | 本地 CLI |
| SEC-7 Error Messages | N/A | 本地工具 |
| SEC-8 Dependencies | N/A | D3.js 内联，无新依赖引入 |

## Out of Scope

- 直接集成 CodeFlow 源码（4700 行 React SPA，依赖 CDN，架构不兼容）
- Mermaid 以外的输入格式支持
- 实时文件监听 / 热重载
- 多语言 AST 解析（PactKit 已有 visualize.py 负责）
- 导出 PDF / PNG（后续 Story 可扩展）
