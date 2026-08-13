# Test Cases: STORY-slim-138 — pactkit commit-gate pre-commit test gate

| Field | Value |
|-------|-------|
| Story | STORY-slim-138 |
| Level | API (unit) — tests/unit/test_commit_gate.py |
| Generated | 2026-08-13 |
| Verdict | QA PASS |

---

## TC-01: 红灯拦截 (R1)


- **Scenario**: Failing mapped tests block
  - **Given** a changed source file whose mapped tests fail
  - **When** pactkit commit-gate runs
  - **Then** the output summarizes failures and implicated files
  - **And** the exit code is 1

## TC-02: IMPACT 最小测试集 (R1)


- **Scenario**: Impact strategy runs only mapped test files
  - **Given** one changed source file mapped to two test files
  - **When** commit-gate runs
  - **Then** only those files are passed to pytest

- **Scenario**: Empty mapping falls back to full unit suite
  - **Given** a changed file with no test mapping
  - **When** commit-gate runs
  - **Then** the full unit suite runs

- **Scenario**: Doc-only changes skip testing
  - **Given** only docs changed
  - **When** commit-gate runs
  - **Then** the gate exits 0 without invoking pytest

## TC-03: skip 透明化 (R2)


- **Scenario**: Skips are listed explicitly
  - **Given** a run with 10 passed and 3 environment-skipped tests
  - **When** commit-gate runs
  - **Then** passed/failed/skipped are reported separately
  - **And** each skipped test and its reason is listed as WARN
  - **And** the exit code is 0

## TC-04: hook 模式只拦 git commit (R3)


- **Scenario**: Non-commit commands pass instantly
  - **Given** a hook payload for git status
  - **When** commit-gate --hook runs
  - **Then** it exits 0 without running tests

- **Scenario**: Red commit is blocked with exit 2
  - **Given** a hook payload for git commit with failing tests
  - **When** commit-gate --hook runs
  - **Then** it exits 2 with the reason on stderr

- **Scenario**: Explicit --no-verify bypass is allowed
  - **Given** a hook payload for git commit --no-verify
  - **When** commit-gate --hook runs
  - **Then** it exits 0 without running tests

## TC-05: 门禁自锁防护 (R3)


- **Scenario**: pytest missing allows with loud WARN
  - **Given** an environment without pytest
  - **When** commit-gate --hook processes a commit
  - **Then** it exits 0 with a gate-unavailable warning

## TC-06: hook 幂等部署 (R4)


- **Scenario**: Install preserves user config and is idempotent
  - **Given** a settings.json with existing user configuration
  - **When** install_hook runs twice
  - **Then** user keys are preserved and exactly one pactkit entry exists

- **Scenario**: Invalid JSON is left untouched
  - **Given** a malformed settings.json
  - **When** install_hook runs
  - **Then** the file is unchanged and a warning is returned

- **Scenario**: enterprise.no_git skips installation
  - **Given** pactkit.yaml with enterprise.no_git true
  - **When** install_hook runs
  - **Then** no settings.json is created

## TC-07: 主干分支全量 (R1)


- **Scenario**: Direct commits on main/master/develop run full suite
  - **Given** the current branch is a main-line branch
  - **When** commit-gate runs
  - **Then** the full unit suite runs regardless of impact mapping

## TC-08: 测试套件全通过 (R1-R5)


- **Scenario**: Full suite green
  - **When** .venv/bin/pytest tests/ runs
  - **Then** all tests pass except the pre-existing test_story_slim132 failure
