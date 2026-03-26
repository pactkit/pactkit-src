# STORY-slim-055: File I/O safety: atomic writes, encoding edge cases, large file protection

| Field | Value |
|-------|-------|
| ID | STORY-slim-055 |
| Status | Done |
| Priority | P1 |
| Release | 2.4.1 |

## Background

PactKit skill scripts (`board.py`, `scaffold.py`, `visualize.py`) 和核心库模块执行文件读写操作。
STORY-slim-052 为 `board.py` 中的 `update_version` 引入了 atomic write（tmp+rename 模式），
但经过代码审查，仍存在以下三类真实问题：

1. **`visualize.py` 中的非原子写入**：所有 `.mmd` 图文件输出（`unified_graph.mmd`、
   `code_graph.mmd`、`call_graph.mmd`、`focus_*.mmd`）均使用裸 `write_text()`，
   无 tmp+rename 保护。若进程在写入途中被中断（crash、Ctrl-C），将产生残缺文件，
   后续 CI/可视化工具读到残缺 Mermaid 会静默失败。

2. **`deployer.py` 中 `read_text()` 缺少 `encoding='utf-8'`**：三处调用使用平台默认编码，
   在 Windows（默认 cp1252/GBK）环境下读取含非 ASCII 字符的 JSON/Markdown 文件时会抛出
   `UnicodeDecodeError` 或静默乱码，导致 deploy 失败。

3. **`visualize.py` 中 Python 源文件缺少单文件大小保护**：`_build_class_graph`、
   `PythonAnalyzer.extract_imports`、`PythonAnalyzer.extract_functions_and_calls` 对每个
   `.py` 文件执行 `read_text()` + `ast.parse()`，无单文件字节数上限。
   若仓库包含自动生成的超大 `.py` 文件（如 proto 生成代码、数据嵌入文件），
   将触发 OOM 或长时间阻塞，超出 `MAX_SCAN_FILES=500` 的保护意图。

注：`scaffold.py` 中的 `write_text()` 调用均为新建文件（已有 `if p.exists(): return` 防重覆盖），
不涉及覆盖现有内容，crash 风险极低，不列入本次修复范围。

## Requirements

### R1: visualize.py .mmd 输出改用 atomic write (MUST)

`visualize.py` 中所有将 `.mmd` 内容写入磁盘的位置，MUST 替换为 tmp+rename 模式（`path.with_suffix('.tmp')` + `os.replace()`），与 `board.py` 保持一致。

受影响的写入点：
- `_visualize_unified()`：`dest.write_text(graph.to_mermaid(), ...)` → `unified_graph.mmd`
- `_visualize_unified()` split 分支：`dest.write_text(content, ...)` → 各 split 图文件
- `visualize()` 普通模式：`dest.write_text(content, ...)` → `code_graph.mmd` / `call_graph.mmd` 等
- `export_focus_graphs()`：`dest.write_text(sub.to_mermaid(), ...)` → `focus_*.mmd` 文件

当前代码（`visualize.py` line 893）：
```python
dest.write_text(graph.to_mermaid(), encoding='utf-8')
```

修复后：
```python
tmp = dest.with_suffix('.tmp')
tmp.write_text(graph.to_mermaid(), encoding='utf-8')
os.replace(tmp, dest)
```

### R2: deployer.py read_text() 补全 encoding='utf-8' (MUST)

`deployer.py` 中三处 `read_text()` 调用缺少 `encoding='utf-8'` 参数，MUST 补全：

**位置一** — `_read_opencode_providers()`（line 894）：
```python
# 当前（缺少 encoding）
data = json.loads(json_path.read_text())
# 修复后
data = json.loads(json_path.read_text(encoding='utf-8'))
```

**位置二** — `_migrate_claude_local_md()`（line 1316）：
```python
# 当前（缺少 encoding）
existing_content = claude_md_path.read_text()
# 修复后
existing_content = claude_md_path.read_text(encoding='utf-8')
```

**位置三** — `_read_codex_config()`（line 1639）：
```python
# 当前（缺少 encoding）
config = json.loads(json_path.read_text())
# 修复后
config = json.loads(json_path.read_text(encoding='utf-8'))
```

### R3: visualize.py Python 文件扫描添加单文件大小保护 (MUST)

`visualize.py` 中对 Python 源文件执行 `read_text()` + `ast.parse()` 前，MUST 检查文件字节数，
若超过 `MAX_FILE_BYTES`（默认 1 MB = 1_048_576 字节）则跳过该文件并发出警告，防止 OOM。

```python
MAX_FILE_BYTES = 1_048_576  # 1 MB per-file ceiling
```

受影响的调用位置（均在循环内）：
- `PythonAnalyzer.extract_imports()` — `file_path.read_text(encoding='utf-8')`
- `PythonAnalyzer.extract_functions_and_calls()` — `file_path.read_text(encoding='utf-8')`
- `_build_class_graph()` — `p.read_text(encoding='utf-8')`

当前代码（`PythonAnalyzer.extract_imports`）：
```python
tree = ast.parse(file_path.read_text(encoding='utf-8'))
```

修复后：
```python
if file_path.stat().st_size > MAX_FILE_BYTES:
    import sys as _sys
    print(f"⚠️ Skipping large file: {file_path} ({file_path.stat().st_size} bytes)", file=_sys.stderr)
    return []
tree = ast.parse(file_path.read_text(encoding='utf-8'))
```

## Acceptance Criteria

### AC1: .mmd 文件写入中断不产生残缺文件 (R1)

- **Given** `visualize.py` 调用图生成函数，目标 `dest` 为已存在的 `.mmd` 文件
- **When** 进程在写入完成前被中断（模拟：测试断言 tmp 文件被清理，dest 保持完整）
- **Then** 原始 `dest` 内容不被破坏；tmp 文件若存在则为中间产物，不影响 dest

