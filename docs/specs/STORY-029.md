# STORY-029: Enhanced Doctor Diagnostics

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | TBD |

## Context

The current `/project-doctor` provides basic project health checks but lacks depth in identifying common maintenance issues. As projects evolve, architecture documentation becomes stale, specs become orphaned, and configuration drift occurs between `pactkit.yaml` and deployed files.

Enhanced diagnostics can catch these issues early, providing actionable insights for project maintenance. This is particularly important for long-running projects where documentation and specs gradually fall out of sync with implementation.

### Current Doctor Limitations

- Basic checks only (file existence, basic structure)
- No staleness detection for architecture graphs
- No orphaned/missing spec detection
- No configuration drift detection
- Limited actionable guidance

## Target Call Chain

```
pactkit doctor (skill invocation)
  → enhanced_doctor_diagnostics()
    → check_stale_architecture_graphs()
    → check_orphaned_specs()
    → check_missing_specs()
    → check_config_drift()
    → generate_structured_health_report()
```

## Requirements

### R1: Stale Architecture Graph Detection
- The doctor MUST detect architecture graphs with modification time > 7 days since last source file change.
- The check MUST compare `docs/architecture/graphs/*.mmd` mtime against newest source file mtime.
- Stale graphs MUST be reported with severity level `WARN`.
- The report MUST suggest running `visualize` to refresh graphs.

### R2: Orphaned Spec Detection
- The doctor MUST identify spec files in `docs/specs/` that have no corresponding entry in Sprint Board.
- The check MUST parse `docs/product/sprint_board.md` for story references.
- Orphaned specs MUST be reported with severity level `INFO`.
- The report MUST list specific orphaned spec files.

### R3: Missing Spec Detection
- The doctor MUST identify Sprint Board stories that have no corresponding spec file.
- The check MUST verify each story ID in the board has a matching file in `docs/specs/`.
- Missing specs MUST be reported with severity level `WARN`.
- The report MUST suggest using `/project-plan` to create missing specs.

### R4: Configuration Drift Detection
- The doctor MUST compare `pactkit.yaml` configuration against deployed files in `.claude/`.
- Drift checks MUST include: enabled rules, agents, skills, and hook configurations.
- Configuration drift MUST be reported with severity level `ERROR`.
- The report MUST suggest running `pactkit update` to sync configurations.

### R5: Structured Health Report
- The doctor MUST output a structured health report with severity levels: `INFO`, `WARN`, `ERROR`.
- The report MUST group findings by category: Architecture, Specs, Configuration, General.
- Each finding MUST include a clear description and suggested remediation action.
- The report MUST include an overall health score or status summary.

## Acceptance Criteria

### AC1: Stale Architecture Graph Detection
- **Given** architecture graphs exist with mtime > 7 days ago
- **And** source files have been modified more recently
- **When** `/project-doctor` is run
- **Then** a `WARN` severity finding is reported
- **And** the finding suggests running `visualize` to refresh graphs

### AC2: Fresh Architecture Graph Pass
- **Given** architecture graphs have mtime < 7 days ago
- **Or** no source files are newer than the graphs
- **When** `/project-doctor` is run
- **Then** no stale graph warnings are reported
- **And** architecture health is marked as good

### AC3: Orphaned Spec Detection
- **Given** `docs/specs/STORY-999.md` exists
- **And** `STORY-999` is not referenced in Sprint Board
- **When** `/project-doctor` is run
- **Then** an `INFO` finding reports the orphaned spec
- **And** suggests archiving or adding to Sprint Board

### AC4: Missing Spec Detection
- **Given** Sprint Board contains `STORY-888: Feature Title`
- **And** `docs/specs/STORY-888.md` does not exist
- **When** `/project-doctor` is run
- **Then** a `WARN` finding reports the missing spec
- **And** suggests using `/project-plan` to create the spec

### AC5: Configuration Drift Detection
- **Given** `pactkit.yaml` enables a rule that's not deployed in `.claude/rules/`
- **When** `/project-doctor` is run
- **Then** an `ERROR` finding reports configuration drift
- **And** suggests running `pactkit update` to sync

### AC6: No Configuration Drift
- **Given** deployed `.claude/` files match `pactkit.yaml` configuration
- **When** `/project-doctor` is run
- **Then** no configuration drift errors are reported
- **And** configuration health is marked as good

### AC7: Structured Report Format
- **Given** multiple diagnostic findings exist
- **When** `/project-doctor` generates the report
- **Then** findings are grouped by category (Architecture, Specs, Configuration)
- **And** each finding includes severity, description, and remediation
- **And** an overall health summary is provided

### AC8: All Healthy Project
- **Given** a well-maintained project with no issues
- **When** `/project-doctor` is run
- **Then** all checks pass with good health status
- **And** the report shows "No issues found" or similar positive message

### AC9: Mixed Severity Handling
- **Given** findings with different severity levels exist
- **When** `/project-doctor` generates the report
- **Then** `ERROR` findings are listed first
- **Then** `WARN` findings are listed second
- **Then** `INFO` findings are listed last
- **And** overall status reflects the highest severity found

### AC10: Remediation Action Accuracy
- **Given** any finding is reported
- **When** the finding includes a suggested action
- **Then** the action is a valid PactKit command or workflow
- **And** the action would actually resolve the reported issue