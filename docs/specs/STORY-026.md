# STORY-026: Conditional Issue Tracker Integration

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | TBD |

## Context

PactKit's Sprint Board (`docs/product/sprint_board.md`) currently operates as a standalone project management tool with no integration to external issue tracking systems. Users who prefer using GitHub Issues, GitLab Issues, or other trackers for project management cannot sync their PactKit stories with these systems.

Many development workflows rely on linking commits to issues, tracking story progress in external systems, and maintaining audit trails through issue lifecycle management. PactKit should support optional integration while maintaining backward compatibility with standalone operation.

### Competitive Gap

- **Linear**: Native GitHub Issues sync for story tracking
- **Jira**: Bidirectional sync with Git branch/commit workflows
- **GitHub Projects**: Direct integration with Issues and Pull Requests
- **PactKit**: Isolated Sprint Board with no external integrations

## Target Call Chain

```
/project-plan
  → create/update story in sprint_board.md
  → if issue_tracker.provider == 'github':
      → check gh CLI availability
      → create GitHub Issue with story details
      → link issue URL to sprint board story

/project-done
  → mark story complete in sprint_board.md
  → if issue_tracker.provider == 'github':
      → find linked GitHub Issue
      → close issue with commit reference
```

## Requirements

### R1: Issue Tracker Configuration Section
- `pactkit.yaml` MUST support a new optional `issue_tracker` section with a `provider` field.
- The `provider` field MUST default to `none` when not specified.
- Valid provider values MUST be: `github`, `none`.
- Future providers MAY include `gitlab`, `linear` without breaking changes.
- The `validate_config()` function MUST warn on invalid provider values.

### R2: Plan Command Integration
- The `/project-plan` command MUST include an optional step to create external issues when `issue_tracker.provider` is not `none`.
- The issue creation MUST be conditional on `gh` CLI availability for GitHub provider.
- Created issues MUST include story title, requirements summary, and acceptance criteria.
- The Sprint Board story MUST be updated with a link to the created issue.
- If issue creation fails, the command MUST continue with a warning (non-blocking).

### R3: Done Command Integration
- The `/project-done` command MUST include an optional step to close linked issues when `issue_tracker.provider` is not `none`.
- The command MUST parse Sprint Board entries to find linked issue URLs.
- Issue closure MUST include reference to the completing commit hash.
- If issue closing fails, the command MUST continue with a warning (non-blocking).

### R4: Standalone Operation Preservation
- When `issue_tracker.provider: none`, Sprint Board MUST operate exactly as before.
- All existing Sprint Board functionality MUST remain unchanged for standalone mode.
- The Sprint Board file format MUST remain human-readable and git-friendly.
- No external dependencies MUST be required for core PactKit functionality.

## Acceptance Criteria

### AC1: Default Configuration
- **Given** a fresh `pactkit init` with default configuration
- **When** the generated `pactkit.yaml` is inspected
- **Then** it contains `issue_tracker: {provider: none}`
- **And** Sprint Board operates in standalone mode

### AC2: GitHub Issue Creation
- **Given** `pactkit.yaml` contains `issue_tracker: {provider: github}`
- **And** `gh` CLI is available and authenticated
- **When** `/project-plan` creates a new story
- **Then** a GitHub Issue is created with story details
- **And** the Sprint Board entry includes the issue URL
- **And** the issue title matches the story title

### AC3: Missing CLI Graceful Failure
- **Given** `issue_tracker.provider: github` is configured
- **And** `gh` CLI is not available
- **When** `/project-plan` is executed
- **Then** a warning is displayed about missing GitHub CLI
- **And** the story is created in Sprint Board without issue link
- **And** the command completes successfully

### AC4: Issue Closure on Done
- **Given** a Sprint Board story with linked GitHub Issue
- **When** `/project-done` completes the story
- **Then** the linked GitHub Issue is closed
- **And** the issue includes a reference to the commit hash
- **And** the Sprint Board story is moved to Done section

### AC5: Invalid Provider Warning
- **Given** `pactkit.yaml` contains `issue_tracker: {provider: jira}`
- **When** config validation is run
- **Then** a warning is emitted about unsupported provider
- **And** the system treats it as `provider: none`

### AC6: Backward Compatibility
- **Given** an existing `pactkit.yaml` without `issue_tracker` section
- **When** Plan and Done commands are run
- **Then** Sprint Board operates exactly as before
- **And** no external API calls are made
- **And** no errors occur

### AC7: Issue Link Format
- **Given** a GitHub Issue is created for a story
- **When** the Sprint Board is updated
- **Then** the story entry includes format: `- [x] STORY-XXX: Title [#123](https://github.com/owner/repo/issues/123)`
- **And** the link is clickable and properly formatted

### AC8: Partial Failure Handling
- **Given** issue tracker is configured
- **When** GitHub API is unavailable during Plan
- **Then** the story is still created in Sprint Board
- **And** a warning message explains the issue tracker failure
- **And** the command exits successfully