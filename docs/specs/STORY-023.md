# STORY-023: Test Quality Gate in QA Check

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.1.5 |

## Context

PactKit's QA workflow (`project-check`) verifies Spec alignment and runs tests, but does not audit the **quality of the tests themselves**. The Developer Agent writes tests in Phase 2 (TDD), the Done Agent checks they pass (green), but nobody checks whether those tests are meaningful.

AI agents are prone to writing tautological tests (`assert True`), over-mocked tests (everything stubbed → no real verification), or happy-path-only tests (no error/edge cases). If the QA Agent doesn't catch this, the regression gate becomes a false safety net.

The fix: add a "Test Quality Gate" phase to `project-check` that instructs the QA Agent to audit new test code for common anti-patterns.

## Target Call Chain

```
/project-check Phase 3: Spec Verification
  → Phase 3.5: Test Quality Gate              ← NEW
    → QA reads new test files for this Story
    → Checks for anti-patterns (over-mock, assert True, happy-path-only)
    → Reports findings with severity level
  → Phase 4: Layered Execution (unchanged)
```

## Requirements

### R1: Test Quality Gate Phase
- The `project-check` prompt MUST include a new Phase 3.5 "Test Quality Gate" between Phase 3 (Spec Verification) and Phase 4 (Layered Execution).
- The QA Agent MUST read all test files created or modified for the current Story.

### R2: Anti-Pattern Detection
- The QA Agent MUST check for these test anti-patterns:
  - **Tautological assertions**: `assert True`, `assert 1 == 1`, or assertions that can never fail
  - **Over-mocking**: Test mocks/stubs every dependency such that no real logic is exercised
  - **Happy-path only**: Test only covers the success case, no error/edge/boundary cases
  - **Missing assertion**: Test runs code but has no assert statement (silent pass)
- Each finding SHOULD be assigned a severity (P1 for tautological/missing-assertion, P2 for over-mock/happy-path-only).

### R3: Verdict Integration
- Test quality findings MUST appear in the Phase 5 QA Verdict report under a new "Test Quality" row in the Scan Summary table.

### R4: Prompt-Only Change
- All changes MUST be prompt-only modifications to `src/pactkit/prompts/commands.py`.

## Acceptance Criteria

### Scenario 1: QA detects tautological test
- **Given** a test file contains `assert True` or `assert 1 == 1`
- **When** the QA Agent runs the Test Quality Gate
- **Then** the finding is reported as P1 with "Tautological assertion"

### Scenario 2: QA detects happy-path-only tests
- **Given** all test methods only test the success case (no error inputs, no boundary conditions)
- **When** the QA Agent runs the Test Quality Gate
- **Then** the finding is reported as P2 with "Happy-path only — no error/edge case coverage"

### Scenario 3: QA passes well-written tests
- **Given** test files contain meaningful assertions, cover error cases, and use mocks sparingly
- **When** the QA Agent runs the Test Quality Gate
- **Then** no test quality findings are reported

### Scenario 4: Verdict includes test quality row
- **Given** the QA check completes
- **When** the Phase 5 verdict is generated
- **Then** the Scan Summary table includes a "Test Quality" row with finding counts
