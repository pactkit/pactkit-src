# STORY-035: Update README and docs directory documentation

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.2.0 |

## Context

The README has not been updated since v1.1.x to reflect the full v1.2.0 feature set. Key gaps:

1. **No `docs/` directory documentation** — Users and contributors don't know the purpose of `specs/`, `context.md`, `lessons.md`, `sprint_board.md`, `rules.md`, or the architecture graphs. These are core artifacts of the PDCA lifecycle.
2. **No `pactkit.yaml` configuration reference** — The v1.2.0 config schema has 11 sections (stack, version, root, agents, commands, skills, rules, ci, issue_tracker, hooks, lint_blocking, auto_fix, exclude) but none are documented.
3. **CHANGELOG incomplete for v1.2.0** — Missing STORY-031~034 and BUG-006~008 entries.
4. **Skills section outdated** — Lists only 3 scripted skills; 6 prompt-only skills (doctor, draw, release, review, status, trace) are undocumented.

## Target Call Chain

```
README.md update (manual)
CHANGELOG.md update (manual)
No runtime code changes.
```

## Requirements

1. README MUST include a "Project Structure (PDCA-managed)" section documenting the `docs/` directory and its key files
2. README MUST include a "Configuration" section documenting all `pactkit.yaml` fields with descriptions and defaults
3. README SHOULD update the Skills section to list all 9 skills (3 scripted + 6 prompt-only) with their purposes
4. CHANGELOG MUST be updated with all v1.2.0 changes not yet recorded (STORY-031~034, BUG-006~008)
5. README SHOULD include the current version badge and accurate component counts
6. README MUST NOT remove any existing working content — only add or update

## Acceptance Criteria

### AC1: docs/ directory documented in README
- **Given** a new user reading the README
- **When** they look for project structure documentation
- **Then** they find a section explaining each `docs/` subdirectory and key file with its purpose

### AC2: pactkit.yaml configuration reference
- **Given** a user who has run `pactkit init`
- **When** they want to customize their config
- **Then** the README has a table or list of all config fields with descriptions and defaults

### AC3: CHANGELOG complete for v1.2.0
- **Given** the CHANGELOG
- **When** inspected for v1.2.0 entries
- **Then** all stories (STORY-031~034) and bugs (BUG-006~008) are listed

### AC4: Skills section complete
- **Given** the README Skills section
- **When** inspected
- **Then** all 9 skills are listed with their purpose and invocation context
