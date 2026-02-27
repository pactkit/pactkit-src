
### [STORY-005] Plugin Distribution — 支持 Claude Code Plugin 格式分发
> Spec: docs/specs/STORY-005.md

- [x] Add --format parameter to CLI (classic/plugin/marketplace)
- [x] Implement _deploy_plugin_json() for .claude-plugin/plugin.json
- [x] Implement _deploy_claude_md_inline() for self-contained CLAUDE.md
- [x] Implement plugin mode in deploy() — full component deployment
- [x] Implement _deploy_marketplace_json() for marketplace repo structure
- [x] Write unit tests for plugin mode deployment
- [x] Write unit tests for marketplace mode deployment
- [x] Verify classic mode unchanged — all existing tests pass
- [x] Integration test: claude --plugin-dir loads generated plugin

### [STORY-006] Session Context Protocol — 跨会话项目状态自动感知
> Spec: docs/specs/STORY-006.md

- [x] Add context.md generation to Done playbook
- [x] Add context.md generation to Plan playbook
- [x] Add context.md generation to Init playbook
- [x] Add @context.md reference to CLAUDE_MD_TEMPLATE
- [x] Add lessons.md auto-append to Done playbook
- [x] Write unit tests for prompt changes
- [x] Verify plugin mode inline CLAUDE.md unaffected

### [STORY-007] /project-status 冷启动项目状态感知命令
> Spec: docs/specs/STORY-007.md

- [x] Add project-status.md playbook to commands.py
- [x] Add to VALID_COMMANDS and routing table
- [x] Write unit tests for new command content
- [x] Verify non-initialized project fallback

### [STORY-008] Constitution Sharpening — 删除伪优势强化治理规则
> Spec: docs/specs/STORY-008.md

- [x] Remove pseudo-advantages from 01-core-protocol
- [x] Add Session Context rule to core protocol
- [x] Strengthen Hierarchy of Truth wording
- [x] Update tests for changed rule content
- [x] Verify token reduction >= 30%

### [STORY-009] Config Auto-Merge — pactkit init 自动合并新组件
> Spec: docs/specs/STORY-009.md

- [x] Modify load_config() merge logic
- [x] Add auto-append for new components
- [x] Handle user opt-out (exclude)
- [x] Add version tracking to yaml
- [x] Update tests
- [x] Backward compatibility verification

### [STORY-010] Release v1.1.0 — 文档同步 + 版本发布
> Spec: docs/specs/STORY-010.md

- [x] Sync README.md (13→14 commands, add project-status)
- [x] Sync .claude/CLAUDE.md (stale numbers)
- [x] Bump version to 1.1.0 (pyproject + __init__)
- [x] Create CHANGELOG.md
- [x] Run tests + build verification
- [x] Git tag v1.1.0

### [STORY-011] PDCA Slim — 辅助命令降级为 Skill，精简用户界面
> Spec: docs/specs/STORY-011.md

- [x] Remove 6 commands from VALID_COMMANDS and COMMANDS_CONTENT
- [x] Create 6 new SKILL_*_MD templates in skills.py
- [x] Register 6 new skills in VALID_SKILLS
- [x] Update PDCA command prompts to reference skills instead of sibling commands
- [x] Update routing table and agent skill references
- [x] Update deployer to deploy 9 skills
- [x] Add deprecation warnings for removed commands in load_config
- [x] Update all count-based tests

### [STORY-012] Docs Sync — 同步文档站和 GitHub 元数据至 PDCA Slim 架构
> Spec: docs/specs/STORY-012.md

- [x] Update pactkit/pactkit GitHub repo description
- [x] Update index.mdx (At a Glance counts + links)
- [x] Rewrite commands.mdx (8 commands, remove 6 old entries)
- [x] Update skills.mdx (add 6 new prompt-only skills)
- [x] Update installation.mdx and configuration.mdx counts
- [x] Update workflow.mdx trace reference
- [x] Regenerate claude-code-plugin with pactkit init --format marketplace

### [BUG-001] Scripted Skill Prompts Use Wrong Script Path
> Spec: docs/specs/BUG-001.md

- [x] Update SKILL_VISUALIZE_MD path references (R1)
- [x] Update SKILL_BOARD_MD path references (R1)
- [x] Update SKILL_SCAFFOLD_MD path references (R1)
- [x] Verify existing tests pass (R5)

