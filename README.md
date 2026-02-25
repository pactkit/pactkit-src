# PactKit

[![PyPI version](https://img.shields.io/pypi/v/pactkit)](https://pypi.org/project/pactkit/)
[![Python](https://img.shields.io/pypi/pyversions/pactkit)](https://pypi.org/project/pactkit/)
[![CI](https://github.com/pactkit/pactkit/actions/workflows/ci.yml/badge.svg)](https://github.com/pactkit/pactkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Ship features with AI agents that follow specs, not vibes.**

> PactKit gives Claude Code a structured operating system — 9 specialized agents, 8 commands, and a full Plan-Act-Check-Done lifecycle. One `pip install` and your AI assistant writes specs before code, runs TDD, and never commits without passing tests.

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
# Deploy full toolkit (8 commands + 9 agents + 9 skills)
pactkit init

# Update to latest playbooks (preserves your config)
pactkit update

# Check installed version
pactkit version
```

Then in any project with Claude Code:

```bash
# Plan — Analyze requirements, create Spec
/project-plan "Add user authentication"

# Act — Implement with strict TDD
/project-act STORY-001

# Check — Security scan + quality audit (P0-P3 severity)
/project-check

# Done — Safe regression gate + conventional commit
/project-done
```

Or run the full cycle in one command:

```bash
/project-sprint "Add user authentication"
```

## PDCA+ Workflow

| Phase | Command | Agent | What Happens |
|-------|---------|-------|-------------|
| **Plan** | `/project-plan` | System Architect | Codebase scan → Spec generation → Board entry |
| **Act** | `/project-act` | Senior Developer | Visual scan → TDD loop → Regression check |
| **Check** | `/project-check` | QA + Security | 6-phase deep audit (Security/Quality/Spec alignment) |
| **Done** | `/project-done` | Repo Maintainer | Safe regression gate → Archive → Conventional commit |
| **Sprint** | `/project-sprint` | Team Lead | One-command automated PDCA orchestration |
| **Hotfix** | `/project-hotfix` | Senior Developer | Fast-track fix bypassing PDCA (with traceability) |
| **Init** | `/project-init` | System Architect | Bootstrap project structure and governance |
| **Design** | `/project-design` | Product Designer | PRD generation → Story decomposition → Board setup |

### Embedded Skills (auto-invoked by commands)

| Skill | Embedded In | Purpose |
|-------|-------------|---------|
| Trace | Plan, Act | Call graph tracing → Sequence diagram |
| Draw | Plan, Design | Generate Draw.io XML architecture diagrams |
| Status | Init | Cold-start project overview → Sprint + Git + Health report |
| Doctor | Init | Configuration drift detection → Health report |
| Review | Check | PR review with SOLID/Security/Quality checklists |
| Release | Done | Version bump → Archive → Git tag → Changelog |

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

PactKit deploys 9 skills (3 scripted + 6 prompt-only), auto-invoked by commands:

| Skill | Type | Purpose |
|-------|------|---------|
| **pactkit-visualize** | Scripted | Code dependency graph (Mermaid): file-level, class-level, call-level |
| **pactkit-board** | Scripted | Sprint board operations: add story, update task, archive |
| **pactkit-scaffold** | Scripted | File scaffolding: create spec, test files, git branches, skills |
| **pactkit-trace** | Prompt-only | Deep code tracing and execution flow analysis |
| **pactkit-draw** | Prompt-only | Generate Draw.io XML architecture diagrams |
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
├── commands/                 ← 8 command playbooks
├── agents/                   ← 9 agent definitions
└── skills/                   ← 9 skill packages (3 scripted + 6 prompt-only)
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
| `commands` | list | all 8 | Command playbooks to deploy |
| `skills` | list | all 9 | Skills to deploy |
| `rules` | list | all 6 | Constitution rule modules to deploy |
| `exclude` | object | `{}` | Components to exclude (e.g., `exclude.agents: [agent-name]`, `exclude.commands: [cmd-name]`) |
| `ci` | object | `provider: none` | CI/CD pipeline generation; `ci.provider` supports `github`, `gitlab`, `none` |
| `issue_tracker` | object | `provider: none` | External issue tracker; `issue_tracker.provider` supports `github`, `none` |
| `hooks` | object | disabled | Opt-in hook templates (pre-commit, post-test, pre-push); command-type only, report-only |
| `lint_blocking` | bool | `false` | Whether lint failures block commits in Done command |
| `auto_fix` | bool | `false` | Whether to auto-fix lint errors before checking |
| `agent_models` | object | `{}` | Per-agent model overrides (values: `haiku`, `sonnet`, `opus`, `inherit`) |
| `rule_scopes` | object | `{}` | Map rule IDs to glob patterns for context-aware scoping |

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
