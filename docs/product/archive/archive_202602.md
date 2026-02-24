
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
