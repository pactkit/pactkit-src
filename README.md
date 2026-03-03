<p align="center">
  <img src="https://raw.githubusercontent.com/pactkit/pactkit/main/docs/assets/logo.png" alt="PactKit" width="480" />
</p>

<p align="center">
  <a href="https://pypi.org/project/pactkit/"><img src="https://img.shields.io/pypi/v/pactkit" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/pactkit/"><img src="https://img.shields.io/pypi/pyversions/pactkit" alt="Python" /></a>
  <a href="https://github.com/pactkit/pactkit/actions/workflows/ci.yml"><img src="https://github.com/pactkit/pactkit/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
</p>

<p align="center"><strong>Ship features with AI agents that follow specs, not vibes.</strong></p>

> PactKit gives Claude Code a structured operating system — 9 specialized agents, 11 commands, 10 skills, and a full Plan-Act-Check-Done lifecycle. One `pip install` and your AI assistant writes specs before code, runs TDD, and never commits without passing tests.

### What it looks like

```
You:  /project-sprint "Add OAuth2 login"

 Plan   System Architect scans codebase, writes Spec, updates Board
 Act    Senior Developer writes tests first (RED), then code (GREEN)
 Check  QA Engineer runs 6-phase audit (security + quality + spec alignment)
 Done   Repo Maintainer gates regression, archives story, commits
```

## Why PactKit?

AI coding assistants are powerful but unpredictable without structure. PactKit adds a **spec-driven governance layer**:

- **Spec is the Law** — Specifications are the single source of truth (Spec > Tests > Code)
- **Multi-Agent Ensemble** — 9 specialized agents collaborate, each with defined roles
- **Full PDCA Lifecycle** — Plan → Act → Check → Done, with quality gates at every stage
- **Safe by Design** — TDD-first development, safe regression testing, pre-existing test protection

## Installation

```bash
pip install pactkit
```

