# STORY-034: Auto-refresh pactkit.yaml in Plan Init Guard

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.2.0 |

## Context

After PactKit is upgraded (new pip version), the deployed `pactkit.yaml` may be missing newly-added config sections (hooks, ci, lint_blocking, etc.). STORY-033 added `auto_merge_config_file()` backfill support, but it only triggers when `pactkit init` or `pactkit update` is explicitly run.

Users who go straight to `/project-plan` after upgrading won't see new config sections until they manually run `pactkit update`. This causes confusion ("where are my hooks?") and feature loss.

The fix: extend Plan's Init Guard (Phase 0.5) to detect stale configs and auto-refresh them.

## Target Call Chain

```
/project-plan
  → Phase 0.5: Init Guard
    → Check pactkit.yaml exists          (existing)
    → Check config completeness           (NEW)
    → If stale: run `pactkit update`      (NEW)
    → Continue to Phase 1
```

## Requirements

1. Plan Phase 0.5 (Init Guard) MUST check if `pactkit.yaml` is missing config sections after verifying markers exist
2. The check SHOULD compare the yaml content against known section names (hooks, ci, issue_tracker, lint_blocking, auto_fix)
3. If missing sections are detected, the agent MUST run `pactkit update` to backfill
4. The agent SHOULD report what was added (e.g., "Config refreshed: added hooks, ci sections")
5. The refresh MUST be idempotent — running it on an already-complete config does nothing
6. This is a prompt-only change to `commands.py` — no runtime code changes needed

## Acceptance Criteria

### AC1: Plan Init Guard detects stale config
- **Given** a `pactkit.yaml` with only `stack`, `version`, `root` (missing hooks/ci/etc.)
- **When** `/project-plan` is invoked
- **Then** Phase 0.5 detects the incomplete config before proceeding to Phase 1

### AC2: Auto-refresh runs pactkit update
- **Given** a stale `pactkit.yaml` detected in Phase 0.5
- **When** the Init Guard runs the refresh
- **Then** `pactkit update` is executed
- **And** missing sections are backfilled on disk
- **And** the agent reports what was added

### AC3: Complete config skips refresh
- **Given** a `pactkit.yaml` that already has all sections
- **When** `/project-plan` is invoked
- **Then** Phase 0.5 skips the refresh silently (no "Config refreshed" message)

### AC4: Prompt template updated
- **Given** the Plan command template in `commands.py`
- **When** inspected at source level
- **Then** Phase 0.5 includes a config completeness check step
- **And** the step references `pactkit update` as the refresh mechanism
