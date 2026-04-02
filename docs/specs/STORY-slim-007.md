# STORY-slim-007: Document Schema Registry — Centralize Document Structure Rules as Executable Constants

| Field | Value |
|-------|-------|
| ID | STORY-slim-007 |
| Status | Draft |
| Priority | P1 |
| Release | 2.1.0 |
| Depends | STORY-slim-005 (FormatProfile), STORY-slim-006 (template vars) |

## Background

### 当前状态

PactKit 生成/解析 7 种文档类型，但其结构规则散落在 4+ 个文件中：

| 文档类型 | 规则数 | 当前定义位置 | 有 Source of Truth? | 有代码强制? |
|----------|:---:|-------------|:---:|:---:|
| **Spec** | 13 | spec_linter.py (E001-E008, W001-W005) | ✅ | ✅ E 规则阻断 |
| **Sprint Board** | 6 | board.py (`_BACKLOG`, `_IN_PROGRESS`, `_DONE`), scaffold.py (template) | 部分 | 部分 (regex) |
| **context.md** | 6 sections | commands.py 的 3 个 playbook 中重复描述 "Canonical Format" | ❌ 散落 | ❌ |
| **lessons.md** | 1 行格式 | commands.py project-done playbook 文本 | ❌ | ❌ |
| **test_case** | 3 规则 | commands.py project-check playbook 文本 | ❌ | ❌ |
| **pactkit.yaml** | ~20 字段 | config.py `VALID_*` 集合 + `validate_config()` | 部分 | 部分 |
| **Spec template** | 1 模板 | scaffold.py `create_spec()` 内联字符串 | ❌ 内联 | N/A |

**核心问题**：
1. **重复定义**：context.md 的 section 列表在 `/project-plan`、`/project-done`、`/project-init` 三处重复写。改一处漏一处 → bug。
2. **无 Schema 常量**：lessons.md 的行格式、test_case 的 Gherkin 格式只在 prompt 文本里描述，没有可引用的常量。
3. **Spec template 内联**：scaffold.py 的 `create_spec()` 直接写死 metadata 表格式，与 spec_linter.py 的验证规则没有共享常量。
4. **Board 标题层级不统一**：BUG-027 导致 `###` 和 `####` 都被接受，格式不一致。

### 目标

创建 `src/pactkit/schemas.py` 作为所有文档结构规则的 single source of truth。所有消费方（spec_linter, board.py, scaffold.py, playbook 文本）从这里引用，而不是各自定义。

## Requirements

### R1: schemas.py — 文档结构常量注册表 (MUST)

新建 `src/pactkit/schemas.py`，定义以下结构常量：

