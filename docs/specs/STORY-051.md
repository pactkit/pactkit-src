# STORY-051: PDCA Workflow Streamlining

| Field | Value |
|-------|-------|
| ID | STORY-051 |
| Status | Draft |
| Priority | P1 |
| Author | System Architect |
| Created | 2026-02-27 |
| Release | 1.4.0 |

## Background

After 50+ stories, the PDCA workflow has accumulated significant complexity through organic growth. Analysis reveals:
- **Done command**: 13+ sub-phases (overloaded)
- **Redundant operations**: `visualize` called 9x across commands, Lint Gate in both Act and Done
- **Scattered responsibilities**: Issue Tracker split across Plan and Done

This Story streamlines the workflow while preserving all quality gates.

## Target Call Chain

```
project-plan.md → (removed: Issue Tracker creation)
project-act.md  → (removed: Phase 3.4 Lint Check)
project-done.md → (extracted: Release, PR phases)
project-release.md → (new: Phase 3.8 content)
project-pr.md → (new: Phase 4.2 content)
```

## Requirements

### R1: Split Done Command
The Done command MUST be refactored to extract release and PR functionality:
- **Done** SHOULD retain: Regression Gate, Hygiene, Archive, Git Commit, Context Update
- **Release** MUST be a new standalone command with: version detection, snapshot, tag
- **PR** MUST be a new standalone command with: push, PR generation, user confirmation

### R2: Consolidate Lint Gate
Lint checking MUST occur only in Done Phase 2.7 (blocking gate):
- Act Phase 3.4 (conditional lint) SHOULD be removed
- Done Phase 2.7 MUST remain as the single lint enforcement point
- Done lint gate MUST respect `lint_blocking` and `auto_fix` config flags

### R3: Lazy Visualize
The `visualize` command SHOULD be executed conditionally:
- MUST run if `git diff --name-only` includes files in `source_dirs` (from LANG_PROFILES)
- MUST run if `code_graph.mmd` does not exist
- SHOULD skip with log message if no source files changed

### R4: Centralize MCP Detection
MCP tool availability checks SHOULD be consolidated:
- A new Phase 0.2 SHOULD detect all MCP tools once per command
- Subsequent phases SHOULD use boolean flags instead of repeated tool checks
- This is an optimization; existing behavior MUST be preserved

### R5: Simplify Issue Tracker Flow
Issue Tracker operations MUST be consolidated in Done:
- Plan Phase 3.4 (Issue creation) SHOULD be removed
- Done Phase 3.5.5 (backfill safety net) MUST remain as the single creation point
- Done Phase 3.6 (closure) MUST remain unchanged

## Acceptance Criteria

### AC1: Done Command Reduced
**Given** the refactored Done command
**When** counting sub-phases
**Then** Done MUST have ≤ 9 phases (down from 13+)

### AC2: New Commands Functional
**Given** `/project-release` is invoked after a version bump
**When** the command executes
**Then** it MUST create snapshots and git tag

**Given** `/project-pr` is invoked on a feature branch
**When** the command executes
**Then** it MUST generate PR title/body and create PR via `gh`

### AC3: Lint Gate Single Point
**Given** the Act command is executed
**When** Phase 3 completes
**Then** NO lint check should occur in Act (only in Done)

### AC4: Lazy Visualize Works
**Given** a doc-only change (only `.md` files modified)
**When** Done command runs
**Then** `visualize` SHOULD be skipped with log: "Graph up-to-date — no source changes"

### AC5: Quality Gates Preserved
**Given** the streamlined workflow
**When** a Story completes the full PDCA cycle
**Then** all 4 quality gates MUST still execute:
- Spec Lint Gate (Act Phase 0.5)
- TDD Loop (Act Phase 3)
- Regression Gate (Done Phase 2.5)
- Lint Gate (Done Phase 2.7)

## Non-Goals

- Removing or weakening any quality gate
- Changing the TDD requirement
- Modifying the Spec structure or linting rules
- Affecting `/project-sprint` orchestration logic

## Migration Notes

- Existing workflows will not break — Release and PR were optional phases
- Users who relied on auto-PR in Done should now call `/project-pr` explicitly
- Version bump detection in Done will prompt: "Run `/project-release` to create tag?"

## Files to Modify

| File | Change |
|------|--------|
| `~/.claude/commands/project-done.md` | Remove Phase 3.7, 3.8, 4.2; add prompts for release/pr |
| `~/.claude/commands/project-act.md` | Remove Phase 3.4 Lint Check |
| `~/.claude/commands/project-plan.md` | Remove Phase 3.4 Issue Tracker creation |
| `~/.claude/commands/project-release.md` | New file — extracted from Done Phase 3.8 |
| `~/.claude/commands/project-pr.md` | New file — extracted from Done Phase 4.2 |
| `src/pactkit/prompts/commands.py` | Sync all template changes |
| `.claude/pactkit.yaml` | Add `project-release`, `project-pr` to commands list |
| `docs/architecture/graphs/system_design.mmd` | Update "9 commands" → "11 commands" |
