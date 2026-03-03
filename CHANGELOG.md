# Changelog

All notable changes to PactKit will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [1.6.3] - 2026-03-03

### Fixed
- **PyPI Logo Display** — README logo now uses absolute GitHub raw URL for PyPI rendering

## [1.6.2] - 2026-03-03

### Added
- **MCP Recommendations** — After `pactkit init` and `pactkit update`, displays 6 recommended MCP servers (Context7, Memory, Playwright, Draw.io, shadcn, Chrome DevTools) with purposes and config hint; helps users discover optional integrations (STORY-062)
- **Subagent Model Selection Guidance** — Core protocol now includes model selection guidance (haiku for simple tasks, sonnet for general, opus for complex); balances cost and capability in multi-agent workflows

## [1.6.1] - 2026-03-03

### Fixed
- **Init Hang Prevention** — Phase 0.5 Git Guard now prints warning instead of blocking prompt; enterprise flags (`--no-git`, `--no-external`, `--non-interactive`) wired end-to-end from CLI to deploy(); `visualize.py` scan truncated at 500 files with `--focus` escape hatch (STORY-060)

### Changed
- **Prompt Token Optimization** — Removed 10 redundant `<thinking>` block instructions from PDCA playbooks (4 in commands.py, 6 in workflows.py); Claude's native extended thinking makes explicit instructions unnecessary, saving ~50-100 tokens per invocation (STORY-061)

## [1.6.0] - 2026-02-28

### Added
- **Security Check Scope Filtering** — Plan generates a Security Scope section in Specs; Check phase skips non-applicable SEC-* checks based on the scope table, reducing false positives for prompt-only changes (STORY-056)

### Fixed
- **Routing Table Accuracy** — Split single "Embedded Skills" table into two: command-invoked (trace, release) and agent-only (draw, status, doctor, review, analyze); corrects 5 incorrect "Embedded In" claims (STORY-058)
- **Playbook Implicit Instructions** — Removed unverifiable Step 1.5 (Fast-Suite Shortcut) that referenced unobservable state; added explicit [High]/[Medium] signal labels to Clarify Gate ambiguity detection (STORY-057)
- **Version Sync on Init/Update** — `pactkit.yaml` version field now auto-syncs to `__version__` on every `pactkit init` and `pactkit update` (BUG-026)

### Changed
- **Lesson Scoring Simplified** — Replaced 5-dimension scoring with 2-check gate for lesson quality evaluation in Done phase
- **CI Dependencies** — Bump actions/checkout from 4 to 6, actions/setup-python from 5 to 6

## [1.5.0] - 2026-02-27

### Added
- **PDCA Quality Gates** — Security checklist, lesson scoring threshold, and implementation steps table in Specs; `check.security_checklist` and `done.lesson_quality_threshold` config fields (STORY-055)
- **Deployment Completeness Audit** — E2E tests verify exact counts and names of deployed files using `VALID_*` set equality assertions (STORY-054)
- **Impact-Based Regression** — `visualize impact --entry <func>` traces callers via call graph for targeted test selection; `regression.strategy` and `regression.max_impact_tests` config (STORY-053)
- **Conditional GitHub Release** — `release.github_release` config enables/disables `gh release create` in release workflow (STORY-052)
- **PDCA Workflow Streamlining** — Split overloaded Done command into focused Done + Release + PR commands; `/project-release` re-promoted from skill to command (STORY-051)
- **Doc-Only Regression Shortcut** — Skip full test suite when only non-source files changed; `LANG_PROFILES[stack].source_dirs` classification (STORY-050)
- **Community Standards** — CODE_OF_CONDUCT.md, SECURITY.md, dependabot.yml with content-assertion tests (STORY-049)
- **Worktree Isolation for Sprint** — `isolation="worktree"` for subagent Sprint; merge/copy recovery instructions for Stage A/C (STORY-048)

### Fixed
- **Stale project-release reference** — Updated stale-ref tests after re-promoting `/project-release` from skill to command (BUG-025)

## [1.4.0] - 2026-02-26

