# STORY-054: Deployment Completeness Audit — E2E File Verification

| Field | Value |
|-------|-------|
| ID | STORY-054 |
| Status | Draft |
| Priority | P1 |
| Author | System Architect |
| Created | 2026-02-27 |
| Release | 1.4.0 |

## Background

**已确认 Bug（Docker 验证）**：通过 `python:3.11-slim` 容器执行 `pip install pactkit && pactkit init` 发现，PyPI v1.4.0 部署后缺少 2 个 command：

```
缺失: project-pr.md, project-release.md
PyPI v1.4.0 COMMANDS: 9 个（发布时的状态）
本地源码   COMMANDS: 11 个（后续新增了 project-pr / project-release，未触发新版本发布）
```

本地代码 `VALID_COMMANDS` 与 `COMMANDS_CONTENT` 完全一致（均为 11 个），**本地测试无法复现此 Bug**。
该 Bug 只有通过"安装 PyPI 包 + 运行 init"的容器级验证才能发现。

现有 e2e 测试存在两个不足：
1. 验证条件过宽（`len >= 1`），即使只部署 1 个文件也通过
2. 测试针对本地源码运行，无法覆盖「源码超前于 PyPI 发布包」的情形

本 Story 在现有 e2e 测试中补充**精确完整性断言**，配合 Release Gate 共同防护：
- 完整性测试：保证源码层面 `VALID_*` 与实际部署文件严格对齐（防止 VALID 和 CONTENT 未来出现不一致）
- 当前 Bug 的直接修复：重新发布 PyPI（另行执行 `/project-release`）

## Target Call Chain

```
pactkit init -t <target>
  └── cli.main()
       └── deploy(config=None, target=<target>, format="classic")
            └── _deploy_classic(config, target)
                 ├── _deploy_skills(skills_dir, enabled_skills)     → 10 skill dirs
                 ├── _deploy_rules(claude_root, enabled_rules)       → 6 rule files
                 ├── _deploy_claude_md(claude_root, enabled_rules)   → CLAUDE.md
                 ├── _deploy_agents(agents_dir, enabled_agents)      → 9 agent files
                 └── _deploy_commands(commands_dir, enabled_commands)→ 11 command files
```

## Requirements

### R1: All agents deployed
`pactkit init -t <target>` MUST deploy exactly 9 agent files matching VALID_AGENTS:
- `code-explorer.md`
- `product-designer.md`
- `qa-engineer.md`
- `repo-maintainer.md`
- `security-auditor.md`
- `senior-developer.md`
- `system-architect.md`
- `system-medic.md`
- `visual-architect.md`

### R2: All commands deployed
MUST deploy exactly 11 command files matching VALID_COMMANDS:
- `project-act.md`, `project-check.md`, `project-clarify.md`, `project-design.md`
- `project-done.md`, `project-hotfix.md`, `project-init.md`, `project-plan.md`
- `project-pr.md`, `project-release.md`, `project-sprint.md`

### R3: All skills deployed with correct structure
MUST deploy exactly 10 skill directories matching VALID_SKILLS, each containing at minimum a `SKILL.md` file.

Scripted skills MUST also contain a `scripts/` subdirectory with the corresponding Python script:
- `pactkit-visualize/scripts/visualize.py`
- `pactkit-board/scripts/board.py`
- `pactkit-scaffold/scripts/scaffold.py`

### R4: All rules deployed
MUST deploy exactly 6 rule files matching VALID_RULES:
- `01-core-protocol.md`, `02-hierarchy-of-truth.md`, `03-file-atlas.md`
- `04-routing-table.md`, `05-workflow-conventions.md`, `06-mcp-integration.md`

### R5: No empty files
Every deployed file MUST have non-zero content (size > 0 bytes).

### R6: Agent frontmatter integrity
Every agent `.md` file MUST contain a YAML frontmatter block with the fields:
`name`, `description`, `tools`, `model`.

### R7: Command frontmatter integrity
Every command `.md` file MUST contain a YAML frontmatter block with the fields:
`description`, `allowed-tools`.

### R8: CLAUDE.md references all deployed rules
The deployed `CLAUDE.md` MUST contain `@~/.claude/rules/` import lines for all 6 rules.

## Acceptance Criteria

### AC1: Full Agent Completeness
**Given** `pactkit init -t <target>` runs against a clean empty directory
**When** I list `target/agents/*.md`
**Then** I MUST find exactly 9 files matching every identifier in `VALID_AGENTS`

### AC2: Full Command Completeness
**Given** `pactkit init -t <target>` runs against a clean empty directory
**When** I list `target/commands/*.md`
**Then** I MUST find exactly 11 files matching every identifier in `VALID_COMMANDS`

### AC3: Full Skill Completeness
**Given** `pactkit init -t <target>` runs against a clean empty directory
**When** I inspect `target/skills/`
**Then** I MUST find exactly 10 subdirectories matching `VALID_SKILLS`
**And** each subdirectory MUST contain `SKILL.md`
**And** `pactkit-visualize`, `pactkit-board`, `pactkit-scaffold` MUST each have `scripts/<name>.py`

### AC4: Full Rule Completeness
**Given** `pactkit init -t <target>` runs against a clean empty directory
**When** I list `target/rules/*.md`
**Then** I MUST find exactly 6 files matching the filenames derived from `VALID_RULES`

### AC5: No Empty Files
**Given** any deployed file (agent, command, skill `SKILL.md`, rule, `CLAUDE.md`)
**When** I check its byte size
**Then** the size MUST be greater than 0

### AC6: Agent Frontmatter Valid
**Given** any deployed agent file in `target/agents/`
**When** I read its content
**Then** it MUST start with `---` (YAML frontmatter delimiter)
**And** MUST contain the fields `name:`, `description:`, `tools:`, `model:`

### AC7: CLAUDE.md Rule References
**Given** `target/CLAUDE.md` deployed by `pactkit init`
**When** I read its content
**Then** it MUST contain exactly 6 lines beginning with `@~/.claude/rules/`
**And** each of the 6 rule filenames MUST appear in those lines

## Implementation Notes

- Add a new test class `TestDeploymentCompleteness` to `tests/e2e/cli/test_cli_e2e.py`
- Import `VALID_AGENTS`, `VALID_COMMANDS`, `VALID_SKILLS`, `VALID_RULES` from `pactkit.config`
- Use the existing `run_pactkit("init", "-t", str(target))` subprocess pattern
- Scripted skills set: `{'pactkit-visualize', 'pactkit-board', 'pactkit-scaffold'}`

## Non-Goals

- Docker-based isolation (virtualenv is sufficient for CI completeness check)
- Content accuracy validation (covered by existing unit tests in `test_prompts_package.py`, `test_skill_structure.py`, etc.)
- PyPI version pinning (assume latest installed)
