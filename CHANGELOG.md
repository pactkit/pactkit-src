# Changelog

All notable changes to PactKit will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/).

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