### [BUG-002] Plugin Mode Deploys Hardcoded ~/.claude/skills/ Paths
> Spec: docs/specs/BUG-002.md

- [x] Add skills_prefix param to _deploy_skills() (R1)
- [x] Add skills_prefix param to _deploy_commands() (R2)
- [x] Pass CLAUDE_PLUGIN_ROOT prefix from _deploy_plugin() (R3)
- [x] Write tests for classic and plugin path verification (R6)
- [x] Verify all existing tests pass (R6)

### STORY-013: Draw.io MCP Integration — pactkit-draw 接入官方 MCP 实现即时预览
- [x] Add Draw.io MCP to rules.py MCP section (R1)
- [x] Update SKILL_DRAW_MD with conditional MCP mode (R2)
- [x] Update visual-architect agent prompt (R3)
- [x] Update DRAW_PROMPT_TEMPLATE with MCP output step (R4)
- [x] Update system_design.mmd (R5)
- [x] Write unit tests for STORY-013 (R6)

### STORY-004: Project Visibility — GitHub/PyPI/README/Website 曝光度优化
- [x] Set GitHub topics for pactkit/pactkit (12 topics)
- [x] Update GitHub description for pactkit/pactkit
- [x] Set GitHub metadata for pactkit/pactkit.dev (homepage + topics)
- [x] Update README.md (tagline, remove --mode common, add downloads badge)
- [x] Update pyproject.toml (keywords + classifier)
- [x] Optimize website Hero sub-headline

### STORY-003: Init Guard — project-plan / project-doctor 自动检测初始化状态
- [x] Add Phase 0.5 Init Guard to `project-plan.md` prompt template
- [x] Add Phase 0.5 Init Guard to `project-doctor.md` prompt template
- [x] Write unit tests verifying Init Guard text in command templates
- [x] Verify all existing tests pass (787 passed, 0 failed)

### STORY-002: Selective Deployment — Deployer 按 Config 过滤部署
- [x] Modify `deploy()` to accept and use config parameter
- [x] Implement selective agent deployment with cleanup
- [x] Implement selective command deployment with cleanup
- [x] Implement selective skill deployment
- [x] Implement selective rule deployment and dynamic CLAUDE.md generation
- [x] Generate `pactkit.yaml` on first `pactkit init`
- [x] Update `cli.py` to load config and pass to deployer
- [x] Add deployment summary output
- [x] Write unit tests for selective deployment
- [x] Integration test: partial config end-to-end

### STORY-001: Config Schema — pactkit.yaml 加载、验证、默认值
- [x] Create `src/pactkit/config.py` with load/validate/default/generate functions
- [x] Add `pyyaml` dependency to `pyproject.toml`
- [x] Delete `src/pactkit/common_user.py` and `tests/unit/test_common_user.py`
- [x] Remove `--mode` argument and common_user branch from `cli.py`
- [x] Write unit tests for config module
- [x] Verify all existing tests still pass (747 passed, 0 failed)

### [BUG-005] board.py archive vs classify inconsistent for taskless stories
> Spec: docs/specs/BUG-005.md

- [x] Write failing test
- [x] Fix archive_stories guard
- [x] Regression check

### [BUG-004] deployer.py dead set() call in _deploy_rules
> Spec: docs/specs/BUG-004.md

- [x] Write failing test
- [x] Remove dead code
- [x] Regression check

### [BUG-003] visualize.py ast.Import only captures last alias
> Spec: docs/specs/BUG-003.md

- [x] Write failing test
- [x] Fix _build_file_graph import loop
- [x] Regression check

### [STORY-014] Release v1.1.3: sync CHANGELOG, plugin, and PyPI
> Spec: docs/specs/STORY-014.md

- [x] Update CHANGELOG.md
- [x] Bump version to 1.1.3
- [x] Commit and tag v1.1.3
- [x] Sync plugin repo
- [x] Publish to PyPI

### [STORY-015] Add conditional CI lint gate to Done command
> Spec: docs/specs/STORY-015.md

- [x] Fix unused imports in test files
- [x] Add lint_command to LANG_PROFILES
- [x] Add Step 2.7 CI Lint Gate to Done command
- [x] Add lint gate to Act command Phase 3

### [STORY-016] CLAUDE.md hygiene: language matching rule and project context cleanup
> Spec: docs/specs/STORY-016.md

- [x] Add language-matching rule to core protocol
- [x] Update project .claude/CLAUDE.md to remove stale data
- [x] Verify deployed rules contain language rule

