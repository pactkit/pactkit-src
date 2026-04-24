# STORY-slim-106: Plan 阶段横向扫描强化与 hooks 死代码清理

| Field | Value |
|-------|-------|
| ID | STORY-slim-106 |
| Status | Done |
| Priority | P1 |
| Release | 2.11.0 |

## Background

### 问题来源

PactSearch 项目（v0.3.x → v0.4.0）在 STORY-101~140 的开发过程中累积了 10 个技术债 Story（STORY-141~150）。根因分析表明：

1. **Plan 阶段缺少横向扫描** — System Architect 在 Plan Phase 1 只做纵向 trace（目标函数的调用链），不检查项目内部同一操作模式已有多少个独立实现。导致 OWL 写入路径从 1 条增长到 10+ 条时无人发觉。
2. **Solution Design Protocol 盲区** — 只看 "framework vs project" 的能力 delta，不看 "project 内部同一模式出现几次"。当新 feature 不涉及新 framework 时，Protocol 根本不触发。
3. **hooks 死代码** — `deployer.py` 中 STORY-027 实现的 3 个 Claude Code hook 模板从未生效：脚本生成到 `.claude/hooks/` 但未注册到 `.claude/settings.json`（Claude Code 不扫描目录，只读 settings.json 的 hooks 配置），且所有脚本都 `exit 0`（report-only）。
4. **Architecture Principles 的 DRY/OCP/SRP 示例全部绑定 PactKit 内部概念** — 部署到用户项目时，AI 将其理解为 "PactKit 的内部规范" 而非通用原则。

### 现有基础设施

PactKit `visualize.py` 已实现：
- `_build_reverse_graph()` — 从函数反向 BFS 找所有调用者
- `fan_in` 计算 — 统计每个函数被多少处调用
- `visualize --mode call --reverse --entry <func>` — CLI 可直接使用

Claude Code 内置 LSP 工具支持 `findReferences`、`incomingCalls`、`workspaceSymbol` 等语义级查询。

**核心判断**：不需要新建工具，需要的是让 Plan playbook 和 Solution Design Protocol 引导 Architect 使用已有工具做横向扫描。

## Requirements

### R1: Plan Phase 1 增加 Lateral Scan 步骤 (MUST)

在 `commands.py` 的 Plan playbook Phase 1 Archaeology 中，Logic Trace 之后、Solution Design 之前，增加 **Phase 1.5: Lateral Scan（横向扫描）**：

1. 从 Spec 需求中识别核心操作（如 "写入 OWL"、"发送通知"、"创建 DB 记录"）
2. 使用分层策略查找项目内已有实现数量：
   - **首选 LSP**（如果可用）：`incomingCalls` 或 `findReferences` 查找核心操作的所有调用者
   - **次选 visualize**：`visualize --mode call --reverse --entry <operation>` 读取 fan-in
   - **兜底 grep**：`grep -rn "<operation>" src/`
3. 输出格式：
   ```
   Lateral Scan:
   - Operation: {name}
   - Existing implementations: {N} ({file1}:{func1}, {file2}:{func2}, ...)
   - Assessment: {Reuse existing | Extract shared abstraction | New is justified}
   ```
4. **如果同一操作的独立实现 ≥ 3 个**，Spec 的 Technical Design MUST 包含共享抽象评估 — 未评估违反 SHOULD 规则

### R2: Solution Design Protocol 扩展 Project Internal Patterns (MUST)

在 `rules.py` 的 Solution Design Protocol 中，Step 3 "Query Project Existing Capabilities" 之后，增加 **Step 3.5: Query Project Internal Patterns**：

- **Goal**: 项目内部是否已有同类操作的多个独立实现？
- **方法**：同 R1 的分层策略（LSP → visualize → grep）
- **Output checkpoint**: `"Internal pattern: {operation} has {N} implementations in {files}"`
- **Delta Assessment 扩展**（Step 4 表格增加一行）：

  | Framework Has It | Project Uses It | Project Has Multiple | Decision |
  |---|---|---|---|
  | — | — | ≥ 3 independent | **Extract shared service** — MUST evaluate before adding Nth implementation |

### R3: Architecture Principles 通用化 (SHOULD)

修改 `rules.py` 的 `architecture` 规则模块：

1. DRY (§1) — 当前示例（`profiles.py`, `schemas.py`, `config.py`）替换为通用示例 + PactKit 示例并列
2. OCP (§2) — 增加通用反模式示例：N 个 if/elif 分支应改为 strategy/registry pattern
3. SRP (§5) — 增加模块膨胀检测指引：单文件超过 500 行 SHOULD 评估拆分

### R4: 删除 hooks 死代码 (MUST)

从以下文件中删除 hooks 相关代码：

1. `config.py` — 删除 `VALID_HOOK_TEMPLATES` 常量、`hooks` default config section、hooks validation 逻辑、hooks YAML 序列化/反序列化
2. `deployer.py` — 删除 `_HOOK_PRE_COMMIT_LINT`、`_HOOK_POST_TEST_COVERAGE`、`_HOOK_PRE_PUSH_CHECK` 模板、`_HOOK_TEMPLATES` 字典、`_deploy_hooks()` 函数、调用处
3. Plan playbook Phase 0.5 — 删除 "check config completeness (hooks, ci, issue_tracker sections)" 中的 hooks 引用

**不删除**：`pactkit.yaml` 用户文件中已有的 `hooks:` section（向后兼容：读到未知 key 时忽略即可，已有行为）

### R5: Spec Technical Design 格式扩展 (SHOULD)

在 Spec scaffold 模板和 spec_linter 中：

