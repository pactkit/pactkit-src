# STORY-021: Spec Amendment Protocol (RFC Mechanism)

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.2.0 |

## Context

The Hierarchy of Truth (rule 02) establishes: Spec > Tests > Code. When code conflicts with a Spec, modify the code. This is correct as a default, but it creates a blind obedience problem: if the Spec itself is technically infeasible, the Senior Developer agent has no protocol to escalate.

Current behavior: the Developer agent encounters an impossible Spec requirement, cannot modify the Spec (Tier 1 is sacred), and either produces bad code trying to satisfy it or silently ignores the requirement. Neither outcome is acceptable.

The fix is a formal "RFC (Request for Change)" protocol that lets the Developer agent flag a Spec issue, STOP implementation, and request human review — without violating the Hierarchy of Truth.

## Target Call Chain

```
/project-act
  → Phase 0: Read Spec
    → Developer finds infeasible requirement     ← GAP: no escalation path
    → Continues implementing bad solution         ← WRONG

Proposed:
  → Phase 0: Read Spec
    → Developer finds infeasible requirement
    → Triggers RFC Protocol                       ← NEW
    → STOP and report to user                     ← SAFE
```

## Requirements

### R1: RFC Trigger in project-act
- The `project-act` prompt Phase 0 MUST include an RFC clause: "If you identify a requirement in the Spec that is technically infeasible, contradictory, or would require violating a security/architectural constraint, invoke the RFC Protocol."

### R2: RFC Protocol Behavior
- The agent MUST STOP implementation immediately.
- The agent MUST report to the user with:
  - Which Spec requirement is problematic (quote the exact text).
  - Why it is infeasible (technical reasoning).
  - A suggested alternative approach.
- The agent MUST NOT modify the Spec unilaterally — only the user (or Architect agent in a new Plan cycle) may amend Tier 1.

### R3: Hierarchy of Truth Amendment
- Rule 02 (`hierarchy-of-truth`) SHOULD be updated to add an exception clause: "If the Senior Developer determines a Spec requirement is technically infeasible, they MUST invoke the RFC Protocol rather than producing non-compliant code."
- The amendment MUST NOT weaken the general principle (Spec > Code). It only adds an escalation path.

### R4: Prompt-Only Changes
- All changes MUST be prompt-only modifications to `src/pactkit/prompts/commands.py` and `src/pactkit/prompts/rules.py`.

## Acceptance Criteria

### Scenario 1: Infeasible Spec triggers RFC
- **Given** a Spec requires "implement distributed locking using SQLite"
- **When** the Developer agent reads the Spec in Phase 0
- **Then** the agent invokes RFC Protocol: STOP, report the infeasibility, suggest alternatives

### Scenario 2: Normal Spec proceeds without RFC
- **Given** a Spec requires "add input validation to the login form"
- **When** the Developer agent reads the Spec in Phase 0
- **Then** the agent proceeds to Phase 1 normally (no RFC triggered)

### Scenario 3: RFC does not grant Spec modification rights
- **Given** the Developer agent invokes RFC Protocol
- **When** the agent reports the issue
- **Then** the agent does NOT modify the Spec file — it STOPS and waits for user guidance

### Scenario 4: Hierarchy of Truth preserves Spec authority
- **Given** a normal code-vs-Spec conflict (code is wrong, Spec is correct)
- **When** the conflict is detected
- **Then** the code is modified per Spec (existing behavior unchanged)