### [STORY-017] project-init 自动生成项目级 CLAUDE.md
> Spec: docs/specs/STORY-017.md

- [x] 在 project-init.md prompt 中 Phase 1 添加生成项目级 CLAUDE.md 的步骤
- [x] 编写测试验证 prompt 内容

## ✅ Done

### [STORY-018] Architecture docs staleness prevention
> Spec: docs/specs/STORY-018.md

- [x] Add system_design.mmd validation to Done Phase 2
- [x] Add rules.md invariants refresh to Done Phase 3
- [x] Add snapshot verification gate to Done Phase 3.8
- [x] Update stale data in system_design.mmd and rules.md

### [STORY-019] Bailout Protocol for TDD Environment Failures
> Spec: docs/specs/STORY-019.md

- [x] Add env-failure bailout to Act TDD loop
- [x] Add loop iteration cap (max 5)
- [x] Add ConnectionError/service-down STOP
- [x] Write tests for bailout prompt text

### [STORY-020] Visualize Horizon Limit
> Spec: docs/specs/STORY-020.md

- [x] Add --depth parameter to visualize.py
- [x] Add --max-nodes cap with truncation note
- [x] Update Plan/Act prompts with focus heuristic
- [x] Write tests for depth and max-nodes

### [STORY-021] Spec Amendment Protocol (RFC Mechanism)
> Spec: docs/specs/STORY-021.md

- [x] Add RFC clause to project-act Phase 0
- [x] Update Hierarchy of Truth rule with exception clause
- [x] Write tests for RFC prompt text

## 🔄 In Progress

### [STORY-022] Bailout Decision Tree (Project Module vs Third-Party)
> Spec: docs/specs/STORY-022.md

- [x] Add decision tree to bailout prompt
- [x] Add ImportError project-path check
- [x] Write tests for decision tree prompt text

### [STORY-023] Test Quality Gate in QA Check
> Spec: docs/specs/STORY-023.md

- [x] Add Test Quality Gate phase to project-check
- [x] Add anti-pattern detection checklist
- [x] Add Test Quality row to verdict report
- [x] Write tests for quality gate prompt text

### [STORY-024] Native Agent Enhancement — Smart Model, Hooks, and Memory
> Spec: docs/specs/STORY-024.md

- [x] R1: Smart Model Default (inherit)
- [x] R2: User-Configurable Model Overrides in pactkit.yaml
- [x] R3: Agent-Scoped Hooks for Constraint Enforcement
- [x] R4: Expanded Persistent Memory
- [x] R5: Permission Mode Enforcement
- [x] R6: Deployer YAML Serialization

### [STORY-025] Conditional CI/CD Pipeline Generation

- [x] Add `ci` configuration section to pactkit.yaml with provider field (default: none)
- [x] Implement GitHub Actions workflow generation when provider is github
- [x] Implement GitLab CI configuration generation when provider is gitlab
- [x] Add CI workflow templates with pytest and linting commands
- [x] Ensure backward compatibility for projects without ci section
- [x] Add config validation for invalid CI providers

### [STORY-026] Conditional Issue Tracker Integration

- [x] Add `issue_tracker` configuration section to pactkit.yaml (default: none)
- [x] Integrate GitHub Issue creation in /project-plan command
- [x] Integrate GitHub Issue closure in /project-done command
- [x] Add Sprint Board linking to external issue URLs
- [x] Implement graceful fallback when GitHub CLI unavailable
- [x] Ensure standalone Sprint Board operation preservation

### [STORY-027] Safe Opt-in Hook Templates

- [x] Add `hooks` configuration section with boolean template flags
- [x] Create safe pre-commit lint hook template (command-type, exit 0)
- [x] Create post-test coverage hook template (report-only)
- [x] Create pre-push check hook template (warning-only)
- [x] Deploy enabled hook scripts to .claude/hooks/ directory
- [x] Integrate with git hooks while preserving existing hooks

### [STORY-028] Context-Aware Rule Scoping

- [x] Add optional `scope` field to rule configuration with glob patterns
- [x] Generate Claude Code includeFiles frontmatter for scoped rules
- [x] Implement glob pattern validation with warning for invalid patterns
- [x] Support multiple scope patterns per rule as YAML list
- [x] Maintain backward compatibility for rules without scope
- [x] Test rule scoping with common patterns (auth, api, frontend modules)

