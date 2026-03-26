# STORY-slim-053: Fix visualize.py latent bugs: Mermaid injection, O(N*E) perf, module collision, substring match

| Field | Value |
|-------|-------|
| ID | STORY-slim-053 |
| Status | Done |
| Priority | P1 |
| Release | 2.4.1 |

## Background

STORY-slim-052 的深度调用链审计发现了 4 个 visualize.py 中的**潜伏 bug**（编号 R14-R17）。它们通过了当时的测试，但仅仅是因为 PactKit 自身的代码库没有触发条件——用于其他项目时（函数名含双引号、500+ 模块、同名文件、相似前缀文件名）这些 bug **必然触发**。

**为什么必须现在修**：
- PactKit 已有 4 个外部用户（截至 2026-03-26），他们的项目结构不受我们控制
- `visualize` 是每次 `/project-act`、`/project-done` 都会调用的核心命令，出错影响面极大
- 这 4 个 bug 的修复方案已明确，修复成本极低（每个 < 10 行代码变更）
- 放着不修只会让修复时间变长（代码继续演进，上下文丢失）

**潜伏条件汇总**：

| Bug | 触发条件 | 后果 |
|-----|---------|------|
| R1 Mermaid 引号注入 | 函数名或文件名含 `"` | 生成的 .mmd 文件语法错误，图无法渲染 |
| R2 O(N×E) 性能 | 大型项目 (200+ 模块, 1000+ 调用边) | `visualize --mode call` 可能需要数十秒 |
| R3 module_index 碰撞 | 不同目录下存在同名 .py 文件 | 依赖图中部分文件"消失"，边指向错误目标 |
| R4 focus substring 误匹配 | 文件名存在前缀关系 (auth.py / oauth.py) | focus 图包含不相关文件的节点 |

## Requirements

### R1: Escape double quotes in Mermaid node labels (MUST)

**当前代码（L514, L704）**：
```python
nodes.append(f'    {nid}["{f.name}"]')       # _build_file_graph L514
lines.append(f'    {safe(fn)}["{fn}"]')       # _build_call_graph L704
```

**问题**：当 `f.name` 或 `fn` 包含双引号 `"` 时，生成的 Mermaid 输出为：
```
    node_id["parse"data"]
```
这会导致 Mermaid 解析器报语法错误，整个图无法渲染。

**修复方案**：在所有拼接标签的位置，先对标签做 `label.replace('"', '#quot;')` 转义。Mermaid 支持 HTML 实体。

**影响范围**：`_build_file_graph` L514, `_build_call_graph` L704, L723。以及 `to_mermaid()` 中 WorkflowGraph 节点输出 L1051。共 4 处拼接点，需全部覆盖。

**验证方法**：构造含双引号的函数名/文件名，验证输出 .mmd 文件可被 Mermaid CLI 解析（`mmdc -i file.mmd -o /dev/null`），或至少不含未转义的 `"` 嵌套。

### R2: Replace O(N×E) `_resolve_callee` with dict lookup (MUST)

**当前代码（L762-768）**：
```python
def _resolve_callee(callee, all_func_names):
    if callee in all_func_names: return callee
    for fn in all_func_names:                    # O(N) linear scan
        if fn.endswith(f'.{callee}'): return fn
    return None
```

**问题**：`_resolve_callee` 被 `_build_call_graph` 在每条 call edge 上调用一次。对于 N 个函数和 E 条边，总复杂度为 O(N×E)。当 N=200、E=1000 时，执行 200,000 次字符串比较。在 PactKit 自身（N~150, E~800）已经接近边界。

**修复方案**：
1. 在 `_build_call_graph` 入口处，预构建一个 **suffix_index** 字典：
   ```python
   suffix_index = {}
   for fn in all_func_names:
       short = fn.rsplit('.', 1)[-1]  # "module.Class.method" → "method"
       suffix_index.setdefault(short, []).append(fn)
   ```
2. 修改 `_resolve_callee` 签名接受 `suffix_index`，查找改为 O(1) dict lookup + O(k) 歧义解析（k 为同名函数数，通常 1-2）。
3. 同步修改 `_reverse_caller_bfs`（L800）中对 `_resolve_callee` 的调用，传入同一个 `suffix_index`。

**验证方法**：对比修改前后 `_build_call_graph` 在 PactKit 自身代码上的执行时间（应从 ~0.5s 降至 ~0.05s），或用 `timeit` 衡量 1000 个函数 × 5000 条边的 benchmark。

### R3: Fix `_scan_files` module_index collision with list storage (MUST)

**当前代码（L155-168）**：
```python
module_index[module_name] = p          # L158 — 直接覆盖
module_index[short_name] = p           # L161 — 直接覆盖
module_index[pkg_name] = p             # L164 — 直接覆盖
module_index[short_pkg] = p            # L167 — 直接覆盖
```

