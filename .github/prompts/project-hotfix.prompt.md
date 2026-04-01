---
mode: agent
description: "Hotfix fast track: lightweight fix path that bypasses PDCA"
---

# Command: Hotfix (v1.3.0 Traceable Fast Track)
- **Usage**: `/project-hotfix "$ARGUMENTS"`
- **Agent**: Senior Developer

> **PRINCIPLE**: This command is a lightweight fast-fix channel with traceability.
> Lightweight Spec + Board entry are auto-created. No TDD workflow required.
> Suitable for typos, configuration changes, style adjustments, obvious bugs, and other minor fixes.
> **Spec Lint Gate exemption**: This path SKIPS the Spec Lint Gate (Phase 0.5 in `/project-act`). Hotfix Specs use a lightweight format and are not subject to full structural validation.

## ⚠️ Scope of Application
- ✅ Fix typos / spelling errors
- ✅ Modify configuration files
- ✅ Adjust style / formatting
- ✅ Fix obvious small bugs (single file, clear logic)
- ❌ New feature development → use `/project-plan` + `/project-act`
- ❌ Multi-module refactoring → use `/project-plan` + `/project-act`

## 🧠 Phase 0: Locate & Register
1.  **Parse**: Understand what needs to be fixed from `$ARGUMENTS`.
2.  **Locate**: Use `Grep` or `Glob` to quickly locate the target file and code line.
3.  **Assess**: Confirm this is a minor fix (suitable for Hotfix), not a change requiring full PDCA.
    - If the assessment reveals a complex change, **proactively suggest the user switch to** `/project-plan`.
4.  **Assign HOTFIX-ID**: Run `pactkit next-id` from the terminal to get the next STORY number, then use HOTFIX-{developer}-{NNN} pattern (e.g., HOTFIX-slim-001). The numeric part should match the next-id output.
5.  **Create Spec**: Create a lightweight Spec at `docs/specs/HOTFIX-{NNN}.md` with:
    - Title, Background (one sentence), Target file/line, and what was fixed.
6.  **Add Board Entry**: Add the hotfix to the Board:
    - `python3 .github/skills/pactkit-board/scripts/board.py add_story HOTFIX-{NNN} "Short title" "Fix description"`

## 🔧 Phase 1: Fix
1.  **Fix**: Use `Edit` or `Write` to directly fix the target code.
2.  **Scope**: Keep the modification scope as small as possible — only change what must be changed, no extra optimization or refactoring.
3.  **No Side Effects**: Ensure the modification does not introduce new dependencies or change interface signatures.

## ✅ Phase 2: Verify
1.  **Run Tests (Incremental)**: Run `pactkit test-map <changed-files>` from the terminal to find related test files, then run only those tests (e.g., `pytest tests/unit/test_foo.py -q`). Fallback to full suite if no mapping.
2.  **Run Lint**: Run the project linter (e.g., `ruff check src/ tests/` for Python, `npm run lint` for Node) to verify no lint errors in changed files. If run the project linter is unavailable, fall back to the stack's lint command directly.
3.  **On Failure**: If tests or lint fail:
    - Output the failing test name and error message
    - **Do not auto-rollback** — let the user decide whether to continue
    - Suggestion: check whether the fix is correct, or switch to `/project-act` for the full workflow

## 📦 Phase 3: Commit
1.  **Conventional Commit**: Generate a standardized commit message:
    - Format: `fix(scope): short description for HOTFIX-{NNN}`
    - Infer scope from the modified file path (e.g. `config`, `auth`, `ui`)
2.  **Confirm**: **Must ask the user for confirmation** before executing `git commit`.
    - Output: "Suggested commit: `fix(scope): description`. Confirm commit?"
3.  **Execute**: After user confirmation, execute git add + git commit.
4.  **Update Board**: Run `python3 .github/skills/pactkit-board/scripts/board.py update_task HOTFIX-{NNN} "Task Name"` for each task to mark it done.

## 📋 Phase 3.5: Session Context Update
1.  **Update Context**: Generate `docs/product/context.md` manually (Sprint Status, Current Stories, Recent Completions, Active Branches, Key Decisions, Next Recommended Action) to regenerate `docs/product/context.md`. Set "Last updated by" to `/project-hotfix`.

## 🚫 What This Command Does NOT Do
- Does not require writing tests before code (no TDD)
- Does not run `visualize` to update architecture graphs


---

## Rules Reference

# Core Protocol

## Session Context
On new session, check `.github/pactkit.yaml` exists. If not, run `pactkit init --format copilot` from the terminal.
If `.github/pactkit.yaml` does not exist (check `.github/`), run `pactkit init --format copilot` from the terminal to create it before proceeding.
Then read `docs/product/context.md` to understand project state before taking action.
If the file is missing, suggest `/project-init` to bootstrap the project.
If "Last updated" date is before today, suggest running `$daily-retro`.

## Visual First
Before modifying code:
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py` to view file dependency graph
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode class` for class inheritance
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode call --entry <func>` to trace call chains
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode module` for module-level architectural overview
- **PDCA Exemption**: When a PDCA command is active, the command's own visualize phases take precedence — skip Visual First.