```python
"""Document structure schemas — single source of truth for all PactKit document formats.

All document creation/parsing/validation code MUST reference constants from this module.
Do NOT hardcode section headers, field names, or format patterns elsewhere.

When modifying a schema:
    1. Update the constant in this file
    2. All consumers auto-pick up the change (spec_linter, board.py, scaffold, playbooks)
    3. Run full test suite to verify consistency
"""

from dataclasses import dataclass

# ─── Spec Schema ────────────────────────────────────────────────────────────

SPEC_REQUIRED_METADATA_FIELDS = ("ID", "Status", "Priority", "Release")

SPEC_REQUIRED_SECTIONS = ("## Requirements", "## Acceptance Criteria")

SPEC_OPTIONAL_SECTIONS = (
    "## Background",
    "## Target Call Chain",
    "## Implementation Steps",
    "## Security Scope",
    "## Out of Scope",
)

SPEC_REQUIREMENT_PATTERN = r"### R\d+:"    # E004
SPEC_AC_PATTERN = r"### AC\d+:|### Scenario \d+:"  # E006
SPEC_GIVEN_WHEN_THEN = ("Given", "When", "Then")  # E007
SPEC_RFC_KEYWORDS = ("MUST", "SHOULD", "MAY", "SHALL", "REQUIRED", "RECOMMENDED")

# ─── Sprint Board Schema ────────────────────────────────────────────────────

BOARD_SECTION_BACKLOG = "## 📋 Backlog"
BOARD_SECTION_IN_PROGRESS = "## 🔄 In Progress"
BOARD_SECTION_DONE = "## ✅ Done"
BOARD_SECTIONS = (BOARD_SECTION_BACKLOG, BOARD_SECTION_IN_PROGRESS, BOARD_SECTION_DONE)

BOARD_TASK_UNCHECKED = "- [ ] "
BOARD_TASK_CHECKED = "- [x] "

# Story title: unified ### level (deprecate #### per BUG-027)
BOARD_STORY_PREFIX = "- **"  # e.g. "- **STORY-slim-007**: title [P1]"

# ─── context.md Schema ──────────────────────────────────────────────────────

CONTEXT_HEADER = "# Project Context (Auto-generated)"
CONTEXT_SECTIONS = (
    "## Sprint Status",
    "## Current Stories",
    "## Recent Completions",
    "## Active Branches",
    "## Key Decisions",
    "## Next Recommended Action",
)

# ─── lessons.md Schema ──────────────────────────────────────────────────────

LESSONS_TABLE_HEADER = "| Date | Lesson | Context |"
LESSONS_TABLE_SEPARATOR = "|------|--------|---------|"
LESSONS_ROW_FORMAT = "| {date} | {lesson} | {context} |"

# ─── Test Case Schema ───────────────────────────────────────────────────────

TEST_CASE_TITLE_FORMAT = "# Test Cases: {id} — {description}"
TEST_CASE_SCENARIO_PATTERN = r"## TC-\d+:"
TEST_CASE_KEYWORDS = ("**Given**", "**When**", "**Then**")

# ─── Spec Template (used by scaffold.py) ────────────────────────────────────

SPEC_TEMPLATE = """# {id}: {title}

| Field | Value |
|-------|-------|
| ID | {id} |
| Status | Draft |
| Priority | P1 |
| Release | 2.3.0 |

## Background

(Description of the problem or feature)

## Requirements

### R1: (Requirement Name) (MUST)

(Description)

## Acceptance Criteria

### AC1: (Scenario Name)

- **Given** (precondition)
- **When** (action)
- **Then** (expected result)

## Out of Scope

- (Items explicitly excluded)
"""
```

### R2: spec_linter.py 引用 schemas (MUST)

spec_linter.py 的规则硬编码字符串改为引用 `schemas.py` 常量：

```python
# Before (inline)
if "## Requirements" not in lines: ...
if not re.search(r"### R\d+:", content): ...

# After (from schema)
from pactkit.schemas import SPEC_REQUIRED_SECTIONS, SPEC_REQUIREMENT_PATTERN
if SPEC_REQUIRED_SECTIONS[0] not in lines: ...
if not re.search(SPEC_REQUIREMENT_PATTERN, content): ...
```

### R3: board.py 引用 schemas (MUST)

board.py 的 `_BACKLOG`, `_IN_PROGRESS`, `_DONE` 改为引用 schemas：

```python
# Before (inline constants)
_BACKLOG = '## 📋 Backlog'
_IN_PROGRESS = '## 🔄 In Progress'
_DONE = '## ✅ Done'

# After (from schema)
from pactkit.schemas import BOARD_SECTION_BACKLOG, BOARD_SECTION_IN_PROGRESS, BOARD_SECTION_DONE
_BACKLOG = BOARD_SECTION_BACKLOG
_IN_PROGRESS = BOARD_SECTION_IN_PROGRESS
_DONE = BOARD_SECTION_DONE
```

注意：board.py 作为独立部署的 skill 脚本，不能 `import pactkit`。需要在部署时由 deployer 注入，或在 board.py 头部保持内联定义但加注释引向 source of truth。

### R4: scaffold.py 引用 SPEC_TEMPLATE (MUST)

scaffold.py 的 `create_spec()` 改为使用 `SPEC_TEMPLATE`：

```python
# Before
content = f"# {i}: {t}\n\n| Field | Value |\n|-------|-------|\n| ID | {i} |..."

# After
from pactkit.schemas import SPEC_TEMPLATE
content = SPEC_TEMPLATE.format(id=i, title=t)
```

同样有独立部署问题 — scaffold.py 的 SPEC_TEMPLATE 需要内联但标注 source of truth。

### R5: Playbook 中 context.md 格式统一引用 (MUST)

commands.py 中 3 处 "Context.md Canonical Format (see Shared Protocols)" 改为引用 `CONTEXT_SECTIONS` 常量列出的 section 名：

