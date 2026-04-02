# STORY-slim-015: Doctor & Release CLI — Deterministic Diagnostics

| Field | Value |
|-------|-------|
| ID | STORY-slim-015 |
| Status | Draft |
| Priority | P1 |
| Release | 2.2.0 |

## Background

The STORY-slim-014 migration audit identified high-value deterministic operations still executed by LLM prose in the `pactkit-doctor` and `pactkit-release` skills. These operations are pure filesystem/text operations with no AI judgment needed, making them ideal migration candidates.

### Current State

**Doctor skill (`SKILL_DOCTOR_MD`)** — three deterministic operations still in prompt prose:
1. **Orphaned/missing spec cross-reference**: Two-way set diff between `docs/specs/*.md` filenames and `sprint_board.md` story IDs. Currently the LLM reads both, extracts IDs via regex, and reports mismatches manually.
2. **Config drift detection**: Compares `pactkit.yaml` declared agents/rules/skills against files actually deployed on disk. The LLM reads YAML, lists directories, and does set comparison.
3. **Stale graph mtime check**: Compares `docs/architecture/graphs/*.mmd` modification times against newest source file mtime with a >7-day threshold. The LLM runs `stat` commands and does arithmetic.

**Release skill (`SKILL_RELEASE_MD`)** — one deterministic operation:
4. **Spec backfill**: Scans `docs/specs/*.md` for `Release: TBD` and replaces with the actual version string. Currently the LLM does a directory glob, reads each file, regex-matches, and writes back.

**Done command (`project-done.md`)** — one deterministic operation:
5. **Issue tracker sync** (Phase 3.5.5 + 3.6): Full lifecycle of GitHub issue management — search for existing issue, backfill if missing, link to board, close on completion. Entirely structured `gh` CLI orchestration with JSON parsing.

## Target Call Chain

```
pactkit CLI → cli.py → new subcommands:
  pactkit doctor              → doctor.py → check_orphaned_specs(), check_config_drift(), check_stale_graphs()
  pactkit backfill-release VER → backfill.py → scan_and_replace_tbd()
  pactkit issue-sync ID       → issue_sync.py → search_issue(), create_issue(), link_to_board(), close_issue()
```

## Requirements

### R1: pactkit doctor — Orphaned/missing spec detection
MUST implement `check_orphaned_specs(project_root)` that:
- Scans `docs/specs/*.md` for all spec IDs (STORY-*, BUG-*, HOTFIX-*)
- Parses `docs/product/sprint_board.md` for all story IDs (including archived in `docs/product/archive/`)
- Returns orphaned specs (in specs/ but not on board or archive) and missing specs (on board but no spec file)

### R2: pactkit doctor — Config drift detection
MUST implement `check_config_drift(project_root)` that:
- Reads `pactkit.yaml` for enabled agents, commands, skills, rules lists
- Checks that each enabled item has a corresponding deployed file in the expected directory
- Returns list of missing deployments and unexpected deployments

### R3: pactkit doctor — Stale graph detection
MUST implement `check_stale_graphs(project_root, threshold_days=7)` that:
- Finds newest source file mtime (using `LANG_PROFILES[stack].source_dirs` and `file_ext`)
- Compares against `docs/architecture/graphs/*.mmd` mtimes
- Returns list of stale graphs (older than threshold) and missing graphs

### R4: pactkit backfill-release — Spec TBD replacement
MUST implement `scan_and_replace_tbd(specs_dir, version)` that:
- Scans `docs/specs/*.md` for lines matching `| Release | 2.3.0 |`
- For specs whose stories are marked done (all tasks `[x]` on board or in archive), replaces `TBD` with the provided version
- Returns list of backfilled spec files and skipped files (not done yet)

### R5: pactkit issue-sync — GitHub issue lifecycle
SHOULD implement `issue_sync(item_id, project_root)` that:
- Parses item type from ID (STORY-* → skip with message "IP protection", BUG-*/HOTFIX-* → proceed)
- Reads `pactkit.yaml` for `issue_tracker.provider`
- If `github`: checks `gh` CLI availability, searches for existing issue, creates if missing, links URL to board entry, closes on completion
- Returns structured result with actions taken