1. `schemas.py` — 在 SPEC_REQUIRED_SECTIONS 或 Spec 模板中，Technical Design section 增加 `### Lateral Scan Results` 子节
2. Plan playbook Phase 3.2a — 引导 Architect 将 Phase 1.5 的横向扫描结果写入此子节
3. spec_linter — 新增 W006 WARNING：如果 Spec 有 `## Technical Design` 但缺少 `### Lateral Scan Results`，报警（非阻断）

## Acceptance Criteria

### AC1: Lateral Scan 出现在 Plan playbook 中 (R1)

- **Given** 用户执行 `/project-plan` 且目标项目有既有代码
- **When** Architect 进入 Phase 1 Archaeology
- **Then** playbook 在 Logic Trace 之后包含 Lateral Scan 步骤，且文本中明确列出 LSP → visualize → grep 的分层策略

### AC2: Solution Design Protocol 包含 Internal Patterns 步骤 (R2)

- **Given** Solution Design Protocol 被触发
- **When** Architect 执行到 Step 3.5
- **Then** Protocol 文本要求用 LSP/visualize/grep 检查同类操作的已有实现数量，且 Delta Assessment 表格包含 "≥ 3 independent → Extract shared service" 行

### AC3: Architecture Principles 不含 PactKit-only 示例 (R3)

- **Given** `rules.py` 中 `architecture` 规则模块被部署
- **When** AI 在非 PactKit 项目中读取该规则
- **Then** DRY/OCP 示例为通用描述（不以 PactKit 的 `profiles.py` / `schemas.py` / `FormatProfile` 为唯一示例），每条原则至少有一个通用反模式示例

### AC4: hooks 代码完全删除 (R4)

- **Given** `config.py` 和 `deployer.py` 修改完成
- **When** 在源码中搜索 `grep -rn "HOOK\|_deploy_hooks\|VALID_HOOK" src/pactkit/`
- **Then** 0 个结果
- **And** `pactkit deploy` 仍然正常执行（不因缺少 hooks 代码而报错）
- **And** 已有 `pactkit.yaml` 中包含 `hooks:` section 时不报错（忽略未知 key）

### AC5: spec_linter 新增 W006 (R5)

- **Given** 一个 Spec 文件包含 `## Technical Design` 但没有 `### Lateral Scan Results`
- **When** 执行 `pactkit spec-lint` 
- **Then** 输出 W006 WARNING（非 ERROR，不阻断 `/project-act`）
- **And** 一个没有 `## Technical Design` 的 Spec 不触发 W006（仅当 Technical Design 存在时才检查子节）

## Target Call Chain

```
R1/R2: rules.py RULES_MODULES["solution"] → deployed to rules/12-solution-design.md
       commands.py COMMANDS_CONTENT["project-plan.md"] → deployed to commands/project-plan.md
R3:    rules.py RULES_MODULES["architecture"] → deployed to rules/08-architecture-principles.md
R4:    config.py VALID_HOOK_TEMPLATES / get_default_config()["hooks"] / _write_yaml() hooks section
       deployer.py _deploy_hooks() / _HOOK_TEMPLATES / _HOOK_*
       commands.py Phase 0.5 Init Guard hooks reference
R5:    schemas.py SPEC_REQUIRED_SECTIONS (or scaffold template)
       spec_linter.py → new W006 rule
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Plan playbook Phase 1 增加 Lateral Scan 步骤 | None | Low |
| 2 | `src/pactkit/prompts/rules.py` | Solution Design Protocol 增加 Step 3.5 Internal Patterns | None | Low |
| 3 | `src/pactkit/prompts/rules.py` | Architecture Principles 通用化 DRY/OCP/SRP 示例 | None | Medium |
| 4 | `src/pactkit/config.py` | 删除 VALID_HOOK_TEMPLATES、hooks default/validation/serialization | None | Medium |
| 5 | `src/pactkit/generators/deployer.py` | 删除 _HOOK_* 模板、_HOOK_TEMPLATES、_deploy_hooks() 及调用 | Step 4 | Medium |
| 6 | `src/pactkit/prompts/commands.py` | Plan Phase 0.5 删除 hooks 引用 | Step 4 | Low |
| 7 | `src/pactkit/spec_linter.py` | 新增 W006 Lateral Scan Results 检查 | None | Low |
| 8 | `tests/unit/` | 新增/更新测试覆盖 R1-R5 | Steps 1-7 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | prompt 文本和 config 删除，不涉及 secrets |
| SEC-2 | N/A | 无新用户输入路径（config 变更为删除，非新增） |
| SEC-3 | N/A | 无数据库操作 |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无 auth/session 变更 |
| SEC-6 | N/A | 无 API 路由变更 |
| SEC-7 | N/A | 无 error handling 变更（spec_linter W006 是 WARNING 输出，非异常处理） |
| SEC-8 | N/A | 无依赖变更 |

## Out of Scope

- **新 CLI 命令**：不新增 `pactkit lateral-scan` 或 `pactkit deferred-audit` CLI — 本次只改 prompt 层指导，利用已有的 visualize/LSP
- **Act playbook 改动**：不改 Act Phase 的 Self-Check — 横向扫描职责归 Plan（Architect），不归 Act（Developer）
- **hooks 替代方案**：不设计新的 Claude Code hooks 方案 — hooks 的正确用法是用户在 `.claude/settings.json` 自行配置
- **DEFERRED 累积上限**：本次不加 — 需要先有 `pactkit deferred-audit` CLI 才能自动化，属于后续 Story
- **可观测性规则**：PactSearch STORY-148 暴露的 "51 个文件无 logger" 问题属于项目级实践，不适合写入 PactKit 通用规则
