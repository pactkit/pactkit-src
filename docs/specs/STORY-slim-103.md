# STORY-slim-103: Rules anti-pattern: add Merge-over-Replace and Parameterize-over-Hardcode to existing rules

| Field | Value |
|-------|-------|
| ID | STORY-slim-103 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.6 |

## Background

LLM has two systematic design biases that current rules fail to counter:

1. **Full-replace bias**: LLM defaults to full file overwrites (Write tool) instead of incremental edits (Edit tool / merge). This has caused 5+ bugs in PactKit history (BUG-010, BUG-slim-089, STORY-033, STORY-slim-054) where user config was silently destroyed.

2. **Hardcode bias**: LLM defaults to writing concrete values inline instead of extracting configurable parameters. The existing `No Magic Values` constraint in `12-solution-design.md` only covers code implementation — it misses rules, Specs, configs, and playbooks.

Both biases are LLM cognitive shortcuts (lower token cost, simpler reasoning). Without standing rules, each occurrence is discovered as a bug post-facto and fixed as a one-off spec, never promoted to a reusable principle.

### PDCA Coverage Map (Rules → Commands)

| Rules File | Referenced By |
|---|---|
| `08-architecture-principles.md` | Plan, Act, Design, Sprint |
| `12-solution-design.md` | Plan (Phase 1), Act (Phase 1) |

Both target files are loaded into context during architecture decisions (08) and implementation design (12) — the exact phases where these biases manifest.

## Requirements

### R1: Merge over Replace Principle in 08-architecture-principles.md (MUST)

Add §9 to `~/.claude/rules/08-architecture-principles.md` establishing "Merge over Replace" as a standing architecture principle:
- Signal level: L3 SHOULD (non-blocking, but violation = data loss risk)
- MUST include a Decision Matrix: when full-replace is safe vs. when incremental merge is required
- MUST define the criteria: "If the target file may contain user-modified content or sections managed by other tools, use incremental merge"
- SHOULD reference the 5 historical bugs as evidence (without bloating the rule)

### R2: Expand No Magic Values to All Artifacts in 12-solution-design.md (MUST)

Expand the existing `No Magic Values` constraint in `12-solution-design.md` Implementation Constraints:
- Broaden scope from "code implementation" to "all artifacts" (rules, Specs, configs, playbooks, prompts)
- Add a **Flexibility Litmus Test**: "If changing this value requires grep + multi-file edits, it should be parameterized"
- Add explicit examples for non-code artifacts (rule thresholds, path patterns, tool names)

### R3: No New Rules Files (MUST NOT)

MUST NOT create any new rules file. All changes MUST be edits to existing `08-architecture-principles.md` and `12-solution-design.md` — violation breaks the user's constraint of keeping the rules count stable.

## Acceptance Criteria

### AC1: Merge over Replace principle exists in 08 (R1)

- **Given** `08-architecture-principles.md` is loaded by Plan/Act/Design/Sprint
- **When** LLM reads the file during any PDCA command
- **Then** §9 "Merge over Replace" is present with a Decision Matrix distinguishing safe-to-replace vs. must-merge scenarios

### AC2: No Magic Values scope covers all artifacts (R2)

- **Given** `12-solution-design.md` is loaded by Plan/Act
- **When** LLM enters Implementation Constraints during Solution Design Protocol
- **Then** "No Magic Values" explicitly states it applies to rules, Specs, configs, playbooks — not just code
- **Then** a Flexibility Litmus Test is present ("If changing this value requires grep + multi-file edits → parameterize")

### AC3: No new rules files created (R3)

- **Given** the current rules directory has N files
- **When** this story is implemented
- **Then** the rules directory still has exactly N files (no additions, no deletions)

## Target Call Chain

N/A — this story modifies rules files (prompt-level artifacts), not source code. No call chain.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `~/.claude/rules/08-architecture-principles.md` | Add §9 Merge over Replace with Decision Matrix after §8 | None | Low |
| 2 | `~/.claude/rules/12-solution-design.md` | Expand No Magic Values scope + add Flexibility Litmus Test | None | Low |
| 3 | Verify | Confirm no new files in `~/.claude/rules/`, spec-lint passes | Step 1-2 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | Docs/rules only |
| SEC-2 Auth/AuthZ | N/A | Docs/rules only |
| SEC-3 Data Exposure | N/A | Docs/rules only |
| SEC-4 Injection | N/A | Docs/rules only |
| SEC-5 Cryptography | N/A | Docs/rules only |
| SEC-6 Dependency | N/A | Docs/rules only |
| SEC-7 Logging | N/A | Docs/rules only |
| SEC-8 Config | N/A | Docs/rules only |

## Out of Scope

- Modifying PDCA skill files (skill.md) — the `@` references already load 08 and 12, no skill changes needed
- Adding enforcement tooling (linter, hook) — this story adds principles only; automation is a separate story
- Modifying PactKit source code — rules files are prompt-level artifacts