```markdown
Update `docs/product/context.md` with the following sections:
{CONTEXT_SECTIONS}
Set "Last updated by" to `/{command_name}`.
```

用 `{CONTEXT_SECTIONS}` 模板变量，渲染时从 schemas.py 导入列表生成文本。

### R6: Playbook 中 lessons.md 格式统一 (SHOULD)

commands.py project-done 的 lessons 追加规则改为引用 `LESSONS_ROW_FORMAT`：

```markdown
Append a row: `{LESSONS_ROW_FORMAT}`
```

### R7: 文档格式查询命令 `pactkit schema` (SHOULD)

新增 CLI 子命令 `pactkit schema [type]`，输出指定文档类型的结构规则：

```bash
$ pactkit schema spec
Spec Document Schema:
  Required Metadata: ID, Status, Priority, Release
  Required Sections: ## Requirements, ## Acceptance Criteria
  Requirement Pattern: ### R{N}: (description) (RFC 2119)
  AC Pattern: ### AC{N}: (scenario)
  AC Keywords: Given, When, Then

$ pactkit schema board
Sprint Board Schema:
  Sections: ## 📋 Backlog, ## 🔄 In Progress, ## ✅ Done
  Story Format: - **{ID}**: title [priority]
  Task Format: - [ ] unchecked / - [x] checked

$ pactkit schema --all
(outputs all document types)
```

## Acceptance Criteria

### AC1: schemas.py 存在且包含所有文档类型

- **Given** `src/pactkit/schemas.py`
- **When** 导入模块
- **Then** 包含 Spec (7+), Board (5+), Context (6+), Lessons (3+), TestCase (3+) 常量

### AC2: spec_linter 从 schemas 引用

- **Given** `src/pactkit/skills/spec_linter.py`
- **When** 搜索 `"## Requirements"` 等硬编码字符串
- **Then** 改为 `SPEC_REQUIRED_SECTIONS[0]` 等 schema 引用

### AC3: scaffold SPEC_TEMPLATE 统一

- **Given** 通过 `create_spec` 生成的 Spec 文件
- **When** 用 `pactkit spec-lint` 验证
- **Then** 0 个 ERROR（模板与 linter 规则一致）

### AC4: context.md section 列表单一定义

- **Given** `commands.py` 的 project-plan, project-done, project-init playbook
- **When** 搜索 context.md section 列表
- **Then** 只引用 `{CONTEXT_SECTIONS}` 变量，不再内联列出 section 名

### AC5: `pactkit schema spec` 输出正确

- **Given** 运行 `pactkit schema spec`
- **When** 检查输出
- **Then** 包含 `## Requirements`, `### R{N}:`, `Given/When/Then` 等规则

### AC6: 全量测试通过

- **Given** 修改后的代码
- **When** 运行 `pytest tests/ -v`
- **Then** 2269+ 通过，0 失败

## Implementation Steps

| Step | File | Action | Risk |
|------|------|--------|------|
| 1 | `src/pactkit/schemas.py` (NEW) | 创建文档结构常量注册表 | Low |
| 2 | `src/pactkit/skills/spec_linter.py` | 引用 schemas 常量替代内联字符串 | Medium |
| 3 | `src/pactkit/skills/scaffold.py` | 内联 SPEC_TEMPLATE 标注 source of truth；独立部署脚本不能 import | Low |
| 4 | `src/pactkit/skills/board.py` | 内联 Board 常量标注 source of truth | Low |
| 5 | `src/pactkit/prompts/commands.py` | context.md/lessons.md 格式引用统一 | Medium |
| 6 | `src/pactkit/generators/deployer.py` | `_render_prompt` 添加 `{CONTEXT_SECTIONS}` 变量 | Low |
| 7 | `src/pactkit/cli.py` | 新增 `pactkit schema` 子命令 | Low |
| 8 | Tests | 新增 schemas 单元测试 + 一致性验证 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1~8 | No | 常量提取，无逻辑变更 |

## Out of Scope

- pactkit.yaml 的 JSON Schema 验证（独立 Story）
- BUG-027 Board `####` 弃用（独立修复）
- 新增 Spec section 类型（保持现有规则）
