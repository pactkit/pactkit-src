# STORY-slim-056: E2E test coverage expansion: CLI subcommand coverage, error path testing, integration scenarios

| Field | Value |
|-------|-------|
| ID | STORY-slim-056 |
| Status | Done |
| Priority | P2 |
| Release | 2.5.0 |

## Background

PactKit CLI 共有 25 个子命令，但 E2E 测试（`tests/e2e/cli/test_cli_e2e.py`）仅覆盖 4 个：`version`、`init`（含 classic/plugin/marketplace）、`update`、`spec-lint`。**覆盖率仅 16%**。

**当前 E2E 覆盖状态**：

| 状态 | 子命令 |
|------|--------|
| 已覆盖 (4) | `version`, `init`, `update`, `spec-lint` |
| 未覆盖 (21) | `upgrade`, `schema`, `guard`, `next-id`, `clean`, `regression`, `context`, `sec-scope`, `lint-context`, `lint-lessons`, `lint-testcase`, `visualize`, `doctor`, `backfill-release`, `issue-sync`, `test-map`, `lint`, `lesson-append`, `invariants-refresh`, `coverage-gate`, `spec-status` |

**为什么需要扩展**：
- 单元测试覆盖函数级行为，但 CLI 参数解析、子进程调用、文件系统交互的集成路径未被验证
- 已有的 4 个 E2E 测试发现了单元测试遗漏的 bug（如 init 格式部署完整性）
- 外部用户通过 CLI 使用 PactKit，CLI 是唯一的用户界面——E2E 测试是用户体验的最终验证

**优先级分层**：本 story 按风险和使用频率将 21 个未覆盖子命令分为 3 层，优先覆盖高频和 PDCA 关键路径。

## Requirements

### R1: High-frequency CLI subcommand E2E coverage (MUST)

覆盖 PDCA 工作流中每次都会调用的高频子命令（共 8 个）：

| 子命令 | 调用场景 | 测试重点 |
|--------|---------|---------|
| `guard` | Plan Phase 0.5 | 有/无 init markers 两种场景 |
| `next-id` | Plan Phase 3.1 | 正确递增、无 specs 时的初始值 |
| `clean` | Act Phase 4, Done Phase 2 | 清理 temp artifacts，不删源码 |
| `regression` | Act Phase 3, Done Phase 2.5 | SKIP/FULL/IMPACT 三种分类 |
| `context` | Done Phase 4.5 | 输出包含所有 canonical sections |
| `visualize` | Act Phase 1, Done Phase 2 | file/class/call 三种模式正常退出 |
| `lint` | Act Phase 3, Done Phase 2.7 | 有/无 lint_command 两种场景 |
| `spec-status` | Done Phase 3 | Draft→Done 状态更新 |

**测试方法**：每个子命令至少 2 个 E2E 测试（正常路径 + 错误路径），使用 `subprocess.run` 调用 CLI，验证退出码和 stdout/stderr。

### R2: Validation and linting subcommand E2E coverage (SHOULD)

覆盖文档验证类子命令（共 7 个）：

| 子命令 | 测试重点 |
|--------|---------|
| `lint-context` | 合法/不合法 context.md |
| `lint-lessons` | 合法/不合法 lessons.md |
| `lint-testcase` | 合法/不合法 test_case.md |
| `sec-scope` | 有/无变更文件 |
| `schema` | 输出包含已知 schema 名称 |
| `doctor` | 健康/不健康项目 |
| `test-map` | 有/无映射的源文件 |

**测试方法**：同 R1，每个子命令至少 1 个正常路径测试。

### R3: CLI error path and edge case coverage (MUST)

验证 CLI 的错误处理和边界情况：

1. **未知子命令**：`pactkit foobar` → 非零退出码 + 错误提示
2. **缺失必需参数**：`pactkit spec-status`（无文件参数）→ 错误提示
3. **不存在的文件路径**：`pactkit spec-lint /nonexistent.md` → 优雅失败
4. **无 init 项目**：在空目录运行 `pactkit guard` → 正确报告缺失 markers
5. **Unicode 项目路径**：在含中文的目录名下运行 `pactkit init` → 正常完成
6. **`--help` 一致性**：所有 25 个子命令的 `--help` 返回退出码 0

**测试方法**：每个场景 1 个测试用例，重点验证退出码和错误信息不含 traceback。

### R4: Remaining low-frequency subcommand coverage (MAY)

覆盖剩余 6 个低频子命令：