### [STORY-029] Enhanced Doctor Diagnostics

- [x] Implement stale architecture graph detection (7+ days old)
- [x] Add orphaned spec detection (specs without Sprint Board entries)
- [x] Add missing spec detection (Sprint Board stories without specs)
- [x] Implement configuration drift detection (pactkit.yaml vs deployed files)
- [x] Generate structured health report with severity levels (INFO/WARN/ERROR)
- [x] Group findings by category with actionable remediation suggestions

### [STORY-030] Smart Lint Integration in Done Command

- [x] Read lint_command from LANG_PROFILES for detected stack
- [x] Add `lint_blocking` configuration option (default: false)
- [x] Add `auto_fix` configuration option (default: false)
- [x] Implement non-blocking lint warnings as default behavior
- [x] Support blocking lint mode when configured
- [x] Implement auto-fix with verification re-run capability

### [STORY-032] Greenfield redirect heuristic in /project-plan
> Spec: docs/specs/STORY-032.md

- [x] Add greenfield detection to Plan Phase 0
- [x] Write tests for greenfield heuristic keywords

### [STORY-031] Auto git-init in /project-init for non-dev users
> Spec: docs/specs/STORY-031.md

- [x] Add git repo guard to project-init Phase 0.5
- [x] Write tests for git-init detection logic

### [BUG-007] Stale /project-trace references in deployed agent and skill files
> Spec: docs/specs/BUG-007.md

- [x] Fix code-explorer agent prompt stale references
- [x] Fix system-architect agent prompt stale reference
- [x] Fix SKILL_VISUALIZE_MD stale reference
- [x] Write tests verifying no /project-trace in deployed files

### [BUG-006] visualize _scan_files exclude list incomplete for marketplace deployment
> Spec: docs/specs/BUG-006.md

- [x] Add skills/commands/rules/agents to _scan_files excludes
- [x] Extract excludes to SCAN_EXCLUDES constant
- [x] Write tests for marketplace exclude behavior

### [BUG-008] Stale demoted-command references in agent and skill prompts
> Spec: docs/specs/BUG-008.md

- [x] Fix 4 stale command refs in agents.py
- [x] Fix 3 stale command refs in skills.py
- [x] Write TDD tests for all 7 references
- [x] Verify deployed artifacts contain correct refs

### [STORY-033] Config auto-backfill for missing sections on update
> Spec: docs/specs/STORY-033.md

- [x] Extend auto_merge_config_file to backfill missing non-list sections
- [x] Extend _rewrite_yaml to write all config sections
- [x] Write TDD tests for backfill behavior
- [x] Verify pactkit update backfills old config files

### [STORY-034] Auto-refresh pactkit.yaml in Plan Init Guard
> Spec: docs/specs/STORY-034.md

- [x] Add config completeness check to Plan Phase 0.5
- [x] Write TDD tests for Plan prompt template
- [x] Verify deployed Plan command includes refresh step

### [BUG-009] pactkit update does not backfill project-level config
> Spec: docs/specs/BUG-009.md

- [x] Add project-level config backfill to _deploy_classic
- [x] Write TDD tests for dual-config backfill
- [x] Verify existing global config behavior unchanged

### [STORY-035] Update README and docs directory documentation
> Spec: docs/specs/STORY-035.md

- [x] Update README with docs/ directory structure section
- [x] Add pactkit.yaml configuration reference to README
- [x] Update Skills section with all 9 skills
- [x] Complete CHANGELOG v1.2.0 entries

### [BUG-010] _rewrite_yaml drops agent_models and rule_scopes sections
> Spec: docs/specs/BUG-010.md

- [x] Add agent_models serialization to _rewrite_yaml
- [x] Add rule_scopes serialization to _rewrite_yaml
- [x] Fix _deploy_hooks to use stack-aware lint command
- [x] Add round-trip fidelity tests

### [BUG-011] Fix stale command references in agent and skill prompt templates
> Spec: docs/specs/BUG-011.md

- [x] Update agents.py: replace 4 stale /project-* protocol headers with skill-aware phrasing
- [x] Update workflows.py: replace 3 stale Usage lines in skill prompt templates
- [x] Verify zero stale references via grep audit

### [BUG-012] Call graph noise filter — remove builtins and local method calls from visualize --mode call
> Spec: docs/specs/BUG-012.md

