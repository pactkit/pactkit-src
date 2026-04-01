# STORY-slim-077: Monorepo stack detection + redetect-stack CLI

| Field | Value |
|-------|-------|
| ID | STORY-slim-077 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.12 |

## Background

STORY-slim-076 added multi-stack visualize support, but stack detection (`detect_stacks()` in `cleaners.py` and `_detect_stacks()` in `visualize.py`) only checks marker files at the project root level (`project_root / marker_file`). Monorepo projects like phase-smith have markers in subdirectories (`backend/go.mod`, `frontend/package.json`) — these are invisible to the current logic.

Additionally, for projects that already have a `pactkit.yaml`, there is no way to re-detect and update the `stack` field. `_generate_config_if_missing()` exits immediately when the yaml exists, and `auto_merge_config_file()` does not backfill `stack`.

**Three problems**:
1. Marker detection is root-only — monorepo subdirectory markers are missed
2. No CLI command to re-detect stack for existing projects
3. `pactkit init` on existing projects does not update the stack field

## Requirements

### R1: Subdirectory marker detection (MUST)

`detect_stacks()` in `cleaners.py` and `_detect_stacks()` in `visualize.py` MUST scan one level of subdirectories (`root/*/marker_file`) when root-level markers are insufficient. This enables monorepo detection (e.g., `backend/go.mod` + `frontend/package.json`).

### R2: `pactkit redetect-stack` CLI subcommand (MUST)

A new CLI subcommand `pactkit redetect-stack` MUST re-detect stacks from marker files and update the `stack` field in the existing `pactkit.yaml`. It MUST print the before/after values. If no yaml exists, it MUST suggest `pactkit init`.

### R3: `pactkit init` updates stack for existing yaml (SHOULD)

When `pactkit init` (or `update`) runs on a project with an existing yaml where `stack` is `auto` or a single string, it SHOULD re-detect and update the stack field to reflect actual markers.

### R4: Backward compatibility (MUST)

Single-stack projects with root-level markers (e.g., `pyproject.toml` at root) MUST continue to work identically. The subdirectory scan is additive — root matches take priority.

## Acceptance Criteria

### AC1: Monorepo subdirectory detection (R1)

- **Given** a project with `backend/go.mod` and `frontend/package.json` but no root-level markers
- **When** `detect_stacks()` is called
- **Then** returns `['go', 'node']` (or `['node', 'go']` depending on marker order)

### AC2: Mixed root + subdirectory markers (R1, R4)

- **Given** a project with `pyproject.toml` at root AND `backend/go.mod` in subdirectory
- **When** `detect_stacks()` is called
- **Then** returns `['python', 'go']` (root markers found first, subdirectory adds go)

### AC3: Root-only project unchanged (R4)

- **Given** a project with only `pyproject.toml` at root, no subdirectory markers
- **When** `detect_stacks()` is called
- **Then** returns `['python']` (identical to pre-fix behavior)

### AC4: `redetect-stack` updates yaml (R2)

- **Given** a project with `.claude/pactkit.yaml` containing `stack: node`
- **When** `pactkit redetect-stack` is run and markers detect `[go, node]`
- **Then** yaml is updated to `stack:\n  - go\n  - node` and before/after is printed

### AC5: `redetect-stack` no yaml (R2)

- **Given** a project with no `pactkit.yaml`
- **When** `pactkit redetect-stack` is run
- **Then** prints error suggesting `pactkit init`

### AC6: visualize `_detect_stacks` subdirectory fallback (R1)

- **Given** a project with `backend/go.mod` and `frontend/package.json`, yaml has `stack: auto`
- **When** visualize `_detect_stacks()` falls through to marker scan
- **Then** detects both `go` and `node` from subdirectories

### AC7: init updates stale stack (R3)

- **Given** a project with yaml `stack: node` but markers show `[go, node]`
- **When** `pactkit init` is run
- **Then** yaml stack field is updated to `[go, node]`

### AC8: Depth-1 only — no deep recursion (R1)

- **Given** a project with `deep/nested/sub/go.mod` (3 levels deep)
- **When** `detect_stacks()` is called
- **Then** does NOT detect go — only scans root and root/* (depth 1)

## Target Call Chain

```
pactkit redetect-stack
  → cli.py: handle "redetect-stack" subcommand
    → config.find_pactkit_yaml() → get yaml path
    → cleaners.detect_stacks(cwd) → scan root + root/* for markers
    → config.update_yaml_stack(yaml_path, new_stacks) → rewrite stack field
    → print before/after

pactkit init (existing yaml)
  → deployer.deploy() → _deploy_classic()
    → _update_stack_if_stale(project_yaml) → detect_stacks() → compare → rewrite if changed

detect_stacks(root)
  → scan root/marker for each _STACK_MARKERS
  → if insufficient: scan root/*/marker for each _STACK_MARKERS (depth-1)
  → deduplicate, return list
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/cleaners.py` | Extend `detect_stacks()` to scan `root/*/marker` after root scan | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Same depth-1 extension in `_detect_stacks()` marker scan block | Step 1 (same pattern) | Low |
| 3 | `src/pactkit/config.py` | Add `update_yaml_stack(yaml_path, stacks)` to rewrite stack field in-place | None | Low |
| 4 | `src/pactkit/cli.py` | Add `redetect-stack` subcommand | Steps 1, 3 | Low |
| 5 | `src/pactkit/generators/deployer.py` | In `_deploy_classic()`, call `_update_stack_if_stale()` after `auto_merge` | Steps 1, 3 | Low |
| 6 | `tests/unit/test_story_slim077.py` | Tests for AC1–AC8 | Steps 1–5 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 User Input | N/A | No user input — reads marker files and yaml |
| SEC-2 Auth | N/A | Local CLI only |
| SEC-3 Data Storage | N/A | Only modifies local pactkit.yaml |
| SEC-4 Secrets | N/A | No secrets involved |
| SEC-5 Network | N/A | No network access |
| SEC-6 File Ops | Low | Scans one level of subdirs — bounded, no symlink follow |
| SEC-7 Dependencies | N/A | No new dependencies |
| SEC-8 Logging | N/A | No sensitive data logged |

## Out of Scope

- Deep recursive scanning (depth > 1) — monorepo convention is marker at direct subdirectory
- Auto-update stack on `pactkit update --if-needed` version-check-only mode
- Scanning non-standard marker files beyond `_STACK_MARKERS`
