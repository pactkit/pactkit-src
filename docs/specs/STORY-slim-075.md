# STORY-slim-075: Prompt engineering quality: graduated safety language, tool call guidance, routing disambiguation, lessons rotation

| Field | Value |
|-------|-------|
| ID | STORY-slim-075 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.5 |

## Background

Analysis of Claude Code's prompt engineering (48 prompt files across 4 categories) revealed 5 reusable patterns where PactKit's current prompts are weaker:

1. **Graduated Safety Language**: Claude Code uses a consistent 4-tier wording system (NEVER/CRITICAL → IMPORTANT/Always → Prefer/Consider → If/When). PactKit mixes MUST, CRITICAL, MANDATORY inconsistently across playbooks — e.g., Done uses "MANDATORY" and "CRITICAL" for the same severity level, while Act uses only "MUST" for equally important TDD rules.

2. **PDCA-Specific Parallel/Serial Guidance**: Claude Code's BashTool prompt has generic tool call concurrency guidance, but PactKit's agent prompts lack **PDCA workflow-specific** concurrency knowledge — e.g., "Spec 和 Board 可以并行读取" or "schemas.py 改动必须先于所有消费者"。这些是领域知识，harness 不会提供。

3. **Routing Table Disambiguation**: Claude Code's AgentTool lists explicit "When NOT to use the Agent tool" scenarios. PactKit's Routing Table (Rule 04) lists commands and their roles, but never says "When NOT to use X" — leading to confusion between `/project-act` vs `/project-hotfix`, `/project-plan` vs `/project-design`.

4. **Lessons Rotation**: Claude Code's Session Memory has MAX_SECTION=2000 tokens and MAX_TOTAL=12000 tokens, preventing memory bloat. PactKit's `lessons.md` is append-only with no row limit — it grows indefinitely. Only the last 5 entries are used (for context.md and dedup), so older entries serve diminishing value.

5. **Example-Driven Instruction**: Claude Code uses concrete when/when-not examples instead of abstract rules. PactKit's Routing Table provides only command names and roles — no usage scenarios or disambiguation examples.

Reference analysis: `~/workspaces/claude-code/docs/prompts/patterns.md` (10 patterns), `~/workspaces/claude-code/docs/prompts/assembly.md` (assembly architecture), `~/workspaces/claude-code/docs/prompts/catalog.md` (52 prompt catalog).

## Requirements

### R1: Graduated Safety Language — 4-Tier Consistency (MUST)

Audit all playbooks in `commands.py` and all agent prompts in `agents.py`. Normalize safety language to a consistent 4-tier system:

| Tier | Keywords | Semantics | Example |
|------|----------|-----------|---------|
| T1 — Prohibition | NEVER, MUST NOT, CRITICAL | Violation = bug, immediate stop | "NEVER skip TDD" |
| T2 — Obligation | MUST, IMPORTANT, Always | Required step, blocks progress | "MUST run regression before commit" |
| T3 — Recommendation | Prefer, Consider, Generally | Best practice, non-blocking | "Prefer editing existing files" |
| T4 — Conditional | If/When...then | Situation-dependent guidance | "If CI fails, report but don't block" |

Rules:
- MANDATORY is retired — replace with MUST (T2) or CRITICAL (T1) depending on severity.
- A single phase MUST NOT use both CRITICAL and MUST for the same severity level.
- T1 keywords MUST appear only for: security violations, data loss, spec compliance, pre-existing test protection.

### R2: Agent PDCA-Specific Parallel/Serial Guidance (MUST)

Add **PDCA workflow-specific** concurrency guidance to `agents.py` — at minimum to `senior-developer` and `repo-maintainer` (the two agents that modify files). This complements Claude Code harness's generic tool call guidance with PactKit domain knowledge.

The guidance MUST cover PactKit-specific patterns:
- When to parallelize: reading Spec + reading Board (independent reads), editing multiple unrelated source files, running lint + test in parallel if independent.
- When to serialize: Spec change → test update → code update (Hierarchy of Truth order), `schemas.py` constant change → all consumers, `_render_prompt()` var_map change → prompt template update.
- NOT in scope: generic "edit multiple files in parallel" — Claude Code harness already covers that.

### R3: Routing Table "When NOT to Use" Disambiguation (MUST)

