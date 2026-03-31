# STORY-slim-069: Extend dispatch hint and inheritance edges to all tree-sitter languages

| Field | Value |
|-------|-------|
| ID | STORY-slim-069 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.3 |

## Background

STORY-slim-068 为 `visualize --mode call` 实现了 4 类断链修复（R1 scan collision、R2 dispatch hint、R3 inheritance edges、R4 stub edges），但 R2（dispatch hint 注释解析）和 R3（继承边链接）仅在 `PythonAnalyzer`（基于 `ast` 模块）中实现。`TreeSitterAnalyzer` 的 3 个子类（`GoAnalyzer`、`JavaAnalyzer`、`TSAnalyzer`）仍然缺少这两项能力，导致非 Python 项目的 call graph 无法受益于断链修复。

各语言的继承语义差异：
- **Go**: struct embedding（`type Sub struct { Base }`）+ 隐式 interface satisfaction（无 `implements` 关键字）
- **Java**: `extends` 单继承 + `implements` 多接口
- **TypeScript**: `class Sub extends Base`

dispatch hint 注释格式跨语言统一使用 `// pactkit-trace: dispatches_to Target1, Target2`（Go/Java/TS 均使用 `//` 行注释）。tree-sitter 中注释节点是函数体 body node 的直接子节点，可以通过 scoped query 捕获。

## Requirements

### R1: Tree-Sitter Dispatch Hint Parsing (MUST)

`TreeSitterAnalyzer._extract_calls_from_body()` MUST 在解析调用目标的同时，扫描 body_node 内的注释节点。当注释文本匹配 `pactkit-trace: dispatches_to` 前缀时，MUST 将声明的目标追加到 callee 列表。注释查询需语言感知：Go/TS 使用 `(comment) @comment`，Java 使用 `[(line_comment)(block_comment)] @comment`。每个子类 MUST 在 `__init__` 中初始化 `self._comment_query`。

### R2: Go Inheritance Edges — Struct Embedding (MUST)

`GoAnalyzer._extract_funcs_and_calls()` MUST 检测 struct embedding 关系（`type Sub struct { Base }` 格式，即 `field_declaration` 无 `field_identifier` 仅有 `type_identifier`）。当嵌入的 base struct 和 sub struct 均定义同名 method 时，MUST 添加 `Base.method → Sub.method` 虚拟边。

### R3: Java Inheritance Edges — extends/implements (MUST)

`JavaAnalyzer._extract_funcs_and_calls()` MUST 检测 `class_declaration` 的 `superclass`（extends）和 `super_interfaces`（implements）。当子类方法与基类/接口同名方法匹配时，MUST 添加 `Base.method → Sub.method` 虚拟边。

### R4: TypeScript Inheritance Edges — class extends (MUST)

`TSAnalyzer._extract_funcs_and_calls()` MUST 检测 `class_declaration` 的 `class_heritage` → `extends_clause`。当子类方法与基类同名方法匹配时，MUST 添加 `Base.method → Sub.method` 虚拟边。

## Acceptance Criteria

### AC1: Go Dispatch Hint Parsed (R1)

- **Given** 一个 Go 函数体内包含注释 `// pactkit-trace: dispatches_to Handler.Run, Logger.Write`
- **When** `GoAnalyzer` 的 `_extract_calls_from_body()` 解析该函数
- **Then** 返回的 callee 列表包含 `Handler.Run` 和 `Logger.Write`

### AC2: Java Dispatch Hint Parsed (R1)

- **Given** 一个 Java 方法体内包含注释 `// pactkit-trace: dispatches_to SubService.handle`
- **When** `JavaAnalyzer` 的 `_extract_calls_from_body()` 解析该方法
- **Then** 返回的 callee 列表包含 `SubService.handle`

### AC3: TS Dispatch Hint Parsed (R1)

- **Given** 一个 TypeScript 方法体内包含注释 `// pactkit-trace: dispatches_to ReactRouter.navigate`
- **When** `TSAnalyzer` 的 `_extract_calls_from_body()` 解析该方法
- **Then** 返回的 callee 列表包含 `ReactRouter.navigate`

### AC4: Go Struct Embedding Inheritance Edges (R2)

- **Given** Go 代码定义 `type Base struct{}` 有方法 `Deploy()`，`type Sub struct { Base }` override `Deploy()`
- **When** `GoAnalyzer.extract_functions_and_calls()` 扫描该文件
- **Then** call graph 包含虚拟边 `Base.Deploy → Sub.Deploy`

