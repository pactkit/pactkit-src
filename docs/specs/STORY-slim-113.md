# STORY-slim-113: pactkit interface-summary CLI — Code Enforce 接口摘要

| Field | Value |
|-------|-------|
| ID | STORY-slim-113 |
| Status | Done |
| Priority | P1 |
| Release | 2.13.0 |

## Background

### 问题

STORY-slim-108 引入了"接口摘要"概念——Act Phase 1 对 trace 发现的非目标模块只读签名+docstring。但当前实现**完全依赖 Prompt 指导**（pactkit-trace SKILL.md 的 "Layered Output" 表格 + Act Phase 1.2 的一句 "Layered Loading"），AI 实际执行时仍然直接 Read 完整文件，因为：

1. 没有工具约束——AI 调用 Read 工具时没有 `--summary-only` 限制
2. 一句文字指导不足以改变 AI 的默认行为
3. 违反了 PactKit 自己的 "Code Enforces, Prompt Instructs" 原则（架构原则 §10）

### 方案

新增 `pactkit interface-summary <file>` CLI 命令：
- 基于现有 `python_analyzer.py` 的 AST 能力（已有 `extract_classes`、`extract_functions_and_calls`）
- 输出经代码裁剪的接口摘要，AI 拿到的物理上就是精简内容
- Act Phase 1 改为**显式步骤**：对非目标模块调用此 CLI 而非 Read

### 为什么不用 hook

用户明确要求不使用 hook。本方案通过 CLI 输出 + playbook 步骤变更来实现 Code Enforce，无需 harness 层面的文件拦截。

## Requirements

### R1: 新增 `pactkit interface-summary` CLI 命令 (MUST)

新增子命令接受一个或多个文件路径，输出接口摘要：

```
pactkit interface-summary src/pactkit/generators/deployer.py
```

输出格式（per file）：
```
# deployer.py — Interface Summary

class ClassicDeployer(BaseDeployer):
    """Deploy PactKit to ~/.claude/ (Classic format)."""
    +deploy(target, config) -> DeployResult
    +_deploy_rules(claude_root, enabled_rules) -> None
    +_deploy_skills(claude_root, enabled_skills) -> None
    -_cleanup_legacy(target) -> None

def atomic_write(path: Path, content: str) -> None:
    """Write content atomically via tempfile + rename."""

def _render_prompt(template: str, profile: FormatProfile) -> str:
    """Replace placeholders with profile-specific values."""
```

提取规则：
- **Class**: class name + bases + docstring 第一行 + public/private methods with signature
- **Function**: def name + params with type hints + return type + docstring 第一行
- **Skip**: 函数体、局部变量、内部逻辑
- **Constants/Enums**: 顶层 `UPPER_CASE` 赋值保留名称和类型

### R2: 多语言支持通过 LANG_PROFILES 分派 (SHOULD)

使用已有的 `LANG_PROFILES` + analyzer 架构：
- Python: `ast` 模块提取（已有基础设施）
- TypeScript: `tree_sitter_typescript` 提取 exported declarations
- Go: `tree_sitter_go` 提取 exported (大写) func/struct

初始版本 MUST 支持 Python。TS/Go 为 SHOULD。

### R3: Act Phase 1 增加显式步骤 (MUST)

修改 `project-act/SKILL.md` Phase 1.2，从当前的一句指导：
> "Layered Loading: For non-target modules discovered by trace, read interface summary..."

改为显式步骤：
```
2b. **Interface Summary** (for non-target modules):
    - For each module discovered by trace that is NOT the modification target:
      `pactkit interface-summary <file>`
    - Only escalate to `Read <file>` when you confirm the module needs modification.
```

### R4: pactkit-trace SKILL.md 更新输出格式指引 (MUST)

修改 pactkit-trace SKILL.md Phase 3 "Layered Output" 部分，从"建议 AI 自行精简"改为"调用 CLI 获取"：

> For related (non-target) modules, run `pactkit interface-summary <file>` instead of reading full source.