**问题**：当两个不同目录存在同名文件（如 `pkg_a/utils.py` 和 `pkg_b/utils.py`）时，短名 `utils` 在 `module_index` 中后者覆盖前者。导致：
- `import utils` 边永远指向最后扫描到的那个文件
- 另一个文件在依赖图中"失联"——没有任何入边

**修复方案**：
1. 将 `module_index` 的值类型从 `Path` 改为 `list[Path]`：
   ```python
   module_index.setdefault(module_name, []).append(p)
   ```
2. `module_index.get(name)` 的所有调用方改为取列表第一个元素，或在有歧义时（`len > 1`）使用消费者文件的目录前缀做 **就近匹配**：
   ```python
   candidates = module_index.get(imported_module, [])
   tf = _best_match(candidates, consumer_file) if len(candidates) > 1 else (candidates[0] if candidates else None)
   ```
3. `_best_match` 逻辑：优先选与消费者在同一父包下的文件。

**影响范围**：`_scan_files` 返回值变更 → `_build_file_graph`、`_build_call_graph` 中所有 `module_index.get()` 调用需适配。约 6 处调用点。

**验证方法**：构造含 `pkg_a/utils.py` + `pkg_b/utils.py` 的项目，验证两者在 code_graph.mmd 中都有节点且边指向正确。

### R4: Replace focus graph substring match with exact path match (MUST)

**当前代码**：
```python
# _build_file_graph L541 — focus target matching
if focus in str(f.relative_to(root)): target_ids.add(nid)

# _build_file_graph L551 — node filtering
if any(rid in line for rid in relevant_ids): final_lines.append(line)

# _build_file_graph L580 — depth BFS node filtering
if any(nid in line for nid in allowed): final_lines.append(line)
```

**问题**：三处都用 `in` 做 **子串匹配**。
- L541: `focus="auth.py"` 会匹配 `oauth.py`、`auth_helper.py`、`src/auth.py`
- L551/L580: `rid="cli_py"` 会匹配 `cli_py_old`、`pactkit_cli_py` 等 node ID

**修复方案**：
1. **L541**（focus target）：用路径尾部精确匹配替代子串：
   ```python
   rel = str(f.relative_to(root))
   if rel == focus or rel.endswith('/' + focus):
       target_ids.add(nid)
   ```
2. **L551/L580**（node ID 过滤）：改用 set 查找替代子串扫描：
   ```python
   # 先从 line 中提取 node ID
   nid_in_line = line.strip().split('[')[0].strip()
   if nid_in_line in relevant_ids:
       final_lines.append(line)
   ```
   对于 `click` 行，也需要提取 ID。可用辅助函数 `_extract_node_id(line)` 统一处理。

**验证方法**：构造 `src/auth.py` + `src/oauth.py` 项目，`--focus auth.py` 后验证 oauth.py 节点不在输出中。

### R5: Replace BFS `list.pop(0)` with `collections.deque` (SHOULD)

**当前代码**：visualize.py 中有 4 处 BFS 使用 `list.pop(0)`：
- `_build_call_graph` L692: `queue.pop(0)`
- `_reverse_caller_bfs` L812: `queue.pop(0)`
- `WorkflowGraph.forward_reach` L1108: `queue.pop(0)`
- `WorkflowGraph.reverse_reach` L1125: `queue.pop(0)`

**问题**：`list.pop(0)` 是 O(N) 操作（需移动所有元素）。在大图上 BFS 时，总复杂度从 O(V+E) 退化为 O(V²+E)。当前图规模 < 500 节点，性能差异不明显，但与 R2 的性能修复一起做是零成本的。

**修复方案**：
```python
from collections import deque
queue = deque([start])
while queue:
    current = queue.popleft()  # O(1)
```

4 处统一替换。注意：`collections` 已在 `_SHARED_HEADER` 的 stdlib 导入列表中，但 visualize.py 的 standalone header 需要添加 `from collections import deque`。

**验证方法**：现有 BFS 测试通过即可（行为不变）。可选：对比 1000 节点图的 BFS 耗时。

## Acceptance Criteria

### AC1: Mermaid output renders with quoted labels (R1)

- **Given** a project containing a file named `parse"data.py` and a function named `get"value`
- **When** `visualize` and `visualize --mode call` are executed
- **Then** the generated `.mmd` files contain `#quot;` instead of raw `"` inside node labels, and no nested double-quote syntax errors exist

### AC2: Call graph builds in O(N+E) time (R2)

- **Given** a synthetic project with 1000 functions and 5000 call edges
- **When** `_build_call_graph` is executed
- **Then** execution completes in < 1 second (vs previous ~25 seconds), and the output graph is identical to the O(N*E) version

### AC3: Same-name files in different packages both appear in graph (R3)