### AC5: Java extends/implements Inheritance Edges (R3)

- **Given** Java 代码定义 `class Base { void deploy() {} }`、`class Sub extends Base { void deploy() {} }`
- **When** `JavaAnalyzer.extract_functions_and_calls()` 扫描该文件
- **Then** call graph 包含虚拟边 `Base.deploy → Sub.deploy`

### AC6: TS class extends Inheritance Edges (R4)

- **Given** TypeScript 代码定义 `class Base { deploy() {} }`、`class Sub extends Base { deploy() {} }`
- **When** `TSAnalyzer.extract_functions_and_calls()` 扫描该文件
- **Then** call graph 包含虚拟边 `Base.deploy → Sub.deploy`

### AC7: No Hint No Extra Callees (R1)

- **Given** 一个 Go/Java/TS 函数体内无 `pactkit-trace` 注释
- **When** `_extract_calls_from_body()` 解析该函数
- **Then** callee 列表不包含任何 dispatch hint 目标（行为与改动前一致）

### AC8: No False Inheritance Edge (R2, R3, R4)

- **Given** 子类定义了一个基类中不存在的方法
- **When** 对应语言的 `extract_functions_and_calls()` 扫描该文件
- **Then** 不会为该方法生成虚拟继承边

## Target Call Chain

```
TreeSitterAnalyzer._extract_calls_from_body()  [line 393] — R1: add comment query + hint parsing
  ↳ self._comment_query (new)                  — per-language comment node query

GoAnalyzer.__init__()        [line 427] — R1: init self._comment_query = (comment) @comment
GoAnalyzer._extract_funcs_and_calls()  [line 438] — R2: detect struct embedding, add inheritance edges

JavaAnalyzer.__init__()      [line 497] — R1: init self._comment_query = [(line_comment)(block_comment)] @comment
JavaAnalyzer._extract_funcs_and_calls()  [line 509] — R3: detect extends/implements, add inheritance edges

TSAnalyzer.__init__()        [line 567] — R1: init self._comment_query = (comment) @comment
TSAnalyzer._extract_funcs_and_calls()  [line 576] — R4: detect class_heritage extends, add inheritance edges
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py` | R1: Add `_comment_query` init to `GoAnalyzer.__init__`, `JavaAnalyzer.__init__`, `TSAnalyzer.__init__` with language-specific comment query | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | R1: Extend `_extract_calls_from_body()` to run `self._comment_query` on body_node, parse `pactkit-trace: dispatches_to` prefix, append targets to callee list | Step 1 | Low |
| 3 | `src/pactkit/skills/visualize.py` | R2: In `GoAnalyzer._extract_funcs_and_calls()`, query `type_spec` for struct embedding, build class→bases map, post-pass to add virtual inheritance edges for shared methods | Step 2 | Medium |
| 4 | `src/pactkit/skills/visualize.py` | R3: In `JavaAnalyzer._extract_funcs_and_calls()`, query `class_declaration` for `superclass`/`super_interfaces`, post-pass to add virtual inheritance edges | Step 2 | Medium |
| 5 | `src/pactkit/skills/visualize.py` | R4: In `TSAnalyzer._extract_funcs_and_calls()`, query `class_declaration` for `class_heritage` → `extends_clause`, post-pass to add virtual inheritance edges | Step 2 | Medium |
| 6 | `tests/unit/test_visualize_multilang_chain.py` | TDD tests for AC1-AC8 | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Code Injection) | Yes | Comment text parsed for dispatch hints — ensure no eval/exec, only string splitting |
| SEC-2 (Input Handling) | N/A | No external input; comments from source files only |
| SEC-3 (Database) | N/A | No database patterns |
| SEC-4 (Frontend) | N/A | No frontend files |
| SEC-5 (Auth) | N/A | No auth patterns |
| SEC-6 (API) | N/A | No API/route files |
| SEC-7 (Error Handling) | Yes | tree-sitter query/parse errors must not crash the scan |
| SEC-8 (Dependencies) | N/A | No new dependencies — uses existing tree-sitter grammars |

## Out of Scope

- Go interface satisfaction 自动推断（隐式 interface，需要类型检查器，非静态分析可达）
- 跨文件继承检测（仅处理同文件内的 class/struct 定义）
- R1/R4 stub edges（已在 STORY-slim-068 实现，不重复）
- PythonAnalyzer 修改（已在 STORY-slim-068 完成）
- 运行时 tracing / instrumentation