Requires Python 3.10+ and [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Quick Start

```bash
# Deploy full toolkit (11 commands + 9 agents + 10 skills)
pactkit init

# Update to latest playbooks (preserves your config)
pactkit update

# Deploy to multiple AI agents (Claude Code + Cursor + Copilot)
pactkit init --agent all

# Check installed version
pactkit version
```

Then in any project with Claude Code:

```bash
# Clarify — Surface ambiguities before planning
/project-clarify "Add user authentication"

# Plan — Analyze requirements, create Spec
/project-plan "Add user authentication"

# Act — Spec lint + consistency check + TDD implementation
/project-act STORY-001

# Check — Security scan + quality audit (P0-P3 severity)
/project-check

# Done — Regression gate + auto-PR + conventional commit
/project-done
```

Or run the full cycle in one command:

```bash
/project-sprint "Add user authentication"
```

## PDCA+ Workflow

| Phase | Command | Agent | What Happens |
|-------|---------|-------|-------------|
| **Clarify** | `/project-clarify` | System Architect | Ambiguity detection → Structured questions → Clarified brief |
| **Plan** | `/project-plan` | System Architect | Clarify gate → Codebase scan → Spec generation → Board entry |
| **Act** | `/project-act` | Senior Developer | Spec lint → Consistency check → TDD loop → Regression check |
| **Check** | `/project-check` | QA + Security | 8-item security checklist + quality audit + spec alignment |
| **Done** | `/project-done` | Repo Maintainer | Regression gate → Archive → Conventional commit |
| **Release** | `/project-release` | Repo Maintainer | Version bump → Snapshot → Git tag → GitHub Release |
| **PR** | `/project-pr` | Repo Maintainer | Push branch → Create pull request via gh CLI |
| **Sprint** | `/project-sprint` | Team Lead | One-command automated PDCA orchestration |
| **Hotfix** | `/project-hotfix` | Senior Developer | Fast-track fix bypassing PDCA (with traceability) |
| **Init** | `/project-init` | System Architect | Bootstrap project structure and governance |
| **Design** | `/project-design` | Product Designer | PRD generation → Story decomposition → Board setup |

### Embedded Skills (auto-invoked by commands)

| Skill | Embedded In | Purpose |
|-------|-------------|---------|
| Trace | Plan Phase 1, Act Phase 1 | Deep code tracing and execution flow analysis |
| Release | Release Phase 1 | Version release: snapshot, archive, Git tag |

### Agent Skills (invoked via agent roles)

| Skill | Available To | Purpose |
|-------|-------------|---------|
| Draw | visual-architect, system-architect | Generate Draw.io XML architecture diagrams |
| Status | system-medic | Project state overview |
| Doctor | system-medic | Diagnose project health |
| Review | qa-engineer | PR Code Review |
| Analyze | senior-developer (Act inline) | Cross-artifact consistency check: Spec ↔ Board ↔ Test Cases |

## Agent Ensemble

PactKit deploys 9 specialized agents, each with constrained tools and focused responsibilities:

| Agent | Role | Core Capability |
|-------|------|----------------|
| System Architect | Architecture design | Maintain Intent Graph, write Specs |
| Senior Developer | Full-stack development | TDD loop, call chain analysis, hotfix |
| QA Engineer | Quality gates | Deep check (P0-P3), PR review |
| Security Auditor | Security audit | OWASP scanning, threat modeling |
| Repo Maintainer | Repository ops | Cleanup, archiving, Git conventions, releases |
| System Medic | System diagnostics | Configuration drift repair |
| Visual Architect | Architecture visualization | Draw.io XML generation |
| Code Explorer | Code tracing | Call graph + sequence diagram |
| Product Designer | Product design | PRD, story decomposition, board init |

## Skills

PactKit deploys 10 skills (3 scripted + 7 prompt-only), auto-invoked by commands:

| Skill | Type | Purpose |
|-------|------|---------|
| **pactkit-visualize** | Scripted | Code dependency graph (Mermaid): file-level, class-level, call-level |
| **pactkit-board** | Scripted | Sprint board operations: add story, update task, archive |
| **pactkit-scaffold** | Scripted | File scaffolding: create spec, test files, git branches, skills |
| **pactkit-trace** | Prompt-only | Deep code tracing and execution flow analysis |
| **pactkit-draw** | Prompt-only | Generate Draw.io XML architecture diagrams |
| **pactkit-analyze** | Prompt-only | Cross-artifact consistency check: Spec ↔ Board ↔ Test Cases |
| **pactkit-status** | Prompt-only | Cold-start project overview (sprint + git + health) |
| **pactkit-doctor** | Prompt-only | Configuration drift detection and health report |
| **pactkit-review** | Prompt-only | PR code review with SOLID/Security/Quality checklists |
| **pactkit-release** | Prompt-only | Version bump, architecture snapshot, git tag |

## Safe Regression

PactKit's safe regression system prevents agents from blindly modifying pre-existing tests:

- **TDD Loop** — Only iterates on tests created in the current story
- **Regression Check** — Read-only gate; pre-existing test failure = STOP and report
- **Done Gate** — Full regression by default; incremental only when ALL safety conditions are met

## Hierarchy of Truth

```
Tier 1: Specs & Test Cases           — The Law
Tier 2: Tests                        — The Verification
Tier 3: Implementation               — The Mutable Reality
```

When conflicts arise: Spec wins. Always.

## Project Structure (PDCA-managed)

PactKit's PDCA lifecycle manages a `docs/` directory with the following structure:

```
docs/
├── product/
│   ├── sprint_board.md          ← Current iteration board (Backlog/In Progress/Done)
│   ├── context.md               ← Auto-generated session context for cross-session awareness
│   ├── archive/                 ← Archived completed stories (by month)
│   └── prd.md                   ← Product Requirements Document (greenfield projects)
├── specs/                       ← The Law — requirement specifications (STORY-*, BUG-*, HOTFIX-*)
├── test_cases/                  ← Gherkin acceptance scenarios mapped from specs
└── architecture/
    ├── graphs/                  ← Architecture graph files (Mermaid .mmd)
    │   ├── code_graph.mmd       ← File-level dependency graph (auto-generated)
    │   ├── class_graph.mmd      ← Class diagram with inheritance
    │   ├── call_graph.mmd       ← Function-level call graph
    │   └── system_design.mmd    ← High-level design (manually maintained)
    ├── governance/
    │   ├── rules.md             ← Architecture decisions (ADRs) and invariants
    │   └── lessons.md           ← Lessons learned per story (auto-appended by Done)
    └── snapshots/               ← Versioned architecture graph snapshots
```

## Configuration

PactKit deploys to `~/.claude/`:

```
~/.claude/
├── CLAUDE.md                 ← Modular constitution (entry point)
├── rules/                    ← 6 rule modules
├── commands/                 ← 11 command playbooks
├── agents/                   ← 9 agent definitions
└── skills/                   ← 10 skill packages (3 scripted + 7 prompt-only)
    ├── pactkit-visualize/
    ├── pactkit-board/
    └── pactkit-scaffold/
```

### pactkit.yaml Configuration Reference

The `pactkit.yaml` file controls which components are deployed and how they behave. All fields below are configurable:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stack` | string | auto-detected | Project stack (`python`, `node`, `go`, `java`) |
| `version` | string | current | PactKit version that generated the config |
| `root` | string | `.` | Project root directory (deployment target resolves to `~/.claude` by default) |
| `agents` | list | all 9 | Agent definitions to deploy |
| `commands` | list | all 11 | Command playbooks to deploy |
| `skills` | list | all 10 | Skills to deploy |
| `rules` | list | all 6 | Constitution rule modules to deploy |
| `exclude` | object | `{}` | Components to exclude (e.g., `exclude.agents: [agent-name]`, `exclude.commands: [cmd-name]`) |
| `ci` | object | `provider: none` | CI/CD pipeline generation; `ci.provider` supports `github`, `gitlab`, `none` |
| `issue_tracker` | object | `provider: none` | External issue tracker; `issue_tracker.provider` supports `github`, `none` |
| `hooks` | object | disabled | Opt-in hook templates (pre-commit, post-test, pre-push); command-type only, report-only |
| `lint_blocking` | bool | `false` | Whether lint failures block commits in Done command |
| `auto_fix` | bool | `false` | Whether to auto-fix lint errors before checking |
| `check.security_checklist` | bool | `true` | Enable 8-item structured security checklist in Check phase |
| `done.lesson_quality_threshold` | int | `15` | Minimum quality score (0-25) for lessons to be auto-appended |
| `agent_models` | object | `{}` | Per-agent model overrides (values: `haiku`, `sonnet`, `opus`, `inherit`) |
| `rule_scopes` | object | `{}` | Map rule IDs to glob patterns for context-aware scoping |
| `enterprise` | object | all `false` | Enterprise flags: `no_git`, `no_external`, `non_interactive`, `debug` |

## MCP Integration

PactKit conditionally integrates with MCP servers when available:

| MCP Server | Purpose | PDCA Phase |
|------------|---------|------------|
| Context7 | Library documentation lookup | Act |
| shadcn | UI component search/install | Design |
| Playwright | Browser automation testing | Check |
| Chrome DevTools | Performance/console/network | Check |
| Memory | Cross-session knowledge graph | Plan/Act/Done |
| Draw.io | Architecture diagram instant preview | Plan, Design |

All MCP instructions are conditional — gracefully skipped when unavailable.

## Upgrading

```bash
pip install --upgrade pactkit
pactkit update
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