| 子命令 | 测试重点 |
|--------|---------|
| `upgrade` | legacy 迁移场景 |
| `backfill-release` | TBD→version 替换 |
| `issue-sync` | STORY 跳过、BUG/HOTFIX 处理 |
| `lesson-append` | 去重检查、specificity 检查 |
| `invariants-refresh` | 测试计数更新 |
| `coverage-gate` | 阈值判断（PASS/WARN/BLOCK） |

**测试方法**：每个子命令 1 个 happy-path 测试。

## Acceptance Criteria

### AC1: High-frequency subcommands have E2E tests (R1)

- **Given** 一个通过 `pactkit init` 初始化的临时项目目录
- **When** 依次运行 `guard`, `next-id`, `clean`, `regression`, `context`, `visualize`, `lint`, `spec-status` 子命令
- **Then** 每个子命令的正常路径返回退出码 0，错误路径返回非零退出码，且 stderr 不含 Python traceback

### AC2: Validation subcommands have E2E tests (R2)

- **Given** 一个含有效和无效文档文件的临时项目目录
- **When** 运行 `lint-context`, `lint-lessons`, `lint-testcase`, `sec-scope`, `schema`, `doctor`, `test-map`
- **Then** 有效文档返回退出码 0，无效文档返回非零退出码或包含警告信息

### AC3: Error paths produce graceful output (R3)

- **Given** 各种错误输入场景（未知命令、缺失参数、不存在文件、空目录、Unicode 路径）
- **When** 运行对应的 CLI 命令
- **Then** 所有场景返回非零退出码（`--help` 除外），stderr 包含用户可读的错误信息，不含 `Traceback (most recent call last)`

### AC4: All 25 subcommands have at least one E2E test (R1+R2+R3+R4)

- **Given** 完成 R1-R4 的所有测试编写
- **When** 统计 `tests/e2e/cli/test_cli_e2e.py` 中的测试方法数
- **Then** 至少 50 个测试方法，覆盖全部 25 个子命令

## Target Call Chain

```
tests/e2e/cli/test_cli_e2e.py
  → subprocess.run([".venv/bin/pactkit", "<subcommand>", ...])
    → src/pactkit/cli.py → click.group() dispatch
      → 各子命令实现函数
```

E2E 测试不涉及内部调用链跟踪——仅验证 CLI 入口到退出码的黑盒行为。

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/e2e/cli/test_cli_e2e.py` | 添加 `TestGuardCommand`, `TestNextIdCommand`, `TestCleanCommand` 测试类 | None | Low |
| 2 | `tests/e2e/cli/test_cli_e2e.py` | 添加 `TestRegressionCommand`, `TestContextCommand`, `TestVisualizeCommand` 测试类 | None | Low |
| 3 | `tests/e2e/cli/test_cli_e2e.py` | 添加 `TestLintCommand`, `TestSpecStatusCommand` 测试类 | None | Low |
| 4 | `tests/e2e/cli/test_cli_e2e.py` | 添加 R2 验证类子命令测试（7 个子命令） | None | Low |
| 5 | `tests/e2e/cli/test_cli_e2e.py` | 添加 `TestErrorPaths` 测试类（R3 的 6 个场景） | None | Low |
| 6 | `tests/e2e/cli/test_cli_e2e.py` | 添加 R4 低频子命令测试（6 个子命令） | None | Low |
| 7 | `tests/e2e/cli/test_cli_e2e.py` | 添加 `TestHelpConsistency` — 循环验证所有 25 个子命令的 `--help` | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | 纯测试代码，不处理用户输入 |
| SEC-2 Path Traversal | N/A | 测试在临时目录中运行 |
| SEC-3 Secret Leakage | N/A | 无凭证处理 |
| SEC-4 Command Injection | N/A | subprocess 参数为硬编码列表，非字符串拼接 |
| SEC-5 Dependency | N/A | 无新依赖 |
| SEC-6 Auth/AuthZ | N/A | 无认证逻辑 |
| SEC-7 Data Integrity | N/A | 测试代码不修改生产数据 |
| SEC-8 Logging | N/A | 无日志变更 |

## Out of Scope

- 单元测试补充——本 story 仅关注 E2E（subprocess 级别）测试
- 性能基准测试——不测量子命令执行时间
- 跨平台测试——仅在 macOS/Linux 上验证，Windows 不在范围内
- `init --format opencode` / `init --format codex` 的 E2E 测试——需要对应工具环境
- CI pipeline 集成测试——`issue-sync` 的 GitHub API 调用使用 mock 或 skip