- [x] Add BUILTIN_CALLEES filter set to _extract_calls
- [x] Filter non-self attribute calls (local variable methods) from call edges
- [x] In _build_call_graph, only emit edges where at least one endpoint is in func_registry
- [x] Verify --entry BFS tracing still works correctly
- [x] Verify call_graph.mmd line count drops significantly

## 🔄 In Progress

## ✅ Done

### [BUG-013] Deployer reads config from wrong path — use project-level config only
> Spec: docs/specs/BUG-013.md

- [x] Change _deploy_classic to read config from CWD/.claude/pactkit.yaml
- [x] Change _generate_config_if_missing to write full config at CWD/.claude/
- [x] Remove _backfill_project_config (single config source)
- [x] Change load_config default path to CWD/.claude/pactkit.yaml
- [x] Add orphan warning for ~/.claude/pactkit.yaml

### [BUG-014] Stale version numbers in Spec Release fields, prompt templates, and CHANGELOG [#2](https://github.com/pactkit/pactkit/issues/2)
> Spec: docs/specs/BUG-014.md

- [x] Update 6 specs from Release 1.1.5 to 1.2.0
- [x] Update 4 specs from Release 1.2.1 to 1.2.0
- [x] Backfill 13 specs from Release TBD to correct version
- [x] Unify 14 prompt template version labels to v1.2.0
- [x] Add BUG-010~013 to CHANGELOG [1.2.0] Fixed section
- [x] Verify zero TBD specs and no stale prompt versions remain

### [STORY-036] Sync pactkit.dev documentation with current README and codebase
> Spec: docs/specs/STORY-036.md | PR: https://github.com/pactkit/pactkit.dev/pull/1

- [x] Fix pactkit.yaml path on installation.mdx (GAP-01)
- [x] Fix Core Protocol description on configuration.mdx (GAP-02)
- [x] Fix root default and exclude type on configuration.mdx (GAP-03/04)
- [x] Complete MCP tool lists on mcp-integration.mdx (GAP-16~19)
- [x] Document agent_models config field (GAP-05)
- [x] Fix README: root default, exclude type, Tier 1 Test Cases (GAP-03/04/23)

## ✅ Done

### [BUG-016] GitHub Releases missing for v1.2.0 and v1.3.0
> Spec: docs/specs/BUG-016.md

- [x] Create GitHub Release for v1.2.0
- [x] Create GitHub Release for v1.3.0 (Latest)
- [x] Add gh release create step to pactkit-release skill

### [BUG-015] PactKit CI workflow fails due to missing pactkit init step
> Spec: docs/specs/BUG-015.md

- [x] Remove redundant pactkit.yml workflow
- [x] Verify ci.yml still passes

### [STORY-037] Fix regression decision tree — replace unverifiable conditions
> Spec: docs/specs/STORY-037.md

- [x] Replace Condition 1 (session freshness) with git-diff-based check
- [x] Replace Condition 3 (test_map_pattern) with fallback-tolerant check
- [x] Add decision logging to regression output
- [x] Fix Act regression "if unsure" clause with explicit criteria

### [STORY-038] Add call_graph.mmd to standard PDCA update cycle
> Spec: docs/specs/STORY-038.md

- [x] Add `visualize --mode call` to Act Phase 4 "Update Reality"
- [x] Add `visualize --mode call` to Done Phase 2 "Update Reality"
- [x] Fix focus_graph.mmd collision with mode-specific filenames

## 🔄 In Progress

### [BUG-017] /project-init playbook generates incomplete pactkit.yaml
> Spec: docs/specs/BUG-017.md
- [x] Update Phase 1 Step 1 to invoke `pactkit init` CLI
- [x] Add CLI availability check with fallback
- [x] Update Phase 1 Step 2 to use `pactkit update` for existing config
- [x] Add test case for playbook behavior

### [STORY-039] Virtual Environment Configuration Support
> Spec: docs/specs/STORY-039.md

- [x] Config schema extension
- [x] Auto-detection logic
- [x] Prompt template updates
- [x] LANG_PROFILES enhancement
- [x] Tests

### [BUG-018] Issue Tracker verification missing in Done command — no backfill for skipped Plan step [#20](https://github.com/pactkit/pactkit/issues/20)
> Spec: docs/specs/BUG-018.md

- [x] Add Phase 3.5.5 verification step to project-done prompt
- [x] Write TDD tests for prompt template
- [x] Verify existing Done workflow unchanged

