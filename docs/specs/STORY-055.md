# Spec: STORY-055

## Metadata
| Field | Value |
|-------|-------|
| ID | STORY-055 |
| Title | PDCA Quality Gates Enhancement |
| Status | Draft |
| Priority | P1 |
| Author | System Architect |
| Created | 2026-02-27 |
| Release | 1.4.0 |

## Summary
Enhance PDCA workflow quality gates by integrating structured security checklists, lesson quality scoring, and implementation step planning. This story consolidates learnings from the `everything-claude-code` project analysis into PactKit's existing PDCA framework without introducing hook dependencies.

## Background
Analysis of the `everything-claude-code` project revealed several valuable patterns:
1. **Structured Security Checklist** - 8-item checklist vs. descriptive prose
2. **Lesson Quality Scoring** - 5-dimension evaluation before saving lessons
3. **Implementation Steps Template** - Dependencies + Risk fields in planning

Current PactKit gaps:
- Check Phase 1 Security Scan is descriptive, not actionable checklist
- Done Phase 3.3 Lessons Auto-append has no quality threshold
- Plan Phase 3.1 Spec template lacks structured implementation planning

## Requirements

### R1: Plan Phase - Spec Template Enhancement
The system MUST add an optional `## Implementation Steps` section to the Spec template.

**R1.1**: The section MUST support a table format with columns: Step, File, Action, Dependencies, Risk.

**R1.2**: The Dependencies column MUST accept values: `None`, `Step N`, or comma-separated step references.

**R1.3**: The Risk column MUST accept values: `Low`, `Medium`, `High`.

**R1.4**: The section SHOULD be auto-populated from Plan Phase 1 Trace findings when modifying existing code.

**R1.5**: The Spec Linter SHOULD add a WARN rule: if `## Implementation Steps` exists, validate table format.

### R2: Check Phase - Structured Security Checklist
The system MUST replace the descriptive Security Scan in Check Phase 1 with a structured 8-item checklist.

**R2.1**: The checklist MUST include these items:
| ID | Category | Check |
|----|----------|-------|
| SEC-1 | Secrets | No hardcoded API keys, tokens, or passwords in source code |
| SEC-2 | Input | All user inputs validated (schema validation or whitelist) |
| SEC-3 | SQL | All database queries use parameterized queries (no string concat) |
| SEC-4 | XSS | User-provided content sanitized before rendering |
| SEC-5 | Auth | Authentication tokens in httpOnly cookies (not localStorage) |
| SEC-6 | Rate | Rate limiting configured on public endpoints |
| SEC-7 | Error | Error messages do not expose stack traces or internal paths |
| SEC-8 | Deps | No known CVEs in dependencies (npm audit / pip-audit clean) |

**R2.2**: Each item MUST output one of: `PASS`, `FAIL`, `N/A` (not applicable to this story).

**R2.3**: Any `FAIL` on SEC-1 through SEC-5 MUST be classified as P0 (Critical).

**R2.4**: The checklist results MUST be included in Phase 5 Verdict under `### Security Checklist`.

**R2.5**: The checklist MAY be disabled via `pactkit.yaml` config `check.security_checklist: false`.

### R3: Done Phase - Lesson Quality Scoring
The system MUST add a 5-dimension quality gate before appending lessons to `lessons.md`.

**R3.1**: The 5 dimensions MUST be:
| Dimension | 1 (Low) | 3 (Medium) | 5 (High) |
|-----------|---------|------------|----------|
| Specificity | Abstract principles only | Has code example | Covers all usage patterns |
| Actionability | Unclear what to do | Main steps understandable | Immediately actionable |
| Scope Fit | Too broad or narrow | Mostly appropriate | Name and content aligned |
| Non-redundancy | Nearly identical to existing | Some unique perspective | Completely unique value |
| Coverage | Partial coverage | Main cases covered | Includes edge cases |

**R3.2**: Each dimension MUST be scored 1-5 by the agent.

**R3.3**: The total score (sum of 5 dimensions, max 25) MUST meet the threshold to append.

**R3.4**: The default threshold MUST be 15 (configurable via `done.lesson_quality_threshold`).

**R3.5**: If score < threshold, the system MUST log: `"Lesson skipped (score {N}/25 < threshold {T})"`.

**R3.6**: If score >= threshold, the lesson row MUST include the score: `| {date} | {summary} (score: {N}/25) | {STORY_ID} |`.

**R3.7**: Lessons triggered by Check Phase P0/P1 findings SHOULD receive a +3 bonus to total score.

### R4: Configuration - New pactkit.yaml Options
The system MUST add new configuration options to `pactkit.yaml`.

**R4.1**: Add `check.security_checklist` (boolean, default: `true`).

**R4.2**: Add `done.lesson_quality_threshold` (integer 0-25, default: `15`).

**R4.3**: The `pactkit update` command MUST backfill these options if missing.

**R4.4**: The `config.py` validation MUST include these new keys in `KNOWN_KEYS`.

