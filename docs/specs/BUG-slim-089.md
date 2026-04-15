# BUG-slim-089: Global CLAUDE.md overwritten on every deploy

| Field | Value |
|-------|-------|
| ID | BUG-slim-089 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.14 |

## Background

`_deploy_claude_md()` (`deployer.py:632-642`) unconditionally overwrites `~/.claude/CLAUDE.md` via `atomic_write()` on every `pactkit init`, `pactkit update`, and `pactkit upgrade` invocation. This destroys any user customizations in the global instructions file.

The project-level counterpart `_generate_project_claude_md()` (line 1343) has 3 layers of protection:
1. Home directory skip (R6) — avoids overwriting global CLAUDE.md when cwd is `~`
2. User-modification detection — checks if first line matches PactKit template
3. Content migration — moves user content to `CLAUDE.local.md` before overwriting

None of these protections exist in `_deploy_claude_md()`.

Additionally, `/project-init` (Phase 1 Step 3) unconditionally calls `pactkit init` or `pactkit update`, which triggers `_deploy_classic()` → `_deploy_claude_md()`, causing a scope violation: a project-level command overwrites global state.

### Affected Call Chain
```
/project-init Phase 1.3
  → pactkit init / pactkit update (shell)
    → cli.main() (cli.py:328)
      → deploy() (deployer.py:248)
        → ClassicDeployer.deploy() (deployer.py:192)
          → _deploy_classic() (deployer.py:305)
            → _deploy_claude_md(~/.claude/, ...) (deployer.py:363)
              → atomic_write(~/.claude/CLAUDE.md, template) ← DESTRUCTIVE
```

## Requirements

### R1: Global CLAUDE.md user-content preservation (MUST)

`_deploy_claude_md()` MUST NOT overwrite `~/.claude/CLAUDE.md` if the file contains user-modified content. Detection heuristic: if the file does not start with `# PactKit Global Constitution`, treat it as user-modified. If user-modified content is detected, preserve the original file and append/merge PactKit-managed content (the `@./docs/product/context.md` reference) only if not already present.

### R2: Global CLAUDE.md idempotent re-deploy (MUST)

If `~/.claude/CLAUDE.md` already contains the expected PactKit template content (matching version header and `@./docs/product/context.md`), `_deploy_claude_md()` SHOULD skip the write entirely. If the version differs (upgrade), update the version header in-place without destroying other content.

### R3: /project-init scope isolation (MUST)

`/project-init` playbook MUST NOT trigger global `~/.claude/` re-deployment as a side effect. The playbook's call to `pactkit init`/`pactkit update` is necessary for deploying rules, agents, and skills, but the global CLAUDE.md write must be guarded by R1. This is a code-level fix, not a playbook change — the guard belongs in `_deploy_claude_md()` itself.

### R4: Backward compatibility (SHOULD)

Fresh installations (no existing `~/.claude/CLAUDE.md`) MUST still receive the full PactKit template. The fix MUST NOT break first-time setup.

## Acceptance Criteria

### AC1: User-modified global CLAUDE.md is preserved (R1)

- **Given** `~/.claude/CLAUDE.md` exists with content that does NOT start with `# PactKit Global Constitution`
- **When** `pactkit init` or `pactkit update` is executed
- **Then** the original file content is preserved unchanged; PactKit MUST NOT overwrite it

### AC2: PactKit-managed CLAUDE.md is updated in-place (R2)

- **Given** `~/.claude/CLAUDE.md` exists with content starting with `# PactKit Global Constitution (v2.9.13 Modular)`
- **When** `pactkit init` is executed with version 2.9.14
- **Then** the version header is updated to `v2.9.14` but no other content is destroyed; `@./docs/product/context.md` reference remains

### AC3: Fresh install creates full template (R4)

- **Given** `~/.claude/CLAUDE.md` does NOT exist
- **When** `pactkit init` is executed
- **Then** the full PactKit template is created with version header and `@./docs/product/context.md` reference

### AC4: /project-init does not destroy global CLAUDE.md (R1, R3)

- **Given** `~/.claude/CLAUDE.md` contains user customizations
- **When** `/project-init` triggers `pactkit init` or `pactkit update`
- **Then** the global CLAUDE.md user content is preserved (protected by the code-level guard in `_deploy_claude_md`)

### AC5: Idempotent re-deploy skips unnecessary write (R2)

- **Given** `~/.claude/CLAUDE.md` already matches the expected PactKit template for the current version
- **When** `pactkit update` is executed
- **Then** no file write occurs (or write is a no-op producing identical content)

## Target Call Chain

```
_deploy_classic() (deployer.py:305)
  → _deploy_claude_md(claude_root, enabled_rules) (deployer.py:363)
    → [NEW] _is_pactkit_managed_global_md(content) — detect PactKit template
    → [NEW] if user-modified: skip overwrite
    → [NEW] if PactKit-managed: update version header only
    → [EXISTING] if file missing: atomic_write() full template
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/generators/deployer.py` | Add `_is_pactkit_managed_global_md(content)` helper: returns True if first line starts with `# PactKit Global Constitution` | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | Refactor `_deploy_claude_md()`: read existing file, check user-modified, skip write if user-modified, update version if PactKit-managed, create if missing | Step 1 | Medium |
| 3 | `tests/unit/test_deployer.py` | Add tests for AC1-AC5: user-modified preservation, version update, fresh install, idempotent skip | Step 2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code file modified (deployer.py) — review for injection via file content |
| SEC-2 | N/A | No user input handling — reads existing file content only |
| SEC-3 | N/A | No database patterns |
| SEC-4 | N/A | No frontend files |
| SEC-5 | N/A | False positive — no auth/session logic; pattern match on file write helpers |
| SEC-6 | N/A | No API/route files |
| SEC-7 | Yes | File read may fail (permissions, encoding) — needs graceful fallback to create |
| SEC-8 | N/A | No dependency manifests changed |

## Out of Scope

- Project-level `.claude/CLAUDE.md` handling — `_generate_project_claude_md()` already has adequate protection
- `/project-init` playbook refactoring — the fix is at the code level in `_deploy_claude_md()`; no playbook changes needed
- CLAUDE.local.md migration for global — global does not need a local.md split; simply preserving existing content is sufficient
