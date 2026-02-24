# STORY-022: Bailout Decision Tree (Project Module vs Third-Party)

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.2.0 |

## Context

STORY-019 introduced a Bailout Protocol in Act Phase 3 TDD loop: when a test fails with `ModuleNotFoundError` or `ImportError`, the agent stops modifying business code and attempts `pip install` or reports to the user.

The current bailout treats ALL `ModuleNotFoundError` equally. But there are two distinct cases:
1. **Third-party package** (`import redis`) — agent cannot create this, bailout is correct
2. **Project-internal module** (`from myapp.new_feature import X`) — agent SHOULD create this as part of its implementation task, bailout is incorrect

In normal `/project-act` this is low-impact (user can correct). In `/project-sprint` (autonomous multi-agent), a false bailout blocks the pipeline without human intervention.

## Target Call Chain

```
/project-act Phase 3 Step 2: TDD Loop
  → Test fails with ModuleNotFoundError
  → Current: always trigger bailout           ← IMPRECISE
  → Proposed: check if module is project-internal
    → If project module → continue implementing (back to Step 1)  ← NEW
    → If third-party   → trigger bailout (existing behavior)      ← UNCHANGED
```

## Requirements

### R1: Decision Tree in Bailout
- The bailout prompt MUST include a decision step before triggering: "Check if the missing module path is under the project root directory."
- If the module IS a project-internal path, the agent MUST treat it as incomplete implementation and return to Phase 3 Step 1 to create the module.
- If the module is NOT project-internal (third-party package, external service), the existing bailout behavior MUST apply unchanged.

### R2: ImportError Distinction
- The same decision tree SHOULD apply to `ImportError` (e.g., `cannot import name 'X' from 'myapp.utils'`): if the source file is in the project, this is the agent's code to fix, not an environment issue.

### R3: Prompt-Only Change
- All changes MUST be prompt-only modifications to `src/pactkit/prompts/commands.py`.
- No Python runtime code changes required.

## Acceptance Criteria

### Scenario 1: Project module triggers continue, not bailout
- **Given** a test fails with `ModuleNotFoundError` for a module under the project root
- **When** the bailout decision tree is evaluated
- **Then** the agent treats it as incomplete implementation and continues coding

### Scenario 2: Third-party package triggers bailout
- **Given** a test fails with `ModuleNotFoundError` for a third-party package (e.g., `redis`, `celery`)
- **When** the bailout decision tree is evaluated
- **Then** the existing bailout behavior applies (pip install → STOP if unresolved)

### Scenario 3: ImportError on project file triggers continue
- **Given** a test fails with `ImportError: cannot import name 'X' from 'myapp.utils'`
- **When** the bailout decision tree is evaluated
- **Then** the agent recognizes `myapp.utils` as project code and modifies it

### Scenario 4: Existing bailout for external services unchanged
- **Given** a test fails with `ConnectionRefusedError` or `PermissionError`
- **When** the bailout decision tree is evaluated
- **Then** behavior is unchanged (STOP and report)