### R5: 不修改 Read 工具行为 (MUST NOT)

本 story 不修改 Claude Code harness 的 Read 工具、不添加 hook、不拦截文件访问。通过提供更好的替代工具来引导行为，而非限制现有工具。

## Acceptance Criteria

### AC1: CLI 输出接口摘要 (R1)

- **Given** 一个 Python 文件 `src/pactkit/generators/deployer.py`（含多个 class 和函数）
- **When** 运行 `pactkit interface-summary src/pactkit/generators/deployer.py`
- **Then** 输出包含所有 class（带 bases 和 methods 签名）和顶层函数（带参数和返回类型），不包含函数体

### AC2: 输出行数显著小于原文件 (R1)

- **Given** `deployer.py` 约 600+ 行
- **When** 运行 `pactkit interface-summary` 对其生成摘要
- **Then** 输出行数 ≤ 原文件行数的 25%（即 ≤ 150 行）

### AC3: 多文件支持 (R1)

- **Given** 两个 Python 文件 A.py 和 B.py
- **When** 运行 `pactkit interface-summary A.py B.py`
- **Then** 输出两个文件的摘要，以 `# filename — Interface Summary` 分隔

### AC4: Act Phase 1 步骤可验证 (R3)

- **Given** 修改后的 project-act SKILL.md
- **When** 读取 Phase 1 内容
- **Then** 存在显式编号步骤 "2b" 包含 `pactkit interface-summary` 命令

### AC5: 非 Python 文件 graceful fallback (R2)

- **Given** 一个 .go 文件但 tree-sitter-go 未安装
- **When** 运行 `pactkit interface-summary file.go`
- **Then** 输出警告 "Unsupported or unavailable analyzer for .go" 并退出 0（不阻塞）

## Target Call Chain

```
pactkit interface-summary <files>
  → cli.py: main() → parse args → _interface_summary_command(args)
  → interface_summary.py: generate_summary(file_paths)
    → detect language from extension
    → LANG_PROFILES dispatch → python_analyzer / ts_analyzer / go_analyzer
    → For Python:
      → ast.parse(source)
      → Extract: class defs (name, bases, docstring, method signatures)
      → Extract: top-level functions (name, params, return type, docstring)
      → Extract: top-level constants (UPPER_CASE assignments)
    → Format output as structured text
    → Print to stdout
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/interface_summary.py` | 新建：接口摘要提取逻辑，复用 python_analyzer AST 能力 | None | Medium |
| 2 | `src/pactkit/cli.py` | 注册 `interface-summary` 子命令 | Step 1 | Low |
| 3 | `~/.claude/skills/project-act/SKILL.md` (source: `src/pactkit/prompts/commands.py`) | Phase 1.2 → 1.2a + 1.2b 显式步骤 | Step 1-2 | Low |
| 4 | `~/.claude/skills/pactkit-trace/SKILL.md` (source: `src/pactkit/prompts/skills.py`) | Phase 3 Layered Output 改为 CLI 调用指引 | Step 1-2 | Low |
| 5 | `tests/unit/test_interface_summary.py` | 新建：单元测试覆盖 Python 文件摘要输出 | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | 无秘钥变更 |
| SEC-2 | No | 输入为本地文件路径，已有 file_path.stat() 大小检查 |
| SEC-3 | No | 无数据库 |
| SEC-4 | No | 无 UI |
| SEC-5 | No | 无认证 |
| SEC-6 | No | 无接口暴露 |
| SEC-7 | No | CLI 输出，无敏感信息 |
| SEC-8 | No | 无新依赖（复用现有 ast + tree_sitter） |

## Out of Scope

- 修改 Claude Code Read 工具行为
- Hook 机制
- 自动拦截 AI 的 Read 调用
- Java analyzer 支持（已有但不在本 story 优先级内）
- `pactkit trace` CLI 命令（本 story 只做 interface-summary，trace 仍是 skill）
