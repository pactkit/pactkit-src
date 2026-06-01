# STORY-slim-127: project CLAUDE.md managed-block update

| Field | Value |
|-------|-------|
| ID | STORY-slim-127 |
| Status | Done |
| Priority | P1 |
| Release | 2.15.0 |

## Background

`_generate_project_claude_md` currently uses `atomic_write` to fully overwrite `.claude/CLAUDE.md` on every `pactkit update`. This violates Architecture Principle §9 (Merge over Replace) — any content the user manually adds to CLAUDE.md is silently destroyed.

The fix: adopt the same managed-block pattern used by `_upsert_venv_managed_block` in CLAUDE.local.md. PactKit owns a `<!-- pactkit:start -->` / `<!-- pactkit:end -->` region; user content outside that region is preserved.

## Requirements

### R1: Managed-block update for project CLAUDE.md (MUST)

`_generate_project_claude_md` MUST use `<!-- pactkit:start -->` / `<!-- pactkit:end -->` markers. Only content between these markers is regenerated. User content outside is preserved.

### R2: Migration from legacy full-replace (MUST)

When CLAUDE.md exists but has no markers:
- If content matches PactKit template (detected via `# {project_name} — Project Context` header) → wrap entire content in markers (safe migration).
- If content has user modifications (no PactKit header) → append managed block at end of file, preserve all existing content.

### R3: Fresh install (MUST)

When CLAUDE.md does not exist, create it with the managed block including markers. Also include `@` import references outside the managed block so users can add content above or below.

### R4: Preserve @import references position (MUST)

The `@./docs/product/context.md` and `@./.claude/CLAUDE.local.md` references MUST be placed outside the managed block (after `<!-- pactkit:end -->`) so they are never accidentally removed if the user rearranges content.

### R5: Codegraph section conditional inclusion (SHOULD)

When `.codegraph/` exists, include the "Code Intelligence" section inside the managed block. When absent, omit it. This is dynamic per-deploy.

## Acceptance Criteria

### AC1: Existing user content preserved on update (R1)

- **Given** `.claude/CLAUDE.md` exists with user content outside markers
- **When** `pactkit update` runs
- **Then** user content is unchanged; only content between `<!-- pactkit:start -->` and `<!-- pactkit:end -->` is regenerated

### AC2: Legacy CLAUDE.md migrated with markers (R2)

- **Given** `.claude/CLAUDE.md` exists with PactKit-generated content but no markers
- **When** `pactkit update` runs
- **Then** content is wrapped in markers; no content is lost

### AC3: User-modified legacy CLAUDE.md preserved (R2)

- **Given** `.claude/CLAUDE.md` exists with user-written content (no PactKit header)
- **When** `pactkit update` runs
- **Then** existing content is preserved, managed block is appended

### AC4: Fresh install creates file with markers (R3)

- **Given** `.claude/CLAUDE.md` does not exist
- **When** `pactkit update` runs
- **Then** file is created with `<!-- pactkit:start -->` ... `<!-- pactkit:end -->` and `@` imports after the end marker

### AC5: @imports are outside managed block (R4)

- **Given** any state of CLAUDE.md
- **When** `pactkit update` runs
- **Then** `@./docs/product/context.md` and `@./.claude/CLAUDE.local.md` appear after `<!-- pactkit:end -->`

### AC6: Codegraph section appears when .codegraph/ exists (R5)

- **Given** project has `.codegraph/` directory
- **When** `pactkit update` runs
- **Then** managed block includes "Code Intelligence (codegraph)" section

## Target Call Chain

```
deployer.deploy() → _generate_project_claude_md(config)
  → _build_managed_block(config, project_root)  [NEW]
  → _upsert_claude_md_managed_block(claude_md_path, managed_block)  [NEW]
      → if file missing: write fresh (markers + @imports)
      → if has markers: regex replace between markers
      → if legacy PactKit template: wrap in markers
      → if user content: append managed block
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/generators/deployer.py` | Add `_CLAUDE_MD_START` / `_CLAUDE_MD_END` constants | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | Extract `_build_claude_md_managed_content()` from existing lines[] logic | None | Low |
| 3 | `src/pactkit/generators/deployer.py` | Rewrite `_generate_project_claude_md` to use upsert pattern (detect markers, migrate, or fresh create) | Steps 1-2 | Medium |
| 4 | `tests/unit/` | Unit tests for all 4 paths (fresh, has-markers, legacy-template, user-modified) | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | No user input — paths from cwd |
| SEC-2 Authentication | N/A | Local CLI tool |
| SEC-3 Authorization | N/A | Local CLI tool |
| SEC-4 Data Exposure | N/A | No secrets |
| SEC-5 Injection | N/A | No shell/SQL |
| SEC-6 Dependencies | N/A | No new deps |
| SEC-7 Cryptography | N/A | Not applicable |
| SEC-8 Logging | N/A | No sensitive data |

## Out of Scope

- Global `~/.claude/CLAUDE.md` — already has user-modified detection, not changing
- `CLAUDE.local.md` — already uses managed-block pattern, not changing
- Plugin/marketplace format CLAUDE.md — separate code path
