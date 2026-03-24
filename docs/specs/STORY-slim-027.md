# STORY-slim-027: Proactive Quality Sweep — Substring Bugs, Schema Mismatches, and Workflow Gaps

| Field | Value |
|-------|-------|
| ID | STORY-slim-027 |
| Status | Done |
| Priority | P1 |
| Release | 2.3.6 |

## Background

STORY-slim-025/026 修复了 spec_linter W007 substring bug 和 Plan scaffold-first 问题。这些都是用户发现后才修的。通盘审查发现同类问题仍存在于其他文件和流程中：

1. **同类 substring bug**: `issue_sync.py:71` 用 `item_id in title` 做匹配，`STORY-1` 会匹配 `STORY-10`
2. **Schema-Linter 语义矛盾**: `schemas.py` 把 `## Security Scope` 归为 `SPEC_OPTIONAL_SECTIONS`，但 `spec_linter.py` E009 以 ERROR 级别强制检查——两个文件对"是否必须"的定义不一致
3. **E007 flat scan**: Given/When/Then 检查对整个 AC section 做一次 scan，不检查每个 `### AC{N}` 子节是否都有三个关键词
4. **Placeholder 穿透**: W001/W002 只检查 section 存在，scaffold placeholder `(Description of the problem or feature)` 可以通过 lint
5. **Workflow parity gaps**: Design 不跑 `sec-scope`；Act 不跑 `lint`；Act 不移 Story 到 In Progress

### 根因

所有问题的共同模式：**在一个地方修了 bug，但没有搜索其他地方是否存在同类问题**。STORY-slim-025 修了 W007 的 `\b` 问题，但没有检查 `issue_sync.py` 的相同模式；增加了 E009 但没有同步 `SPEC_OPTIONAL_SECTIONS` 的分类。

## Requirements

### R1: Fix issue_sync.py substring matching (MUST)

`issue_sync.py:71` 的 `if item_id in issue.get("title", "")` MUST 改为 word-boundary 匹配。`STORY-1` 不得匹配 `STORY-10` 的 title。

推荐模式：`re.search(re.escape(item_id) + r'(?=\s|:|$)', title)` 或 `re.search(rf"(?<!\w){re.escape(item_id)}(?!\w)", title)`。

### R2: Reconcile Security Scope in schemas.py (MUST)

`SPEC_OPTIONAL_SECTIONS` 中的 `"## Security Scope"` MUST 移到 `SPEC_REQUIRED_SECTIONS`，与 E009 的 ERROR 级别保持一致。

修改后 `SPEC_REQUIRED_SECTIONS = ("## Requirements", "## Acceptance Criteria", "## Security Scope")`。

### R3: E007 per-subsection Given/When/Then check (MUST)

E007 MUST 检查 **每个** `### AC{N}` 子节是否都包含 Given、When、Then 三个关键词，而不是对整个 AC section 做 flat scan。如果某个 AC 子节缺少任一关键词，E007 MUST 报告该子节的 ID。

### R4: Detect scaffold placeholder in W001/W002 (SHOULD)

W001 和 W002 SHOULD 检测 section body 是否仍然是 scaffold placeholder 文本。如果 `## Background` body 包含 `(Description of the problem or feature)` 或 `## Target Call Chain` body 包含 `(Trace call chain here)`，SHOULD 发出 warning。

新增 W008 (placeholder detection) 或扩展 W001/W002 均可。

### R5: Design workflow MUST call sec-scope (SHOULD)

Design workflow 在生成每个 Spec 后 SHOULD 调用 `pactkit sec-scope` 填充 `## Security Scope` section，与 Plan Phase 3.2c 对齐。

### R6: Act workflow SHOULD run lint (SHOULD)

Act Phase 3 在 regression check 之后 SHOULD 运行 `pactkit lint`，使 lint 反馈不必等到 Done Phase 2.5。

### R7: Act SHOULD move Story to In Progress (SHOULD)

