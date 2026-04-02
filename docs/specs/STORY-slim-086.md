# Spec STORY-slim-086: Prompt Writing Quality — Signal Strength, Consequence Language, NO_TOOLS Mode

## Metadata
| Field | Value |
|-------|-------|
| ID | STORY-slim-086 |
| Title | Prompt Writing Quality — Signal Strength, Consequence Language, NO_TOOLS Mode |
| Status | Done |
| Priority | P1 |
| Author | System Architect |
| Created | 2026-04-02 |
| Release | 2.10.0 |

## Summary
借鉴 Claude Code 源码中的 prompt 工程模式，对 PactKit 的规则文件和 playbook 进行三项写法改进：(1) 统一信号强度层级，(2) 在关键禁止规则后添加后果语言，(3) 在分析阶段添加 NO_TOOLS 显式禁止。这三项改动均为纯文本 prompt 修改，不涉及 Python 代码变更。

## Background
通过分析 Claude Code 的 1,884 个源文件（特别是 48 个 prompt 文件），发现其 prompt 写法有三个 PactKit 当前缺失的模式：

1. **信号强度层级**：Claude Code 使用 4 级信号词（NEVER > CRITICAL > IMPORTANT > Prefer），PactKit 当前混用 MUST/DO NOT/CRITICAL 无统一层级，AI 无法区分轻重
2. **后果语言**：Claude Code 在关键禁止后加后果（"will FAIL"、"will waste your only turn"），PactKit 只有命令式（"不要做 X"）无后果说明
3. **NO_TOOLS 模式**：Claude Code 在纯分析场景用三重否定禁止所有写入工具，PactKit 的 Check 和 Retro 分析阶段没有显式工具禁止

参考来源：`~/workspaces/claude-code/docs/prompts/patterns.md`（P3: Graduated Safety Language, P6: NO_TOOLS_PREAMBLE）

## Requirements

### R1: Signal Strength Convention（信号强度层级规范）
在 `~/.claude/rules/` 中新增一个约定，定义 4 级信号强度：

| 级别 | 关键词 | 语义 | 使用场景 |
|------|--------|------|---------|
| **L1 Absolute** | `NEVER` / `MUST NOT` | 违反 = bug，零容忍 | 安全红线、数据丢失、Spec 篡改 |
| **L2 Strong** | `CRITICAL` / `MUST` / `ALWAYS` | 违反 = 需要修复的问题 | Phase gate、TDD 强制、regression 阻断 |
| **L3 Recommended** | `IMPORTANT` / `SHOULD` | 违反 = 警告，不阻断 | 最佳实践、性能建议、风格偏好 |
| **L4 Advisory** | `Prefer` / `Consider` / `If possible` | 建议，可按情况跳过 | 优化提示、可选增强 |

此约定 MUST 被写入一个规则文件（可以是新文件或追加到现有文件），作为所有 playbook 和规则文件的写作参考。

### R2: 现有规则文件信号强度校准
对以下文件中的信号词进行校准（升级或降级），使其符合 R1 的层级定义：

**R2.1** `01-core-protocol.md`:
- "The agent MUST NOT skip TDD" → 保持 L2（MUST NOT 在此上下文是 strong，不是 absolute）
- "All tests must pass before committing" → 升级为 "All tests MUST pass before committing"（L2 统一大写）

**R2.2** `02-hierarchy-of-truth.md`:
- "do not modify the failing test" → 升级为 "NEVER modify a pre-existing failing test — doing so silently corrupts the regression baseline and the failure will only surface in CI"（L1 + 后果语言，见 R3）
- "You MUST NOT assume you understand the design intent" → 保持 L1

**R2.3** `10-safety.md`:
- "NEVER print passwords, keys, or tokens to stdout" → 保持 L1，添加后果（见 R3）
- "NEVER delete user files without explicit dry-run confirmation" → 保持 L1，添加后果（见 R3）

### R3: Consequence Language（后果语言）
在以下 **7 条关键禁止规则** 后添加后果说明（格式：`— {consequence}`）：

