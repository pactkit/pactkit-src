# Test Cases: STORY-slim-136 — pactkit done-verify archive honesty gate

| Field | Value |
|-------|-------|
| Story | STORY-slim-136 |
| Level | API (unit) — tests/unit/test_done_verify.py |
| Generated | 2026-08-13 |
| Verdict | QA PASS |

---

## TC-01: 证据链输出与退出码 (R1)


- **Scenario**: All-green story exits 0
  - **Given** a story with spec, case file, done board and existing test files
  - **When** pactkit done-verify runs
  - **Then** every check prints PASS or WARN with evidence
  - **And** the exit code is 0

## TC-02: P0-4 场景复现即拦截 (R3)


- **Scenario**: Board all checked but case has an open declaration
  - **Given** board tasks all checked and a case file containing an open declaration
  - **When** done-verify runs
  - **Then** the R3 check FAILs with the case file line reference
  - **And** the exit code is 1

- **Scenario**: Vocabulary discussed in code spans is not a hit
  - **Given** a case file mentioning blocker vocabulary inside backticks
  - **When** done-verify runs
  - **Then** the R3 check PASSes

## TC-03: 缺失测试证据即拦截 (R2)


- **Scenario**: Missing case file fails and names the gap
  - **Given** a spec with MUST requirements but no case file
  - **When** done-verify runs
  - **Then** the R2 check FAILs citing the missing case file

- **Scenario**: Case file not covering a MUST requirement fails
  - **Given** a case file referencing R1 but not R2
  - **When** done-verify runs
  - **Then** the R2 evidence line for R2 FAILs

- **Scenario**: Mapped test file missing on disk fails
  - **Given** a spec listing tests/unit/test_sample.py which does not exist
  - **When** done-verify runs
  - **Then** the test-files check FAILs naming the missing file

## TC-04: 零生产调用方组件告警 (R4)


- **Scenario**: New symbol with zero callers warns
  - **Given** a new source file whose public function is called nowhere
  - **When** done-verify runs
  - **Then** the R4 check WARNs listing the symbol
  - **And** the exit code stays 0

- **Scenario**: Same-file usage counts as wired
  - **Given** a helper called by other functions in its own module
  - **When** done-verify runs
  - **Then** it is not flagged as an orphan

## TC-05: 状态机矛盾即拦截 (R5)


- **Scenario**: Board complete but spec not flipped fails
  - **Given** board all checked but spec Status still Draft
  - **When** done-verify runs
  - **Then** the R5 check FAILs and exit code is 1

- **Scenario**: Spec Done with unchecked board tasks fails
  - **Given** spec Status Done but unchecked board tasks
  - **When** done-verify runs
  - **Then** the R5 check FAILs

## TC-06: playbook 强制关卡生效 (R6)


- **Scenario**: Gate step exists after spec-status flip in source and artifact
  - **Given** the updated project-done playbook
  - **When** source and pactkit-plugin artifact are inspected
  - **Then** the done-verify step sits after spec-status update and before archive
  - **And** non-zero exit is documented as flow-blocking

## TC-07: 测试套件全通过 (R1-R7)


- **Scenario**: Full suite green and parsers reused
  - **When** .venv/bin/pytest tests/ runs
  - **Then** all tests pass except the pre-existing test_story_slim132 failure
  - **And** done_verify reuses board/spec/test-map parsers (R7)
