# STORY-slim-20260905efced66ebc9c: 剧本-契约冲突修复:阻塞边界/工具回退/验证指纹/准确阶段胶囊 R1-R6

| Field | Value |
|-------|-------|
| ID | STORY-slim-20260905efced66ebc9c |
| Status | Done |
| Priority | P1 |
| Release | 2.26.0 |

## Background

RUNTIME_KERNEL（`src/pactkit/prompts/rules.py:1006`）确立了阻塞边界（Hard rules
may block only credential exposure, permissions, or material risk of irreversible
damage）、失败语义（incomplete_continue，不创建 workflow lock）与按需加载原则，
但四个高频阶段剧本（`src/pactkit/prompts/commands.py` 的 COMMANDS_CONTENT）仍残留
六处与 kernel 直接冲突的执行指令。2026-09-06 会话中已逐条源码核对确认（非推测）：

1. Done coverage gate `<50% BLOCK for confirmation`（commands.py:600）超出 kernel 阻塞边界
2. Act 禁止直接使用 `rg`/SQLite/Codegraph，仅允许 `pactkit query` 路径（commands.py:234、280）
3. Done 的 `lesson-append` 不可用时要求停机升级 Core（commands.py:621），制造 workflow lock
4. Done 在测试绿但任务未勾选时强制询问用户（commands.py:615），违反"仅在重大决策/外部动作时询问"
5. Done 回归基线用 `git diff HEAD~1`（commands.py:574、590），不对应上次验证状态
6. init/clarify/design 三命令错配加载 `phase-plan` 胶囊（rules.py:1541-1550），而
   PHASE_CONTRACTS 中各自的契约已存在（rules.py:1275、1291、1362）；debug 有契约（rules.py:1376）
   但无任何 phase 胶囊

后果：小改动付出接近完整 PDCA 的固定摩擦成本；模型在剧本与 kernel 冲突时行为不稳定。
本 Story 将剧本拉齐到既有 kernel 语义，并为回归基线提供机械化指纹（ADR-0001：判定落代码层）。

## Requirements

### R1: 覆盖率门禁降级为验收缺口报告 (MUST)

Done 剧本 Step 2.5（commands.py:600）的 coverage 分级 MUST 改为：≥80% PASS；
50–79% WARN；<50% 报告为验收缺口（acceptance gap）并继续 Done 流程，由用户决定
是否在验收前修复覆盖率。MUST NOT 出现 "BLOCK for confirmation" 或任何要求停机
确认的措辞。

### R2: Act 工具限制改为 query 优先 + 记录原因的回退 (MUST)

Act 剧本 Phase 1（commands.py:234）与 Phase 3 regression 段（commands.py:280）
的措辞 MUST 改为：`pactkit query` 路由优先；当路由不可用或失败时，允许回退到
标准工具（rg/Grep/Read 等），但 MUST 在 preflight 证据中记录降级原因并继续；
`--allow-fallback` 的存在保持不变（它自动产出审计记录）。MUST NOT 保留无回退
路径的绝对禁令。

### R3: lesson-append 缺失报告缺口而非停机 (MUST)

Done 剧本 Phase 3.3（commands.py:621）：`pactkit lesson-append` 不可用时 MUST
在完成摘要中报告缺口（lesson 未记录、需升级 Core）并继续 Done 流程。"禁止手写
共享 Lesson 投影"的完整性禁令 MUST 保留。

### R4: 任务勾选证据核验后直接更新 (MUST)

Done 剧本 Phase 3.2 Auto-Fix（commands.py:615）：测试 GREEN 但任务未勾选时，
MUST 逐任务核验证据（测试结果、coverage 表、Spec AC 对应）后直接通过
`pactkit board complete-task` 更新并在报告中说明核验依据；仅当某任务的证据
无法定位时才询问用户。MUST NOT 保留无条件的强制询问。

### R5: 回归基线改为验证指纹 (MUST)

`pactkit regression` MUST 新增验证指纹机制：

