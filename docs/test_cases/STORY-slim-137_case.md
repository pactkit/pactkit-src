# Test Cases: STORY-slim-137 — pactkit deps external dependency check/install

| Field | Value |
|-------|-------|
| Story | STORY-slim-137 |
| Level | API (unit) — tests/unit/test_deps.py |
| Generated | 2026-08-13 |
| Verdict | QA PASS |

---

## TC-01: 检测状态表 (R1)


- **Scenario**: Mixed environment reports per-tool status
  - **Given** codegraph installed and gh missing on macOS
  - **When** pactkit deps check runs
  - **Then** codegraph shows installed with version
  - **And** gh shows missing with "brew install gh"
  - **And** the exit code is 1

- **Scenario**: Registry entries are complete and shell-safe
  - **Given** the DEP_REGISTRY
  - **Then** every entry has detect/purpose/install metadata
  - **And** every install command is an argv list, never a shell string

## TC-02: 引导安装 (R2)


- **Scenario**: assume-yes installs via registry command
  - **Given** gh missing on macOS
  - **When** pactkit deps install --yes runs
  - **Then** "brew install gh" is printed before execution
  - **And** a summary line confirms installation

- **Scenario**: Prerequisites install first
  - **Given** both node and codegraph missing
  - **When** install runs
  - **Then** node is attempted before codegraph

- **Scenario**: User decline skips without failure
  - **Given** a missing dependency
  - **When** the user declines at the prompt
  - **Then** the item is skipped with manual instructions and exit code 0

- **Scenario**: A failed item does not stop the rest
  - **Given** one install failing and one succeeding
  - **When** install runs
  - **Then** the failure is reported, later items still attempted, exit code 1

## TC-03: 企业环境拒绝执行 (R2, R5)


- **Scenario**: no_external refuses any install
  - **Given** pactkit.yaml with enterprise.no_external true
  - **When** pactkit deps install runs
  - **Then** no install command executes
  - **And** the refusal explains why with manual guidance

## TC-04: init 接线位置正确 (R3)


- **Scenario**: Phase 1.5 sits between Phase 1 and Phase 3 in both source and artifact
  - **Given** the updated project-init playbook
  - **When** source and pactkit-plugin artifact are inspected
  - **Then** Phase 1.5 exists before Discovery and requires user consent before install

## TC-05: CLI init 只读摘要 (R4)


- **Scenario**: Missing deps are reported, never installed
  - **Given** an environment missing codegraph
  - **When** pactkit init runs (non-interactive)
  - **Then** the output lists the missing dep with manual guidance
  - **And** no install command was executed

## TC-06: doctor 报告 deps 健康 (R4)


- **Scenario**: Missing dependency surfaces in doctor
  - **Given** a missing external dependency
  - **When** pactkit doctor runs
  - **Then** the missing item and install hint are reported
  - **And** the exit code is 1

## TC-07: 测试套件全通过 (R1-R5)


- **Scenario**: Full suite green with installs fully mocked
  - **When** .venv/bin/pytest tests/ runs
  - **Then** all tests pass except the pre-existing test_story_slim132 failure
  - **And** no test performs a real system install
