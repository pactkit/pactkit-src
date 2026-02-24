# Spec STORY-031: Auto git-init in /project-init for non-dev users
- **Release**: 1.2.0

## Context
When non-developer users (e.g., office automation UC3) run `/project-init` in a fresh directory, the project has no git repository. Later, `/project-done` attempts `git commit` which fails. The Init command should detect the absence of a git repo and offer to initialize one.

This removes a barrier for non-technical users who don't know about `git init`.

## Requirements
- The `/project-init` command MUST check if the current directory is inside a git repository (via `git rev-parse --is-inside-work-tree`).
- If no git repo exists, the command MUST ask the user for confirmation before running `git init`.
- If the user declines, the command SHOULD print a warning that git operations (commit, branch) will not work.
- The git init check MUST happen in Phase 1 (Environment & Config), before any file creation.
- Existing projects with git repos MUST NOT be affected.

## Acceptance Criteria

### Scenario 1: Fresh directory gets git init prompt
- **Given** a directory with no `.git/` folder
- **When** `/project-init` is executed
- **Then** the command detects no git repo and asks the user to confirm `git init`

### Scenario 2: User accepts git init
- **Given** the user confirms git init
- **When** init proceeds
- **Then** `git init` is run, and the directory now has a `.git/` folder

### Scenario 3: User declines git init
- **Given** the user declines git init
- **When** init proceeds
- **Then** a warning is printed: "Git operations will not work without a repository."
- **And** the rest of init completes normally

### Scenario 4: Existing git repo skips check
- **Given** a directory that is already inside a git repository
- **When** `/project-init` is executed
- **Then** the git init check is skipped silently

## Design
Add a "Phase 0.5: Git Repository Guard" to `project-init.md` in `commands.py`, immediately after Phase 0 (Thinking) and before Phase 1 (Environment & Config).

## Target Call Chain
`commands.py` → `COMMANDS_CONTENT["project-init.md"]` → Phase 0.5 (new)
