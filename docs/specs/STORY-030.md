# STORY-030: Smart Lint Integration in Done Command

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.2.0 |

## Context

The current Done command lacks intelligent linting integration, which is a critical quality gate before commits. Many development workflows rely on consistent code style and automated fixing, but the integration should be configurable to accommodate different team preferences and project requirements.

Some teams prefer non-blocking lints (warnings only) to maintain development velocity, while others require strict lint compliance before commits. The solution must be stack-aware, configurable, and safe by default.

### Current Limitations

- No automatic lint integration in Done command
- No stack-aware lint command detection
- No configurable blocking behavior
- No auto-fix capabilities
- Manual lint checking required

### Competitive Gap

- **Pre-commit**: Automatic linting with configurable blocking
- **Husky**: Git hook integration with auto-fix support
- **GitHub Actions**: Lint checks with auto-fix PR creation
- **PactKit**: Manual lint checking only

## Target Call Chain

```
/project-done
  → detect_project_stack()
  → read lint_command from LANG_PROFILES[stack]
  → read lint_blocking and auto_fix from pactkit.yaml
  → if auto_fix:
      → run lint_command --fix
      → re-run lint_command to verify
  → run lint_command (check mode)
  → if lint_blocking and failures:
      → block commit with error
  → else:
      → report warnings, proceed with commit
```

## Requirements

### R1: Stack-Aware Lint Command Detection
- The Done command MUST read `lint_command` from existing `LANG_PROFILES` for the detected project stack.
- If no `lint_command` is defined for the stack, linting MUST be skipped with an info message.
- The lint command detection MUST work with existing stack detection logic.
- Custom lint commands MUST be configurable via `pactkit.yaml` override.

### R2: Configurable Blocking Behavior
- `pactkit.yaml` MUST support an optional `lint_blocking` field (boolean).
- The `lint_blocking` field MUST default to `false` (non-blocking warnings).
- When `lint_blocking: false`, lint failures MUST be reported as warnings and not prevent commits.
- When `lint_blocking: true`, lint failures MUST block the commit with an error exit code.

### R3: Auto-Fix Support
- `pactkit.yaml` MUST support an optional `auto_fix` field (boolean).
- The `auto_fix` field MUST default to `false` (no automatic modifications).
- When `auto_fix: true`, the Done command MUST run lint with auto-fix flags first.
- After auto-fix, the command MUST re-run lint in check mode to verify all issues are resolved.
- If issues remain after auto-fix, they MUST be reported according to `lint_blocking` setting.

### R4: LANG_PROFILES Enhancement
- Existing `LANG_PROFILES` entries MUST be enhanced with `lint_command` where appropriate.
- Lint commands MUST include both check and fix variants where possible.
- Example: Python should support both `ruff check` and `ruff check --fix`.
- Lint commands MUST be compatible with common project structures.

### R5: Safe Default Configuration
- Default behavior MUST be non-blocking to preserve development velocity.
- No files MUST be automatically modified unless explicitly enabled.
- Lint failures MUST NOT prevent commits by default.
- All lint settings MUST be clearly documented in generated `pactkit.yaml`.

## Acceptance Criteria

### AC1: Default Non-Blocking Behavior
- **Given** a Python project with default `pactkit.yaml` configuration
- **When** `/project-done` is executed with lint violations
- **Then** lint warnings are displayed to the user
- **And** the commit proceeds successfully
- **And** no files are automatically modified

### AC2: Blocking Mode
- **Given** `pactkit.yaml` contains `lint_blocking: true`
- **When** `/project-done` is executed with lint violations
- **Then** an error message explains the lint failures
- **And** the commit is blocked with non-zero exit code
- **And** the user is prompted to fix issues manually

### AC3: Auto-Fix Without Blocking
- **Given** `pactkit.yaml` contains `auto_fix: true, lint_blocking: false`
- **When** `/project-done` is executed with fixable lint violations
- **Then** auto-fix is applied to source files
- **And** lint is re-run to verify fixes
- **And** remaining issues are shown as warnings
- **And** the commit proceeds

### AC4: Auto-Fix With Blocking
- **Given** `pactkit.yaml` contains `auto_fix: true, lint_blocking: true`
- **When** `/project-done` is executed with mixed fixable and non-fixable violations
- **Then** auto-fix is applied to fixable issues
- **And** remaining non-fixable issues block the commit
- **And** the user is shown exactly what still needs manual fixing

### AC5: Stack Detection Integration
- **Given** a JavaScript project is detected
- **When** `/project-done` runs lint checks
- **Then** the appropriate ESLint or Prettier command is used from `LANG_PROFILES`
- **And** the lint command matches the project's tooling conventions

### AC6: No Lint Command Available
- **Given** a project stack with no defined `lint_command` in `LANG_PROFILES`
- **When** `/project-done` is executed
- **Then** an info message explains that no linting is configured for this stack
- **And** the commit proceeds without lint checking
- **And** no errors occur

### AC7: Custom Lint Command Override
- **Given** `pactkit.yaml` contains a custom `lint_command: "custom-linter --check"`
- **When** `/project-done` is executed
- **Then** the custom lint command is used instead of `LANG_PROFILES` default
- **And** auto-fix works if custom command supports fix flags

### AC8: Lint Command Not Found
- **Given** a configured lint command that is not installed
- **When** `/project-done` attempts to run linting
- **Then** a warning explains the missing lint tool
- **And** the commit proceeds without lint checking
- **And** the user is advised how to install the missing tool

### AC9: Empty Project (No Lintable Files)
- **Given** a project with no files matching lint patterns
- **When** `/project-done` runs lint checks
- **Then** linting completes successfully with no findings
- **And** an info message confirms no files were linted
- **And** the commit proceeds normally

### AC10: Lint Configuration File Validation
- **Given** a project with lint configuration files (e.g., `.eslintrc`, `pyproject.toml`)
- **When** `/project-done` runs lint checks
- **Then** the lint tool uses the project's configuration
- **And** lint results respect project-specific rules and settings
- **And** any configuration errors are reported clearly