Act Phase 0.6 (Consistency Check) 之后 SHOULD 调用 board 操作将 Story 从 Backlog 移到 In Progress。

### R8: scaffold.py create_skill path hardcode fix (SHOULD)

`scaffold.py:209` 硬编码 `~/.claude/skills` 路径 SHOULD 改为使用 `base_dir` 参数或 `{SKILLS_ROOT}` 占位符，以支持 OpenCode 等环境。

### R9: GWT keyword word-boundary (SHOULD)

`spec_linter.py:199` 的 `kw.lower() not in body_lower` SHOULD 改为 `re.search(r'\b' + kw.lower() + r'\b', body_lower)` 以避免 `"when"` 匹配 `"whenever"` 等误判。

### R10: schemas.py MUST include Non-Goals alias (SHOULD)

`SPEC_OPTIONAL_SECTIONS` SHOULD 增加 `"## Non-Goals"` 条目，与 W004 的 alias 接受逻辑保持文档一致。或新增常量 `SPEC_NON_GOALS_SECTION = "Non-Goals"`。

### R11: spec_linter fallback RFC pattern SHOULD derive from tuple (SHOULD)

`spec_linter.py:41` fallback block 中的 RFC keyword regex SHOULD 从 `SPEC_RFC_KEYWORDS` tuple 动态构建，而非硬编码字面量字符串。

## Acceptance Criteria

### AC1: issue_sync STORY-1 does not match STORY-10 (R1)

- **Given** a GitHub issue titled `"STORY-10: Some Feature"`
- **When** `_find_issue("STORY-1")` is called
- **Then** it returns `None` (no match)

### AC2: issue_sync exact match works (R1)

- **Given** a GitHub issue titled `"STORY-1: Some Feature"`
- **When** `_find_issue("STORY-1")` is called
- **Then** it returns the matching issue

### AC3: Security Scope in SPEC_REQUIRED_SECTIONS (R2)

- **Given** `schemas.py` is loaded
- **When** inspecting `SPEC_REQUIRED_SECTIONS`
- **Then** `"## Security Scope"` is in the tuple
- **And** `"## Security Scope"` is NOT in `SPEC_OPTIONAL_SECTIONS`

### AC4: E007 per-subsection check (R3)

- **Given** a spec with 2 ACs where AC1 has Given/When/Then but AC2 only has Given
- **When** running `validate_spec`
- **Then** E007 fires with message mentioning AC2
- **And** E007 does NOT fire for AC1

### AC5: E007 all ACs valid passes (R3)

- **Given** a spec where every AC subsection has Given, When, and Then
- **When** running `validate_spec`
- **Then** E007 does NOT fire

### AC6: W001 detects Background placeholder (R4)

- **Given** a spec with `## Background` containing `(Description of the problem or feature)`
- **When** running `validate_spec`
- **Then** a warning fires mentioning placeholder text

### AC7: W002 detects Target Call Chain placeholder (R4)

- **Given** a spec with `## Target Call Chain` containing `(Trace call chain here)`
- **When** running `validate_spec`
- **Then** a warning fires mentioning placeholder text

### AC8: Design prompt includes sec-scope (R5)

- **Given** the `DESIGN_PROMPT` in `workflows.py`
- **When** inspecting the Spec generation phase
- **Then** `pactkit sec-scope` or `sec-scope` appears in the text

### AC9: Act prompt includes lint step (R6)

- **Given** the `project-act.md` prompt content
- **When** inspecting Phase 3 text
- **Then** `pactkit lint` or lint gate instruction is present

### AC10: Act prompt moves story to In Progress (R7)

- **Given** the `project-act.md` prompt content
- **When** inspecting Phase 0.6 or Phase 1
- **Then** a board operation to set status to "In Progress" is referenced

### AC11: create_skill uses base_dir for path (R8)

