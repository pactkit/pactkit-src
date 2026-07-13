# STORY-slim-133: Structured Debug Skill with Hypothesis-Driven Troubleshooting

| Field | Value |
|-------|-------|
| ID | STORY-slim-133 |
| Status | Done |
| Priority | P1 |
| Release | 2.16.0 |

## Background

当前 troubleshooting 流程存在两个核心问题：
1. **假设发散不收敛** — AI 列出大量可能原因但不逐个验证排除，导致排查停滞
2. **信息过载** — 漫无目的地 grep/read 大量文件，消耗 token 但不推进定位

现有工具覆盖不了这个场景：
- `pactkit-trace` 是静态分析工具，前提是"已知要看哪里"
- `pactkit-doctor` 仅做项目健康检查
- `system-medic` 仅处理环境/配置问题
- `project-hotfix` 前提是"已定位到问题"

需要一个**从症状到根因**的结构化排查 skill，强制走「假设→验证→缩小」循环，用 opus 模型的强推理能力替代漫无目的的搜索。

## Requirements

### R1: Hypothesis-Driven Loop (MUST)

Skill MUST enforce a structured loop: Observe → Hypothesize (≤3) → Verify (executable command per hypothesis) → Narrow. Each hypothesis MUST have a concrete verification step (a runnable command or code inspection with expected vs actual outcome). Skill MUST NOT proceed to the next hypothesis without executing verification on the current one first.

### R2: Evidence-Gated File Access (MUST)

Every file read MUST be justified by a stated hypothesis or evidence trail. Skill MUST NOT read files "to get familiar with the codebase" or "to understand the context" without linking to a specific hypothesis being tested — violation of this produces the exact "查不到点子上" problem this skill solves.

### R3: Structured Input Protocol (MUST)

Skill MUST provide a structured input template that minimizes user typing while capturing critical debugging info:
- **Symptom**: What's happening (error message, unexpected behavior)
- **Expected**: What should happen instead
- **Reproduction**: How to trigger it (command, URL, input)
- **Context**: What changed recently (optional)

When user provides raw text instead of structured input, skill MUST extract and organize into this structure before proceeding.

### R4: Convergence Guarantee (MUST)

Each loop iteration MUST reduce the hypothesis space. If after 3 iterations no hypothesis is confirmed, skill MUST escalate:
- **Round 1 escalation**: ask user for more information (additional symptoms, reproduction steps)
- **Round 2 escalation (still stuck)**: nudge to `/project-plan` — "This looks like a cross-module issue that needs full architectural trace."

MUST NOT loop indefinitely on the same hypothesis set. The skill's job is fast triage, not deep surgery.

### R5: Model Selection (MUST)

Skill MUST specify `model: sonnet` in SKILL.md frontmatter. Sonnet + structured protocol handles 80% of common bugs. For complex cross-module issues that don't converge, the escalation path is `/project-plan` (full PDCA with trace), not model upgrade.

### R6: Concluding Report (MUST)

Upon locating root cause, skill MUST output a structured conclusion:
- **Root Cause**: One-sentence statement
- **Evidence**: The verification step that confirmed it
- **Fix Path**: Concrete next action (file:line to change, or command to run)
- **PDCA Nudge**: Recommend `/project-hotfix` or `/project-act` as appropriate

### R7: Codegraph Integration (SHOULD)

If `.codegraph/` exists, skill SHOULD prefer codegraph for caller/callee analysis over grep during hypothesis verification. Fallback to grep when codegraph is unavailable.

## Acceptance Criteria

### AC1: Hypothesis Loop Enforced (R1, R4)

- **Given** user invokes `/project-debug "tests fail with KeyError on user_id"`
- **When** the skill starts processing
- **Then** it outputs: (1) structured symptom summary, (2) ≤3 ranked hypotheses each with a verification command, (3) executes verification commands in order, (4) narrows based on results, (5) converges to root cause within ≤5 iterations

### AC2: No Aimless File Reading (R2)

- **Given** the skill is in a verification phase
- **When** it needs to read a file
- **Then** the read is preceded by a one-line justification linking to a hypothesis (e.g., "H2 verification: checking if `models.py:45` validates user_id before access")

### AC3: Structured Input Extraction (R3)

- **Given** user provides unstructured text like "部署之后接口报500了"
- **When** the skill receives this input
- **Then** it extracts and formats into the 4-field template, asks for missing critical fields (Reproduction), and does NOT start hypothesizing until Symptom is clear

### AC4: Convergence Escalation (R4)

- **Given** 3 iterations have passed without confirming a hypothesis
- **When** the skill enters the 4th iteration
- **Then** it asks user for more info; if still stuck after 1 more round, it nudges `/project-plan` with a summary of what was tried and ruled out

### AC5: Sonnet Model with PDCA Escalation (R5)

- **Given** the SKILL.md file exists at `~/.claude/skills/project-debug/SKILL.md`
- **When** inspecting the frontmatter
- **Then** the `model` field is set to `sonnet`

### AC6: Conclusion Report Format (R6)

- **Given** root cause has been identified through the verification loop
- **When** the skill outputs its conclusion
- **Then** it includes all 4 fields: Root Cause (one sentence), Evidence (which verification confirmed it), Fix Path (file:line or command), and PDCA Nudge (appropriate command recommendation)

### AC7: Codegraph Preferred When Available (R7)

- **Given** the project has `.codegraph/` directory
- **When** the skill needs to trace callers/callees during verification
- **Then** it uses `codegraph` CLI instead of raw grep

## Target Call Chain

```
User invokes /project-debug "$symptom"
→ SKILL.md protocol loaded (model: opus)
→ Phase 1: Symptom Structuring (extract/confirm 4-field template)
→ Phase 2: Hypothesis Generation (≤3, ranked by probability)
→ Phase 3: Verification Loop (execute → observe → narrow)
  └─ Loop until: root cause confirmed OR escalation triggered
→ Phase 4: Conclusion Report (root cause + fix path + PDCA nudge)
```

No code implementation needed — this is a pure SKILL.md protocol (prompt-as-code for diagnostic reasoning).

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `~/.claude/skills/project-debug/SKILL.md` | Create skill protocol with all phases | None | Low |
| 2 | `~/.claude/rules/pactkit.md` | Add command to routing table | Step 1 | Low |
| 3 | Board | Register skill in available-skills | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Injection) | N/A | No user input passed to shell unsanitized — verification commands are AI-composed |
| SEC-2 (Auth) | N/A | No auth logic involved |
| SEC-3 (Data Exposure) | N/A | Reads local files only |
| SEC-4 (XSS) | N/A | No web output |
| SEC-5 (Config) | N/A | No config files modified |
| SEC-6 (Crypto) | N/A | No crypto involved |
| SEC-7 (Logging) | N/A | No logging changes |
| SEC-8 (SSRF) | N/A | No network requests |

## Out of Scope

- 自动修复代码 — skill 仅定位问题，修复走 `/project-hotfix` 或 `/project-act`
- 环境/配置问题 — 已有 `system-medic` + `pactkit-doctor` 覆盖
- 性能分析 — 属于另一个专项 skill 的范畴
- CI/CD pipeline 问题 — 超出本地 debug 范围
