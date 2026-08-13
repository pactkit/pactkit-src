# STORY-slim-138: pactkit commit-gate: pre-commit test gate with skip transparency

| Field | Value |
|-------|-------|
| ID | STORY-slim-138 |
| Status | Done |
| Priority | P1 |
| Release | 2.17.0 |

## Background

最初门禁分析（2026-08-13）的门禁 1：PactKit 有 `test-map`（源文件↔测试映射）、`regression`（变更分级）、`coverage-gate` 等 30+ 子命令，但全是"谁记得谁跑"的被动工具——commit 动作发生前没有任何机械拦截点。历史事故（外部项目 P0-1：54 个测试红灯被标 Done 并提交）的直接原因就是提交路径上无 code enforce。

第二个病灶是 **skip≠pass 语义缺失**：integration 测试在依赖（如 PG）不可达时 skipif 跳过，"unit 绿 + integration 全 skip"被当成"全绿"报告。门禁必须区分"跳过"和"通过"，skip 超阈值要显式报告。

现状实锤：本仓库零 git hook（无 pre-commit/lefthook/husky），PactKit 不部署也不管理 `.claude/settings.json`（`audit.py` 只读取它做 H5 评分），项目只有 `settings.local.json`——hook 部署机制是从零建设。

两个拦截通道：Claude Code **PreToolUse hook**（拦 agent 发起的 `git commit`，读 stdin JSON，exit 2=block）与 **git pre-commit hook**（拦人肉提交，exit 1=block），共用同一判定逻辑。

## Requirements

### R1: `pactkit commit-gate` 判定逻辑 (MUST)

新增 `src/pactkit/commit_gate.py`。流程：取变更文件（staged + working tree）→ 复用 `regression.classify_changes()` 分级 → SKIP 直接放行；FULL 跑全量 unit；IMPACT 用 `test_mapper.map_to_tests()` 选最小测试集，映射为空回退全量 unit。在 main/master/develop 分支上直接 commit 时 MUST 跑全量 unit（无视 IMPACT 分级）。测试红 → exit 1 并输出失败摘要。

### R2: skip≠pass 透明化 (MUST)

pytest 以 `-rs` 运行，解析汇总行的 skipped 计数与原因。退出码语义 MUST 为：有 fail → 1；全 pass 且 skip 未超阈值 → 0；全 pass 但 skip 超过阈值 → 0 且输出显式 WARN（列出被跳过的测试与原因）。门禁输出 MUST 分别报告 passed/failed/skipped 三个数，禁止只报"绿/红"。阈值定义为模块级常量（默认 0，即任何 skip 都要显式列出），后续可迁入 pactkit.yaml。

### R3: PreToolUse hook 模式 (MUST)

`pactkit commit-gate --hook` 从 stdin 读取 Claude Code hook JSON，仅在 `tool_input.command` 含 `git commit` 时执行门禁，其余命令立即 exit 0。Block 时按 Claude Code 契约 exit 2 并将原因写 stderr。**自锁防护**：门禁自身异常（pytest 不存在、解析失败等）MUST exit 0 + 大声 WARN，不得 block——否则修门禁本身的 commit 也会被拦。

### R4: hook 部署机制 (MUST)

`pactkit init` / `pactkit update` 将 PreToolUse hook 条目**合并**写入项目 `.claude/settings.json`：保留用户已有配置（含 settings.local.json 优先级语义），重复部署幂等（识别并更新 pactkit 自己的条目，不重复追加）。可选 `--git-hook` 标志写 `.git/hooks/pre-commit`（薄包装，调用同一 CLI）。`enterprise.no_git: true` 时跳过全部 hook 安装。

### R5: 不碰历史失败 (MUST NOT)

门禁发现测试失败时 MUST NOT 尝试自动修复或修改任何测试/源码——只报告（哪些测试红、疑似关联的变更文件），行为与 project-done Phase 2.5 Step 3 Gate 一致。门禁 MUST NOT 修改用户的 git 提交内容或 message。

## Acceptance Criteria

### AC1: 红灯拦截 (R1)

- **Given** 变更了某源文件且其映射测试失败
- **When** 执行 `pactkit commit-gate`
- **Then** 输出失败测试摘要与关联变更文件；退出码为 1

### AC2: IMPACT 最小测试集 (R1)

- **Given** 变更 1 个源文件，`regression` 判定 IMPACT，`test-map` 映射到 2 个测试文件且全部通过
- **When** 执行 `pactkit commit-gate`
- **Then** 仅运行这 2 个测试文件（输出可见所跑集合）；退出码为 0

### AC3: skip 透明化 (R2)

