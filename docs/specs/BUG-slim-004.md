# BUG-slim-004: Cross-Flow Integrity Gaps — Unreferenced CLI & Missing Lint in Hotfix

| Field | Value |
|-------|-------|
| ID | BUG-slim-004 |
| Status | Draft |
| Priority | P2 |
| Release | 2.2.0 |

## Background

A full end-to-end PDCA workflow audit (Plan→Act→Check→Done→Release, Sprint, Hotfix, Design) revealed 3 categories of cross-flow integrity gaps after the STORY-slim-014/015/016 CLI migration:

1. **Hotfix skips lint entirely** — Plan/Act/Done all reference `pactkit lint`, but Hotfix has no lint step at all. Hotfixed code can merge with lint errors.
2. **3 document validators never called** — `pactkit lint-context`, `pactkit lint-lessons`, `pactkit lint-testcase` are registered CLI subcommands with full test coverage, but zero prompt references. Done Phase 3 should use them.
3. **`upgrade` subparser missing `--agent` flag** — `init` and `update` both have `--agent`, but `upgrade` does not, creating a parity gap.
4. **Check Phase 3.1 duplicates `pactkit spec-lint`** — Check manually inspects "Does Spec have `## Acceptance Criteria`?" but `pactkit spec-lint` E006 already validates this. Should delegate.
5. **Design missing `pactkit context`** — Plan/Done/Init all call `pactkit context` to update session context, but Design does not. After `/project-design` creates N stories, `context.md` is stale.

### Target Call Chain

```
Hotfix Phase 2  → (missing) pactkit lint
Done Phase 3    → (missing) pactkit lint-context, pactkit lint-lessons, pactkit lint-testcase
cli.py upgrade  → (missing) --agent argument
Check Phase 3.1 → (duplicate) manual AC check vs pactkit spec-lint E006
Design Phase 5  → (missing) pactkit context
```

## Requirements

### R1: Add lint step to Hotfix flow
MUST update HOTFIX_PROMPT in `workflows.py` to include a lint step after tests pass (Phase 2), referencing `pactkit lint`. This aligns Hotfix with Done Phase 2.7 behavior.

### R2: Reference document validators in Done prompt
MUST update DONE_PROMPT in `commands.py` to call `pactkit lint-context`, `pactkit lint-lessons` (in Phase 3 Hygiene), validating `docs/product/context.md` and `docs/architecture/governance/lessons.md` structure after writing them. These are non-blocking checks (warn only).

### R3: Add `--agent` flag to `upgrade` subparser
MUST add the `--agent` argument to `upgrade_parser` in `cli.py` with the same choices as `init`/`update` (`claude`, `cursor`, `copilot`, `generic`, `all`).

### R4: Forward `--agent` in upgrade handler
MUST forward `args.agent` in the `upgrade` branch of `cli.py` `main()` to `deploy()`. Currently `deploy()` receives `agent` from `init`/`update` branches via `getattr(args, "agent", "claude")` but `upgrade` never sets it.

### R5: Check Phase 3 should use `pactkit spec-lint` for Spec structure verification
MUST update CHECK_PROMPT Phase 3.1 in `commands.py` to run `pactkit spec-lint docs/specs/{STORY_ID}.md` instead of manually checking "Does Spec have `## Acceptance Criteria`?" The E006 rule already validates this.

### R6: Design must call `pactkit context` after board setup
MUST update DESIGN_PROMPT in `workflows.py` to call `pactkit context` after Phase 4 (Board Setup), matching the pattern used by Plan (Phase 3.3), Done (Phase 4.5), and Init (Phase 6).

## Acceptance Criteria

### Scenario 1: Hotfix includes lint step
- **Given** HOTFIX_PROMPT in `workflows.py`
- **When** reading the Phase 2 section
- **Then** it contains `pactkit lint` reference after the test step

### Scenario 2: Done references document validators
- **Given** DONE_PROMPT in `commands.py`
- **When** reading Phase 3 Hygiene section
- **Then** it contains `pactkit lint-context` and `pactkit lint-lessons`

### Scenario 3: upgrade has --agent flag
- **Given** `pactkit upgrade --help`
- **When** reading help output
- **Then** `--agent` appears with choices `claude`, `cursor`, `copilot`, `generic`, `all`

### Scenario 5: Check uses spec-lint for Spec structure
- **Given** CHECK_PROMPT in `commands.py`
- **When** reading Phase 3.1
- **Then** it contains `pactkit spec-lint` reference

### Scenario 6: Design updates context.md
- **Given** DESIGN_PROMPT in `workflows.py`
- **When** reading after Phase 4
- **Then** it contains `pactkit context` reference

### Scenario 7: All existing tests pass
- **Given** all changes applied
- **When** running `pytest tests/ -v`
- **Then** all existing tests pass with zero failures

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/workflows.py` | R1: Add `pactkit lint` to Hotfix Phase 2 | None | Medium |
| 2 | `src/pactkit/prompts/commands.py` | R2: Add `pactkit lint-context`/`pactkit lint-lessons` to Done Phase 3 | None | Medium |
| 3 | `src/pactkit/cli.py` | R3+R4: Add `--agent` to upgrade_parser, forward in handler | None | Low |
| 4 | `src/pactkit/prompts/commands.py` | R5: Add `pactkit spec-lint` to Check Phase 3.1 | None | Low |
| 5 | `src/pactkit/prompts/workflows.py` | R6: Add `pactkit context` to Design after Phase 4 | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No new error handling paths |
| SEC-8 | No | No dependency file changes |
