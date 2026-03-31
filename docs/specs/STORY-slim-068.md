# STORY-slim-068: Fix 4 call chain断链 in static analysis pipeline

| Field | Value |
|-------|-------|
| ID | STORY-slim-068 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.3 |

## Background

`visualize --mode call` 的静态分析管道存在4类调用链断链（broken chain），导致生成的 call graph 中关键调用路径不可见：

1. **Scan collision (dict.update last-wins)**: `_build_call_graph:738-739` 使用 `dict.update()` 合并多文件扫描结果。当项目内存在同名函数（如 `pactkit-plugin/` 部署副本中的 `_build_call_graph`），后扫描文件的 `call_edges` 覆盖前者，导致边丢失。
2. **Dynamic dispatch 不可见**: `_extract_calls:820-831` 只识别 `ast.Name`（裸函数调用）和 `self.method()`。`obj.method()` 形式的调用（如 `deployer_instance.deploy()`）被忽略，导致通过 registry/dict 的动态分发路径断链。
3. **Abstract method orphan**: `extract_functions_and_calls:266-276` 不追踪类继承关系。`DeployerBase.deploy` 与其子类 `ClassicDeployer.deploy`、`OpenCodeDeployer.deploy` 之间无连接，显示为孤立节点。
4. **Cross-package 不可见**: `_scan_files:197` 只扫描项目 root 内文件。外部适配器包（pactkit-opencode、pactkit-codex）的调用边不在扫描范围内。

问题在 STORY-slim-067（嵌套调用链）和 HOTFIX-slim-069（边去重 + cycle 修复）完成后，对 PactKit 自身代码运行 call graph 分析时发现。

## Requirements

### R1: Scan Collision Prevention (MUST)

`_build_call_graph()` 合并多文件扫描结果时，同名函数的 `call_edges` 不得被覆盖。当多个文件定义同名函数时，MUST 合并（extend）其 callee 列表而非替换（update）。同时，`pactkit-plugin/` 等部署产物目录 MUST 加入默认 `SCAN_EXCLUDES`。

### R2: Dynamic Dispatch Hint (SHOULD)

支持通过注释提示（comment annotation）声明动态分发目标。格式：`# pactkit-trace: dispatches_to ClassName.method, ClassName2.method`。`_extract_calls()` SHOULD 解析此注释并将声明的目标加入 callee 列表。

### R3: Inheritance Edge Linking (MUST)

当扫描到类定义时，`extract_functions_and_calls()` MUST 识别继承关系。如果子类方法与基类同名方法匹配（override），在 call graph 中 MUST 添加 `BaseClass.method → SubClass.method` 的虚拟边。

### R4: Cross-Package Stub Support (MAY)

支持在 `pactkit.yaml` 的 `visualize` 节中声明外部包的 stub edges。格式：`stub_edges: ["deployer.deploy → pactkit_opencode.deployer.deploy"]`。如果配置存在，`_build_call_graph()` MAY 将这些边注入到 call graph 中。

## Acceptance Criteria

### AC1: dict.update Merge Does Not Overwrite (R1)

- **Given** 两个文件各定义同名函数 `foo`，文件A的 `foo` 调用 `[bar]`，文件B的 `foo` 调用 `[baz]`
- **When** `_build_call_graph()` 扫描这两个文件
- **Then** `call_edges['foo']` 包含 `[bar, baz]`（合并），而非仅 `[baz]`（覆盖）

### AC2: pactkit-plugin in Default SCAN_EXCLUDES (R1)

- **Given** 项目目录下存在 `pactkit-plugin/skills/.../visualize.py`
- **When** `_scan_files()` 使用默认 `SCAN_EXCLUDES` 扫描
- **Then** `pactkit-plugin/` 下的文件不在返回的 `all_files` 中

### AC3: Dispatch Hint Parsed (R2)

- **Given** 一个函数体包含注释 `# pactkit-trace: dispatches_to ClassicDeployer.deploy, OpenCodeDeployer.deploy`
- **When** `_extract_calls()` 解析该函数
- **Then** 返回的 callee 列表包含 `ClassicDeployer.deploy` 和 `OpenCodeDeployer.deploy`

### AC4: Inheritance Override Edges (R3)

- **Given** `class Base` 定义 `deploy()`, `class Sub(Base)` override `deploy()`
- **When** `extract_functions_and_calls()` 扫描该文件
- **Then** call graph 包含虚拟边 `Base.deploy → Sub.deploy`

### AC5: Stub Edges Injected from Config (R4)

- **Given** `pactkit.yaml` 包含 `visualize.stub_edges: ["deploy → pactkit_opencode.deployer.deploy"]`
- **When** `_build_call_graph()` 构建 call graph
- **Then** 生成的边列表包含 `deploy → pactkit_opencode.deployer.deploy`

### AC6: Full Graph No Regression (R1, R3)

- **Given** 对 PactKit 自身代码运行 `visualize --mode call` (无 `--entry`)
- **When** 生成完整 call graph
- **Then** 无 `dict.update` 覆盖导致的边丢失；`DeployerBase.deploy` 不再是孤立节点

## Target Call Chain

```
visualize (CLI entry)
  → _build_call_graph()           [line 730] — R1 fix: dict.update → extend merge
    → PythonAnalyzer.extract_functions_and_calls()  [line 255] — R3 fix: inheritance edges
      → _extract_calls()          [line 817] — R2 fix: parse dispatch hints
  → _scan_files()                 [line 190] — R1 fix: add pactkit-plugin/ to SCAN_EXCLUDES
  → _load_scan_excludes()         [line 116] — R4: read stub_edges from pactkit.yaml
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py` | R1: Add `'pactkit-plugin'` to `SCAN_EXCLUDES` set (line 78) | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | R1: Change `call_edges.update(ce)` to extend-merge (line 739): for each key, extend existing list instead of replacing | Step 1 | Low |
| 3 | `src/pactkit/skills/visualize.py` | R2: In `_extract_calls()`, parse `# pactkit-trace: dispatches_to` comments from function body source and add declared targets to callees | Step 2 | Medium |
| 4 | `src/pactkit/skills/visualize.py` | R3: In `extract_functions_and_calls()`, track class inheritance (`ast.ClassDef.bases`), add virtual edges from base method to override method | Step 2 | Medium |
| 5 | `src/pactkit/skills/visualize.py` | R4: In `_build_call_graph()`, read `stub_edges` from `pactkit.yaml` via `_load_scan_excludes()` path and inject as additional edges | Step 4 | Low |
| 6 | `tests/unit/test_visualize_*.py` | TDD tests for AC1-AC6 | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Code Injection) | Yes | `_extract_calls()` parses comment annotations — ensure no eval/exec of user content |
| SEC-2 (Input Handling) | Yes | `stub_edges` from YAML config — validate format, reject malicious patterns |
| SEC-3 (Database) | N/A | No database patterns |
| SEC-4 (Frontend) | N/A | No frontend files |
| SEC-5 (Auth) | N/A | No auth patterns |
| SEC-6 (API) | N/A | No API/route files |
| SEC-7 (Error Handling) | Yes | File parse errors must not crash the scan |
| SEC-8 (Dependencies) | N/A | No new dependencies |

## Out of Scope

- Runtime tracing / instrumentation（非静态分析）
- 自动发现外部包调用（仅支持手动 stub 声明）
- 修改 TreeSitterAnalyzer（仅影响 PythonAnalyzer）
- 跨语言调用链分析
