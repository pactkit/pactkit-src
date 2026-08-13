# STORY-slim-136: pactkit done-verify: mechanical archive honesty gate

| Field | Value |
|-------|-------|
| ID | STORY-slim-136 |
| Status | Done |
| Priority | P1 |
| Release | 2.17.0 |

## Background

PactKit 宪法写明 "Code Enforces, Prompt Instructs"，但 `/project-done` 的归档主路径上目前没有任何 code 在 enforce：playbook 里"跑测试""核验完成状态""归档"全是 prompt 级指令，执行 agent 可以跳过、假跑、勾假账。历史事故（外部项目 P0-1：54 个测试红灯的故事被标 Done；P0-4：test case 文件诚实写了 `RFC open` 而归档勾选完成）都是这一缺失的直接后果。

横向扫描结论：项目已有三个相邻实现——`pactkit-analyze`（prompt-only skill，检查 Spec↔Board↔TestCase 一致性，但由 LLM 执行、纯 advisory、无任何强制力）、`doctor.check_orphaned_specs`（code，但只查 spec 与 board 的存在性）、`spec-lint`（code，只查单文件结构）。没有任何一个做"归档前证据链核验"，且 analyze 的两项检查逻辑需要在 code 层重新实现为可强制执行的判定。

本故事把归档诚实性从"靠 LLM 自觉"变成"代码强制"：新增 `pactkit done-verify` 子命令做机械核验，并把它接进 `/project-done` playbook 作为归档前的强制关卡（退出码非 0 即中止）。

## Requirements

### R1: `pactkit done-verify` 子命令与证据链输出 (MUST)

新增 CLI 子命令 `pactkit done-verify {STORY_ID}`（扁平命名，与 `spec-lint` / `coverage-gate` 一致）。对每项检查输出一行判定：`[PASS|FAIL|WARN] {检查项} — {证据（文件路径:行号 或 缺失说明）}`。退出码：任何 FAIL → 1；仅 WARN/PASS → 0。判定 MUST 全部由 code 完成，不依赖 LLM 阅读。

### R2: R 项 → 测试证据链 (MUST)

对 Spec 中每个标注 `(MUST)` 的 R{N} 项机械核验：(a) `docs/test_cases/{STORY_ID}_case.md` 存在；(b) case 文件中存在引用该 R{N}（或其映射的 AC）的 Scenario 条目；(c) 经由 `test-map` 映射的测试文件真实存在于磁盘。任一缺失 → FAIL，证据行指出缺在哪一环。

### R3: 归档勾选 ↔ case 文件诚实性 (MUST)

当 Board 上该 Story 全部 Task 为 `[x]` 时，机械扫描 Spec 与 test case 文件中的矛盾标记：Status 非 Done、以及 case/spec 正文中的未决声明（`open`、`pending`、`TODO`、`FIXME`、`未解决`、`待确认` 等可配置词表）。发现矛盾 → FAIL 并引用具体行。词表 MUST 提取为模块级常量（No Magic Values），后续可迁入 pactkit.yaml。

### R4: 接线验证（零生产调用方检测）(MUST)

检测本 Story diff 引入的新增公开函数/类/模块是否有测试目录之外的调用方：codegraph 可用（`graph_provider: codegraph`）时用 `pactkit query --callers`，否则退化 grep。零生产调用方的新组件 → **WARN**（列出清单），默认不 block；豁免规则（CLI 入口、`__all__` 显式导出、测试辅助）MUST 在代码中显式定义。WARN 而非 FAIL 的理由：机械判定无法区分"纯装饰"与"为下一故事预埋的接口"，宁可误报为 WARN 也不误杀。

### R5: 状态机一致性 (MUST)

核验三处状态互相一致：Spec 的 Status 字段、Board 条目状态、archive 文件。矛盾场景即 FAIL，例如：Spec 为 Draft 但 Board 全部 `[x]` 且即将归档；Story 已存在于 archive 但 Board 仍有未勾选项。

### R6: playbook 强制接线 (MUST)

修改 `prompts/commands.py` 的 `project-done.md`：在 Phase 3 的 Spec Status Update（步骤 6）**之后**插入强制步骤——运行 `pactkit done-verify {STORY_ID}`，退出码非 0 MUST 中止 Done 流程并输出 FAIL 证据链，禁止继续归档与提交。同步重新生成 `pactkit-plugin/commands/project-done.md` artifact。

> **修正记录（Act 实施期）**：原稿为"步骤 6 之前插入"，与 R5/AC5 矛盾——Spec 的 Status 翻转发生在步骤 6，verify 若在其前运行，则"Draft + Board 全勾"这一**正常中间态**会被 AC5 误判 FAIL。接线点改为步骤 6 之后，使 R5 的语义严格成立（此时 Spec 必须为 Done）。

### R5 补充语义（Act 修正后）

verify 在 spec-status 翻转之后运行，判定为：Board 全 `[x]` 且 Spec Status == Done → PASS；Board 全勾但 Spec 非 Done → FAIL（翻转被跳过）；Spec 为 Done 但 Board 有未勾项 → FAIL；Story 已在 archive 但 Board/Spec 状态不完整 → FAIL。

### R7: 不与 pactkit-analyze 双写 (MUST NOT)

`pactkit-analyze` 保持 Act Phase 0.6 的 advisory 定位不变。`done-verify` 的 Spec/Board/case 解析 MUST 复用现有 code 层解析器（`spec_status.py`、board 脚本、validators），不得复制出第二份解析逻辑；analyze 与 done-verify 不得各自维护一份 R 项/AC 提取正则。