For each of the 11 commands in Rule 04 (Routing Table in `rules.py`), add a "When NOT to use" field with 1-2 concrete disambiguation scenarios. Priority pairs to disambiguate:
- `/project-act` vs `/project-hotfix` — when to use each
- `/project-plan` vs `/project-design` — new feature vs greenfield
- `/project-check` vs `/project-done` — QA verification vs commit-ready
- `/project-release` vs `/project-done` — version bump vs regular commit

### R4: Lessons Rotation — Max Rows + Auto-Archive (MUST)

Add row limit and auto-archive to `lessons.py`:
- New constant `LESSONS_MAX_ROWS = 50` in `schemas.py`.
- When `append_lesson()` would exceed max rows, move the oldest entries (beyond the limit) to `docs/architecture/governance/archive/lessons_archive_YYYYMM.md`.
- Archive file format: same table structure as lessons.md, grouped by month.
- The rotation MUST be atomic: read → split → write archive → write truncated lessons.md.
- `pactkit lint-lessons` SHOULD warn if row count > LESSONS_MAX_ROWS (non-blocking).

### R5: Example-Driven Routing Scenarios (SHOULD)

For the priority disambiguation pairs in R3, include concrete scenario examples using the pattern:
```
**Use `/project-act`**: When a Spec exists on the board (e.g., `STORY-XXX` in Backlog/In Progress).
**Use `/project-hotfix` instead**: When fixing a production bug that has no Spec and needs to ship immediately.
```

This replaces abstract role descriptions with actionable decision logic.

## Acceptance Criteria

### AC1: No MANDATORY in deployed prompts (R1)

- **Given** all prompt source files (`commands.py`, `agents.py`, `skills.py`, `rules.py`)
- **When** searching for the word `MANDATORY` (case-insensitive)
- **Then** zero occurrences are found — all replaced with MUST or CRITICAL

### AC2: Consistent tier usage in Done playbook (R1)

- **Given** the Done playbook in `commands.py`
- **When** examining Phase 2.5 (Regression Gate) and Phase 3 (Hygiene)
- **Then** T1 keywords (CRITICAL/NEVER) are used only for: regression gate skip prevention and pre-existing test protection. T2 keywords (MUST) are used for: mandatory steps (spec status, lessons, invariants). No tier mixing within the same severity level.

### AC3: Parallel guidance in senior-developer prompt (R2)

- **Given** the `senior-developer` agent prompt in `agents.py`
- **When** reading the prompt text
- **Then** it contains explicit guidance for when to parallelize tool calls (independent file edits) and when to serialize (dependent changes)

### AC4: "When NOT to use" for all 11 commands (R3)

- **Given** Rule 04 (Routing Table) in `rules.py`
- **When** examining each command entry
- **Then** every command has a "When NOT to use" clause with at least 1 concrete scenario

### AC5: Priority pair disambiguation (R3, R5)

- **Given** Rule 04 in `rules.py`
- **When** examining `/project-act` and `/project-hotfix` entries
- **Then** each explicitly references the other as a disambiguation target with a concrete scenario (e.g., "Use /project-hotfix instead when: no Spec exists and fix is urgent")

### AC6: Lessons rotation at 50 rows (R4)

- **Given** a `lessons.md` file with 55 rows of lesson entries
- **When** `append_lesson()` is called
- **Then** the oldest entries (rows 1-6) are moved to `docs/architecture/governance/archive/lessons_archive_YYYYMM.md`, and `lessons.md` retains only the most recent 50 rows

### AC7: Lessons archive file format (R4)

- **Given** entries rotated out of `lessons.md`
- **When** examining the archive file
- **Then** it has the same table header (`| Date | Lesson | Context |`) and contains the moved rows in chronological order

### AC8: LESSONS_MAX_ROWS constant in schemas.py (R4)

- **Given** `schemas.py`
- **When** searching for `LESSONS_MAX_ROWS`
- **Then** the constant exists with value 50 and is used by `append_lesson()` in `lessons.py`

### AC9: lint-lessons warns on overflow (R4)

- **Given** a `lessons.md` with 60 rows
- **When** running `pactkit lint-lessons`
- **Then** output includes a warning about row count exceeding LESSONS_MAX_ROWS (non-blocking — does not fail)

## Target Call Chain

