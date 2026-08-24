"""Document structure schemas — single source of truth for all PactKit document formats.

All document creation/parsing/validation code MUST reference constants from this module.
Do NOT hardcode section headers, field names, or format patterns elsewhere.

When modifying a schema:
    1. Update the constant in this file
    2. All consumers auto-pick up the change (spec_linter, board.py, scaffold, playbooks)
    3. Run full test suite to verify consistency

When adding a new document type:
    1. Add a clearly-separated section below (use the ─── separator style)
    2. Define all structural constants (headers, patterns, formats)
    3. Add the type to the SCHEMA_REGISTRY at the bottom
"""

# ─── Spec Schema ────────────────────────────────────────────────────────────

SPEC_REQUIRED_METADATA_FIELDS = ("ID", "Status", "Priority", "Release")

SPEC_REQUIRED_SECTIONS = ("## Requirements", "## Acceptance Criteria", "## Security Scope")

SPEC_OPTIONAL_SECTIONS = (
    "## Background",
    "## Target Call Chain",
    "## Implementation Steps",
    "## Out of Scope",
    "## Non-Goals",
    "## Dependency Surface",
)

# ─── Dependency Surface Schema (STORY-slim-143) ─────────────────────────────
# Machine-readable story dependency declaration in each Spec. Consumed by
# spec_linter (E010/W011) and `pactkit spec-graph` (DAG / waves / conflicts).

DEP_SURFACE_SECTION = "Dependency Surface"
DEP_SURFACE_FIELDS = ("Depends on", "Provides", "Touches", "Conflict risk")
DEP_SURFACE_RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")

# Story/bug/hotfix ID pattern: historical sequential IDs plus decentralized IDs.
# Decentralized timestamp form (\d{8}[0-9a-f]{12}) MUST come before the generic
# \d+ branch in the alternation — otherwise findall() short-matches the
# timestamp's 8-digit prefix and never reaches the hex suffix.
ITEM_ID_PATTERN = (
    r"(?:STORY|HOTFIX|BUG)(?:-[a-z]+)?-"
    r"(?:\d{8}[0-9a-f]{12}|\d+(?:-[0-9a-f]{4,32})?)"
)

# E004: requirement subsection pattern
SPEC_REQUIREMENT_PATTERN = r"### R\d+[:\s]"

# E006: acceptance criteria subsection pattern
SPEC_AC_PATTERN = r"### AC\d+[:\s]|### Scenario\s+\d+[:\s]"

# E007: Given/When/Then keywords (stored as-is; linter lowercases for matching)
SPEC_GIVEN_WHEN_THEN = ("Given", "When", "Then")

# W003: RFC 2119 keywords for requirement strength
SPEC_RFC_KEYWORDS = ("MUST", "SHOULD", "MAY", "SHALL", "REQUIRED", "RECOMMENDED", "OPTIONAL")

# Compiled RFC2119 pattern (for use in spec_linter)
import re as _re  # noqa: E402

SPEC_RFC_PATTERN = _re.compile(r"\b(" + "|".join(SPEC_RFC_KEYWORDS) + r")\b")

# E009: Security Scope section name and SEC-* entry pattern
SPEC_SECURITY_SCOPE_SECTION = "Security Scope"
# Accepts both pipe-table rows (| SEC-1 | ...) and heading format (### SEC-1:)
SPEC_SEC_PATTERN = r"\|\s*SEC-|^###\s*SEC-"

# DEFERRED comment pattern for tracking skipped SHOULD requirements (STORY-slim-105)
DEFERRED_COMMENT_PATTERN = _re.compile(r"#\s*DEFERRED\(SHOULD\):\s*R\d+")

# ─── Spec Template ──────────────────────────────────────────────────────────
# Used by scaffold.py create_spec(). Must be consistent with spec_linter rules.
# IMPORTANT: scaffold.py (deployed as standalone script) inlines a copy of this
# template. When updating here, also update src/pactkit/skills/scaffold.py.

SPEC_TEMPLATE = """\
# {id}: {title}

| Field | Value |
|-------|-------|
| ID | {id} |
| Status | Draft |
| Priority | P1 |
| Release | TBD |

## Background

(Description of the problem or feature)

## Requirements

### R1: (Requirement Name) (MUST)

(Description)

## Acceptance Criteria

### AC1: (Scenario Name) (R1)

- **Given** (precondition)
- **When** (action)
- **Then** (expected result)

## Target Call Chain

(Trace call chain here)

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/example.py` | (Description) | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | (Reason) |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | None |
| Touches | (files this story modifies) |
| Conflict risk | LOW |

## Out of Scope

- (Items explicitly excluded)
"""

# ─── Spec Status Values ──────────────────────────────────────────────────────

SPEC_VALID_STATUSES = ("Draft", "In Progress", "Done")

# ─── LANG_PROFILES Key Schema ───────────────────────────────────────────────
# Canonical key set for LANG_PROFILES entries in workflows.py.
# All test files MUST import this instead of hardcoding their own key lists.