| 文件 | 当前写法 | 改为 |
|------|---------|------|
| `02-hierarchy-of-truth.md` | "do not modify the failing test" | "NEVER modify a pre-existing failing test — doing so silently corrupts the regression baseline and the failure will only surface in CI" |
| `02-hierarchy-of-truth.md` | "You MUST NOT assume you understand the design intent behind pre-existing tests" | 添加 "— misinterpreting intent leads to tests that pass but verify the wrong behavior" |
| `10-safety.md` | "NEVER print passwords, keys, or tokens to stdout" | 添加 "— leaked secrets enter shell history and log files, requiring immediate rotation" |
| `10-safety.md` | "NEVER delete user files without explicit dry-run confirmation" | 添加 "— deleted files cannot be recovered if not committed to git" |
| `project-act.md` Phase 2 | "DO NOT write source code yet" | 改为 "NEVER write source code in this phase — doing so breaks TDD causality: tests must exist before the code they verify" |
| `project-act.md` Phase 3 | "DO NOT modify it. STOP and report" (pre-existing test) | 改为 "NEVER modify a pre-existing failing test — doing so silently corrupts the regression baseline. STOP and report to the user." |
| `project-check.md` Principle | "identify issues but do not fix them" | 改为 "identify issues but NEVER modify code — fixes made during QA bypass the TDD loop and produce untested changes" |

### R4: NO_TOOLS Explicit Prohibition（分析阶段工具禁止）
在以下 playbook 的分析阶段添加 TOOL RESTRICTION 块：

**R4.1** `project-check.md` — 在 Phase 0 之前（Principle 行之后）添加：
```markdown
> **TOOL RESTRICTION**: This entire command is analysis-only.
> NEVER use Edit, Write, or Bash(write operations) in any phase.
> Tool calls that modify files will produce incorrect analysis — the QA verdict
> must reflect the code AS-IS, not code you changed during review.
```

**R4.2** `project-check.md` — `allowed-tools` frontmatter确认不包含 Edit 和 Write（当前已正确：`[Read, Bash, Grep, Glob]`）。但 Bash 可以执行写入操作，所以需要在 prompt 层面显式禁止 Bash 写入。

