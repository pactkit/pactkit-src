# STORY-slim-076: Multi-stack visualize: class mode + multi-language file scanning

| Field | Value |
|-------|-------|
| ID | STORY-slim-076 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.12 |

## Background

`visualize.py` 的 `_detect_stack(root)` 只返回单一语言标识（如 `node` 或 `go`），导致 `_scan_files()` 只扫描一种扩展名的文件。对于 Go+Node 等多栈混合项目，另一种语言的源文件被完全排除，file/call/class 三种模式全部只能看到部分代码。

此外，`_build_class_graph()` 硬编码使用 Python `ast.parse()`，即使 `all_files` 包含了非 Python 文件，也会因 `SyntaxError` 被静默跳过。Go struct/interface、TS/Java class 的继承关系无法在 class 模式下呈现。

当前 node 项目有一个 hardcode 的特殊分支（同时扫描 `.ts` + `.js`），但这不可扩展，且 `_load_code_graph()` 缺失该逻辑。

**根因**：三层缺陷叠加 — (1) 单一 stack 检测 (2) class 模式硬编码 Python AST (3) `_load_code_graph` 缺 node 双扫描

## Requirements

### R1: Multi-stack detection (MUST)

新增 `_detect_stacks(root) -> list[str]` 函数，返回项目中所有检测到的语言栈列表。检测逻辑：
- 优先读取 `pactkit.yaml` 的 `stack` 字段（如果是 `auto` 或未设置，走 marker 检测）
- 遍历 `_STACK_MARKERS` 收集所有命中的 stack（而非 first-match return）
- 单一 stack 项目行为不变（列表长度为 1）
- `_detect_stack(root)` 保留为兼容接口，返回 `_detect_stacks(root)[0]`

### R2: Multi-stack file scanning (MUST)

`visualize()`、`impact()`、`_load_code_graph()` 三个入口函数 MUST 对所有检测到的 stack 分别调用 `_scan_files()`，合并 `all_files`、`module_index`、`file_to_node`。移除 node 的 hardcode 特殊分支。

### R3: `extract_classes()` ABC method (MUST)

`LanguageAnalyzer` ABC MUST 新增抽象方法 `extract_classes(file_path) -> list[tuple]`，返回 `(rel_path, class_name, bases, methods)` 元组列表。四个 analyzer 子类均 MUST 实现：
- `PythonAnalyzer`：从现有 `_build_class_graph` 中 `ast.parse()` 逻辑迁移
- `GoAnalyzer`：提取 struct（含 embedded types）+ interface + 方法签名
- `TSAnalyzer`：提取 class（含 extends）+ 方法签名
- `JavaAnalyzer`：提取 class（含 extends/implements）+ 方法签名

### R4: `_build_class_graph()` 多语言重构 (MUST)

`_build_class_graph()` MUST 接收 `analyzer` 参数（或 `analyzers: list`），调用 `extract_classes()` 代替硬编码 `ast.parse()`。多 stack 时对每个 analyzer+对应文件集分别提取，合并结果。

### R5: Multi-stack analyzer selection (MUST)

新增 `_select_analyzers(stacks: list[str]) -> list[tuple[str, LanguageAnalyzer]]`，为每个 stack 创建对应 analyzer。调用方可按 stack 分组处理文件。

### R6: Backward compatibility (MUST)

- `pactkit.yaml` 中 `stack: python`（或任何单一值）的行为 MUST 与修改前完全一致
- 无 `pactkit.yaml` 的项目 MUST 继续走 marker 自动检测
- `_detect_stack()` 的返回值和签名 MUST 保持不变（返回第一个检测到的 stack）

## Acceptance Criteria

### AC1: Multi-stack detection returns all stacks (R1)

- **Given** 一个项目同时包含 `go.mod` 和 `package.json`
- **When** 调用 `_detect_stacks(root)`
- **Then** 返回 `['node', 'go']` 或 `['go', 'node']`（顺序按 `_STACK_MARKERS` 定义）

### AC2: Single-stack backward compatibility (R1, R6)

- **Given** 一个只有 `pyproject.toml` 的 Python 项目
- **When** 调用 `_detect_stacks(root)` 和 `_detect_stack(root)`
- **Then** `_detect_stacks` 返回 `['python']`，`_detect_stack` 返回 `'python'`

### AC3: Multi-stack file scanning merges all files (R2)

- **Given** 一个 Go+Node 项目，含 `.go` 和 `.ts` 源文件
- **When** `visualize()` 构建 `all_files`
- **Then** `all_files` 同时包含 `.go` 和 `.ts` 文件

### AC4: Class mode shows Go structs (R3, R4)

- **Given** 一个 Go 项目，含带 embedded struct 的源文件
- **When** 运行 `visualize --mode class`
- **Then** 输出的 `class_graph.mmd` 包含 Go struct 名称、方法签名、继承箭头（`Base <|-- Sub`）