## Acceptance Criteria

### AC1: 证据链输出与退出码 (R1)

- **Given** 一个各项检查全过的 Story
- **When** 执行 `pactkit done-verify {STORY_ID}`
- **Then** 每条检查输出 `[PASS] {项} — {证据}`；退出码为 0

### AC2: P0-4 场景复现即拦截 (R3)

- **Given** Board 上某 Story 全部 Task 已勾 `[x]`，但其 test case 文件正文含 `RFC open` 未决声明
- **When** 执行 `pactkit done-verify {STORY_ID}`
- **Then** 该检查输出 `[FAIL]` 并引用 case 文件具体行号；退出码为 1

### AC3: 缺失测试证据即拦截 (R2)

- **Given** Spec 含 `(MUST)` 的 R2 项，但 case 文件不存在或无任何 Scenario 引用 R2
- **When** 执行 `pactkit done-verify`
- **Then** R2 对应行输出 `[FAIL]`，指明缺失环节（case 文件缺失 / Scenario 未覆盖 / 测试文件不存在）；退出码为 1

### AC4: 零生产调用方组件告警 (R4)

- **Given** Story diff 新增了一个无任何测试目录外调用方的模块
- **When** 执行 `pactkit done-verify`
- **Then** 输出 `[WARN]` 清单列出该组件；退出码仍为 0

### AC5: 状态机矛盾即拦截 (R5)

- **Given** Board 上该 Story 全部 `[x]`，但 Spec Status 仍为 Draft（spec-status 翻转被跳过）
- **When** 执行 `pactkit done-verify`
- **Then** 状态一致性检查输出 `[FAIL]`；退出码为 1

### AC6: playbook 强制关卡生效 (R6)

- **Given** 修改后的 `project-done.md`（source 与 plugin artifact）
- **When** 检查 Phase 3 步骤顺序
- **Then** `pactkit done-verify` 调用位于 spec-status Done 翻转**之后**、归档之前，且明确"退出码非 0 中止流程"；`pactkit-plugin/commands/project-done.md` 与 source 一致

### AC7: 测试套件全通过 (R1-R7)

- **Given** 全部修改完成
- **When** 运行 `.venv/bin/pytest tests/ -v`
- **Then** 所有测试通过，无新失败

## Target Call Chain

```
/project-done Phase 3 (spec-status Done 之后、归档之前)
  → pactkit done-verify {STORY_ID}                     [cli.py 新子命令]
    → done_verify.verify_story(story_id, project_root)  [src/pactkit/done_verify.py 新模块]
      ├─ R2: spec 解析 R 项 → test_cases/{ID}_case.md 引用检查 → test_mapper.map_to_tests()
      ├─ R3: board.py 解析勾选状态 + spec/case 未决词表扫描（BLOCKER_TERMS 常量）
      ├─ R4: git diff 新增公开符号 → pactkit query --callers (codegraph) / grep fallback
      └─ R5: spec_status 读取 + board 状态 + docs/product/archive/ 交叉比对
    → exit 0/1 → playbook 据此放行或中止归档
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/done_verify.py` | 新模块：R2/R3/R5 核验逻辑 + 证据链输出 + 退出码 | None | Medium |
| 2 | `src/pactkit/done_verify.py` | R4 接线验证（codegraph query + grep fallback + 豁免规则） | Step 1 | Medium（WARN 误报率需用本仓库实测调优） |
| 3 | `src/pactkit/cli.py` | 注册 done-verify 子命令 | Step 1 | Low |
| 4 | `src/pactkit/prompts/commands.py` | project-done Phase 3 插入强制调用步骤 | Step 3 | Low |
| 5 | `pactkit-plugin/commands/project-done.md` | 重新生成 plugin artifact 并 grep 验证 | Step 4 | Low |
| 6 | `tests/unit/test_done_verify.py` | 构造 AC2-AC5 场景 fixture 的单测 | Step 1-3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 新增 CLI 子命令，STORY_ID 参数须防路径穿越（校验 ID 格式，拒绝 `../` 等） |
| SEC-2 | Yes | 读取并解析用户项目内的 spec/case/board 文件，解析失败须优雅降级不崩溃 |
| SEC-3 | N/A | 无数据库相关（sec-scope 命中为关键词误报；codegraph db 为只读查询） |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无认证/会话逻辑（sec-scope 命中为关键词误报） |
| SEC-6 | N/A | 无 API/路由变更 |
| SEC-7 | Yes | 各检查项的单项失败不得导致整体崩溃——单检查异常须捕获并降级为 WARN + 错误说明 |
| SEC-8 | N/A | 无依赖变更（复用现有 codegraph/sqlite3，无新第三方包） |

## Out of Scope

- 提交前测试门禁（`pactkit commit-gate`：pre-commit/PreToolUse 拦截 + skip≠pass 语义）——独立故事，依赖本故事的命令化模式但不共用实现
- `pactkit deps` 外部依赖一键安装（codegraph/gh/node）——单独建卡
- 不修改 `pactkit-analyze` 的 advisory 行为与触发时机（R7）
- R4 的 WARN→FAIL 升级开关（blocking 配置）留待积累误报数据后再决定
- 未决词表的 pactkit.yaml 配置化（本期为模块级常量，依赖 STORY-slim-135 的 schema 落地后可一行迁入）