### AC2: mmd 输出函数使用 tmp+rename 模式 (R1)

- **Given** 调用 `visualize()`、`_visualize_unified()`、或 `export_focus_graphs()`
- **When** 目标目录存在且可写
- **Then** 写入过程先创建 `<dest>.tmp`，再通过 `os.replace()` 原子替换为最终文件名；不直接调用 `dest.write_text()`

### AC3: deployer 在 Windows 兼容环境下正确读取含非 ASCII 字符的文件 (R2)

- **Given** `deployer.py` 读取一个含 UTF-8 非 ASCII 字符（如中文注释）的 JSON 或 Markdown 文件
- **When** 运行时平台默认编码不是 `utf-8`（模拟：测试使用 `mock` 覆盖默认编码）
- **Then** 三处 `read_text()` 调用均指定 `encoding='utf-8'`，文件内容被正确解码，不抛出 `UnicodeDecodeError`

### AC4: 超大 Python 文件在扫描时被跳过并记录警告 (R3)

- **Given** 项目目录包含一个 > 1 MB 的 `.py` 文件
- **When** 调用 `visualize --mode file`、`--mode class` 或 `--mode call`
- **Then** 该文件被跳过（不被 `ast.parse()` 处理），stderr 输出包含 `⚠️ Skipping large file:` 警告；其余文件正常扫描

### AC5: MAX_FILE_BYTES 常量定义在 visualize.py 顶部 (R3)

- **Given** 阅读 `visualize.py` 源码
- **When** 搜索 `MAX_FILE_BYTES`
- **Then** 常量定义与 `MAX_SCAN_FILES`、`MAX_WORKFLOW_NODES` 在同一位置（文件顶部常量区），值为 `1_048_576`

## Target Call Chain

```
visualize --mode file/class/call
  └─ visualize()
       ├─ _build_file_graph() / _build_class_graph() / _build_call_graph()
       │    └─ PythonAnalyzer.extract_imports() / extract_functions_and_calls()
       │         └─ file_path.read_text()  ← R3: 需要大小保护
       └─ dest.write_text()               ← R1: 需要改为 atomic write

visualize --mode unified
  └─ _visualize_unified()
       └─ dest.write_text(graph.to_mermaid())  ← R1

export_focus_graphs(graph, output_dir)
  └─ dest.write_text(sub.to_mermaid())         ← R1

deployer.py
  ├─ _read_opencode_providers()
  │    └─ json_path.read_text()       ← R2: 缺少 encoding
  ├─ _migrate_claude_local_md()
  │    └─ claude_md_path.read_text()  ← R2: 缺少 encoding
  └─ _read_codex_config()
       └─ json_path.read_text()       ← R2: 缺少 encoding
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/visualize.py` | 在顶部常量区添加 `MAX_FILE_BYTES = 1_048_576` | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | `PythonAnalyzer.extract_imports()` 添加大小检查 | Step 1 | Low |
| 3 | `src/pactkit/skills/visualize.py` | `PythonAnalyzer.extract_functions_and_calls()` 添加大小检查 | Step 1 | Low |
| 4 | `src/pactkit/skills/visualize.py` | `_build_class_graph()` 循环内添加大小检查 | Step 1 | Low |
| 5 | `src/pactkit/skills/visualize.py` | `visualize()` 普通模式写入改为 tmp+rename | None | Low |
| 6 | `src/pactkit/skills/visualize.py` | `_visualize_unified()` 写入（unified + split）改为 tmp+rename | None | Low |
| 7 | `src/pactkit/skills/visualize.py` | `export_focus_graphs()` 写入改为 tmp+rename | None | Low |
| 8 | `src/pactkit/generators/deployer.py` | 三处 `read_text()` 补全 `encoding='utf-8'` | None | Low |
| 9 | `tests/unit/` | 为 R1/R2/R3 编写单元测试（先 RED，后 GREEN） | Steps 1-8 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 路径遍历 | No | 所有写入路径均由内部逻辑构造，不接受用户路径输入 |
| SEC-2 命令注入 | No | 无 shell 命令执行，`os.replace()` 为系统调用 |
| SEC-3 敏感信息泄露 | No | 不读写凭证或密钥，仅处理代码图和配置文件 |
| SEC-4 权限提升 | No | 不修改文件权限（visualize 的 `.mmd` 文件均为普通用户文件） |
| SEC-5 DoS（大文件 OOM） | Yes | R3 的 `MAX_FILE_BYTES` 正是 DoS 防护——防止恶意/异常大文件耗尽内存 |
| SEC-6 Race condition（TOCTOU） | Partial | atomic write 通过 tmp+rename 消除了写中断风险；读-然后-写在单线程脚本场景下可接受 |
| SEC-7 编码攻击 | Yes | R2 的 `encoding='utf-8'` 显式声明，防止平台默认编码差异导致的静默数据损坏 |
| SEC-8 Tmp 文件残留 | Yes | atomic write 产生 `.tmp` 中间文件；若进程被 kill -9 则 tmp 文件残留，需在文档中说明清理方式（超出本次范围） |

## Out of Scope

- `scaffold.py` 中的 `write_text()` 调用——均为新建文件，已有存在性保护（`if p.exists(): return`），crash 风险极低
- `spec_linter.py` 中的 `read_text()`——只读操作，无写入风险
- `board.py` 中的写入——已在 STORY-slim-052 中完成 atomic write 修复
- `atomic_write` utility 本身的扩展（如添加文件大小参数）
- `.tmp` 残留文件的自动清理机制（可作独立 story）
- Windows 平台的实际 CI 测试（仅通过 `mock` 验证 encoding 参数）
