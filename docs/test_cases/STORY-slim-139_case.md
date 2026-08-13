# Test Cases: STORY-slim-139 — Skill manifest single source + adapter parity

| Field | Value |
|-------|-------|
| Story | STORY-slim-139 |
| Level | API (unit) — tests/unit/test_story_slim139_skill_manifest.py + adapter E2E |
| Generated | 2026-08-13 |
| Verdict | QA PASS |

---

## TC-01: 清单单一事实源 (R1)

- **Scenario**: Manifest covers every pactkit skill exactly once
  - **Given** the SKILL_MANIFEST registry
  - **When** compared against VALID_SKILLS pactkit-* entries
  - **Then** the name sets are equal and every entry has skill_md plus script_name metadata

- **Scenario**: _deploy_skills contains no local hardcoded list
  - **Given** the refactored deployer
  - **When** its source is inspected
  - **Then** it iterates get_skill_manifest() with no scripted/prompt-only local lists

## TC-02: 部署清单可机器读 (R2)

- **Scenario**: Deploy writes a manifest matching the actual deployment
  - **Given** a deploy for any format
  - **When** .pactkit-deployed.json is read
  - **Then** it carries format, pactkit version, and skills/commands/agents lists
  - **And** commands respect profile exclusions (no project-sprint for codex)

## TC-03: 漂移被显式报告 (R3)

- **Scenario**: Manifest missing a registry skill is reported
  - **Given** a codex manifest lacking pactkit-garden
  - **When** check_deploy_parity runs
  - **Then** drift is True naming codex and pactkit-garden

- **Scenario**: Missing or corrupt manifests degrade to warnings
  - **Given** a deployed-looking directory without a manifest, or with corrupt JSON
  - **When** check_deploy_parity runs
  - **Then** a re-deploy warning is emitted and drift stays False

## TC-04: 合法差异不误报 (R3, R5)

- **Scenario**: Capability-matrix exclusions are not drift
  - **Given** a codex deployment legitimately lacking project-sprint
  - **When** check_deploy_parity runs
  - **Then** no sprint-related drift is reported

## TC-05: adapter 消费后补齐 (R4)

- **Scenario**: codex adapter deploys the full registry
  - **Given** the refactored pactkit-codex consuming get_skill_manifest()
  - **When** a codex deploy runs
  - **Then** 13 skills deploy including garden/audit/report
  - **And** the deployment manifest is written

- **Scenario**: copilot adapter keeps its format-specific extra
  - **Given** the refactored pactkit-copilot
  - **When** a copilot deploy runs
  - **Then** 13 skills deploy and spec_linter.py still ships beside scaffold.py

## TC-06: 测试套件全通过 (R1-R5)

- **Scenario**: Core and adapter suites green
  - **When** the core suite and each adapter suite run
  - **Then** no new failures (adapter pre-existing failures unchanged at baseline)
