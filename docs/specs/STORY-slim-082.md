# STORY-slim-082: Sync prompt templates for --mode module and --focus scoping

| Field | Value |
|-------|-------|
| ID | STORY-slim-082 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.12 |

## Background

STORY-slim-081 added `--mode module` (module-level dependency graph) and changed `--focus <module>` to work with file/class/call modes (scoped scan within a module directory). However, the downstream prompt templates that document `pactkit visualize` were not updated:

1. **`SKILL_VISUALIZE_MD`** (skills.py): The canonical skill documentation still lists only 3 modes (`file|class|call`), and `--focus` is described as "requires `--mode call`" — both incorrect after STORY-slim-081.
2. **Visual First** (rules.py): The "before modifying code" checklist lists 3 visualize commands but omits `--mode module` for architectural overview.
3. **Release snapshot** (workflows.py): The release skill runs "all three modes (file, class, call)" but doesn't include module graph.
4. **Init Phase 3** (commands.py): Project initialization runs file + class mode but doesn't generate module graph for multi-module projects.

All changes are prompt template text edits — no code logic changes.

## Requirements

### R1: SKILL_VISUALIZE_MD update (MUST)

Update `SKILL_VISUALIZE_MD` in `src/pactkit/prompts/skills.py`:
- Description: change "three analysis modes" → "four analysis modes"
- Command syntax: add `module` to choices → `[--mode file|class|call|module]`
- Parameter table: add row for `--mode module` (module-level dependency graph with weighted cross-module edges)
- Parameter table: fix `--focus <module>` description — remove "requires `--mode call`", replace with "Scope scan to a specific module directory (works with file, class, call modes)"
- Output Files table: add row for `--mode module` → `docs/architecture/graphs/module_graph.mmd` | `graph TD`

### R2: Visual First rule update (SHOULD)

Update the "Visual First" section in `src/pactkit/prompts/rules.py`:
- Add a fourth bullet: `Run `visualize --mode module` for module-level architectural overview`

### R3: Release snapshot update (SHOULD)

Update `SKILL_RELEASE_MD` in `src/pactkit/prompts/workflows.py`:
- Where it says "all three modes (file, class, call)", change to "all four modes (file, class, call, module)"

### R4: Init Phase 3 update (SHOULD)

Update the init command template in `src/pactkit/prompts/commands.py`:
- In Phase 3 (Discovery), after the file + class visualize steps, add `--mode module` for multi-module projects

### R5: Deploy and verify (MUST)

After editing prompt sources, run `pactkit update` to deploy updated templates. Verify the deployed `.github/skills/pactkit-visualize/SKILL.md` reflects R1 changes.

## Acceptance Criteria

### AC1: SKILL_VISUALIZE_MD contains --mode module (R1)

- **Given** the deployed `SKILL_VISUALIZE_MD` template
- **When** reading the command syntax line
- **Then** it contains `file|class|call|module`

### AC2: --focus description corrected (R1)

- **Given** the `--focus` row in the parameter table
- **When** reading the description
- **Then** it does NOT contain "requires `--mode call`" and instead mentions file, class, call scoping

### AC3: module_graph.mmd in output table (R1)

- **Given** the Output Files table in SKILL_VISUALIZE_MD
- **When** reading the table rows
- **Then** a row for `--mode module` → `module_graph.mmd` exists

### AC4: Visual First includes module mode (R2)

- **Given** the Visual First section in rules.py
- **When** reading the checklist
- **Then** it includes `visualize --mode module`

### AC5: Release snapshot mentions 4 modes (R3)

- **Given** the release skill template
- **When** it references visualize modes
- **Then** it mentions "four modes" or includes "module" in the list

### AC6: Init generates module graph (R4)

- **Given** the init command Phase 3
- **When** reading the discovery steps
- **Then** it includes `visualize --mode module`

### AC7: Deployed SKILL.md matches source (R5)

- **Given** running `pactkit update`
- **When** reading `.github/skills/pactkit-visualize/SKILL.md`
- **Then** it contains `--mode module` in the command syntax

## Target Call Chain

```
src/pactkit/prompts/skills.py    → SKILL_VISUALIZE_MD (string constant)
src/pactkit/prompts/rules.py     → CORE_PROTOCOL (Visual First section)
src/pactkit/prompts/workflows.py → SKILL_RELEASE_MD (snapshot section)
src/pactkit/prompts/commands.py  → CMD_INIT_MD (Phase 3 discovery)
  ↓ (deploy via pactkit update)
.github/skills/pactkit-visualize/SKILL.md
.github/prompts/project-init.prompt.md
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/skills.py` | Update `SKILL_VISUALIZE_MD`: add `--mode module`, fix `--focus`, add output row | None | Low |
| 2 | `src/pactkit/prompts/rules.py` | Add `visualize --mode module` to Visual First | None | Low |
| 3 | `src/pactkit/prompts/workflows.py` | Update release snapshot mode list | None | Low |
| 4 | `src/pactkit/prompts/commands.py` | Add `--mode module` to init Phase 3 | None | Low |
| 5 | Deploy | Run `pactkit update` to deploy templates | Steps 1-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Path Traversal | N/A | Prompt text only, no file I/O |
| SEC-2 Injection | N/A | Prompt text only, no user input handling |
| SEC-3 Auth | N/A | No auth changes |
| SEC-4 Data Exposure | N/A | No sensitive data |
| SEC-5 Dependencies | N/A | No new dependencies |
| SEC-6 Config | N/A | No config surface changes |
| SEC-7 Logging | N/A | No logging changes |
| SEC-8 Crypto | N/A | No cryptographic operations |

## Out of Scope

- Lazy Visualize Protocol: intentionally excludes module mode from auto-refresh (module graph is on-demand only)
- Agent prompt templates: reference visualize generically, no enumeration of modes to update
- Doctor/Trace skills: use specific modes (file+class / call), no need to add module
