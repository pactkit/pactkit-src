# STORY-slim-017: Done Phase Deterministic Gate Migration — Lessons, Invariants, Coverage

| Field | Value |
|-------|-------|
| ID | STORY-slim-017 |
| Status | Draft |
| Priority | P2 |
| Release | 2.2.0 |

## Background

The full-flow PDCA audit after STORY-slim-014/015/016 identified that Done Phase 2.5 and Phase 3 still contain the largest blocks of deterministic logic executed manually by the LLM:

1. **Done Phase 3.3 Lessons auto-append** — Specificity check (references concrete file/function?), dedup check (different from last 5 entries?), formatted row append. Pure regex/text operations.
2. **Done Phase 3.4 Invariants refresh** — Read `rules.md`, find test count pattern (`All {N}+ tests`), replace with actual count. Pure regex replacement.
3. **Done Phase 2.5/Step 2.5 Coverage verification** — Construct `pytest --cov=<modules>`, parse output, apply 3-tier threshold (>=80% PASS, 50-79% WARN, <50% BLOCK). Mechanical command construction + threshold comparison.
4. **Done Phase 3.6 Board issue URL parsing** — Regex extract `[#N](url)` from sprint board markdown. Pure regex.

These four operations have no AI judgment component — they are pattern matching, config reading, and formatted output. Migrating them to CLI commands follows the same pattern as STORY-slim-014 (guards, cleaners, validators) and STORY-slim-015 (doctor, backfill, issue-sync).

### Current State (MANUAL_IN_PROMPT)

Each Done invocation, the LLM must:
- Read lessons.md tail, check for duplicates, format and append a row
- Read rules.md, regex-find the test count line, replace the number
- Construct pytest --cov command with changed module paths, parse coverage output, compare against 3 thresholds
- Parse sprint board markdown for `[#123](https://...)` patterns

### Target State (CLI_DELEGATED)

```
pactkit lesson-append --story STORY-XXX --text "lesson text" --context "file.py:func"
pactkit invariants-refresh --test-count 2587
pactkit coverage-gate <changed-files>
```

### Target Call Chain

```
Done Phase 3.3 → pactkit lesson-append → lessons.py → append_lesson()
Done Phase 3.4 → pactkit invariants-refresh → invariants.py → refresh_test_count()
Done Phase 2.5 → pactkit coverage-gate → coverage_gate.py → check_coverage()
```

## Requirements

### R1: pactkit lesson-append — Lessons auto-append with dedup
MUST implement `append_lesson(project_root, story_id, text, context)` that:
- Reads `docs/architecture/governance/lessons.md`
- Checks specificity: does `text` reference a concrete file path, function name, or code pattern? (regex for `.py`, `.ts`, `()`, `/`)
- Checks dedup: is `text` meaningfully different from the last 5 entries? (Jaccard similarity on word sets, threshold < 0.5)
- If both pass: appends row `| {YYYY-MM-DD} | {text} | {story_id} |`
- Returns `{"action": "appended"|"skipped", "reason": str}`

### R2: pactkit invariants-refresh — Test count update
MUST implement `refresh_test_count(project_root, test_count)` that:
- Reads `docs/architecture/governance/rules.md`
- Finds line matching `All \d+\+ tests must pass`
- Replaces the number with `test_count`
- Writes the file back
- Returns `{"action": "updated"|"skipped"|"not_found", "old_count": int, "new_count": int}`
- If `rules.md` does not exist, returns skip result

### R3: pactkit coverage-gate — Coverage verification
MUST implement `check_coverage(changed_files, project_root)` that:
- Detects stack (reuse `cleaners.detect_stack()`)
- Extracts module paths from changed source files (e.g., `src/pactkit/foo.py` → `pactkit.foo`)
- Constructs and runs `pytest --cov=<modules> --cov-report=term-missing tests/`
- Parses the coverage output for per-file percentages
- Applies 3-tier threshold: >=80% PASS, 50-79% WARN, <50% BLOCK
- Returns `{"files": [{"file": str, "coverage": int, "status": "pass"|"warn"|"block"}], "overall": "pass"|"warn"|"block"}`
- If `pytest-cov` is not installed, returns skip result

### R4: CLI wiring
MUST add `lesson-append`, `invariants-refresh`, and `coverage-gate` subcommands to `cli.py`:
- `pactkit lesson-append --story ID --text "..." [--context "..."]`
- `pactkit invariants-refresh --test-count N`
- `pactkit coverage-gate <file1> [file2...]`

### R5: Prompt delegation
MUST update DONE_PROMPT in `commands.py` to delegate:
- Phase 3.3: replace lessons prose with `pactkit lesson-append`
- Phase 3.4: replace invariants prose with `pactkit invariants-refresh --test-count {N}`
- Phase 2.5/Step 2.5: replace coverage prose with `pactkit coverage-gate <changed-files>`

## Acceptance Criteria

### Scenario 1: Lesson appended when specific and non-duplicate
- **Given** lessons.md exists with 5+ entries
- **And** text references a concrete file `"cleaners.py _CLEANUP_PATTERNS..."`
- **And** text is different from all last 5 entries
- **When** running `pactkit lesson-append --story STORY-017 --text "..."`
- **Then** a new row is appended with today's date

### Scenario 2: Lesson skipped when duplicate
- **Given** last entry in lessons.md contains "cleaners.py"
- **When** running `pactkit lesson-append` with near-identical text about cleaners.py
- **Then** returns `{"action": "skipped", "reason": "duplicate of recent entry"}`

### Scenario 3: Invariants updated
- **Given** rules.md contains `All 2572+ tests must pass`
- **When** running `pactkit invariants-refresh --test-count 2587`
- **Then** rules.md now contains `All 2587+ tests must pass`

### Scenario 4: Coverage gate warns on low coverage
- **Given** a changed file with 65% coverage
- **When** running `pactkit coverage-gate src/pactkit/foo.py`
- **Then** output status is "warn" for that file

### Scenario 5: Coverage gate skips when pytest-cov unavailable
- **Given** pytest-cov is not installed
- **When** running `pactkit coverage-gate src/pactkit/foo.py`
- **Then** returns skip result with reason

### Scenario 6: All existing tests pass
- **Given** all changes applied
- **When** running `pytest tests/ -v`
- **Then** all existing tests pass with zero failures

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/lessons.py` (new) | R1: lesson append with dedup | None | Low |
| 2 | `src/pactkit/invariants.py` (new) | R2: test count refresh | None | Low |
| 3 | `src/pactkit/coverage_gate.py` (new) | R3: coverage verification | None | Medium |
| 4 | `src/pactkit/cli.py` | R4: 3 new subcommands | Steps 1-3 | Low |
| 5 | `src/pactkit/prompts/commands.py` | R5: prompt delegation | Step 4 | Medium |

## Out of Scope

- Migrating the full regression decision tree (Done 2.5 Steps 1.7+2) — kept as prompt-level logic since it involves judgment calls about "recent", "high-fan-in", suite size estimation
- HLD consistency check (Done 2.3) — involves AI judgment about component mapping
- Board task marking (Act Phase 4) — requires interactive user flow

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified/created |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No API endpoints |
| SEC-7 | Yes | subprocess execution (pytest --cov) needs error handling |
| SEC-8 | No | No dependency file changes |