- `--record`：在回归测试通过后调用，将 {commit, source/test 脏文件集, 指纹,
  recorded_at} 写入 `.pactkit/verification/<STORY_ID>.json`；STORY_ID 默认取
  `active_story_id`，可用 `--story` 显式指定；无 git 环境时降级报告并正常退出
  （不阻塞）
- `--check-record`：比对当前状态与记录，输出 `VERIFIED-CURRENT`（无 source/test
  变化，回归证据可复用）/ `STALE — {changed files}`（列出失效文件，作为后续
  分类基线）/ `NO-RECORD`（无记录，回退既有 git diff 分类）

Act 剧本（Phase 3.3 regression 段）MUST 指示回归绿后运行 `--record`；Done 剧本
Step 0 / Step 1.7 MUST 用 `--check-record` 结果（或 `git diff <recorded-commit>`）
替代 `HEAD~1` 作为基线。指纹文件是本地投影（.pactkit/ 已忽略），MUST NOT 被提交。

### R6: 注册准确的阶段胶囊 (MUST)

rules.py MUST 注册 `phase-init` / `phase-clarify` / `phase-design` / `phase-debug`
四个规则 ID（内容取自 PHASE_CONTRACTS 对应条目的 render()，filename 为
phases/init-contract.md 等，load_policy="phase"）；COMMAND_RULES_MAP 中
project-init/clarify/design 的 `phase-plan` MUST 替换为各自胶囊，project-debug
MUST 补挂 `phase-debug`；`phase-plan` 的 scope 与 trigger MUST 相应收窄到
project-plan。测试镜像 SPEC_TABLE（test_story_slim011_command_rules.py）MUST
同步更新。

## Acceptance Criteria

### AC1: 覆盖率门禁不再阻塞 (R1)

- **Given** 渲染后的 project-done 剧本
- **When** 检查 Step 2.5 coverage 分级文本
- **Then** 不含 "BLOCK for confirmation"；<50% 分支为验收缺口报告并继续（含 continue 措辞）；≥80% PASS / 50–79% WARN 语义不变

### AC2: Act 工具限制带记录回退 (R2)

- **Given** 渲染后的 project-act 剧本
- **When** 检查 Phase 1 Provider-Routed Scan 与 Phase 3 regression 的工具措辞
- **Then** 两处均含"回退到标准工具 + 记录降级原因"的路径；不含无回退的绝对禁令（"Do not invoke … directly" 类措辞被 query 优先 + auditable fallback 取代）

### AC3: lesson-append 缺失不锁流程 (R3)

- **Given** 渲染后的 project-done 剧本
- **When** `pactkit lesson-append` 不可用分支
- **Then** 措辞为报告缺口并继续 Done 流程；"never write a shared Lesson projection manually" 保留

### AC4: 任务勾选免强制询问 (R4)

- **Given** 渲染后的 project-done 剧本
- **When** 测试 GREEN 且任务未勾选
- **Then** 剧本指示逐任务核验证据后经 `pactkit board complete-task` 更新并报告依据；仅证据不可定位时询问用户

### AC5: 验证指纹记录与复用 (R5)

- **Given** 临时 git 仓库中包含 source 文件与已运行的 `--record`
- **When** 无 source/test 变化后运行 `--check-record`
- **Then** 输出 VERIFIED-CURRENT；修改 source 文件后输出 STALE 且列出该文件；无记录时输出 NO-RECORD；非 git 目录中 `--record` 降级报告且退出码为 0；`.pactkit/verification/<STORY_ID>.json` 含 commit 与指纹字段

### AC6: Act/Done 剧本接入指纹 (R5)

- **Given** 渲染后的 project-act 与 project-done 剧本
- **When** 检查 regression 相关段落
- **Then** Act 含回归绿后 `--record` 指引；Done Step 0/1.7 以 `--check-record` / recorded-commit 为基线；剧本中不再出现 `HEAD~1`；test_story037_regression_fix.py 的 HEAD~1 断言同步更新

### AC7: 四命令挂载准确胶囊 (R6)

- **Given** 更新后的 COMMAND_RULES_MAP 与 RULE_DEFINITIONS
- **When** 校验 project-init/clarify/design/debug 的映射
- **Then** 四命令分别映射 phase-init/phase-clarify/phase-design/phase-debug；phase-plan 的 scope 收窄为 ("project-plan",)；SPEC_TABLE 镜像同步；classic 部署的 project-init SKILL.md 含 `@~/.claude/skills/_rules/phases/init-contract.md` 引用

