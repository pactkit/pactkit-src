# STORY-050: Doc-Only Regression Shortcut — Skip Full Test Suite for Non-Source Changes

| Field     | Value |
|-----------|-------|
| ID        | STORY-050 |
| Status    | Draft |
| Priority  | Medium |
| Release   | 1.4.0 |
| Author    | System Architect |
| Source    | User observation: STORY-049 changed 0 source files but full regression (1696 tests) still ran |

## Background

PactKit 的 PDCA 流程在 Done (Phase 2.5) 和 Act (Phase 3 Step 3) 中都包含 regression gate。当前的决策链有两个问题：

1. **Fast-Suite Shortcut 过于激进**：Done Phase 2.5 Step 1.5 的逻辑是"如果上次测试 < 30 秒，直接跑全量"。这对小项目合理，但掩盖了更基本的判断——**0 个源文件变更时 regression 不需要跑**。
2. **Decision Tree 缺少 Doc-Only 短路**：Step 2 的条件检查 "changed source files ≤ 3"，但没有处理 "changed source files = 0" 的场景。

以 STORY-049 为例，变更文件全部是 `.md`、`.yml` 和 `docs/` 下的文件，零个 `src/*.py` 被修改，但仍然执行了 1696 个测试。对于大型项目（测试套件 10+ 分钟），这种浪费是不可接受的。

### Target Call Chain

```
Done Phase 2.5:
  Step 1: Impact Analysis (git diff)
  → [NEW] Step 1.3: Doc-Only Shortcut ← 插入点
  → Step 1.5: Fast-Suite Shortcut
  → Step 2: Decision Tree
  → Step 3: Gate

Act Phase 3:
  Step 3: Regression Check
  → [NEW] Doc-Only detection ← 插入点
  → Scope decision (fan-in check)
```

修改目标文件：`src/pactkit/prompts/commands.py` (Done 和 Act 的 prompt 字符串)

## Requirements

### R1: Done 命令 Doc-Only Shortcut (MUST)

在 Done Phase 2.5 的 Step 1 (Impact Analysis) 和 Step 1.5 (Fast-Suite Shortcut) 之间插入 **Step 1.3: Doc-Only Shortcut**：

- MUST 使用 `LANG_PROFILES[stack].file_ext` 来判断源文件扩展名（例如 Python 的 `.py`）
- MUST 检查 `git diff --name-only` 和 `git status` 中的 untracked 文件
- MUST 将源文件定义为：扩展名匹配 `file_ext` 且路径在源码目录下（`src/`、`lib/`、项目根的 `.py` 等，但排除 `tests/`、`docs/`、`.github/`）
- MUST 当检测到零个源文件变更时：
  - 如果有**新增测试文件**（本 Story 创建的）：仅运行这些新测试文件
  - 如果**无任何测试文件变更**：完全跳过 regression
- MUST 输出决策日志：`"Regression: SKIP — doc-only change, no source files modified"` 或 `"Regression: STORY-ONLY — {N} new test files, no source changes"`

### R2: Act 命令 Doc-Only Detection (MUST)

在 Act Phase 3 Step 3 (Regression Check) 的 scope decision 之前增加 doc-only 检测：

- MUST 使用与 R1 相同的源文件判断逻辑
- MUST 当零个源文件变更时，仅运行本 Story 新建的测试文件（Act Phase 2 创建的）
- SHOULD 输出决策日志

### R3: LANG_PROFILES 增加 source_dirs (SHOULD)

在 `LANG_PROFILES` 中为每个语言栈添加 `source_dirs` 字段，明确定义源码目录：

- Python: `['src/']`
- Node: `['src/', 'lib/', 'app/', 'pages/']`
- Go: project root (all `.go` files except `*_test.go`)
- Java: `['src/main/java/']`

这样 Doc-Only 检测可以精确判断"源码文件"而不是仅靠扩展名。

### R4: 决策日志兼容 (SHOULD)

Step 2.3 (Decision Logging) SHOULD 增加对 Doc-Only 和 Story-Only 两种新决策类型的格式支持。

## Acceptance Criteria

### AC1: Doc-Only 变更跳过 regression
**Given** 一个 Story 只修改了 `.md`、`.yml`、`docs/` 下的文件
**When** 执行 `/project-done`
**Then** regression gate 输出 `"Regression: SKIP — doc-only change, no source files modified"`
**And** 不执行 `pytest`

### AC2: Doc + 新测试文件只运行新测试
**Given** 一个 Story 修改了 `.md` 文件并新建了 `tests/unit/test_story*.py`
**When** 执行 `/project-done`
**Then** regression gate 输出 `"Regression: STORY-ONLY — {N} new test files, no source changes"`
**And** 仅运行新建的测试文件，不运行全量套件

### AC3: 有源文件变更时行为不变
**Given** 一个 Story 修改了 `src/pactkit/config.py`
**When** 执行 `/project-done`
**Then** regression 决策链正常进入 Step 1.5 / Step 2
**And** 行为与当前完全一致（无回归）

### AC4: Act 命令 regression 同样跳过
**Given** 一个 Doc-Only Story 在 Act Phase 3 TDD loop GREEN 后
**When** 执行 Regression Check
**Then** 仅运行本 Story 的新测试文件

### AC5: LANG_PROFILES 包含 source_dirs
**Given** `LANG_PROFILES` 定义
**When** 读取 Python profile
**Then** 包含 `source_dirs: ['src/']`

## Out of Scope

- 修改 Fast-Suite Shortcut 的 30 秒阈值
- 修改 Decision Tree 的其他条件（fan-in、code_graph 等）
- 运行时 Python 代码变更（这是纯 prompt 变更）
