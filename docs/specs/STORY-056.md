# Spec: STORY-056

## Metadata
| Field | Value |
|-------|-------|
| ID | STORY-056 |
| Title | Security Check Scope Filtering |
| Status | Draft |
| Priority | P1 |
| Author | System Architect |
| Created | 2026-02-27 |
| Release | 1.5.0 |

## Summary
Optimize Security Check flow by adding intelligent filtering. Plan Phase analyzes code changes to determine applicable security checks, generates a Security Scope section in the Spec. Check Phase reads the Scope and only executes relevant checks, skipping inapplicable ones to reduce token consumption.

## Background
STORY-055 introduced an 8-item Security Checklist (SEC-1 through SEC-8) in Check Phase 1. Currently:
- All 8 checks run on every Story regardless of what code changed
- No filtering based on file types or code patterns
- Doc-only or test-only changes still trigger full security scan
- This wastes tokens and time on inapplicable checks

## Target Call Chain

```
Plan Phase 1 (Trace)
    └── Analyze changed files and code patterns
            ↓
Plan Phase 3 (Spec)
    └── Generate "## Security Scope" section  ← NEW
            ↓
Check Phase 0 (Prep)
    └── Read Security Scope from Spec  ← NEW
            ↓
Check Phase 1 (Security Scan)
    └── Execute only Applicable=Yes checks  ← MODIFIED
```

## Requirements

### R1: Plan Phase Security Scope Generation
The Plan Phase MUST analyze changed files to determine applicable security checks.

**R1.1**: The analysis MUST use these detection rules:

| Check | Applicable When |
|-------|-----------------|
| SEC-1 (Secrets) | Any source code file modified (`.py`, `.js`, `.ts`, `.go`, `.java`, etc.) |
| SEC-2 (Input) | Code contains `request.`, `form.`, `input`, `argv`, `sys.stdin`, `process.argv` |
| SEC-3 (SQL) | Files in `models/`, `dao/`, `repository/`; or code contains `SELECT`, `INSERT`, `UPDATE`, `DELETE`, ORM patterns |
| SEC-4 (XSS) | Frontend files (`.tsx`, `.vue`, `.svelte`, `.html`); or code contains `innerHTML`, `dangerouslySetInnerHTML`, template rendering |
| SEC-5 (Auth) | Files in `auth/`, `session/`, `login/`; or code contains `token`, `jwt`, `cookie`, `session` |
| SEC-6 (Rate) | Files in `api/`, `routes/`, `endpoints/`, `controllers/`; or new public endpoints added |
| SEC-7 (Error) | Files in `api/`, `routes/`; or code contains exception handling patterns |
| SEC-8 (Deps) | Dependency files modified (`package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`) |

**R1.2**: If ONLY docs/tests modified (files matching `docs/**`, `tests/**`, `*.md`, `README*`), ALL checks SHOULD be marked N/A with reason "docs/tests only".

**R1.3**: Plan Phase 3 MUST generate a `## Security Scope` section in the Spec:
```markdown
## Security Scope
| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified |
| SEC-2 | No | No user input handling |
| SEC-3 | Yes | models/user.py modified |
...
```

### R2: Check Phase Scope Reading
Check Phase 0 MUST read the Security Scope from the Spec.

**R2.1**: If `## Security Scope` section exists in Spec, Check Phase MUST parse it.

**R2.2**: If `## Security Scope` section is missing (legacy Specs), Check Phase SHOULD fall back to current behavior (run all checks).

**R2.3**: The parsed scope MUST be passed to Phase 1 Security Scan.

### R3: Check Phase Filtered Execution
Check Phase 1 MUST only execute checks marked as `Applicable: Yes`.

**R3.1**: For each check marked `No` or `N/A`, output: `SEC-{N}: SKIPPED ({reason})`.

**R3.2**: Checks marked `Yes` MUST still output `PASS`, `FAIL`, or `N/A` as before.

**R3.3**: The Verdict MUST include the full Security Checklist table showing both executed and skipped checks.

### R4: Configuration Override
**R4.1**: If `pactkit.yaml` contains `check.security_checklist: false`, skip ALL checks regardless of Scope (existing behavior preserved).

**R4.2**: A new config option `check.security_scope_override: full` MAY force all checks to run regardless of Spec Scope.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Add Security Scope generation logic to Plan Phase 3 | None | Medium |
| 2 | `src/pactkit/prompts/commands.py` | Add Scope parsing to Check Phase 0 | Step 1 | Low |
| 3 | `src/pactkit/prompts/commands.py` | Modify Check Phase 1 to skip non-applicable checks | Step 2 | Medium |
| 4 | `src/pactkit/config.py` | Add `check.security_scope_override` config option | None | Low |
| 5 | `tests/unit/test_config.py` | Add tests for new config option | Step 4 | Low |

## Acceptance Criteria

### AC1: Plan generates Security Scope for API changes
**Given** a Story that modifies files in `src/api/` directory
**When** `/project-plan` generates the Spec
**Then** the Spec contains `## Security Scope` with SEC-5, SEC-6, SEC-7 marked as `Applicable: Yes`

### AC2: Plan generates minimal scope for docs-only changes
**Given** a Story that only modifies files in `docs/` directory
**When** `/project-plan` generates the Spec
**Then** the Spec contains `## Security Scope` with all checks marked `N/A` with reason "docs only"

### AC3: Check skips non-applicable checks
**Given** a Spec with `## Security Scope` marking SEC-3, SEC-4 as `No`
**When** `/project-check` runs Phase 1
**Then** output shows `SEC-3: SKIPPED (no database code)` and `SEC-4: SKIPPED (no frontend files)`

### AC4: Check falls back for legacy Specs
**Given** a Spec without `## Security Scope` section
**When** `/project-check` runs Phase 1
**Then** all 8 checks execute as before (backward compatible)

### AC5: Config override forces full scan
**Given** `pactkit.yaml` contains `check.security_scope_override: full`
**When** `/project-check` runs on any Story
**Then** all 8 checks execute regardless of Spec Scope

## Out of Scope
- Automatic detection of security issues (still manual review)
- Integration with external security scanners (SAST/DAST)
- Per-project customization of detection rules