## ✅ Done

### [BUG-019] STORY-039 venv implementation incomplete — detect_venv never called [#21](https://github.com/pactkit/pactkit/issues/21)
> Spec: docs/specs/BUG-019.md

- [x] Call detect_venv in deployer.py
- [x] Add venv section to project CLAUDE.md generation
- [x] Add warning for missing explicit venv.path
- [x] Write TDD tests for venv deployment

### [BUG-020] Project CLAUDE.md generation skips venv when file exists — should backup and regenerate [#22](https://github.com/pactkit/pactkit/issues/22)
> Spec: docs/specs/BUG-020.md

- [x] Modify _generate_project_claude_md to backup existing file
- [x] Add user notification for backup
- [x] Write TDD tests for backup behavior

## 🔄 In Progress

### [BUG-021] CLAUDE.md generation: LANG_PROFILES, platform-aware paths, Playbook alignment
> Spec: docs/specs/BUG-021.md

- [x] R1: Skip when exists
- [x] R2: Platform-aware venv
- [x] R3: Stack-aware lint
- [x] R4: Stack-aware test runner

### [BUG-022] load_config deep merge for nested dict sections
> Spec: docs/specs/BUG-022.md

- [x] R1: Deep merge venv/ci/hooks/issue_tracker
- [x] R2: Non-dict keys unchanged

### [BUG-023] _rewrite_yaml preserves unknown user-defined keys
> Spec: docs/specs/BUG-023.md

- [x] R1: Preserve unknown keys
- [x] R2: Round-trip safety
- [x] R3: Custom section marker

### STORY-041: Test Pyramid Restructuring — E2E Layer & Unit Test Rationalization (https://github.com/pactkit/pactkit/issues/27)
- [x] R1: CLI E2E test suite (subprocess-based, 8+ scenarios)
- [x] R2: E2E directory restructure (remove api/browser, create cli/)
- [x] R3: Integration test separation (deploy-calling tests → tests/integration/)
- [x] R4: Prompt string test consolidation (~770 → ~100 structural checks)
- [x] R5: Shared test fixtures (conftest.py)
- [x] R6: CI tiered test execution config

### STORY-040: Project CLAUDE.md Layered Architecture — Separate Framework and User Content (https://github.com/pactkit/pactkit/issues/26)
- [x] R1: Remove skip-if-exists guard, rename function, always regenerate CLAUDE.md
- [x] R2: Add `@./.claude/CLAUDE.local.md` import to generated CLAUDE.md
- [x] R3: Create `_generate_claude_local_md_if_missing()` function
- [x] R4: Implement migration heuristic for existing user-modified CLAUDE.md
- [x] R5: Verify global CLAUDE.md behavior unchanged
- [x] R6: Preserve HOME and preview-mode guards

### [BUG-024] board.py regex requires brackets — rejects bare STORY-xxx titles (https://github.com/pactkit/pactkit/issues/28)
> Spec: docs/specs/BUG-024.md

- [x] R1: Flexible title pattern (4 regex sites)
- [x] R2: Normalize ID extraction
- [x] R3: add_story canonical format preserved
- [x] R4: Existing board cleanup (archive stuck entries)

### STORY-042: Spec Linter — Non-AI Structural Validation Gate
- [x] R1: Spec Linter script (`spec_linter.py`)
- [x] R2: Act Phase 0.5 集成
- [x] R3: Plan Phase 自检闭环
- [x] R4: CLI 独立调用
- [x] R5: Hotfix 豁免

### STORY-043: Active Clarify — Pre-Plan Requirement Disambiguation
- [x] R1: Ambiguity Detection
- [x] R2: Structured Question Generation
- [x] R3: User Interaction Flow
- [x] R4: Plan Playbook 集成 (Phase 0.7)
- [x] R5: Standalone `/project-clarify` command
- [x] R6: Greenfield 场景强化

### STORY-044: Pre-Act Consistency Check — Left-Shift Quality Gate
- [x] R1: Spec ↔ Board Task 对齐检查
- [x] R2: Spec AC ↔ Test Case 覆盖检查
- [x] R3: Act Phase 0.6 集成
- [x] R4: 输出格式
- [x] R5: Standalone `pactkit-analyze` skill

### STORY-045: Auto-PR Enhancement — Structured PR Body Generation
- [x] R1: PR 自动触发判定
- [x] R2: PR Title 生成
- [x] R3: PR Body 结构化生成
- [x] R4: 用户确认
- [x] R5: Push 保障
- [x] R6: Done Playbook 集成

