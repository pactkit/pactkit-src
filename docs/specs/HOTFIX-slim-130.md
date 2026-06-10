# HOTFIX-slim-130: Fix skill frontmatter parsing — move @ references below YAML block

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-130 |
| Status | Open |
| Priority | P1 |
| Release | 2.15.2 |

## Background

All 11 `project-*` skills have `@` reference lines (file includes) placed **before** the YAML frontmatter block (`---`). Claude Code's skill parser requires frontmatter to start on line 1 of the file. When `@` lines precede `---`, the entire frontmatter is treated as plain text — `model`, `allowed-tools`, and `description` fields are silently ignored.

**Impact**: Every `/project-*` command runs on the session's default model (opus) regardless of the `model:` directive in frontmatter. This wastes tokens (opus for tasks that should use sonnet) and breaks the model routing strategy defined in `pactkit.yaml`.

**Root cause**: Skill files were authored with `@` includes at the top for readability, unaware that this breaks YAML frontmatter detection.

## Affected Files

All skills matching `~/.claude/skills/project-*/SKILL.md` (11 files):

1. `project-act/SKILL.md`
2. `project-check/SKILL.md`
3. `project-clarify/SKILL.md`
4. `project-design/SKILL.md`
5. `project-done/SKILL.md`
6. `project-hotfix/SKILL.md`
7. `project-init/SKILL.md`
8. `project-plan/SKILL.md`
9. `project-pr/SKILL.md`
10. `project-release/SKILL.md`
11. `project-sprint/SKILL.md`

## Requirements

### R1: Frontmatter MUST be first in file (MUST)

Every `SKILL.md` file MUST start with `---` on line 1. No content (including `@` references) may precede the frontmatter block.

### R2: @ references MUST move below frontmatter (MUST)

All `@` include lines MUST be placed immediately after the closing `---` of the frontmatter block, before the markdown body. Preserve the original set of references — do not add or remove any.

### R3: Existing frontmatter fields preserved (MUST)

All existing frontmatter fields (`description`, `allowed-tools`, `model`) MUST remain unchanged in value. Only their position in the file changes.

## Acceptance Criteria

### AC1: Frontmatter starts on line 1 (R1)

- **Given** any file in `~/.claude/skills/project-*/SKILL.md`
- **When** I read line 1
- **Then** it MUST be exactly `---`

### AC2: Model field is parseable (R1, R3)

- **Given** `project-act/SKILL.md` with `model: sonnet` in frontmatter
- **When** Claude Code loads the skill
- **Then** the skill executes on sonnet, not the session default

### AC3: @ references still present (R2)

- **Given** any affected skill file
- **When** I count `@` reference lines
- **Then** the count matches the original (no references lost or added)

### AC4: No content change (R3)

- **Given** the markdown body of any affected skill
- **When** compared to pre-fix content (excluding line position)
- **Then** all instructions, phases, and protocols are identical

## Fix Pattern

Before (broken):
```markdown
@~/.claude/skills/_rules/04-architecture-principles.md
@~/.claude/rules/09-credential-safety.md

---
description: "Implement code per Spec, strict TDD"
model: sonnet
---

# Command: Act
```

After (correct):
```markdown
---
description: "Implement code per Spec, strict TDD"
model: sonnet
---

@~/.claude/skills/_rules/04-architecture-principles.md
@~/.claude/rules/09-credential-safety.md

# Command: Act
```

## Security Scope

SEC-1: No credential or secret handling involved. Pure file reformatting.