## Strict TDD
- Write tests first (RED), then write implementation (GREEN)
- The agent MUST NOT skip TDD except when running `/project-hotfix`
- All tests must pass before committing

## Language Matching
- Match the user's language (Chinese→Chinese, English→English).
- Technical terms (function names, file paths, git commands) stay in original form.


# The Hierarchy of Truth
> **CRITICAL**: Code is NOT the law.
1.  **Tier 1**: **Specs** (`docs/specs/*.md`) & **Test Cases** (`docs/test_cases/*.md`).
2.  **Tier 2**: **Tests** (The verification of the law).
3.  **Tier 3**: **Implementation** (The mutable reality).

## Conflict Resolution Rules
- When Spec conflicts with code: **Spec takes precedence**, modify the code
- When Spec conflicts with tests: **Spec takes precedence**, modify the tests
- When the Spec itself is found to be incorrect: fix the Spec first, then sync code and tests

## RFC Protocol (Spec Amendment Escalation)
- If the Senior Developer determines a Spec requirement is technically infeasible, contradictory, or would violate security/architectural constraints, they MUST invoke the RFC Protocol rather than producing non-compliant code
- RFC Protocol: STOP implementation, report the infeasibility to the user, suggest alternatives, and wait for guidance
- This exception does NOT weaken the general principle (Spec > Code) — it adds a safety valve for genuinely impossible requirements

## Pre-existing Test Protocol
- If a pre-existing test fails during regression, **do not modify** the failing test or the code it tests
- STOP and report: which test failed, what it tests, which change caused it
- You MUST NOT assume you understand the design intent behind pre-existing tests

## Operating Guidelines
- Before modifying code, you must first read the relevant Spec (`docs/specs/`)
- Before modifying tests, you must first read the corresponding Test Case (`docs/test_cases/`)
- When unsure whether a Spec exists, use `Glob` to search `docs/specs/*.md` (covers STORY-*, HOTFIX-*, BUG-* prefixes)
- **Exemption**: `/project-plan` and `/project-design` create new Specs — they are exempt from "read Spec before modifying code" since the Spec does not yet exist.

# File Atlas

| Path | Purpose |
|------|---------|
| `docs/specs/{ID}.md` | **The Law** -- Requirement Specifications (Spec) |
| `commands/*.md` | **The Playbooks** -- Command Execution Logic |
| `docs/product/sprint_board.md` | Sprint Board -- Current Iteration Board |
| `docs/test_cases/{ID}_case.md` | Test Cases -- Gherkin Acceptance Scenarios |
| `docs/architecture/graphs/*.mmd` | Architecture Graphs -- Mermaid Architecture Diagrams |
| `tests/unit/` | Unit Tests |
| `tests/e2e/` | E2E Integration Tests |
| `docs/product/archive/` | Archived Stories |
| `docs/product/prd.md` | Product Requirements Document (PRD) |

# Workflow Conventions

## Git Commit (Conventional Commit)
Format: `type(scope): description`

| Type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation change |
| `chore` | Build/tooling/dependency |
| `refactor` | Refactoring (no behavior change) |
| `test` | Add or modify tests |

- Infer scope from the modified module/directory (e.g. `board`, `auth`, `ui`)
- Description in English, concisely describing "why"
- All tests in the project's test suite must pass before committing

## Branch Naming
- Feature branch: `feature/STORY-{ID}-short-desc`
- Hotfix branch: `fix/HOTFIX-{ID}-short-desc`
- Bug fix branch: `fix/BUG-{ID}-short-desc`
- Main branch: `main` / `master` (no direct push)
- Development branch: `develop`

## PR Conventions
- Title: `feat(scope): short description` (consistent with commit)
- Body: Summary + Test Plan
- Must pass CI and Code Review before merging

# Shared Protocols

## Lazy Visualize Protocol
> Referenced by: Act Phase 4, Done Phase 2

If source files changed (per `LANG_PROFILES[stack].source_dirs`) OR `code_graph.mmd` is missing, run visualize in all 3 modes (file, class, call). Else skip with log: "Graph up-to-date — no source changes".

## Test Mapping Protocol
> Referenced by: Act Phase 3, Check Phase 5, Done Phase 2.5, Hotfix Phase 2

Map changed source files to test files via `LANG_PROFILES[stack].test_map_pattern`. If no mapping can be determined, fall back to the full test suite.

## Context.md Canonical Format
> Referenced by: Init Phase 6, Plan Phase 3, Done Phase 4.5

Write `docs/product/context.md` using this format:
```markdown
# Project Context (Auto-generated)
> Last updated: {ISO timestamp} by {command}

## Sprint Status
{In Progress stories with IDs | Backlog count | Done count}

## Current Stories
{Active stories with brief descriptions}

## Recent Completions
{Last 3 completed stories, one line each}

## Active Branches
{git branch output, or "None" if no feature/fix branches}

## Key Decisions
{Last 5 lessons from lessons.md}

## Next Recommended Action
{If In Progress: `/project-act STORY-XXX` | If Backlog only: `/project-plan` | If empty: `/project-design`}
```

### Credential Safety

NEVER print passwords, keys, or tokens to stdout.
NEVER commit secrets to version control.
