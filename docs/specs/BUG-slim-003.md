# BUG-slim-003: CLI Migration Gaps — Prompt Inconsistencies & Implementation Mismatches

| Field | Value |
|-------|-------|
| ID | BUG-slim-003 |
| Status | Draft |
| Priority | P1 |
| Release | 2.2.0 |

## Background

STORY-slim-014 migrated ~25 deterministic rules to Python CLI subcommands, but a post-migration audit revealed two categories of gaps:

1. **Prompt inconsistencies**: Three CLI commands (`pactkit next-id`, `pactkit sec-scope`, `pactkit context`) exist but are not called in all relevant command playbooks. Some commands still instruct the LLM to perform the same logic manually, creating divergent execution paths.

2. **Implementation mismatches**: Three modules have minor deviations from their canonical source or spec requirements.

### Current State

**Inconsistencies (CLI exists but prompt doesn't call it):**
- `pactkit next-id`: Called in `project-plan` Phase 3.1, but NOT in `project-sprint` Phase 0, `project-hotfix` Phase 0, or `project-design` Phase 3 — all three still instruct manual `docs/specs/` scanning
- `pactkit sec-scope`: Called in `project-check` Phase 0, but NOT in `project-plan` Phase 3.2 — Plan still asks the agent to manually apply the 8-row SEC detection table
- `pactkit context`: Called in `project-done` Phase 4.5, but NOT in `project-plan` Phase 3.3 or `project-init` Phase 6 — both still ask the agent to write context.md directly

**Implementation mismatches:**
- `cleaners.py`: Java cleanup list is `["target/", "*.class", "build/"]` but canonical `LANG_PROFILES["java"]["cleanup"]` is `["target/", "build/", ".gradle/"]` — `.gradle/` missing, `*.class` is an undocumented addition
- `guards.py`: Only checks `pactkit.yaml` file existence, not content completeness (R1 spec says "config completeness")
- `validators.py`: `lint_lessons()` checks table header/separator but does not validate row format against `LESSONS_ROW_FORMAT` (3-column structure)

## Target Call Chain

```
prompts/commands.py → PLAN_PROMPT / INIT_PROMPT → slimmed text referencing `pactkit next-id`, `pactkit sec-scope`, `pactkit context`
prompts/workflows.py → SPRINT_PROMPT / HOTFIX_PROMPT / DESIGN_PROMPT → slimmed text referencing `pactkit next-id`
src/pactkit/cleaners.py → _CLEANUP_PATTERNS["java"] → aligned with LANG_PROFILES
src/pactkit/guards.py → check_init_markers() → extended with config completeness
src/pactkit/validators.py → lint_lessons() → extended with row format check
```

## Requirements

### R1: Fix prompt inconsistencies — `pactkit next-id`
MUST replace manual `docs/specs/` scanning instructions with `pactkit next-id` calls in:
- `workflows.py` SPRINT_PROMPT Phase 0 (line ~349)
- `workflows.py` HOTFIX_PROMPT Phase 0 (line ~585)
- `workflows.py` DESIGN_PROMPT Phase 3 (line ~739)

### R2: Fix prompt inconsistency — `pactkit sec-scope`
MUST replace the manual SEC-1~SEC-8 detection table application in `commands.py` Plan Phase 3.2 with a call to `pactkit sec-scope <changed-files>`, keeping the detection rules table as reference documentation only.

### R3: Fix prompt inconsistency — `pactkit context`
MUST replace manual context.md writing instructions with `pactkit context` calls in:
- `commands.py` Plan Phase 3.3
- `commands.py` Init Phase 6 (if present)

### R4: Fix cleaners.py Java cleanup list
MUST align `_CLEANUP_PATTERNS["java"]` with canonical `LANG_PROFILES["java"]["cleanup"]`: `["target/", "build/", ".gradle/"]`. Remove `*.class`.

### R5: Extend guards.py config completeness check
SHOULD extend `check_init_markers()` to optionally verify that `pactkit.yaml` contains expected top-level sections (developer, stack, agents, commands, skills, rules). Return missing sections in the result.

### R6: Extend lint_lessons row format validation
SHOULD extend `lint_lessons()` to verify that data rows (lines starting with `|` after the separator) have exactly 3 pipe-delimited columns matching `LESSONS_ROW_FORMAT`.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/workflows.py` | Replace manual scan in SPRINT/HOTFIX/DESIGN with `pactkit next-id` | None | Low |
| 2 | `src/pactkit/prompts/commands.py` | Replace manual SEC table in Plan 3.2 with `pactkit sec-scope` | None | Low |
| 3 | `src/pactkit/prompts/commands.py` | Replace manual context write in Plan 3.3 and Init 6 with `pactkit context` | None | Low |
| 4 | `src/pactkit/cleaners.py` | Align Java cleanup list with LANG_PROFILES | None | Low |
| 5 | `src/pactkit/guards.py` | Add config completeness check | None | Low |
| 6 | `src/pactkit/validators.py` | Add LESSONS_ROW_FORMAT column validation | None | Low |
| 7 | Tests | TDD for Steps 4-6 code changes | Steps 4-6 | Low |

## Acceptance Criteria

### Scenario 1: Sprint/Hotfix/Design call pactkit next-id
- **Given** the SPRINT_PROMPT, HOTFIX_PROMPT, and DESIGN_PROMPT text
- **When** searching for "Scan `docs/specs/`" or "determine the next available number"
- **Then** those phrases are replaced with `pactkit next-id` invocations

### Scenario 2: Plan Phase 3.2 calls pactkit sec-scope
- **Given** the Plan command prompt text
- **When** searching Phase 3.2 Security Scope
- **Then** the text delegates to `pactkit sec-scope` rather than asking the agent to manually apply the detection table

### Scenario 3: Plan and Init call pactkit context
- **Given** the Plan Phase 3.3 and Init Phase 6 prompt text
- **When** searching for context.md generation
- **Then** both delegate to `pactkit context`

### Scenario 4: Java cleanup matches LANG_PROFILES
- **Given** `cleaners.py` `_CLEANUP_PATTERNS["java"]`
- **When** compared with `LANG_PROFILES["java"]["cleanup"]`
- **Then** they are identical: `["target/", "build/", ".gradle/"]`

### Scenario 5: Guards check config completeness
- **Given** a `pactkit.yaml` missing the `developer` section
- **When** running `pactkit guard`
- **Then** the output includes a warning about missing config sections

### Scenario 6: lint_lessons validates row format
- **Given** a lessons.md with a malformed row `| 2026-01 | lesson only |` (2 columns instead of 3)
- **When** running `pactkit lint-lessons`
- **Then** an error is reported about column count mismatch

### Scenario 7: All existing tests pass
- **Given** all changes applied
- **When** running `pytest tests/ -v`
- **Then** 2529+ tests pass with zero failures

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (cleaners.py, guards.py, validators.py) |
| SEC-2 | No | No user input handling changes |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error handling changes |
| SEC-8 | No | No dependency file changes |
