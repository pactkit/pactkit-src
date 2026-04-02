# Spec: STORY-058

## Metadata
| Field | Value |
|-------|-------|
| ID | STORY-058 |
| Title | Fix Routing Table Embedded Skills — Match Reality |
| Status | Draft |
| Priority | P2 |
| Author | System Architect |
| Created | 2026-02-28 |
| Release | 1.5.0 |

## Summary
The Embedded Skills table in the Routing Table (`04-routing-table.md`) claims invocation relationships that do not exist in the actual command playbooks. Fix the "Embedded In" column to reflect reality: which commands actually reference each skill, and which skills are only accessible via agents.

## Background
Audit of `src/pactkit/prompts/commands.py` vs the Routing Table revealed 5 incorrect "Embedded In" claims:

| Skill | Routing Table Claims | Reality |
|-------|---------------------|---------|
| `pactkit-draw` | Plan Phase 2, Design Phase 2 | Neither command references it — only used by visual-architect and system-architect agents |
| `pactkit-status` | Init Phase 6, cold-start | Init Phase 6 writes context.md directly — does not invoke this skill. Only system-medic agent uses it |
| `pactkit-doctor` | Init auto-check | Init has no doctor invocation. Only system-medic agent uses it |
| `pactkit-review` | Check Phase 4 (PR variant) | Check Phase 4 is self-contained — does not invoke this skill. Only qa-engineer agent uses it |
| `pactkit-analyze` | Act Phase 0.6 | Act Phase 0.6 implements the same logic inline — does not invoke the skill by name |

The table header says "auto-invoked by commands above" which is factually incorrect for these 5 skills. They are agent-accessible, not command-embedded.

## Target Call Chain

```
rules.py → RULES_MODULES['routing'] → "## Embedded Skills" table
                                        ↓
                                    deployer.py deploys to ~/.claude/rules/04-routing-table.md
                                        ↓
                                    LLM reads routing table to understand skill invocation relationships
```

## Requirements

### R1: Split Embedded Skills Table Into Two Sections
The single "Embedded Skills" table MUST be split into two tables to reflect the real invocation patterns.

**R1.1**: The first table MUST be titled "Embedded Skills (auto-invoked by commands above)" and contain ONLY skills that are actually referenced by command playbooks:

| Skill | Embedded In | Purpose |
|-------|-------------|---------|
| `pactkit-trace` | Plan Phase 1, Act Phase 1 | Deep code tracing and execution flow analysis |
| `pactkit-draw` | visual-architect agent, system-architect agent | Generate Draw.io XML architecture diagrams |
| `pactkit-release` | Release Phase 1 (snapshot/archive) | Version release: snapshot, archive, Tag |

**R1.2**: The second table MUST be titled "Agent Skills (invoked via agent roles, not by commands)" and contain skills that are only accessible through agent definitions:

| Skill | Available To | Purpose |
|-------|-------------|---------|
| `pactkit-status` | system-medic agent | Project state overview |
| `pactkit-doctor` | system-medic agent | Diagnose project health |
| `pactkit-review` | qa-engineer agent | PR Code Review |
| `pactkit-analyze` | Act Phase 0.6 (inline logic) | Cross-artifact consistency check |
| `pactkit-draw` | visual-architect, system-architect agents | Generate Draw.io XML architecture diagrams |

**R1.3**: On further analysis, `pactkit-draw` should be listed ONLY in the Agent Skills table since no command playbook references it.

### R2: Correct the Embedded Skills Table Contents
The final Embedded Skills table (command-invoked) MUST contain exactly these entries:

| Skill | Embedded In | Purpose |
|-------|-------------|---------|
| `pactkit-trace` | Plan Phase 1, Act Phase 1 | Deep code tracing and execution flow analysis |
| `pactkit-release` | Release Phase 1 (snapshot/archive) | Version release: snapshot, archive, Tag |

The final Agent Skills table MUST contain exactly these entries:

| Skill | Available To | Purpose |
|-------|-------------|---------|
| `pactkit-draw` | visual-architect, system-architect agents | Generate Draw.io XML architecture diagrams |
| `pactkit-status` | system-medic agent | Project state overview |
| `pactkit-doctor` | system-medic agent | Diagnose project health |
| `pactkit-review` | qa-engineer agent | PR Code Review |
| `pactkit-analyze` | senior-developer (Act Phase 0.6 inline) | Cross-artifact consistency check: Spec ↔ Board ↔ Test Cases |

### R3: Update Deployed File
The change in `rules.py` MUST propagate to the deployed `~/.claude/rules/04-routing-table.md` via `pactkit update`.

## Acceptance Criteria

### AC1: Routing table has two skill sections
**Given** the `RULES_MODULES['routing']` string
**When** reading the Embedded Skills section
**Then** it contains "Embedded Skills" and "Agent Skills" as two separate headings

### AC2: Command-embedded skills are accurate
**Given** the `RULES_MODULES['routing']` string
**When** reading the "Embedded Skills" table
**Then** it contains only `pactkit-trace` and `pactkit-release` — no `pactkit-draw`, `pactkit-status`, `pactkit-doctor`, `pactkit-review`, or `pactkit-analyze`

### AC3: Agent skills table lists all 5 agent-only skills
**Given** the `RULES_MODULES['routing']` string
**When** reading the "Agent Skills" table
**Then** it contains `pactkit-draw`, `pactkit-status`, `pactkit-doctor`, `pactkit-review`, and `pactkit-analyze`

### AC4: Existing routing table tests still pass
**Given** the existing tests in `test_modular_constitution.py`, `test_story043_active_clarify.py`, `test_sprint_command.py`
**When** running these tests
**Then** all pass (no regression)

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/rules.py` | Replace single Embedded Skills table with two tables | None | Low |
| 2 | `tests/unit/test_story058_routing_fix.py` | Add tests verifying AC1–AC3 | Step 1 | Low |
| 3 | Existing test files | Run to confirm no regression (AC4) | Step 1 | Low |

## Security Scope
| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | No source code logic, only routing metadata |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database code |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth tokens |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No error messages |
| SEC-8 | No | No dependency changes |

## Out of Scope
- Removing orphan skills from the codebase (explicitly deferred)
- Wiring orphan skills into commands (separate story if needed)
- Modifying command playbooks to invoke skills they don't currently use
