# STORY-018: Architecture Docs Staleness Prevention

| Field     | Value |
|-----------|-------|
| Status    | Done |
| Author    | System Architect |
| Release   | 1.1.4 |

## Context

Architecture docs under `docs/architecture/` contain stale data because the PDCA workflow has gaps in update responsibilities:

1. `system_design.mmd` — Plan Phase 2 instructs "Update HLD" but no verification ensures component counts match reality (e.g., `config.py` registries).
2. `governance/rules.md` — written once during Init Phase 5, never updated afterward. The Invariants section (e.g., test count) drifts over time.
3. `snapshots/` — release skill has snapshot logic, but Done Phase 3.8 lacks a verification step to catch missed snapshots.

Root cause: PDCA commands update `code_graph.mmd`, `class_graph.mmd`, `call_graph.mmd`, `lessons.md`, and `context.md` automatically, but `system_design.mmd`, `rules.md`, and `snapshots/` have no automated maintenance path after initial creation.

## Target Call Chain

```
/project-done
  → Phase 2 (Update Reality)
    → visualize (file, class)          ← EXISTS
    → system_design.mmd validation     ← NEW (Gap 1)
  → Phase 3 (Hygiene Check)
    → lessons.md auto-append           ← EXISTS
    → rules.md invariants refresh      ← NEW (Gap 2)
  → Phase 3.8 (Release)
    → snapshot + archive               ← EXISTS
    → snapshot verification gate       ← NEW (Gap 3)
```

## Requirements

### R1: system_design.mmd Consistency Check (Gap 1)
- The Done command Phase 2 MUST include a step to verify `system_design.mmd` component counts against `config.py` VALID_* registries (or equivalent source of truth).
- If a mismatch is detected, the agent MUST warn the user and suggest updating the HLD.
- The check SHOULD compare subgraph labels containing numeric counts (e.g., "8 commands", "9 skills") against actual component counts.

### R2: governance/rules.md Invariants Refresh (Gap 2)
- The Done command Phase 3 MUST include a step to refresh `governance/rules.md` Invariants section.
- The test count invariant MUST be updated to reflect the actual test count from the most recent test run.
- The refresh SHOULD preserve existing ADR entries and only update the Invariants section.

### R3: Release Snapshot Verification (Gap 3)
- The Done command Phase 3.8 MUST verify that architecture snapshots exist for the release version after running the snapshot step.
- If `snapshots/{version}_*.mmd` files are missing after the snapshot step, the agent MUST report an error.

### R4: Prompt-Only Changes
- All fixes MUST be prompt-only changes to `src/pactkit/prompts/commands.py`.
- No runtime Python code changes SHOULD be needed.

## Acceptance Criteria

### Scenario 1: Done detects stale system_design.mmd
- **Given** `system_design.mmd` contains "14 command playbooks" but VALID_COMMANDS has 8 entries
- **When** `/project-done` Phase 2 executes
- **Then** the agent warns about the mismatch and suggests updating

### Scenario 2: Done refreshes rules.md test count
- **Given** `governance/rules.md` says "All 719+ tests" but pytest reports 1035 passed
- **When** `/project-done` Phase 3 executes
- **Then** `rules.md` Invariants section is updated to "All 1035+ tests"

### Scenario 3: Release snapshot verification
- **Given** a version bump Story with version "1.2.0"
- **When** `/project-done` Phase 3.8 runs the release flow
- **Then** `docs/architecture/snapshots/v1.2.0_*.mmd` files exist and the agent confirms their presence

### Scenario 4: No false positives on fresh project
- **Given** a project just initialized with `/project-init`
- **When** `/project-done` runs for the first Story
- **Then** the system_design.mmd check does not error (counts match defaults)
