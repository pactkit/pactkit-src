# STORY-slim-018: Systemic Cross-Flow Guards — Automated Validation for Prompt-CLI Integrity

| Field | Value |
|-------|-------|
| ID | STORY-slim-018 |
| Status | Done |
| Priority | High |
| Release | 2.2.1 |

## Background

BUG-slim-003 through BUG-slim-006 collectively found 20+ cross-reference gaps between prompts and CLI subcommands. Each bug was discovered through manual audit and fixed with one-off patches. The root cause is not any individual missing reference — it is the absence of automated validation layers that would prevent this class of bug from recurring.

Four systemic gaps were identified:
1. No test validates that `pactkit <subcommand>` references in prompts point to registered CLI commands
2. LANG_PROFILES key set is independently hardcoded in 5 test files (SSoT violation)
3. Done flow never updates Spec `Status: Draft` to `Status: Done`
4. No declarative cross-flow coverage matrix encoding which flows MUST call which subcommands

## Requirements

### R1: Prompt-to-CLI cross-reference guard test

Create `tests/unit/test_prompt_cli_refs.py` that:
1. Extracts all `pactkit <word>` patterns from every prompt string (all `COMMANDS_CONTENT` values, `SPRINT_PROMPT`, `HOTFIX_PROMPT`, `DESIGN_PROMPT`)
2. Extracts all registered subcommand names from `cli.py`'s argparse subparsers
3. Asserts `found_refs.issubset(registered_subcommands)` — any prompt reference to a nonexistent subcommand MUST fail the test
4. Also asserts the reverse: for each registered subcommand, at least one prompt references it (dead subcommand detection). Exceptions MAY be whitelisted in a `CLI_NO_PROMPT_REF_ALLOWED` set for utility-only commands (e.g., `version`, `upgrade`).

### R2: Canonical LANG_PROFILES key set as single source of truth

1. Define `LANG_PROFILE_REQUIRED_KEYS` in `src/pactkit/schemas.py` (alongside existing schema constants)
2. Update `test_lang_profiles.py`, `test_smart_regression.py`, `test_story050_doc_only_shortcut.py`, `test_bug_slim005.py`, `test_bug_slim006.py` to import from `schemas.py` instead of hardcoding their own key lists
3. Add a test that asserts every LANG_PROFILES entry has exactly the keys defined in `LANG_PROFILE_REQUIRED_KEYS` — one test, one source, all profiles validated

### R3: Done flow MUST update Spec Status to Done

1. Add a step to Done Phase 3 (Hygiene) in `commands.py` that instructs: "Update `| Status | Draft |` to `| Status | Done |` in `docs/specs/{STORY_ID}.md`"
2. Add a `pactkit spec-status` CLI subcommand (or extend `backfill-release`) that programmatically updates the Status field in a spec file
3. Add `SPEC_VALID_STATUSES = ("Draft", "In Progress", "Done")` to `schemas.py`
4. Extend `spec_linter.py` with a new WARN rule (W006) that flags Status values not in `SPEC_VALID_STATUSES`

### R4: Declarative cross-flow coverage matrix test

Create `tests/unit/test_cross_flow_matrix.py` that:
1. Defines a `FLOW_MATRIX` dict mapping each CLI subcommand to the list of prompt keys it MUST appear in
2. For each entry, asserts the subcommand string appears in the corresponding prompt content
3. The matrix MUST cover at minimum: `pactkit context`, `pactkit lint`, `pactkit next-id`, `pactkit spec-lint`, `pactkit test-map`, `pactkit regression`, `pactkit clean`, `pactkit coverage-gate`, `pactkit lesson-append`, `pactkit invariants-refresh`
4. Adding a new subcommand to a flow requires updating this matrix — creating a forcing function

## Acceptance Criteria

### AC1: Prompt-to-CLI guard catches invalid refs
- **Given**: A `pactkit foo-bar` reference is added to any prompt
- **When**: `pytest tests/unit/test_prompt_cli_refs.py` runs
- **Then**: Test MUST fail with "foo-bar not in registered subcommands"

### AC2: Dead subcommand detection
- **Given**: A new CLI subcommand `pactkit xyz` is registered but no prompt references it
- **When**: `pytest tests/unit/test_prompt_cli_refs.py` runs
- **Then**: Test MUST fail with "xyz registered but not referenced in any prompt" (unless whitelisted)

### AC3: LANG_PROFILE_REQUIRED_KEYS is canonical
- **Given**: `schemas.py` defines `LANG_PROFILE_REQUIRED_KEYS`
- **When**: Any of the 5 test files runs
- **Then**: All import the same canonical set; no test file hardcodes its own key list

### AC4: LANG_PROFILES validated against canonical keys
- **Given**: A key is added or removed from `LANG_PROFILES` in `workflows.py`
- **When**: Tests run
- **Then**: Only `schemas.py` needs updating; all 5 test files auto-pick up the change

### AC5: Done updates Spec Status
- **Given**: `COMMANDS_CONTENT["project-done.md"]`
- **When**: Read the prompt
- **Then**: Contains instruction to update Spec Status field to Done

### AC6: spec-lint validates Status values
- **Given**: A spec with `| Status | Foobar |`
- **When**: `pactkit spec-lint` runs
- **Then**: Returns W006 warning "Status value 'Foobar' not in allowed set"

### AC7: Cross-flow matrix test exists and passes
- **Given**: `tests/unit/test_cross_flow_matrix.py`
- **When**: Run the test
- **Then**: All matrix entries pass; at least 10 subcommands are covered

### AC8: Matrix catches missing flow reference
- **Given**: `pactkit context` is removed from `project-done.md`
- **When**: `pytest tests/unit/test_cross_flow_matrix.py` runs
- **Then**: Test MUST fail with "pactkit context missing from project-done.md"

## Out of Scope

- Refactoring existing CLI subcommands or prompt content (this story adds guards, not new functionality)
- Automated Spec Status transition in CI/CD (manual Done step is sufficient for now)
- Backfilling all 47 existing `Status: Draft` specs to `Status: Done` (separate backfill task)