### R5: Cross-Phase Linkage
The system SHOULD maintain data flow between phases.

**R5.1**: If Spec contains `## Implementation Steps` with Risk=High items, Check Phase 1 SHOULD prioritize those files for security review.

**R5.2**: If Check Phase 1 produces any FAIL result, Done Phase 3.3 SHOULD auto-generate a lesson candidate with the finding.

**R5.3**: The Consistency Check (Act Phase 0.6) SHOULD verify that `## Implementation Steps` dependencies are satisfied in order.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Add `## Implementation Steps` template to Plan Phase 3.1 | None | Low |
| 2 | `src/pactkit/skills/spec_linter.py` | Add WARN rule for Implementation Steps table format | Step 1 | Low |
| 3 | `src/pactkit/prompts/commands.py` | Replace Check Phase 1 prose with 8-item checklist | None | Medium |
| 4 | `src/pactkit/prompts/commands.py` | Add lesson quality scoring to Done Phase 3.3 | None | Medium |
| 5 | `src/pactkit/config.py` | Add `check` and `done` config sections | None | Low |
| 6 | `tests/unit/test_config.py` | Add tests for new config options | Step 5 | Low |
| 7 | `~/.claude/commands/` | Deploy updated commands via `pactkit init` | Steps 1-4 | Low |

## Acceptance Criteria

### AC1: Spec Template Shows Implementation Steps
**Given** a user runs `/project-plan` for a modification task
**When** Plan Phase 1 Trace identifies multiple files to modify
**Then** the generated Spec includes `## Implementation Steps` with Dependencies and Risk columns

### AC2: Security Checklist Produces Structured Output
**Given** a user runs `/project-check` on a Story with API endpoints
**When** Check Phase 1 Security Scan executes
**Then** the output shows 8 checklist items with PASS/FAIL/N/A status

### AC3: Security FAIL Blocks as P0
**Given** Check Phase 1 detects hardcoded API key (SEC-1 FAIL)
**When** the verdict is generated
**Then** the finding is classified as P0 Critical and included in the Verdict

### AC4: Lesson Quality Gate Filters Low-Value Lessons
**Given** Done Phase 3.3 evaluates a generic lesson "fixed a bug"
**When** the 5-dimension score totals 12/25
**Then** the lesson is NOT appended and log shows "Lesson skipped (score 12/25 < threshold 15)"

### AC5: High-Quality Lesson Includes Score
**Given** Done Phase 3.3 evaluates a specific lesson about race condition fix
**When** the 5-dimension score totals 18/25
**Then** the lesson is appended with format `| 2026-02-27 | Race condition fix pattern (score: 18/25) | STORY-055 |`

### AC6: Config Backfill Works
**Given** an existing project with `pactkit.yaml` missing the new options
**When** user runs `pactkit update`
**Then** `check.security_checklist: true` and `done.lesson_quality_threshold: 15` are added

### AC7: Security Checklist Can Be Disabled
**Given** `pactkit.yaml` contains `check.security_checklist: false`
**When** user runs `/project-check`
**Then** Check Phase 1 skips the 8-item checklist with log "Security checklist disabled via config"

## Target Call Chain
```
Plan Phase 3.1 (Spec Creation)
    └── commands.py::PROJECT_PLAN_PROMPT
        └── Spec template with Implementation Steps section

Check Phase 1 (Security Scan)
    └── commands.py::PROJECT_CHECK_PROMPT
        └── 8-item security checklist evaluation

Done Phase 3.3 (Lessons)
    └── commands.py::PROJECT_DONE_PROMPT
        └── 5-dimension quality scoring
        └── Threshold gate before append

Config Loading
    └── config.py::get_default_config()
        └── check.security_checklist
        └── done.lesson_quality_threshold
    └── config.py::KNOWN_KEYS
    └── config.py::_BACKFILL_KEYS
```

## Out of Scope
- Hook-based automation (explicit non-goal due to stability concerns)
- pass^3 stability testing (deferred to future story)
- Checkpoint workflow for Sprint (deferred to future story)
- Rules directory restructuring (deferred to future story)
- Git pattern extraction command (deferred to future story)

## Dependencies
- STORY-053: Impact-Based Regression (provides `call_graph.mmd` infrastructure)
- STORY-052: Conditional GitHub Release (establishes config pattern for optional features)

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Lesson scoring adds friction to Done | Medium | Low | Threshold configurable, can be set to 0 to disable |
| Security checklist too strict for early projects | Low | Medium | N/A option for each item; can disable via config |
| Implementation Steps adds planning overhead | Low | Low | Section is optional, only populated for multi-file changes |

## References
- [everything-claude-code/skills/security-review](https://github.com/affaan-m/everything-claude-code) - Security checklist source
- [everything-claude-code/commands/learn-eval.md](https://github.com/affaan-m/everything-claude-code) - Lesson quality scoring source
- [everything-claude-code/agents/planner.md](https://github.com/affaan-m/everything-claude-code) - Implementation steps template source