### Added
- **Spec Linter (Non-AI Structural Gate)** — `spec_linter.py` enforces 8 ERROR rules (metadata completeness, AC structure, Given/When/Then, no TBD release) and 4 WARN rules before any Act phase; Plan phase runs self-check after Spec generation; `pactkit spec-lint --all` for batch validation (STORY-042)
- **Active Clarify Gate** — Plan Phase 0.7 auto-detects ambiguous requirements using AMBIGUITY_SIGNALS checklist and generates structured questions (Scope/Users/Constraints/Scale/Edge Cases/Non-Goals); Greenfield projects force-trigger clarification; new `/project-clarify` standalone command (STORY-043)
- **Pre-Act Consistency Check** — Act Phase 0.6 advisory check cross-references Spec requirements with Board tasks and AC items with Test Case coverage; non-blocking with alignment matrix output; `pactkit-analyze` skill added (STORY-044)
- **Auto-PR Enhancement** — Done Phase 4.2 generates structured PR body from Spec/Board/test results with Summary, Changes, Acceptance Criteria checklist, and Test Results sections; user confirmation gate; gh CLI fallback (STORY-045)
- **Multi-Agent Compatibility Layer** — `generators/adapter.py` transforms Claude Code playbooks to Cursor (.mdc), GitHub Copilot (single file), and generic (.ai/) formats; `pactkit init/update --agent {claude,cursor,copilot,generic,all}` deploys to agent-specific directories (STORY-046)
- **Enterprise Configuration Flags** — `EnterpriseConfig` dataclass in `pactkit.yaml` supports `no_git`, `no_external`, `non_interactive`, `debug` fields; CLI flags `--no-git`, `--no-external`, `--non-interactive` override yaml config for air-gapped/CI environments (STORY-047)

