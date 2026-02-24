# STORY-027: Safe Opt-in Hook Templates

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.3.0 |

## Context

PactKit users have experienced issues with overly aggressive hooks that caused infinite loops and long pending times with prompt/agent-type hooks. Users need lightweight, safe, report-only hooks for common development workflows without the risk of blocking operations or causing system instability.

Current git hooks in many projects are either too aggressive (blocking commits), too complex (requiring maintenance), or non-existent (missing quality gates). PactKit should provide safe, opt-in hook templates that follow the principle of "report, don't block."

### Safety Requirements Based on User Feedback

The user specifically mentioned:
- **Infinite loops** occurred with prompt/agent-type hooks
- **Long pending times** caused workflow disruption
- Hooks must be **SAFE**: command-type only, report-only, opt-in via pactkit.yaml
- Hooks must be **non-blocking**: always exit 0, never prevent operations

## Target Call Chain

```
pactkit init / pactkit update
  → deployer.deploy()
    → read hooks config from pactkit.yaml
    → for each enabled hook:
        → generate safe shell script in .claude/hooks/
        → set execute permissions
        → register with git hooks (if git repo)
```

## Requirements

### R1: Hook Configuration Section
- `pactkit.yaml` MUST support a new optional `hooks` section with boolean flags for each template.
- Available hook templates MUST include:
  - `pre_commit_lint`: Run linter before commit (report warnings only)
  - `post_test_coverage`: Print coverage summary after test runs
  - `pre_push_check`: Run basic checks before push (branch protection, uncommitted changes)
- All hook templates MUST be disabled (`false`) by default.
- The `validate_config()` function MUST warn on unrecognized hook names.

### R2: Command-Type Only Restriction
- All hook templates MUST be `command` type (shell scripts) only.
- Hook templates MUST NOT invoke Claude, agents, or any AI-powered tools.
- Hook templates MUST NOT use `prompt-type` or `agent-type` configurations.
- Hook scripts MUST be simple, focused, and predictable in execution time.

### R3: Report-Only Safety Guarantee
- All hook scripts MUST exit with code 0 regardless of findings.
- Hook scripts MUST print informational messages to stdout/stderr only.
- Hook scripts MUST NOT block, prevent, or abort git operations.
- Hook scripts MUST NOT modify files automatically (read-only operations).

### R4: Deployment and Registration
- The `/project-init` command MUST deploy enabled hook scripts to `.claude/hooks/`.
- Hook scripts MUST be executable (`chmod +x`).
- If the project is a git repository, hooks MUST be registered with git hooks.
- If git hooks already exist, PactKit hooks MUST be appended, not overwritten.

### R5: Hook Script Templates
- `pre_commit_lint`: Run project linter command from `LANG_PROFILES`, report issues, exit 0.
- `post_test_coverage`: Run coverage analysis if coverage tool is available, print summary, exit 0.
- `pre_push_check`: Check for uncommitted changes, check current branch, print warnings, exit 0.

## Acceptance Criteria

### AC1: Default Disabled State
- **Given** a fresh `pactkit init` with default configuration
- **When** the generated `pactkit.yaml` is inspected
- **Then** all hook templates are set to `false`
- **And** no hook scripts are deployed to `.claude/hooks/`

### AC2: Hook Enablement and Deployment
- **Given** `pactkit.yaml` contains `hooks: {pre_commit_lint: true}`
- **When** `pactkit init` is run
- **Then** `.claude/hooks/pre-commit-lint` script is created
- **And** the script is executable
- **And** git pre-commit hook references the PactKit hook

### AC3: Report-Only Behavior
- **Given** pre-commit lint hook is enabled and deployed
- **When** a commit is made with linting violations
- **Then** linting warnings are printed to console
- **And** the commit proceeds successfully (exit 0)
- **And** no files are modified by the hook

### AC4: Command-Type Only Enforcement
- **Given** any deployed hook script
- **When** the script content is inspected
- **Then** it contains only shell commands and utilities
- **And** it does not invoke `claude`, agents, or AI tools
- **And** it does not contain prompt-type configurations

### AC5: Coverage Hook Functionality
- **Given** `post_test_coverage` hook is enabled
- **And** a coverage tool is available (pytest-cov, coverage.py)
- **When** tests are run via git hook trigger
- **Then** coverage summary is printed to console
- **And** the operation completes with exit 0
- **And** no files are modified

### AC6: Pre-Push Check Hook
- **Given** `pre_push_check` hook is enabled
- **When** `git push` is executed with uncommitted changes
- **Then** a warning message is printed about uncommitted changes
- **And** the push operation continues normally
- **And** no git operations are blocked

### AC7: Invalid Hook Name Warning
- **Given** `pactkit.yaml` contains `hooks: {invalid_hook: true}`
- **When** config validation is run
- **Then** a warning is emitted about unrecognized hook name
- **And** only valid hooks are deployed

### AC8: Git Integration Safety
- **Given** existing git hooks are present
- **When** PactKit hooks are deployed
- **Then** existing hooks are preserved
- **And** PactKit hooks are appended to existing hooks
- **And** no existing hook functionality is broken

### AC9: Non-Git Repository Handling
- **Given** PactKit is initialized in a non-git directory
- **When** hooks are enabled and deployed
- **Then** hook scripts are created in `.claude/hooks/`
- **And** no git hook registration is attempted
- **And** no errors occur during deployment