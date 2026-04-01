---
mode: agent
description: "Push branch and create pull request via gh CLI"
---

# Command: PR (v1.4.0)
- **Usage**: `/project-pr`
- **Agent**: Repo Maintainer

## 🧠 Phase 0: Pre-flight Check
1.  **Branch Check**:
    - Run `git branch --show-current` to get current branch name
    - If branch is `main` or `master`: print "Skipping PR: working on main branch" → STOP
2.  **Existing PR Check**:
    - Run `gh pr list --head <branch> --state open --json number` to check for existing PR
    - If PR exists: print "PR already open: <URL>" → STOP
    - If `gh` CLI unavailable: print "⚠️ gh CLI not available — cannot create PR" → STOP
3.  **Story Detection**: Infer active Story ID from branch name (e.g., `feature/STORY-051-desc` → `STORY-051`).

## 🎬 Phase 1: Push Assurance
1.  **Check Remote**: If remote tracking branch does not exist, run `git push -u origin <branch>`.
2.  **If push fails**: STOP and report the error.

## 🎬 Phase 2: PR Generation
1.  **Generate PR Title**: Format `{type}({scope}): {spec_title}`
    - `type`: `feat` for STORY, `fix` for BUG/HOTFIX
    - `scope`: infer from primary modified directory
    - `spec_title`: extract from `# {ID}: {Title}` heading in Spec (strip the ID prefix)
    - Max 70 characters
2.  **Generate PR Body**: Extract from Spec and test results:
    ```markdown
    ## Summary
    {1-3 sentences from Spec ## Background}

    ## Changes
    {R1, R2, ... from Spec ## Requirements, one bullet each with MUST/SHOULD/MAY}

    ## Acceptance Criteria
    {AC1, AC2, ... as checklist items — mark [x] if a test for it passed}

    ## Test Results
    - Unit: {N} passed, {N} failed
    - E2E: {N} passed, {N} failed

    ## Spec
    - [{STORY_ID}](docs/specs/{STORY_ID}.md)

    🤖 Generated with [GitHub Copilot](https://github.com/features/copilot)
    ```
3.  **User Confirmation**: Show the PR title + body preview. Ask: "Create this PR? (yes/no/edit)"
    - `yes` → execute `gh pr create --title "..." --body "..."`
    - `no` → skip
    - `edit` → accept user feedback, regenerate, ask again
4.  **Output**: Print PR URL on success.


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
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py` to view module dependency graph
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode class` for class inheritance
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode call --entry <func>` to trace call chains
- **PDCA Exemption**: When a PDCA command is active, the command's own visualize phases take precedence — skip Visual First.

## Strict TDD
- Write tests first (RED), then write implementation (GREEN)
- The agent MUST NOT skip TDD except when running `/project-hotfix`
- All tests must pass before committing

## Language Matching
- Match the user's language (Chinese→Chinese, English→English).
- Technical terms (function names, file paths, git commands) stay in original form.


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

### Credential Safety

NEVER print passwords, keys, or tokens to stdout.
NEVER commit secrets to version control.