### R6: CLI wiring
MUST add `doctor`, `backfill-release`, and `issue-sync` subcommands to `cli.py`.

### R7: Prompt delegation
MUST update `SKILL_DOCTOR_MD`, `SKILL_RELEASE_MD`, and Done Phase 3.5.5/3.6 to delegate to the new CLI commands instead of prose instructions.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/doctor.py` (new) | Implement R1-R3 diagnostic functions | None | Low |
| 2 | `src/pactkit/backfill.py` (new) | Implement R4 spec TBD replacement | None | Low |
| 3 | `src/pactkit/issue_sync.py` (new) | Implement R5 GitHub issue lifecycle | None | Medium |
| 4 | `src/pactkit/cli.py` | Add doctor, backfill-release, issue-sync subcommands | Steps 1-3 | Low |
| 5 | `src/pactkit/prompts/skills.py` | Update SKILL_DOCTOR_MD and SKILL_RELEASE_MD | Step 4 | Low |
| 6 | `src/pactkit/prompts/commands.py` | Update Done Phase 3.5.5/3.6 to call `pactkit issue-sync` | Step 4 | Low |
| 7 | Tests | TDD for all new modules | Steps 1-3 | Low |

## Acceptance Criteria

### Scenario 1: pactkit doctor detects orphaned spec
- **Given** `docs/specs/STORY-999.md` exists but STORY-999 is not on the sprint board or in archive
- **When** running `pactkit doctor`
- **Then** output includes "Orphaned: STORY-999 (spec exists, not on board)"

### Scenario 2: pactkit doctor detects missing spec
- **Given** `sprint_board.md` contains STORY-999 entry but `docs/specs/STORY-999.md` does not exist
- **When** running `pactkit doctor`
- **Then** output includes "Missing: STORY-999 (on board, no spec file)"

### Scenario 3: pactkit doctor detects config drift
- **Given** `pactkit.yaml` lists agent `system-architect` but no corresponding deployed file exists
- **When** running `pactkit doctor`
- **Then** output includes a drift warning for the missing agent file

### Scenario 4: pactkit doctor detects stale graphs
- **Given** `code_graph.mmd` was last modified 10 days ago and source files were modified today
- **When** running `pactkit doctor`
- **Then** output includes "Stale: code_graph.mmd (10 days behind source)"

### Scenario 5: pactkit backfill-release replaces TBD
- **Given** `docs/specs/STORY-slim-014.md` contains `| Release | 2.3.0 |` and the story is done
- **When** running `pactkit backfill-release 2.2.0`
- **Then** the file is updated to `| Release | 2.2.0 |`

### Scenario 6: pactkit backfill-release skips incomplete stories
- **Given** `docs/specs/STORY-slim-015.md` contains `| Release | 2.3.0 |` but has unchecked tasks
- **When** running `pactkit backfill-release 2.2.0`
- **Then** the file is NOT modified and output shows "Skipped: STORY-slim-015 (not done)"

### Scenario 7: pactkit issue-sync skips STORY items
- **Given** running `pactkit issue-sync STORY-slim-014`
- **Then** output is "Issue sync skipped for STORY (IP protection)" with exit code 0

### Scenario 8: pactkit issue-sync creates and links BUG issue
- **Given** `pactkit.yaml` has `issue_tracker.provider: github` and `gh` CLI is available
- **And** no existing GitHub issue for BUG-slim-003
- **When** running `pactkit issue-sync BUG-slim-003`
- **Then** a GitHub issue is created and the board entry is updated with the issue link

### Scenario 9: All existing tests pass
- **Given** all changes applied
- **When** running `pytest tests/ -v`
- **Then** all existing tests pass with zero failures

## Out of Scope

- Jira or other issue tracker providers (GitHub only for now)
- Automated CI integration for doctor checks (future: `pactkit doctor` in CI pipeline)
- Doctor checks for test coverage or lint status (covered by existing Done Phase 2.5)

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Multiple source files modified/created |
| SEC-2 | Yes | issue-sync reads user config and passes to `gh` CLI |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No API endpoints |
| SEC-7 | Yes | New CLI commands need error handling for `gh` failures |
| SEC-8 | No | No dependency file changes |
