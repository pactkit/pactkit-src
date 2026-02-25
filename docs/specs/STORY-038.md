# STORY-038: Add call_graph.mmd to standard PDCA update cycle

- **Release**: 1.3.0
- **Priority**: Medium
- **Type**: Enhancement (Prompt-only)

## Problem

The "Update Reality" steps in Act Phase 4 and Done Phase 2 only regenerate two of three graph types:

| Graph | Updated in Act/Done? | Staleness Risk |
|-------|---------------------|----------------|
| `code_graph.mmd` (file-level) | Yes | Low |
| `class_graph.mmd` (class-level) | Yes | Low |
| `call_graph.mmd` (call-level) | **No** | **High** |

`call_graph.mmd` is only updated during:
- Manual trace (Plan/Act Phase 1 with `--entry <func>`)
- Version release (`pactkit-release` runs all 3 modes)

This means the call graph becomes stale after every code change. When `pactkit-release` takes a snapshot, it may archive a stale `call_graph.mmd`.

### Secondary Issue: focus_graph.mmd collision

All three modes (`file`, `class`, `call`) output to the same `focus_graph.mmd` when `--focus` is specified. Sequential invocations silently overwrite each other.

## Requirements

### Update Reality Enhancement

- **MUST** add `visualize --mode call` (without `--entry`) to the "Update Reality" steps in both Act Phase 4 and Done Phase 2
- **MUST** place the call graph update AFTER file and class graph updates (order: file → class → call)
- **SHOULD** add a skip heuristic: if the project has fewer than 5 source files, skip `--mode call` to avoid trivial graphs

### Focus Graph Collision Fix

- **SHOULD** change `visualize.py` output paths for `--focus` mode to include the mode name: `focus_file_graph.mmd`, `focus_class_graph.mmd`, `focus_call_graph.mmd`
- **MUST** update any prompt templates that reference `focus_graph.mmd` to use the new mode-specific names

### Snapshot Integrity

- **SHOULD** add a pre-snapshot freshness check in `pactkit-release`: verify all three graph files have been modified more recently than the newest source file before running `snapshot`

## Acceptance Criteria

### AC1: call_graph.mmd updated in standard cycle
- **Given** the Act Phase 4 "Update Reality" step
- **When** the developer finishes implementing code
- **Then** `call_graph.mmd` is regenerated alongside `code_graph.mmd` and `class_graph.mmd`

### AC2: Done also updates call graph
- **Given** the Done Phase 2 "Update Reality" step
- **When** the maintainer runs housekeeping
- **Then** `call_graph.mmd` is regenerated

### AC3: Focus graph names are mode-specific
- **Given** `visualize --mode class --focus auth` is run
- **When** followed by `visualize --mode call --focus auth`
- **Then** two distinct files exist: `focus_class_graph.mmd` and `focus_call_graph.mmd`

## Target Call Chain

### Prompt changes (no runtime code for AC1/AC2):
- `src/pactkit/prompts/commands.py` → `CMD_ACT_MD` Phase 4 "Update Reality"
- `src/pactkit/prompts/commands.py` → `CMD_DONE_MD` Phase 2 "Update Reality"

### Runtime code change (AC3 — focus_graph collision):
- `src/pactkit/skills/visualize.py` → `_write_graph()` or output path logic
- Need to locate where `focus_graph.mmd` path is determined and make it mode-aware