```
R1-R3, R5: Prompt-only changes (no code execution path)
  commands.py COMMANDS_CONTENT → deployer.py _render_prompt() → deployed playbooks
  agents.py AGENTS_CONTENT → deployer.py _render_prompt() → deployed agent prompts
  rules.py RULES_CONTENT → deployer.py _render_prompt() → deployed rules

R4: Code change
  cli.py lesson-append → lessons.py append_lesson()
    → _get_last_n_entries() [dedup check]
    → NEW: _rotate_if_needed(project_root, max_rows)
      → read lessons.md → count rows
      → if > max_rows: split → write archive → write truncated
    → append row to lessons.md
  cli.py lint-lessons → validators.py lint_lessons()
    → NEW: warn if row_count > LESSONS_MAX_ROWS
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/schemas.py` | Add `LESSONS_MAX_ROWS = 50` constant | None | Low |
| 2 | `src/pactkit/lessons.py` | Add `_rotate_if_needed()` function: read → split → archive → truncate | Step 1 | Medium |
| 3 | `src/pactkit/validators.py` | Add row count warning to `lint_lessons()` | Step 1 | Low |
| 4 | `tests/unit/test_lessons_rotation_075.py` | Tests for AC6-AC9: rotation at 50, archive format, constant, lint warning | Steps 1-3 | Low |
| 5 | `src/pactkit/prompts/commands.py` | Audit all playbooks: replace MANDATORY→MUST/CRITICAL, normalize tier usage | None | Low |
| 6 | `src/pactkit/prompts/agents.py` | Add parallel/serial tool call guidance to senior-developer, repo-maintainer | None | Low |
| 7 | `src/pactkit/prompts/rules.py` | Add "When NOT to use" + example scenarios to all 11 commands in Rule 04 | None | Medium |
| 8 | `tests/unit/test_prompt_quality_075.py` | Tests for AC1-AC5: no MANDATORY, tier consistency, parallel guidance, disambiguation | Steps 5-7 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Prompt text changes only; lessons rotation is file append/write with existing atomic pattern |
| SEC-2 | N/A | No new user input handling — lesson text already validated by specificity/dedup checks |
| SEC-3 | N/A | No database |
| SEC-4 | N/A | No frontend |
| SEC-5 | N/A | No auth change |
| SEC-6 | N/A | No API change |
| SEC-7 | N/A | Lessons rotation uses existing file I/O patterns; no new error paths |
| SEC-8 | N/A | No dependency change |

## Out of Scope

### 不适用于 PactKit 架构（分析后排除）

以下 Claude Code 模式经分析后确认**不适用**于 PactKit，原因是架构层次不同：

- **Prompt Cache 分割（静态/动态边界）** — PactKit 的 prompt 在 deploy 阶段由 `_render_prompt()` 一次性渲染为静态文件。运行时由 Claude Code harness 控制缓存，PactKit 没有 runtime prompt assembly 入口，无法实施 cache 分割。
- **Token 预算计算** — PactKit 不控制 context window 分配（harness 控制）。现有 `BASELINE_TOTAL_CHARS` 监控（STORY-slim-063）已覆盖 prompt 膨胀检测，再做 token 计算是重复劳动。
- **Budget-Aware Prompt 截断** — 同上，PactKit 无法决定 harness 分配给 skill/command 的 context 比例。当前总量 ~78K chars 远低于限制。
- **NO_TOOLS_PREAMBLE（工具禁用）** — Claude Code harness 已管理工具可用性。PactKit 的 skill 通过 `allowed-tools` frontmatter 声明工具权限，不需要 prompt 级别的工具禁用。
- **Prompt 组装优先级链（Override → Agent → Default）** — PactKit 每个 command 只有一个 playbook，没有 override/append 需求。如未来支持企业自定义 playbook 才需要，目前无场景。
- **Tool 并发安全标记（isConcurrencySafe/isReadOnly）** — PactKit 是 prompt-driven 工具系统，不是 code-driven。工具的并发安全由 Claude Code harness 在代码层管理。

### 真正延后的改进

- **AutoDream 风格记忆整理** — 定期合并 lessons.md 中的近义条目（如把 3 条关于"DIP 违规"的 lesson 合并为 1 条）。有价值，但需要 background agent 基础设施，复杂度高，延后到有实际膨胀问题时再做。

### 本次 Scope 边界

- 只改 safety language 措辞，不改 playbook 功能逻辑
- 只加 PDCA 工作流特定的并行指导，不重复 Claude Code harness 已有的通用指导
- 4 类记忆分类法（user/feedback/project/reference）已与 Claude Code 对齐，不改
