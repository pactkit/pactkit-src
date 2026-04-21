# STORY-slim-102: Move version tracking from project yaml to global deploy marker

| Field | Value |
|-------|-------|
| ID | STORY-slim-102 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.5 |

## Background

The `version` field in project-level `pactkit.yaml` tracks which PactKit version last deployed. When PactKit is upgraded via `pipx upgrade pactkit`, running `pactkit update` in one project updates that project's yaml, but all other projects remain stale. This causes `pactkit update --if-needed` (triggered every session by Core Protocol) to report mismatch and run a full redeploy in every other project — even though the global deployment directory (`~/.claude/`) is already up to date.

Root cause: version tracking is in the wrong place. Project yaml's role is **configuration** (which agents/skills/rules to deploy). Deployment **state** (which version last deployed) should live in the global deployment directory alongside the deployed files.

### Current Flow (broken cross-project)
```
pipx upgrade pactkit → __version__ = 2.10.5
cd projectA → pactkit update → projectA yaml = 2.10.5, ~/.claude/ = 2.10.5 ✓
cd projectB → pactkit update --if-needed → projectB yaml = 2.10.1 ≠ 2.10.5 → full redeploy (unnecessary)
```

### Target Flow
```
pipx upgrade pactkit → __version__ = 2.10.5
cd projectA → pactkit update → ~/.claude/.pactkit-version = 2.10.5 ✓
cd projectB → pactkit update --if-needed → reads ~/.claude/.pactkit-version = 2.10.5 → skip ✓
```

## Requirements

### R1: Global Version Marker (MUST)

Classic deployer MUST write `~/.claude/.pactkit-version` containing `__version__` after successful deployment. This is the single source of truth for "which version is currently deployed globally."

### R2: Update --if-needed Reads Global Marker (MUST)

`pactkit update --if-needed` MUST read `~/.claude/.pactkit-version` (not project yaml) to decide whether to skip. If the marker matches `__version__`, skip. If missing or mismatched, proceed to deploy.

### R3: Remove version from Project YAML (MUST)

- `get_default_config()` MUST NOT include a `version` key
- `auto_merge_config_file()` MUST NOT sync version — and MUST remove existing `version` field if present (cleanup migration)
- `_rewrite_yaml()` MUST NOT write a version line
- `load_config()` MUST NOT break if `version` key is absent

### R4: Guard Version Check Uses Global Marker (MUST)

`check_version_mismatch()` in `guards.py` MUST read the global marker instead of project yaml version.

## Acceptance Criteria

### AC1: Global Marker Written on Deploy (R1)

- **Given** `~/.claude/.pactkit-version` does not exist or has old version
- **When** `pactkit update` runs successfully
- **Then** `~/.claude/.pactkit-version` contains `__version__` (e.g., `2.10.5`)

### AC2: Skip When Global Marker Matches (R2)

- **Given** `~/.claude/.pactkit-version` contains `2.10.5` and `__version__ == 2.10.5`
- **When** `pactkit update --if-needed` is run from any project directory
- **Then** Output is `"PactKit 2.10.5 up-to-date — skipping redeploy"` and exit code 0

### AC3: Deploy When Global Marker Mismatches (R2)

- **Given** `~/.claude/.pactkit-version` contains `2.10.1` and `__version__ == 2.10.5`
- **When** `pactkit update --if-needed` is run
- **Then** Full deploy executes and marker is updated to `2.10.5`

### AC4: Default Config Has No Version (R3)

- **Given** `get_default_config()` is called
- **When** Result is inspected
- **Then** No `version` key exists in the returned dict

### AC5: Auto-merge Removes Stale Version (R3)

- **Given** A project yaml with `version: "2.10.1"` and stale components
- **When** `auto_merge_config_file()` is called
- **Then** New components are added AND `version` field is removed from the yaml file

### AC6: Guard Uses Global Marker (R4)

- **Given** `~/.claude/.pactkit-version` matches `__version__`
- **When** `pactkit guard` is run from a project with stale yaml version
- **Then** No version mismatch warning is printed

### AC7: Old YAML With Version Still Loads (R3)

- **Given** A project yaml containing `version: "2.10.1"` (legacy field not yet cleaned)
- **When** `load_config()` is called
- **Then** Config loads without error

## Target Call Chain

```
pactkit update --if-needed
  → cli.py: read ~/.claude/.pactkit-version (R2)
  → if match: skip, exit 0
  → if mismatch: deploy() → _deploy_classic()
    → deployer.py: write ~/.claude/.pactkit-version (R1)

pactkit guard
  → guards.py: check_version_mismatch()
    → read ~/.claude/.pactkit-version (R4)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/generators/deployer.py` | Write `.pactkit-version` at end of `_deploy_classic()` | None | Low |
| 2 | `src/pactkit/cli.py` | Change `--if-needed` to read global marker | Step 1 | Low |
| 3 | `src/pactkit/guards.py` | Change `check_version_mismatch()` to read global marker | Step 1 | Low |
| 4 | `src/pactkit/config.py` | Remove `version` from `get_default_config()`, `auto_merge`, `_rewrite_yaml` | None | Medium |
| 5 | `tests/unit/` | Update version-related tests | Steps 1-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | No secrets |
| SEC-2 | N/A | No user input handling |
| SEC-3 | N/A | No database operations |
| SEC-4 | N/A | No frontend code |
| SEC-5 | N/A | No authentication logic |
| SEC-6 | N/A | No API endpoints |
| SEC-7 | N/A | No error handling code |
| SEC-8 | N/A | No dependency changes |

## Out of Scope

- Adapter packages (codex, copilot, opencode) — they already have their own `.pactkit-version` mechanism
- Plugin/marketplace manifests — `version` in `plugin.json` and `marketplace.json` is package metadata, not deployment state
