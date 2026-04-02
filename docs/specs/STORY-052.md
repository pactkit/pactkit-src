# STORY-052: Conditional GitHub Release in pactkit-release

| Field | Value |
|-------|-------|
| ID | STORY-052 |
| Status | Draft |
| Priority | P1 |
| Author | System Architect |
| Created | 2026-02-27 |
| Release | 1.4.0 |

## Background

pactkit-release skill 的 Step 4 (GitHub Release) 当前是无条件执行的。这导致：
- 未托管在 GitHub 的项目会报错
- 不需要 GitHub Release 的项目被强制执行
- 违反了 PactKit "条件执行、默认关闭" 的设计原则

现有的条件配置模式（`issue_tracker.provider`, `ci.provider`, `lint_blocking`）已证明有效，应复用该模式。

## Target Call Chain

```
pactkit.yaml
  └── release.github_release: true/false

pactkit-release/SKILL.md
  └── Step 4: IF release.github_release == true THEN gh release create

project-release.md
  └── delegates to pactkit-release (no change needed)
```

## Requirements

### R1: Add release Config Section
`pactkit.yaml` MUST support a `release` configuration section:
```yaml
release:
  github_release: false  # Default: disabled
```

### R2: Conditional GitHub Release
pactkit-release skill Step 4 MUST be conditional:
- IF `release.github_release: true` in `pactkit.yaml`: execute `gh release create`
- IF `release.github_release: false` or section missing: skip with log "GitHub Release: SKIP — not configured"

### R3: Config Backfill
`pactkit update` MUST backfill the `release` section for existing configs:
- Add `release.github_release: false` if section missing
- Preserve existing values if section exists

### R4: Validation
`validate_config()` SHOULD accept the new `release` section without error.

## Acceptance Criteria

### AC1: Default Disabled
**Given** a fresh `pactkit init`
**When** the default config is generated
**Then** `release.github_release` MUST be `false`

### AC2: Skip When Disabled
**Given** `release.github_release: false` in pactkit.yaml
**When** `/project-release` is invoked
**Then** Step 4 (GitHub Release) MUST be skipped with log message

### AC3: Execute When Enabled
**Given** `release.github_release: true` in pactkit.yaml
**When** `/project-release` is invoked
**Then** Step 4 MUST execute `gh release create`

### AC4: Backfill Works
**Given** an old pactkit.yaml without `release` section
**When** `pactkit update` is run
**Then** `release.github_release: false` MUST be added

## Non-Goals

- Adding other release providers (GitLab, Bitbucket) — future scope
- Changing the default to `true` — must be opt-in

## Files to Modify

| File | Change |
|------|--------|
| `src/pactkit/config.py` | Add `release` to schema, validation, defaults, backfill |
| `~/.claude/skills/pactkit-release/SKILL.md` | Add conditional check before Step 4 |
| `src/pactkit/prompts/skills.py` | Sync template |
| `tests/unit/test_config.py` | Add tests for release config |
