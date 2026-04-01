---
mode: agent
description: "Version release: snapshot, archive, Git tag, and GitHub Release"
---

# Command: Release (v1.4.0)
- **Usage**: `/project-release`
- **Agent**: Repo Maintainer

## 🧠 Phase 0: Pre-flight Check
1.  **Version Detection**: Check if `pyproject.toml` version was changed vs the previous commit.
    - Run `git diff HEAD~1 pyproject.toml | grep version` (or vs branch base)
    - Capture the new version value (e.g., `1.4.1`).
    - If no version change detected: print "ℹ️ No version bump detected. Update `pyproject.toml` version before releasing." and STOP.
2.  **Read Config**: Read `.github/pactkit.yaml` to detect stack and release configuration.

## 🎬 Phase 1: Invoke pactkit-release Skill
1.  **Delegate to skill**: Invoke the `pactkit-release` skill with `VERSION={version}` from Phase 0.
    - The skill handles the full release protocol:
      Version Update → Spec Backfill → Architecture Snapshot → Git Operations → GitHub Release.
    - Pass the detected version so the skill skips its own auto-detection step.


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