LANG_PROFILE_REQUIRED_KEYS = frozenset({
    "test_runner",
    "file_ext",
    "source_dirs",
    "test_map_pattern",
    "lint_command",
})

# ─── Sprint Board Schema ─────────────────────────────────────────────────────
# board.py (deployed as standalone skill script) maintains inline copies of these
# constants. When updating here, also update src/pactkit/skills/board.py.

BOARD_SECTION_BACKLOG = "## 📋 Backlog"
BOARD_SECTION_IN_PROGRESS = "## 🔄 In Progress"
BOARD_SECTION_DONE = "## ✅ Done"
BOARD_SECTIONS = (BOARD_SECTION_BACKLOG, BOARD_SECTION_IN_PROGRESS, BOARD_SECTION_DONE)

BOARD_TASK_UNCHECKED = "- [ ] "
BOARD_TASK_CHECKED = "- [x] "

# Story entry format: "- **STORY-slim-007**: Title [P1]"
BOARD_STORY_PREFIX = "- **"

# ─── context.md Schema ───────────────────────────────────────────────────────
# Canonical format for docs/product/context.md.
# Used by _render_prompt() via {CONTEXT_SECTIONS} template variable.
# Every /project-* command that writes context.md MUST use these sections.

CONTEXT_HEADER = "# Project Context (Auto-generated)"

CONTEXT_SECTION_CONTINUATION = "## Agent Continuation"

CONTEXT_SECTIONS = (
    "## Sprint Status",
    "## Current Stories",
    "## Recent Completions",
    "## Active Branches",
    "## Key Decisions",
    "## Next Recommended Action",
    CONTEXT_SECTION_CONTINUATION,
)

# Rendered section list for use in playbook templates ({CONTEXT_SECTIONS} variable)
CONTEXT_SECTIONS_TEXT = "\n".join(f"- `{s}`" for s in CONTEXT_SECTIONS)

# ─── lessons.md Schema ───────────────────────────────────────────────────────

LESSONS_TABLE_HEADER = "| Date | Lesson | Context |"
LESSONS_TABLE_SEPARATOR = "|------|--------|---------|"
LESSONS_ROW_FORMAT = "| {date} | {lesson} | {context} |"
LESSONS_MAX_ROWS = 50

# ─── Test Case Schema ─────────────────────────────────────────────────────────

TEST_CASE_TITLE_FORMAT = "# Test Cases: {id} — {description}"
TEST_CASE_SCENARIO_PATTERN = r"## TC-\d+[:\s]"
TEST_CASE_KEYWORDS = ("**Given**", "**When**", "**Then**")

# File naming: docs/test_cases/{ID}_case.md
TEST_CASE_FILE_PATTERN = "{id}_case.md"

# ─── Trace Config Schema ────────────────────────────────────────────────────
# Optional pactkit.yaml `trace` section keys for topology-aware tracing.
# ApiCallParser and AgentParser read these at init time; all keys are optional.

TRACE_CONFIG_KEYS = frozenset({
    "fetch_functions",    # list[str] — custom fetch function names for ApiCallParser
    "agent_strategies",   # list[str] — enabled AgentParser strategies (langgraph/yaml/mcp/a2a)
    "agent_markers",      # list[str] — extra marker paths for declarative agent detection
})

# ─── Schema Registry ─────────────────────────────────────────────────────────
# Used by `pactkit schema` CLI command for discovery.

SCHEMA_REGISTRY = {
    "spec": {
        "description": "Feature specification / bug report",
        "required_metadata": SPEC_REQUIRED_METADATA_FIELDS,
        "required_sections": SPEC_REQUIRED_SECTIONS,
        "optional_sections": SPEC_OPTIONAL_SECTIONS,
        "patterns": {
            "requirement": SPEC_REQUIREMENT_PATTERN,
            "acceptance_criteria": SPEC_AC_PATTERN,
        },
        "keywords": {
            "rfc2119": SPEC_RFC_KEYWORDS,
            "given_when_then": SPEC_GIVEN_WHEN_THEN,
        },
        "dependency_surface": {
            "section": DEP_SURFACE_SECTION,
            "fields": DEP_SURFACE_FIELDS,
            "risk_levels": DEP_SURFACE_RISK_LEVELS,
        },
    },
    "board": {
        "description": "Sprint board (docs/product/sprint_board.md)",
        "sections": BOARD_SECTIONS,
        "task_unchecked": BOARD_TASK_UNCHECKED,
        "task_checked": BOARD_TASK_CHECKED,
    },
    "context": {
        "description": "Session context (docs/product/context.md)",
        "header": CONTEXT_HEADER,
        "sections": CONTEXT_SECTIONS,
    },
    "lessons": {
        "description": "Lessons learned (docs/architecture/governance/lessons.md)",
        "table_header": LESSONS_TABLE_HEADER,
        "row_format": LESSONS_ROW_FORMAT,
    },
    "testcase": {
        "description": "Test cases (docs/test_cases/{ID}_case.md)",
        "title_format": TEST_CASE_TITLE_FORMAT,
        "keywords": TEST_CASE_KEYWORDS,
    },
}