- **Given** `scaffold.py` `create_skill()` source code
- **When** inspecting the generated SKILL.md content
- **Then** it uses the `base_dir` parameter or `{SKILLS_ROOT}` placeholder, not hardcoded `~/.claude/skills`

### AC12: GWT uses word boundary (R9)

- **Given** an AC section containing the word `"whenever"` but not standalone `"when"`
- **When** running the GWT keyword check
- **Then** `"when"` is reported as missing (not matched by `"whenever"`)

### AC13: SPEC_OPTIONAL_SECTIONS includes Non-Goals (R10)

- **Given** `schemas.py` is loaded
- **When** inspecting `SPEC_OPTIONAL_SECTIONS` or related constants
- **Then** `"Non-Goals"` appears as a recognized alias

### AC14: Fallback RFC pattern derived from tuple (R11)

- **Given** `spec_linter.py` fallback block source
- **When** inspecting how `SPEC_RFC_PATTERN` is built
- **Then** it uses `SPEC_RFC_KEYWORDS` tuple, not hardcoded keyword string

### AC15: Existing tests pass (regression)

- **Given** all pre-existing tests
- **When** running `.venv/bin/pytest tests/ -v`
- **Then** all tests pass

## Target Call Chain

```
B1: issue_sync._find_issue() → item_id in title (substring) → MUST use re.search

B2: schemas.SPEC_OPTIONAL_SECTIONS contains "## Security Scope"
    spec_linter._check_security_scope() fires E009 (ERROR)
    → Contradiction: optional vs mandatory

G1: spec_linter._check_acceptance_criteria() → flat body_lower scan
    → MUST split into per-AC subsection checks

G2: spec_linter._check_optional_sections() → W001/W002 check presence only
    → SHOULD also detect SPEC_TEMPLATE placeholder text

G3-G7: prompt text changes in workflows.py (Design) and commands.py (Act)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/issue_sync.py` | Fix `_find_issue()` substring match → word-boundary regex (R1) | None | Low |
| 2 | `src/pactkit/schemas.py` | Move `## Security Scope` from OPTIONAL to REQUIRED sections; add Non-Goals alias (R2, R10) | None | Low |
| 3 | `src/pactkit/skills/spec_linter.py` | E007 per-subsection GWT check; W001/W002 placeholder detection; fallback RFC derive from tuple (R3, R4, R9, R11) | Step 2 | Medium |
| 4 | `src/pactkit/prompts/workflows.py` | Design: add sec-scope call after Spec generation (R5) | None | Low |
| 5 | `src/pactkit/prompts/commands.py` | Act: add lint step in Phase 3; add In Progress board move in Phase 0.6 (R6, R7) | None | Low |
| 6 | `src/pactkit/skills/scaffold.py` | Fix create_skill hardcoded path (R8) | None | Low |
| 7 | `tests/unit/test_story_slim027.py` | Tests for AC1-AC14 | Steps 1-6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | issue_sync.py handles GitHub API responses — verify no injection via title string |
| SEC-2 | N/A | No user input handling beyond existing CLI |
| SEC-3 | N/A | No database |
| SEC-4 | N/A | No rendering |
| SEC-5 | N/A | No authentication changes |
| SEC-6 | N/A | No public endpoints |
| SEC-7 | N/A | No error exposure changes |
| SEC-8 | N/A | No dependency changes |

## Out of Scope

- `board.py:29` 注释方向问题——cosmetic，不影响功能
- `commands.py:610-611` Init prompt 中的环境路径硬编码——Init 运行前无法确定环境，设计上的 tradeoff
- Act 完成后不跑 `pactkit context`——Done 流程会做，gap 仅影响 Act→Done 之间的 stale 窗口
- Design 不跑 `pactkit guard`——Design 面向 greenfield 项目，guard 检查的意义有限
- Hotfix 不跑 `pactkit regression`——设计上 Hotfix 用 incremental test-map，已充分
- 新增 linter 规则检查 test case 文件是否存在（跨文件检查超出 spec_linter 范围）
