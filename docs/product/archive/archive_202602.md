
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