- **Given** a project with `pkg_a/utils.py` importing `helpers` and `pkg_b/utils.py` importing `helpers`
- **When** `visualize` is executed
- **Then** both `pkg_a/utils.py` and `pkg_b/utils.py` appear as separate nodes in `code_graph.mmd`, and import edges point to the correct target (same-package preference)

### AC4: Focus graph excludes substring-similar files (R4)

- **Given** a project with `src/auth.py` and `src/oauth.py`
- **When** `visualize --focus auth.py` is executed
- **Then** the output contains a node for `auth.py` but does NOT contain a node for `oauth.py`

### AC5: BFS uses deque for O(1) popleft (R5)

- **Given** the current visualize.py source code after modification
- **When** all 4 BFS call sites are inspected
- **Then** all use `collections.deque` with `popleft()` instead of `list.pop(0)`, and existing BFS tests pass unchanged

## Target Call Chain

```
R1: _build_file_graph() L514 → nodes.append(f'..."{f.name}"...')
    _build_call_graph() L704, L723 → lines.append(f'..."{fn}"...')
    WorkflowGraph.to_mermaid() L1051 → f'    {nid}["{label}"]'

R2: _build_call_graph() L680 → for each edge → _resolve_callee(callee, all_func_names) L762
    _reverse_caller_bfs() L800 → _resolve_callee(callee, all_func_names)

R3: _scan_files() L155-168 → module_index[short_name] = p (overwrites)
    _build_file_graph() L520-535 → module_index.get(imported) (returns last-wins)
    _build_call_graph() L710-720 → module_index.get(module) (returns last-wins)

R4: _build_file_graph() L541 → focus in str(rel_path) (substring)
    _build_file_graph() L551 → rid in line (substring)
    _build_file_graph() L580 → nid in line (substring)

R5: _build_call_graph() L692, _reverse_caller_bfs() L812,
    WorkflowGraph.forward_reach() L1108, WorkflowGraph.reverse_reach() L1125
    → queue.pop(0) [O(N)]
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py` | Add `_mermaid_escape(label)` helper: `label.replace('"', '#quot;')` | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Apply `_mermaid_escape` at L514, L704, L723, L1051 (4 sites) | Step 1 | Low |
| 3 | `src/pactkit/skills/visualize.py` | Build `suffix_index` dict in `_build_call_graph` entry | None | Low |
| 4 | `src/pactkit/skills/visualize.py` | Refactor `_resolve_callee` to accept `suffix_index`, O(1) lookup | Step 3 | Medium |
| 5 | `src/pactkit/skills/visualize.py` | Update `_reverse_caller_bfs` to pass `suffix_index` | Step 4 | Low |
| 6 | `src/pactkit/skills/visualize.py` | Change `module_index` values from `Path` to `list[Path]` in `_scan_files` | None | Medium |
| 7 | `src/pactkit/skills/visualize.py` | Add `_best_match(candidates, consumer)` helper for same-package preference | Step 6 | Low |
| 8 | `src/pactkit/skills/visualize.py` | Update all ~6 `module_index.get()` call sites in `_build_file_graph` and `_build_call_graph` | Step 6, 7 | Medium |
| 9 | `src/pactkit/skills/visualize.py` | Replace L541 substring focus match with exact path-tail match | None | Low |
| 10 | `src/pactkit/skills/visualize.py` | Replace L551/L580 `rid in line` with `_extract_node_id(line)` + set lookup | Step 9 | Low |
| 11 | `src/pactkit/skills/visualize.py` | Replace 4x `list.pop(0)` with `deque.popleft()` | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | Yes | R1: user-controlled file/function names injected into Mermaid output — escape needed |
| SEC-2 Path Traversal | N/A | No file write path changes; existing `atomic_write` pattern preserved |
| SEC-3 Secret Leakage | N/A | No credential handling in visualize.py |
| SEC-4 Command Injection | N/A | No shell command execution in affected code paths |
| SEC-5 Dependency | N/A | Only stdlib `collections.deque` added — no new third-party deps |
| SEC-6 Auth/AuthZ | N/A | No authentication logic involved |
| SEC-7 Data Integrity | Yes | R3: module_index collision can cause incorrect graph edges — data integrity fix |
| SEC-8 Logging | N/A | No logging changes |

## Out of Scope

- visualize.py 中非 latent 的 bug（已在 STORY-slim-052 修复的 R18/R19）
- 其他 skill 脚本（board.py, scaffold.py, spec_linter.py）的加固——由 STORY-slim-052 覆盖
- 核心库（deployer.py, config.py, profiles.py）的审计——由 STORY-slim-054 覆盖
- 文件 I/O 安全（并发写、编码、大文件）——由 STORY-slim-055 覆盖
- E2E 测试覆盖扩展——由 STORY-slim-056 覆盖
- Mermaid CLI 集成测试（需要 `mmdc` 外部依赖）——仅做单元级验证
