# STORY-slim-095: Fix visualize focus call graph empty output and report empty tab handling

| Field | Value |
|-------|-------|
| ID | STORY-slim-095 |
| Status | Draft |
| Priority | P1 |
| Release | 2.9.14 |

## Background

### Bug 1: visualize focus call graph 输出空内容

`_build_call_graph()` 在 `focus` 不为 None 且没有 `--entry` 时（else 分支，line 808-809），用以下逻辑过滤 caller：

```python
if focus and focus not in func_registry.get(caller, ''): continue
```

`func_registry[caller]` 存储的是**源文件路径**（如 `src/pactkit/cli.py`），而 `focus` 在 STORY-slim-081 R4 的模块解析成功时被清为 `None`（line 1135: `focus = None`）。但在以下场景中 focus 保持原值：

1. 模块解析失败但 `modules` 列表为空 → focus 原值传入 `_build_call_graph`
2. 直接调用 `_build_call_graph(focus="some_module")` → focus 是模块名，`func_registry` 的 value 是文件路径

模块名（如 `pactkit`）和文件路径（如 `src/pactkit/cli.py`）的 `in` 检查可能意外匹配或完全不匹配，导致空图。

### Bug 2: report 对空图 Tab 无提示

`report.html` 的 unified dashboard 为每个 `.mmd` 文件生成 Tab，包括只有 `graph TD` 的空文件。选中空 Tab 时画布完全空白，无任何提示。

## Requirements

### R1: Fix focus filter in _build_call_graph (MUST)

`_build_call_graph()` 的 else 分支 focus 过滤 MUST 正确匹配：

- focus 经模块解析后应为目录路径或 None（不再是原始模块名）
- 当 `focus` 传入 `_build_call_graph` 时，过滤逻辑应检查 caller 的注册文件路径是否在 focus 目录下
- 如果过滤后无任何结果（0 nodes），SHOULD 输出诊断信息而非空 `graph TD`

### R2: Report empty Tab placeholder (SHOULD)

`_render_unified_html()` SHOULD 在空图 Tab 被选中时显示提示信息：

- 检测 `nodes.length === 0`
- 显示 "No data — run `visualize --mode call --focus <module>` to populate"
- 不影响其他有数据的 Tab

### R3: Skip empty .mmd in unified report (SHOULD)

`generate()` 的 `all_mode` SHOULD 跳过只含 `graph TD` 且无节点的 .mmd 文件，不为其生成 Tab。

## Acceptance Criteria

### AC1: Focus call graph produces non-empty output (R1)

- **Given** 项目有源码文件（`src/pactkit/`），`_detect_modules` 返回至少一个模块
- **When** 运行 `visualize --mode call --focus .`（根模块）
- **Then** `focus_call_graph.mmd` 包含至少 1 个节点和 1 条边

### AC2: Focus mismatch produces diagnostic (R1)

- **Given** focus 参数指向一个有源文件的目录
- **When** `_build_call_graph()` 过滤后 0 个 caller 匹配
- **Then** 输出包含诊断文字（如 "0 functions matched"），而非空 `graph TD`

### AC3: Empty Tab shows placeholder (R2)

- **Given** report.html 中某个 Tab 的 graph 有 0 个 nodes
- **When** 用户点击该 Tab
- **Then** 画布中央显示 "No data" 提示文字

### AC4: Empty .mmd skipped in unified report (R3)

- **Given** `docs/architecture/graphs/` 下有一个只含 `graph TD\n` 的 .mmd 文件
- **When** 运行 `pactkit report`（unified 模式）
- **Then** 该文件不出现在 Tab 列表中

## Target Call Chain

```
Bug 1 (R1):
  visualize --mode call --focus <module>
    → visualize.py line 1129-1135: _detect_modules → mod_map lookup
      → if match: focus=None, scan_root=mod_dir
      → if no match: focus=original value (BUG: passed as-is to _build_call_graph)
    → _build_call_graph(root, all_files, focus, entry=None)
      → else branch line 808-809:
        if focus and focus not in func_registry.get(caller, ''): continue
        → BUG: func_registry value = file path, focus = module name → mismatch → all skipped

Bug 2 (R2-R3):
  report.py generate(all_mode=True)
    → graphs_dict includes empty graphs (nodes=[])
    → _render_unified_html() renders Tab with 0 nodes → blank canvas
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py` | Fix focus filter: convert focus to dir path before passing to `_build_call_graph`, or filter by file path prefix | None | Medium |
| 2 | `src/pactkit/skills/visualize.py` | Add diagnostic output when focus filter produces 0 results | Step 1 | Low |
| 3 | `src/pactkit/skills/report.py` | Filter empty graphs in `generate()` all_mode before passing to `_render_unified_html()` | None | Low |
| 4 | `src/pactkit/skills/report.py` | Add empty state placeholder in JS `loadGraph()` function | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | 内部工具，输入为本地文件 |
| SEC-2 | N/A | 不涉及输出编码变更 |
| SEC-3 | N/A | 无 auth |
| SEC-4 | N/A | 不涉及新 HTML 模板变更 |
| SEC-5 | N/A | 不涉及 |
| SEC-6 | N/A | 本地 CLI |
| SEC-7 | N/A | 本地工具 |
| SEC-8 | N/A | 无依赖变更 |

## Out of Scope

- 重写 `_detect_modules` 的模块发现逻辑
- 新增模块匹配算法（fuzzy match 等）
- visualize 的其他模式（file, class, module）的 focus 行为