### AC5: Class mode shows TS classes (R3, R4)

- **Given** 一个 Node 项目，含带 `extends` 的 TypeScript class
- **When** 运行 `visualize --mode class`
- **Then** 输出的 `class_graph.mmd` 包含 TS class 名称、方法签名、继承箭头

### AC6: Class mode shows Java classes (R3, R4)

- **Given** 一个 Java 项目，含带 `extends`/`implements` 的 Java class
- **When** 运行 `visualize --mode class`
- **Then** 输出的 `class_graph.mmd` 包含 Java class 名称、方法签名、继承/实现箭头

### AC7: Mixed-stack class graph merges both languages (R2, R4)

- **Given** 一个 Go+Node 混合项目
- **When** 运行 `visualize --mode class`
- **Then** 输出的 `class_graph.mmd` 同时包含 Go struct 和 TS class

### AC8: `_load_code_graph` multi-extension scanning (R2)

- **Given** 一个 Node 项目含 `.ts` 和 `.js` 文件
- **When** `_load_code_graph(root)` 被调用
- **Then** `all_files` 包含 `.ts` 和 `.js` 文件（不再遗漏 `.js`）

### AC9: Multi-stack analyzer selection (R5)

- **Given** 检测到 stacks 为 `['go', 'node']`
- **When** 调用 `_select_analyzers(stacks)`
- **Then** 返回 `[('go', GoAnalyzer), ('node', TSAnalyzer)]`，每个 stack 对应正确的 analyzer 实例

### AC10: pactkit.yaml stack field override (R1, R6)

- **Given** `pactkit.yaml` 中 `stack: go`
- **When** 调用 `_detect_stacks(root)`
- **Then** 返回 `['go']`（yaml 显式指定时仅返回指定值，不走 marker 检测）

## Target Call Chain

```
visualize(root, mode, ...)
  → _detect_stack(root)              # BUG: returns single str
  → _scan_files(file_ext=single)     # BUG: only one language scanned
  → _select_analyzer(stack)          # BUG: only one analyzer created
  → _build_class_graph(root, all_files, focus)  # BUG: hardcoded ast.parse()
      → ast.parse(p.read_text())     # Python-only, SyntaxError on Go/TS/Java

impact(target, entry)
  → _detect_stack(root)              # same single-stack bug
  → _scan_files(...)                 # same

_load_code_graph(root)
  → _detect_stack(root)              # same
  → _scan_files(file_ext=single)     # BUG: missing node .ts+.js dual-scan
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `visualize.py` | 新增 `_detect_stacks(root) -> list[str]`，重构 `_detect_stack()` 为其 wrapper | None | Low |
| 2 | `visualize.py` | `LanguageAnalyzer` ABC 新增 `extract_classes()` 抽象方法 | None | Low |
| 3 | `visualize.py` | `PythonAnalyzer.extract_classes()` — 从 `_build_class_graph` 迁移 ast 逻辑 | Step 2 | Low |
| 4 | `visualize.py` | `GoAnalyzer.extract_classes()` — 提取 struct/interface/methods via tree-sitter | Step 2 | Medium |
| 5 | `visualize.py` | `TSAnalyzer.extract_classes()` — 提取 class/extends/methods via tree-sitter | Step 2 | Medium |
| 6 | `visualize.py` | `JavaAnalyzer.extract_classes()` — 提取 class/extends/implements/methods | Step 2 | Medium |
| 7 | `visualize.py` | 重构 `_build_class_graph()` 接收 `analyzers` + 按 stack 分组的文件，调用 `extract_classes()` | Steps 3-6 | Medium |
| 8 | `visualize.py` | 重构 `visualize()`/`impact()`/`_load_code_graph()` 的文件扫描：遍历所有 stacks | Step 1 | Medium |
| 9 | `tests/unit/` | 为 R1-R6、AC1-AC9 编写单元测试 | Steps 1-8 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 修改 visualize.py 源码，需确保无回归 |
| SEC-2 | Yes | `_detect_stacks` 读取 pactkit.yaml 输入，需验证异常值处理 |
| SEC-3 | N/A | 无数据库操作 |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无认证逻辑 |
| SEC-6 | N/A | 无 API/路由 |
| SEC-7 | Yes | tree-sitter 解析异常需正确捕获，不泄露路径信息 |
| SEC-8 | N/A | 无依赖变更 |

## Out of Scope

- `pactkit.yaml` 新增 `stack: [go, node]` 列表语法（本期仅支持 marker 自动检测多栈）
- Rust、C/C++ 等语言的 tree-sitter analyzer
- `visualize --mode unified` 和 `--mode workflow` 的多栈支持（这些模式使用 topology parser，不依赖 stack 检测）
- class 模式下跨语言的继承关系（Go struct 不会 extends TS class）
