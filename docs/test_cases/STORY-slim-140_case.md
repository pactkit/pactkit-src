# Test Cases: STORY-slim-140 — commit-gate git-hook fallback for non-Claude environments

| Field | Value |
|-------|-------|
| Story | STORY-slim-140 |
| Level | API (unit) — tests/unit/test_commit_gate.py TestGateChannelDispatch |
| Generated | 2026-08-13 |
| Verdict | QA PASS |

---

## TC-01: 纯 codex 部署自动装 git hook (R1, R2)

- **Scenario**: Non-Claude format with .git gets the pre-commit channel
  - **Given** a project without .claude and with .git
  - **When** ensure_gate_channel runs for format codex
  - **Then** .git/hooks/pre-commit contains pactkit commit-gate
  - **And** the channel reports "git pre-commit"

## TC-02: Claude 环境行为不变 (R1, R2)

- **Scenario**: Classic format keeps the PreToolUse channel only
  - **Given** a classic deploy
  - **When** ensure_gate_channel runs
  - **Then** .claude/settings.json holds the hook and no git hook is auto-installed
  - **And** the channel reports "PreToolUse hook"

## TC-03: no_git 豁免 (R1)

- **Scenario**: enterprise.no_git disables every channel
  - **Given** pactkit.yaml with enterprise.no_git true
  - **When** ensure_gate_channel runs for codex
  - **Then** neither hook is installed and the channel names no_git

## TC-04: 幂等与链式共存 (R3)

- **Scenario**: Repeat dispatch preserves third-party hooks
  - **Given** an existing third-party pre-commit hook
  - **When** ensure_gate_channel runs twice for codex
  - **Then** the third-party content survives with exactly one pactkit entry
