# STORY-slim-038: Done Phase Workflow Integration

| Field | Value |
|-------|-------|
| ID | STORY-slim-038 |
| Status | Done |
| Priority | P2 — Impact 4, Effort 2 |
| Release | TBD |

## Background

The `/project-done` command has a Regression Gate (Phase 2.5) that uses code-level impact analysis to decide between SKIP, INCREMENTAL, or FULL regression. This story adds workflow-level impact to the regression decision: if a changed file is part of the `WorkflowGraph`, the gate also reports which PDCA commands are affected, helping developers understand the blast radius of their changes beyond just test files.

This is the integration point that connects STORY-slim-035 (parser) and STORY-slim-037 (impact) to the actual PDCA workflow.

## Requirements

### R1: Workflow impact in regression gate (MUST)

The `pactkit regression` command (or its underlying logic) MUST, after classifying changes as IMPACT or FULL, also run workflow impact analysis on changed files. For each changed file that appears in the `WorkflowGraph`, it MUST report affected commands.

### R2: Workflow impact output format (MUST)

The workflow impact section MUST be appended to the regression gate output:
```
Regression: IMPACT-BASED — 3 test files based on call graph analysis
Workflow Impact: pactkit-board changed → affects: project-done, project-sprint, project-act
```

### R3: Non-blocking behavior (MUST)

Workflow impact MUST be informational only — it MUST NOT block the commit or change the regression decision (SKIP/IMPACT/FULL). It provides awareness, not enforcement.

### R4: Graceful degradation (MUST)

If `workflow_graph.mmd` does not exist or `build_workflow_graph()` fails (e.g., missing command files), the workflow impact section MUST be silently skipped. It MUST NOT cause the regression gate to fail.

### R5: Lazy workflow graph update (SHOULD)

During `/project-done` Phase 2 housekeeping, `pactkit visualize --lazy` SHOULD also update `workflow_graph.mmd` if command/skill/rule files have changed. This ensures the workflow graph stays current alongside code graphs.

## Acceptance Criteria

### AC1: Workflow impact shown in regression output (R1, R2)

- **Given** a commit that modifies `board.py` (which is in the WorkflowGraph as a skill file)
- **When** running the regression gate
- **Then** the output includes a `Workflow Impact:` line listing affected commands

### AC2: Non-blocking on workflow impact (R3)

- **Given** a commit where workflow impact reports 5 affected commands
- **When** regression gate evaluates the decision
- **Then** the regression decision (SKIP/IMPACT/FULL) is unchanged — workflow impact is informational only

### AC3: Graceful skip when no workflow graph (R4)

- **Given** a project where `workflow_graph.mmd` does not exist and command files are not parseable
- **When** running the regression gate
- **Then** no workflow impact section appears, and the gate proceeds normally

### AC4: Lazy update includes workflow (R5)

- **Given** a `/project-done` run where a command markdown file was modified
- **When** `pactkit visualize --lazy` runs in Phase 2
- **Then** `workflow_graph.mmd` is regenerated alongside code graphs

## Target Call Chain

```
# During regression gate (Phase 2.5)
pactkit regression <changed-files>
  → classify changes (existing logic)
  → build_workflow_graph(root)
  → for each changed file in graph:
      → graph.reverse_reach(file_node_id)
      → collect affected commands
  → print "Workflow Impact: ..." (informational)

# During housekeeping (Phase 2)
pactkit visualize --lazy
  → existing: file, class, call graphs
  → new: workflow graph (if command/skill/rule files changed)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim038.py` | Tests for regression gate with workflow impact | STORY-slim-037 | Low |
| 2 | `src/pactkit/skills/visualize.py` | Add workflow graph to `--lazy` staleness check | STORY-slim-036 | Low |
| 3 | `src/pactkit/cli.py` or regression logic | Integrate workflow impact into `pactkit regression` output | STORY-slim-037 | Medium |
| 4 | Playbook update | Update `/project-done` Phase 2.5 documentation to mention workflow impact | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Low | Changed file list comes from `git diff`, not user input |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- Blocking commits based on workflow impact (future enhancement)
- Automatic PDCA re-execution when workflow breaks detected
- Cross-service regression gate (PRD Epic 2, STORY-slim-043)
- Slack/email notifications for workflow impact
