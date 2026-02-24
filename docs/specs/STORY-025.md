# STORY-025: Conditional CI/CD Pipeline Generation

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.3.0 |

## Context

PactKit currently does not generate CI/CD pipeline configurations, requiring users to manually set up automated testing and linting workflows. Many competing DevOps tools (Cursor, GitHub Copilot Workspace, Roo Code) automatically generate CI configurations when initializing projects.

Users may not want CI/CD at all (local development only), may use different providers (GitHub Actions vs GitLab CI), or may already have existing CI configurations they don't want overwritten. The solution must be conditional and respect the user's environment.

### Competitive Gap

- **GitHub Copilot Workspace**: Automatically generates `.github/workflows/` for detected stacks
- **Cursor**: Suggests CI workflow generation on project init
- **Roo Code**: Has built-in CI templates for common frameworks
- **PactKit**: No CI generation — users must manually create workflows

## Target Call Chain

```
pactkit init
  → deployer.deploy()
    → read ci.provider from pactkit.yaml (NEW)
    → if provider != 'none':
        → _deploy_ci_workflow(provider, project_root) (NEW)
          → read CI template for provider
          → atomic_write(ci_file_path, ci_content)
```

## Requirements

### R1: CI Configuration Section
- `pactkit.yaml` MUST support a new optional `ci` section with a `provider` field.
- The `provider` field MUST default to `none` when not specified.
- Valid provider values MUST be: `github`, `gitlab`, `none`.
- The `validate_config()` function MUST warn on invalid provider values.

### R2: Conditional CI File Generation
- The `/project-init` command MUST generate CI workflow files when `ci.provider` is not `none`.
- When `ci.provider: github`, the deployer MUST create `.github/workflows/pactkit.yml`.
- When `ci.provider: gitlab`, the deployer MUST create `.gitlab-ci.yml`.
- When `ci.provider: none`, no CI files MUST be generated.

### R3: CI Workflow Content
- Generated CI workflows MUST run `pytest tests/` for test execution.
- Generated CI workflows MUST run linting commands based on detected stack (using `LANG_PROFILES`).
- CI workflows MUST trigger on `push` to `main` branch and `pull_request` events.
- CI workflows MUST use appropriate runner environments (ubuntu-latest).

### R4: Backward Compatibility
- Existing `pactkit.yaml` files without a `ci` section MUST continue to work.
- The config loader MUST treat missing `ci` section as `ci: {provider: none}`.
- `pactkit update` MUST NOT generate CI files for existing projects unless explicitly configured.

## Acceptance Criteria

### AC1: Default Configuration
- **Given** a fresh `pactkit init` with default configuration
- **When** the generated `pactkit.yaml` is inspected
- **Then** it contains `ci: {provider: none}`
- **And** no CI workflow files are created

### AC2: GitHub CI Generation
- **Given** `pactkit.yaml` contains `ci: {provider: github}`
- **When** `pactkit init` is run
- **Then** `.github/workflows/pactkit.yml` is created
- **And** the workflow file contains `pytest tests/` job
- **And** the workflow file contains linting commands

### AC3: GitLab CI Generation
- **Given** `pactkit.yaml` contains `ci: {provider: gitlab}`
- **When** `pactkit init` is run
- **Then** `.gitlab-ci.yml` is created
- **And** the CI file contains test and lint stages

### AC4: None Provider Behavior
- **Given** `pactkit.yaml` contains `ci: {provider: none}`
- **When** `pactkit init` is run
- **Then** no CI workflow files are created
- **And** no `.github/` or CI-related directories are generated

### AC5: Invalid Provider Warning
- **Given** `pactkit.yaml` contains `ci: {provider: jenkins}`
- **When** config validation is run
- **Then** a warning is emitted about invalid CI provider
- **And** the init process treats it as `provider: none`

### AC6: Backward Compatibility
- **Given** an existing `pactkit.yaml` without a `ci` section
- **When** `pactkit update` is run
- **Then** no CI files are generated
- **And** no errors occur during deployment

### AC7: CI File Content Validation
- **Given** GitHub CI is generated for a Python project
- **When** the workflow file is inspected
- **Then** it contains `runs-on: ubuntu-latest`
- **And** it contains `pytest tests/` command
- **And** it contains appropriate linting command from `LANG_PROFILES`
- **And** it triggers on push to main and pull requests