## Target Call Chain

```
prompts/commands.py COMMANDS_CONTENT["project-{act,done}.md"]   # R1-R5 文本
  └→ generators/deployer.py _deploy_commands/_get_command_rules  # 渲染到各 host 的 SKILL.md/commands
       └→ COMMAND_RULES_MAP（prompts/rules.py:1540）解析规则 ID → @import 行     # R6

prompts/rules.py:
  PHASE_CONTRACTS（rules.py:1274）
    └→ PHASE_RULE_CONTENTS（rules.py:1387）.render()
         └→ RULE_DEFINITIONS（rules.py:1426）_definition()
              └→ COMMAND_RULES_MAP / RULES_ONDEMAND_FILES → deployer + deploy_manifest

R5 新链路:
  cli.py regression 子命令（cli.py:234）
    └→ regression.py classify_changes（既有）
    └→ regression.py record_verification / check_verification（新增）
         └→ .pactkit/verification/<STORY_ID>.json（本地投影，gitignored）
         └→ run_events.active_story_id 解析默认 story
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/commands.py` | R1-R4 文本改写 + R5 的 Act `--record` 指引与 Done Step 0/1.7 指纹基线 | None | Low |
| 2 | `src/pactkit/regression.py` | 新增 record_verification/check_verification（git 状态采集、指纹、比对） | None | Medium |
| 3 | `src/pactkit/cli.py` | regression 子命令加 `--record`/`--check-record`/`--story` | Step 2 | Low |
| 4 | `src/pactkit/prompts/rules.py` | R6: PHASE_RULE_CONTENTS/RULE_DEFINITIONS/COMMAND_RULES_MAP + phase-plan scope 收窄 | None | Medium |
| 5 | `tests/unit/test_contract_conflict_fixes.py` | 新建: R1-R4 文本断言 + R5 CLI 行为（tmp git repo）+ R6 映射断言 | Steps 1-4 | Low |
| 6 | `tests/unit/test_story_slim011_command_rules.py` | SPEC_TABLE 镜像同步四命令 | Step 4 | Low |
| 7 | `tests/unit/test_story037_regression_fix.py` | HEAD~1 断言更新为指纹基线 | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | verification record 仅含 git 元数据（commit sha、路径、状态码），实现 MUST NOT 将环境变量、token 或命令输出原文写入记录 |
| SEC-2 | Yes | `--story` 参数进入文件路径构造，MUST 以 ITEM_ID_PATTERN 校验后使用，防路径穿越 |
| SEC-3 | N/A | 触碰面无 SQL（sec-scope 命中来自 cli.py 的无关 import） |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | auth_gate 不在触碰面 |
| SEC-6 | N/A | 无 API/route 文件 |
| SEC-7 | Yes | STALE 文件列表与诊断输出使用仓库相对路径，不泄露绝对路径 |
| SEC-8 | N/A | 无依赖清单变更 |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | `pactkit regression --record/--check-record`（验证指纹）；规则 ID phase-init/phase-clarify/phase-design/phase-debug |
| Touches | src/pactkit/prompts/commands.py, src/pactkit/prompts/rules.py, src/pactkit/regression.py, src/pactkit/cli.py, tests/unit/test_contract_conflict_fixes.py（新建）, tests/unit/test_story_slim011_command_rules.py, tests/unit/test_story037_regression_fix.py |
| Conflict risk | LOW |

## Out of Scope

- legacy 引擎退役、`pactkit/skills/board.py` 的 `_legacy_*` 清理、`LEGACY_PHASE_RULE_CONTENTS` 等死代码删除（独立死代码 story）
- 高频 skill 正文瘦身（治理四项中的第 2 项，需以规则遵循遥测数据为裁判）
- sprint-orchestrator 胶囊结构 review、debug 之外命令的 token 预算优化
- `pactkit context --continuation` legacy facade 向 continuation checkpoint 引擎的迁移