**R4.3** 考虑是否需要对 `daily-retro` skill 添加类似限制。daily-retro 的 Phase 2 Multi-Agent Analysis 和 Phase 4 Reflection 是纯分析阶段，SHOULD 包含 NO_TOOLS 提示。但 daily-retro 是 skill 不是 playbook（位于 `~/.claude/skills/daily-retro/`），本 Story 只处理 playbook（commands/*.md）和规则文件（rules/*.md），daily-retro 的调整作为 follow-up 记录。

## Acceptance Criteria

### Scenario 1: Signal strength convention exists
- **Given** the rules directory `~/.claude/rules/`
- **When** I search for "Signal Strength" or "L1 Absolute"
- **Then** a rule file contains the 4-level signal strength convention table

### Scenario 2: Pre-existing test rule uses NEVER + consequence
- **Given** the file `02-hierarchy-of-truth.md`
- **When** I read the Pre-existing Test Protocol section
- **Then** it contains "NEVER modify" (not "do not modify")
- **And** it contains a consequence clause explaining regression baseline corruption

### Scenario 3: Safety rules have consequences
- **Given** the file `10-safety.md`
- **When** I read each rule
- **Then** each NEVER rule is followed by a "—" consequence clause

### Scenario 4: Act Phase 2 uses NEVER + consequence for TDD
- **Given** the file `project-act.md`
- **When** I read Phase 2 (Test Scaffolding)
- **Then** the source code prohibition uses "NEVER" (not "DO NOT")
- **And** it includes a consequence about TDD causality

### Scenario 5: Act Phase 3 pre-existing test uses NEVER + consequence
- **Given** the file `project-act.md`
- **When** I read Phase 3 (Implementation) regression section
- **Then** the pre-existing test prohibition uses "NEVER modify"
- **And** it includes a consequence about regression baseline corruption

### Scenario 6: Check has NO_TOOLS restriction
- **Given** the file `project-check.md`
- **When** I read the top-level instructions (before Phase 0)
- **Then** it contains "TOOL RESTRICTION" block
- **And** the block explicitly prohibits Edit, Write, and Bash write operations
- **And** it includes a consequence explaining why modifications invalidate analysis

### Scenario 7: Check principle uses NEVER + consequence
- **Given** the file `project-check.md`
- **When** I read the PRINCIPLE line
- **Then** it contains "NEVER modify code" (not "do not fix them")
- **And** it includes a consequence about bypassing TDD

### Scenario 8: Signal strength keywords are consistent
- **Given** all modified files (rules + playbooks)
- **When** I grep for signal keywords
- **Then** "NEVER" appears only for L1 (absolute prohibition) contexts
- **And** "CRITICAL" appears only for L2 (strong requirement) contexts
- **And** no rule uses "DO NOT" where "NEVER" is the intended severity

### Scenario 9: No Python code changes
- **Given** the `src/` directory
- **When** I run `git diff --name-only src/`
- **Then** no `.py` files are modified

### Scenario 10: Existing tests still pass
- **Given** the existing test suite
- **When** `.venv/bin/pytest tests/ -v` is run
- **Then** all tests pass without modification

## Design

### Files to Modify

| File | Change Type | Scope |
|------|------------|-------|
| `~/.claude/rules/01-core-protocol.md` | R2.1 | Signal word capitalization |
| `~/.claude/rules/02-hierarchy-of-truth.md` | R2.2 + R3 | NEVER + consequence on pre-existing test rules |
| `~/.claude/rules/10-safety.md` | R2.3 + R3 | Consequence clauses on both rules |
| `pactkit-plugin/commands/project-act.md` | R3 | Phase 2 NEVER + consequence, Phase 3 NEVER + consequence |
| `pactkit-plugin/commands/project-check.md` | R3 + R4 | Principle rewrite + NO_TOOLS block |
| New or existing rule file | R1 | Signal strength convention table |

### Signal Strength Convention Placement
追加到 `01-core-protocol.md` 末尾作为 `## Signal Strength Convention` 节，而非新建文件。理由：core-protocol 是所有 playbook 的基础引用，写作规范放在这里最自然。

### What This Story Does NOT Do
- 不修改 Python 代码（纯 prompt/markdown 变更）
- 不修改 daily-retro skill（follow-up）
- 不修改所有 playbook（只改 act + check，其他 playbook 逐步 apply）
- 不添加自动化 lint 来检查信号强度（未来可以做，但不在本 Story）

## Implementation Steps

| Step | File | Action | Risk |
|------|------|--------|------|
| 1 | `~/.claude/rules/01-core-protocol.md` | 追加 Signal Strength Convention 节 (R1) + 校准现有信号词 (R2.1) | Low |
| 2 | `~/.claude/rules/02-hierarchy-of-truth.md` | 升级 "do not modify" → "NEVER modify" + 添加后果 (R2.2 + R3) | Low |
| 3 | `~/.claude/rules/10-safety.md` | 添加后果语言 (R2.3 + R3) | Low |
| 4 | `pactkit-plugin/commands/project-act.md` | Phase 2 + Phase 3 信号词升级 + 后果 (R3) | Low |
| 5 | `pactkit-plugin/commands/project-check.md` | Principle 重写 + NO_TOOLS block (R3 + R4) | Low |
| 6 | 验证所有 pytest 通过 (Scenario 10) | — | Low |

## Security Scope

| ID | Check | Applicable |
|----|-------|-----------|
| SEC-1 | Secrets | N/A — no code changes |
| SEC-2 | Input | N/A — no code changes |
| SEC-3 | SQL | N/A — no code changes |
| SEC-4 | XSS | N/A — no code changes |
| SEC-5 | Auth | N/A — no code changes |
| SEC-6 | Rate | N/A — no code changes |
| SEC-7 | Error | N/A — no code changes |
| SEC-8 | Deps | N/A — no code changes |
