# STORY-slim-104: Fix L3 SHOULD semantics in Signal Strength Convention

| Field | Value |
|-------|-------|
| ID | STORY-slim-104 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.6 |

## Background

Signal Strength Convention 表中 L3 Recommended 的 Semantics 列当前定义为 "Violation = warning, non-blocking"。这个措辞让 AI 将 SHOULD 误解为 "可以不做"，导致 Spec 中标记为 SHOULD 的 task 被系统性 defer。

RFC 2119 对 SHOULD 的正确定义是："除非有充分理由，否则必须做"（there may exist valid reasons to ignore a particular item, but the full implications must be understood and carefully weighed before choosing a different course）。当前措辞与 RFC 2119 语义不符。

**实际影响**: 观测到 AI 在 Act 阶段完成所有 MUST task 后，将全部 SHOULD task defer，给出的理由包括 "context 太长"、"改动大下次做" 等。这些 SHOULD task 最终全部被补回，总共只花 15 分钟。

**Canonical source**: `src/pactkit/prompts/rules.py:51`，`RULES_MODULES["core"]` 模板字符串。

## Requirements

### R1: Fix L3 Semantics to RFC 2119 (MUST)

Change L3 Recommended row Semantics from `Violation = warning, non-blocking` to `Default required — skip only with stated reason`. This aligns with RFC 2119 SHOULD semantics: the default is to do it, and skipping requires an explicit, stated justification.

### R2: Add SHOULD clarification note (SHOULD)

Add a bullet point after the table clarifying that `SHOULD` (L3) is NOT optional — it means "do unless you have a stated reason not to". This prevents the table's compact format from being misread.

## Acceptance Criteria

### AC1: L3 Semantics text updated (R1)

- **Given** `src/pactkit/prompts/rules.py` contains the Signal Strength Convention table
- **When** I read the L3 Recommended row
- **Then** the Semantics column reads `Default required — skip only with stated reason` (not `Violation = warning, non-blocking`)

### AC2: Clarification note present (R2)

- **Given** `src/pactkit/prompts/rules.py` contains the Signal Strength Convention section
- **When** I read the bullet points after the table
- **Then** there is a bullet clarifying that SHOULD (L3) is not optional — skipping requires a stated reason

### AC3: Deployed rules file reflects change (R1, R2)

- **Given** pactkit has been deployed via `pactkit init` or `pactkit deploy`
- **When** I read `~/.claude/rules/01-core-protocol.md`
- **Then** the L3 row and clarification note match the source in `rules.py`

## Target Call Chain

`RULES_MODULES["core"]` (rules.py:4) → `deployer._deploy_rules()` → writes `01-core-protocol.md`

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/rules.py` | Change L3 Semantics text + add SHOULD clarification bullet | None | Low |
| 2 | `tests/` | Add/update test verifying L3 row content | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Prompt text change only, no code execution logic |
| SEC-2 | N/A | No user input handling |
| SEC-3 | N/A | No database patterns |
| SEC-4 | N/A | No frontend files |
| SEC-5 | N/A | No auth/session logic |
| SEC-6 | N/A | No API/route files |
| SEC-7 | N/A | No error handling logic |
| SEC-8 | N/A | No dependency changes |

## Out of Scope

- STORY-slim-086 Spec 中的中文版表格（历史记录，不影响部署）
- 其他 rules 文件中对 SHOULD 的使用（语义由此表定义，使用方不需改）