### STORY-046: Multi-Agent Compatibility Layer
- [x] R1: Agent Adapter Architecture
- [x] R2: CLI `--agent` Flag
- [x] R3: Format Transformer
- [x] R4: pactkit.yaml agents 配置
- [x] R5: 核心 Playbook 不变

### STORY-047: Enterprise Configuration Flags
- [x] R1: pactkit.yaml enterprise section
- [x] R2: CLI Flag Override
- [x] R3: Command Playbook 条件逻辑
- [x] R4: 优雅降级

### STORY-048: Worktree Isolation for Subagent Sprint
- [x] Modify SPRINT_PROMPT: add isolation="worktree" to all Stage A/B/C Task calls
- [x] Add worktree change recovery strategy (merge for Build/Close, copy for Check)
- [x] Add worktree pre-check phase with fallback for unsupported environments
- [x] Add worktree-specific error handling (merge conflict, residue cleanup)
- [x] Write unit tests (17 tests, all GREEN)
- [x] Full regression pass (1679 tests)

### [STORY-049] GitHub Community Standards & Dependabot
> Spec: docs/specs/STORY-049.md

- [x] Create CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- [x] Create SECURITY.md (GitHub Security Advisory)
- [x] Update CONTRIBUTING.md reference
- [x] Create .github/dependabot.yml (pip + github-actions)

## 🔄 In Progress

## ✅ Done

### [STORY-050] Doc-Only Regression Shortcut
> Spec: docs/specs/STORY-050.md

- [x] Add Step 1.3 Doc-Only Shortcut to Done command prompt
- [x] Add Doc-Only detection to Act command prompt
- [x] Add source_dirs to LANG_PROFILES
- [x] Update Decision Logging format

### [STORY-051] PDCA Workflow Streamlining [#35](https://github.com/pactkit/pactkit/issues/35)
> Spec: docs/specs/STORY-051.md

- [x] R1: Split Done command into Done + Release + PR
- [x] R2: Remove Act Phase 3.4 Lint Check
- [x] R3: Implement lazy visualize (git diff triggered)
- [x] R4: Centralize MCP detection in Phase 0.2
- [x] R5: Remove Plan Phase 3.4 Issue Tracker creation

### [BUG-025] project-release 与 pactkit-release 功能重复 [#36](https://github.com/pactkit/pactkit/issues/36)
> Spec: docs/specs/BUG-025.md

- [x] R1: Command 委托给 Skill
- [x] R2: Skill 增加版本自动检测
- [x] R3: 功能对齐（含 GitHub Release）

### [STORY-052] Conditional GitHub Release in pactkit-release [#37](https://github.com/pactkit/pactkit/issues/37)
> Spec: docs/specs/STORY-052.md

- [x] R1: Add release config section to pactkit.yaml
- [x] R2: Conditional GitHub Release in skill Step 4
- [x] R3: Config backfill for release section
- [x] R4: Validation for new section

### [STORY-053] Impact-Based Regression via Call Graph Analysis [#38](https://github.com/pactkit/pactkit/issues/38)
> Spec: docs/specs/STORY-053.md

- [x] R1: Add reverse caller analysis to visualize.py (--reverse flag)
- [x] R2: Add test mapping function (impact subcommand)
- [x] R3: Update Regression Decision Tree in project-done.md
- [x] R4: Configuration option in pactkit.yaml (optional)
- [x] R5: Release Gate — version bump forces full regression

### STORY-054: Deployment Completeness Audit — E2E File Verification [#39](https://github.com/pactkit/pactkit/issues/39)
- **Status**: Done
- **Priority**: P1
- **Goal**: Add e2e completeness tests that verify all 9 agents, 11 commands, 10 skills, 6 rules are deployed — no empty files, correct frontmatter, CLAUDE.md references all rules.
- **Spec**: `docs/specs/STORY-054.md`
- **Tasks**:
  - [x] T1: Write `TestDeploymentCompleteness` test class in `tests/e2e/cli/test_cli_e2e.py`
  - [x] T2: AC1–AC4 — completeness tests (exact counts + names)
  - [x] T3: AC5 — no-empty-file test
  - [x] T4: AC6–AC7 — frontmatter and CLAUDE.md tests
  - [x] T5: Run full test suite, verify pass (1805 passed)