- **Given** 测试结果为 10 passed / 0 failed / 3 skipped（PG 不可达导致的 skipif）
- **When** 执行 `pactkit commit-gate`
- **Then** 输出显式列出 3 个 skipped 测试及原因，并打印 WARN（非"全绿"表述）；退出码为 0

### AC4: hook 模式只拦 git commit (R3)

- **Given** PreToolUse hook JSON（分别为 `git commit -m "x"` 与 `git status` 两种 command）
- **When** 执行 `pactkit commit-gate --hook` 传入对应 stdin
- **Then** commit 场景执行门禁（红则 exit 2 + stderr 原因）；status 场景立即 exit 0 且不跑任何测试

### AC5: 门禁自锁防护 (R3)

- **Given** 环境中 pytest 不可用
- **When** 执行 `pactkit commit-gate --hook` 处理 git commit
- **Then** exit 0 + 输出"门禁自身异常，已放行"的显式 WARN（不 block）

### AC6: hook 幂等部署 (R4)

- **Given** 项目 `.claude/settings.json` 已含用户自定义配置
- **When** 连续两次执行 `pactkit update`
- **Then** 用户配置原样保留；pactkit hook 条目存在且仅一条；`enterprise.no_git: true` 时不写入任何 hook

### AC7: 主干分支全量 (R1)

- **Given** 当前在 main 分支，变更文件映射仅 1 个测试文件
- **When** 执行 `pactkit commit-gate`
- **Then** 无视映射，运行全量 unit 套件

### AC8: 测试套件全通过 (R1-R5)

- **Given** 全部修改完成
- **When** 运行 `.venv/bin/pytest tests/ -v`
- **Then** 所有测试通过，无新失败（pytest 调用以 mock/fixture 覆盖，单测不依赖真实 PG）

## Target Call Chain

```
Claude Code PreToolUse (Bash: git commit) ──→ pactkit commit-gate --hook [stdin JSON 判定]
人肉 git commit (.git/hooks/pre-commit) ────→ pactkit commit-gate
                                                  ↓ 共用判定
                                    commit_gate.run(project_root)
                                      ├─ git diff --name-only (staged+worktree)
                                      ├─ regression.classify_changes() → SKIP/FULL/IMPACT
                                      ├─ test_mapper.map_to_tests() (IMPACT 时)
                                      ├─ 分支检查: main/master/develop → 全量 unit
                                      └─ pytest -rs → 解析 passed/failed/skipped → exit 0/1/2
pactkit init/update → settings.json hook 条目合并写入（幂等）
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/commit_gate.py` | 新模块：变更收集→regression 分级→test-map→pytest -rs 执行与解析→退出码 | None | High（跑在每次 commit 路径，性能和误判都敏感） |
| 2 | `src/pactkit/commit_gate.py` | --hook 模式：stdin JSON 解析 + git commit 判定 + 自锁防护 | Step 1 | Medium |
| 3 | `src/pactkit/cli.py` | 注册 commit-gate 子命令 | Step 1-2 | Low |
| 4 | `src/pactkit/generators/deployer.py` | settings.json hook 合并写入 + --git-hook 可选安装 | Step 3 | Medium（用户配置合并是细致活） |
| 5 | `tests/unit/test_commit_gate.py` | AC1-AC7 fixture 单测（mock pytest/git） | Step 1-3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | hook 模式解析 stdin JSON（agent 可控输入）——command 字段只做子串匹配，绝不经 shell 执行；subprocess 调用全部列表参数、禁 shell=True |
| SEC-2 | Yes | git diff 输出的文件名含空格/特殊字符时须安全传入 pytest 参数列表 |
| SEC-3 | N/A | 无数据库相关（sec-scope 命中为关键词误报） |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无认证/会话逻辑（sec-scope 命中为关键词误报） |
| SEC-6 | N/A | 无 API/路由变更 |
| SEC-7 | Yes | 自锁防护（R3）：门禁自身一切异常路径必须捕获 → exit 0 + WARN，禁止未捕获异常导致 hook 行为未定义 |
| SEC-8 | N/A | 无新第三方依赖（复用 regression/test_mapper 与 subprocess） |

## Out of Scope

- 门禁阈值的 pactkit.yaml 配置化（skip 阈值等本期为模块级常量，待 STORY-slim-135 schema 落地后迁入）
- pre-push hook / CI 端门禁（本故事只管 commit 时刻；CI 全量门禁由项目自身 workflow 负责）
- 非 Python 栈的测试执行策略（test-map/pytest 语义本期以 python 栈为主；node/go/java 栈走 LANG_PROFILES test_runner，列为 SHOULD 兼容）
- 自动修复红灯测试（R5 明确禁止——与 project-done Gate 行为一致）
- 拦截 `git commit --no-verify` 的人肉绕过（git 层无法拦截，靠 done-verify 的归档核验兜底）
