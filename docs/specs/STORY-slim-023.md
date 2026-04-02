# STORY-slim-023: Auto Version Sync via `pactkit update --if-needed`

| Field | Value |
|-------|-------|
| ID | STORY-slim-023 |
| Status | Done |
| Priority | P2 |
| Release | 2.3.2 |

## Background

After `pip install --upgrade pactkit`, the installed `__version__` advances but project-level files (`.claude/` prompts, rules, skills) remain at the old version. Users must manually run `pactkit update` in every project. This Story adds `--if-needed` to `pactkit update` so PDCA commands can auto-trigger it at session start, achieving zero-friction version sync.

## Target Call Chain

```
cli.py: update_parser (argparse) → args.command == "update"
  → if args.if_needed: compare __version__ vs pactkit.yaml version
    → match: print skip message, exit 0
    → mismatch: fall through to deploy()
  → deploy(target, format, agent, ...)
```

## Requirements

### R1: --if-needed flag
`pactkit update` MUST accept `--if-needed` flag (default: `False`).

### R2: Version comparison
When `--if-needed` is set, the CLI MUST read `pactkit.yaml` version and compare it to `pactkit.__version__`.

### R3: Skip on match
If versions match, the CLI MUST print a skip message and exit 0 without calling `deploy()`.

### R4: Proceed on mismatch
If versions differ (or `pactkit.yaml` not found), the CLI MUST proceed with normal `deploy()`.

### R5: Core Protocol update
The Core Protocol prompt (`rules.py` `RULES_MODULES["core"]`) MUST include `pactkit update --if-needed` in the Session Context section.

### R6: Blast radius
Only `cli.py` and `prompts/rules.py` are modified. No changes to Plan/Act/Done/Sprint/Hotfix commands or `deployer.py`.

## Out of Scope
- Automatic prompt refresh without CLI invocation
- Version check in `pactkit init` (already runs full deploy)

## Acceptance Criteria

### AC1: --if-needed flag exists
Given the CLI parser
When `pactkit update --if-needed` is invoked
Then argparse accepts it without error

### AC2: Skip when versions match
Given `pactkit.yaml` version == `__version__`
When `pactkit update --if-needed` runs
Then output contains "up-to-date" and `deploy()` is NOT called

### AC3: Proceed when versions differ
Given `pactkit.yaml` version != `__version__`
When `pactkit update --if-needed` runs
Then `deploy()` IS called

### AC4: Proceed when no pactkit.yaml
Given no `pactkit.yaml` exists in the project
When `pactkit update --if-needed` runs
Then `deploy()` IS called (first-time setup)

### AC5: Core Protocol prompt updated
Given the deployed `01-core-protocol` rule
When reading the Session Context section
Then it contains `pactkit update --if-needed`

### AC6: Blast radius
Given the full codebase
When checking which prompt constants reference `--if-needed`
Then only `RULES_MODULES["core"]` contains it

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/cli.py` | Add `--if-needed` arg to `update_parser`; add version check before `deploy()` | None | Low |
| 2 | `src/pactkit/prompts/rules.py` | Add `pactkit update --if-needed` to Session Context in core rule | None | Low |
| 3 | `tests/unit/test_story_slim023.py` | Tests for R1-R6 | Step 1, 2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified |
| SEC-2 | N/A | --if-needed is a boolean flag, no user string input |
| SEC-3 | N/A | No database patterns |
| SEC-4 | N/A | No frontend files |
| SEC-5 | N/A | No auth/credential handling — only version string comparison |
| SEC-6 | N/A | No API routes |
| SEC-7 | N/A | Version mismatch falls through to existing deploy() |
| SEC-8 | N/A | No dependency manifests modified |