### Fixed
- **Spec Linter code-block false positive** — Section parser now strips fenced code blocks before heading detection; `## Section` inside ``` examples no longer shadows real sections

## [1.3.1] - 2026-02-25

### Fixed
- **Dynamic version in CLAUDE.md** — CLAUDE_MD_TEMPLATE now uses `__version__` instead of hardcoded "v23.0"; Docker validation confirms correct version display (BUG-018)
- **project-init CLI invocation** — `/project-init` now invokes `pactkit init` CLI for complete config generation instead of partial inline logic (BUG-017)

## [1.3.0] - 2026-02-24

### Added
- **Conditional CI/CD Pipeline Generation** — `ci.provider` config (github/gitlab/none) generates workflow files; disabled by default (STORY-025)
- **Conditional Issue Tracker Integration** — `issue_tracker.provider` config enables GitHub Issue creation in Plan and closure in Done; standalone Sprint Board preserved (STORY-026)
- **Safe Opt-in Hook Templates** — 3 hook templates (pre-commit lint, post-test coverage, pre-push check); command-type only, report-only (exit 0), disabled by default (STORY-027)
- **Context-Aware Rule Scoping** — `rule_scopes` config maps rule IDs to glob patterns; deployer prepends `includeFiles` frontmatter (STORY-028)
- **Enhanced Doctor Diagnostics** — Stale graph detection (7+ days), orphaned/missing spec detection, config drift detection, severity levels (INFO/WARN/ERROR) (STORY-029)
- **Smart Lint Integration** — `lint_blocking` and `auto_fix` config options for Done command; non-blocking warnings by default (STORY-030)
- **TDD Bailout Decision Tree** — Distinguish project-internal modules from third-party packages in autonomous Sprint mode (STORY-022)
- **Test Quality Gate** — QA check detects tautological and over-mocked tests that pass but verify nothing (STORY-023)
- **Native Agent Enhancement** — Smart model defaults (`inherit`), opt-in hooks, Memory MCP integration in agent frontmatter (STORY-024)
- **Use-case validation for marketplace deployment** — Validated 4 deployment personas (solo dev, team lead, open-source maintainer, enterprise) (STORY-031)
- **Marketplace integration testing** — End-to-end deployment verification for marketplace format with correct path rewriting (STORY-032)
- **Config auto-backfill for missing sections** — `auto_merge_config_file` handles both list-type and non-list sections; `_rewrite_yaml` writes all sections (STORY-033)
- **Auto-refresh pactkit.yaml in Plan Init Guard** — Plan Phase 0.5 checks config completeness and runs `pactkit update` before proceeding (STORY-034)
- **README and docs directory documentation** — Complete project structure section, pactkit.yaml configuration reference, all 9 skills listed (STORY-035)

### Fixed
- **Read-only agent hooks removed** — Prompt hooks on qa-engineer, security-auditor, system-medic, code-explorer caused latency and infinite loop risk; tools/disallowedTools already enforce read-only constraint
- **Visualize excludes deployed directories** — `visualize` now excludes PactKit-deployed directories from graph generation to avoid pollution in marketplace mode (BUG-006)
- **Stale command references in prompt templates** — Comprehensive scan fixed 6 demoted command references across agents.py and skills.py (BUG-007, BUG-008)
- **Project-level config backfill** — `pactkit update` now backfills both global and project-level configs (BUG-009)
- **Config serialization data loss** — `_rewrite_yaml`, `generate_default_yaml`, and `_BACKFILL_KEYS` now stay in sync; `agent_models` and `rule_scopes` were validated but never serialized (BUG-010)
- **Stale command references in agent protocols** — Final sweep fixed 7 remaining demoted command references in agent protocol headers and skill Usage lines (BUG-011)
- **Call graph noise filter** — `_extract_calls` skips builtins and non-self attribute calls; `_build_call_graph` only emits edges where callees resolve to `func_registry` (BUG-012)
- **Single-source config consolidation** — Config now reads exclusively from `$CWD/.claude/pactkit.yaml`; removed dual-config architecture (BUG-013)
- **Version hygiene** — Unified 28 stale spec Release fields, 14 prompt template version labels, and 4 missing CHANGELOG entries; eliminated phantom versions 1.1.5 and 1.2.1 that were never released (BUG-014)

## [1.1.4] - 2026-02-24

### Added
- **CI lint gate** — Done and Act commands now run `lint_command` from `LANG_PROFILES` before commit, catching lint errors that CI would reject (STORY-015)
- **Language matching rule** — Core protocol now respects user's language in all PDCA output; project CLAUDE.md cleaned up to be instruction-focused (STORY-016)
- **Project CLAUDE.md generation** — `project-init` now scaffolds a project-level `.claude/CLAUDE.md` with architecture section, dev commands, and context.md reference (STORY-017)
- **Architecture docs staleness prevention** — Done command now verifies `system_design.mmd` component counts, refreshes `rules.md` test count, and checks release snapshots exist (STORY-018)

### Fixed
- **project-init stack detection** — Remove non-standard `language` field from pactkit.yaml schema; constrain `stack` to valid values (`python|node|go|java`)
- **Version tests use dynamic assertions** — Release tests now read canonical version from `pyproject.toml` instead of hardcoding, preventing CI failures on every version bump

## [1.1.3] - 2026-02-24

### Fixed
- **Multi-import graph edges** — `_build_file_graph` now processes all aliases in `import a, b, c` statements and deduplicates edges (BUG-003)
- **Dead code in deployer** — Remove unused `set(enabled_rules)` no-op in `_deploy_rules` (BUG-004)
- **Archive guard for taskless stories** — `archive_stories` now requires at least one `[x]` task before archiving, aligning with `_classify_story` logic (BUG-005)

## [1.1.2] - 2026-02-14

### Fixed
- **Scripted skill paths** — Use absolute paths in SKILL.md prompts for scripted skills; the LLM runs bash from project cwd, not the skill base directory (BUG-001)
- **Plugin mode paths** — Deploy-time path rewriting for plugin/marketplace modes; templates stay canonical, deployer rewrites `~/.claude/skills` to `${CLAUDE_PLUGIN_ROOT}/skills` at write time (BUG-002)

### Added
- **Draw.io MCP Integration** — `pactkit-draw` instant preview via `@drawio/mcp` when MCP server is available (STORY-013)

### Changed
- **Commands → Skills migration** — Demoted 6 commands (trace, draw, status, doctor, review, release) to prompt-only skills; reduces command count from 14 to 8 (STORY-011)
- Lint fixes for CI compliance

## [1.1.1] - 2026-02-13

### Fixed
- Remove downloads badge — PyPI stats not yet indexed
- Remove unused import in test_pdca_slim

### Changed
- Add governance rules and ignore playwright-mcp artifacts
- Sync pactkit.dev, GitHub metadata, and plugin to PDCA Slim architecture (STORY-012)

## [1.1.0] - 2026-02-13

### Added
- **Config Auto-Merge** — `pactkit init` now auto-appends new components to existing `pactkit.yaml`. Users can opt out via an `exclude` section. (STORY-009)
- **`/project-status`** — Cold-start project orientation command. Read-only report of sprint board, git state, and health indicators. (STORY-007)
- **Session Context Protocol** — `context.md` auto-generated by Done/Plan/Init commands for cross-session state awareness. (STORY-006)
- **Plugin & Marketplace Distribution** — `pactkit init --format plugin` and `--format marketplace` for self-contained distribution. (STORY-005)

### Changed
- **Constitution Sharpening** — Removed pseudo-advantages that overlap with LLM native behavior (55% token reduction). Strengthened Hierarchy of Truth and TDD rules. (STORY-008)

## [1.0.0] - 2026-02-01

### Added
- Initial public release on PyPI
- 9 specialized agents, 13 commands, 3 skills, 6 constitution rules
- PDCA+ lifecycle: Plan, Act, Check, Done, Trace, Draw, Doctor, Sprint, Review, Hotfix, Release, Design
- `pactkit.yaml` config schema with load/validate/generate (STORY-001)
- Selective deployment filtered by config (STORY-002)
- Init Guard for project-plan and project-doctor (STORY-003)
- GitHub/PyPI visibility optimization (STORY-004)
