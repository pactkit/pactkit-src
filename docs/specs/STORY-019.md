# STORY-019: Bailout Protocol for TDD Environment Failures

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.1.5 |

## Context

The `project-act` TDD loop (Phase 3 step 2) tells the agent: "Run ONLY the tests created in Phase 2. Loop until GREEN." The pre-existing test failure protocol (Phase 3 step 3) already has a robust STOP mechanism, but the *new test* TDD loop lacks a bailout for environment-class failures.

When a new test fails due to `ModuleNotFoundError`, `ConnectionError`, `FileNotFoundError(.env)`, or similar environment issues, the agent may loop modifying business code instead of fixing the dependency or asking for help. This wastes tokens and can corrupt the implementation.

## Target Call Chain

```
/project-act
  → Phase 3: Implementation
    → Step 2: TDD Loop (new tests only)
      → Test fails with ModuleNotFoundError     ← GAP: no env-failure detection
      → Agent modifies business code             ← WRONG: should fix deps
      → Loop continues...                        ← Token burn
```

## Requirements

### R1: Environment Failure Detection
- The `project-act` Phase 3 TDD loop MUST include a bailout clause for environment-class errors.
- Environment-class errors include: `ModuleNotFoundError`, `ImportError`, `ConnectionError`, `ConnectionRefusedError`, `FileNotFoundError` (for config/env files), `PermissionError`, and timeout errors from external services.

### R2: Bailout Behavior
- When an environment-class error is detected, the agent MUST NOT modify business logic code.
- The agent SHOULD first attempt to resolve the dependency (e.g., `pip install`, update `requirements.txt`, check `.env`).
- If the dependency cannot be resolved after one attempt, the agent MUST STOP and report to the user.

### R3: Loop Iteration Cap
- The TDD loop SHOULD have a maximum iteration count (e.g., 5 iterations).
- If the loop exceeds the cap without reaching GREEN, the agent MUST STOP and report.

### R4: Prompt-Only Change
- All fixes MUST be prompt-only changes to `src/pactkit/prompts/commands.py`.

## Acceptance Criteria

### Scenario 1: ModuleNotFoundError triggers bailout
- **Given** a new test fails with `ModuleNotFoundError: No module named 'redis'`
- **When** the TDD loop detects this error class
- **Then** the agent attempts `pip install redis` before modifying any business code

### Scenario 2: Loop iteration cap reached
- **Given** the TDD loop has run 5 iterations without reaching GREEN
- **When** iteration 6 would start
- **Then** the agent STOPS and reports: "TDD loop exceeded 5 iterations. Likely cause: [error summary]. Please review."

### Scenario 3: ConnectionError triggers bailout
- **Given** a new test fails with `ConnectionRefusedError` (e.g., Redis/Postgres not running)
- **When** the TDD loop detects this error class
- **Then** the agent STOPS and reports: "Test requires external service. Please ensure [service] is running."

### Scenario 4: Normal logic error does NOT trigger bailout
- **Given** a new test fails with `AssertionError` (normal TDD red)
- **When** the TDD loop continues
- **Then** the agent modifies source code normally (no bailout triggered)
