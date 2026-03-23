
### [STORY-059] Add Prototype Generation Phase to project-design
> Spec: docs/specs/STORY-059.md

- [x] Modify DESIGN_PROMPT in workflows.py, Add Section 1.6, Renumber sections, Update Does NOT section, Add tests

### STORY-060: Fix /project-init Hang — Non-interactive Guard & Scan Limits
- **Priority**: P1
- **Spec**: `docs/specs/STORY-060.md`
- **Tasks**:
  - [x] T1: Rewrite Phase 0.5 playbook text (remove interactive prompt)
  - [x] T2: Wire enterprise flags through cli.py → deploy()
  - [x] T3: Add enterprise flags to upgrade subparser
  - [x] T4: Update deploy() signature (accept flags, remove **_kwargs)
  - [x] T5: Add MAX_SCAN_FILES=500 truncation to _scan_files()
  - [x] T6: Narrow bare except clauses in visualize.py

### [STORY-061] Remove Redundant Thinking Block Instructions from PDCA Playbooks
> Spec: docs/specs/STORY-061.md

- [x] T1: Remove 4 thinking instructions from commands.py
- [x] T2: Remove 6 thinking instructions from workflows.py
- [x] T3: Create test_story061 asserting no thinking instructions remain
- [x] T4: Update test_design_command.py test_phase0_still_thinking

## 🔄 In Progress

### [STORY-062] Print MCP Recommendations After Init/Update
> Spec: docs/specs/STORY-062.md

- [x] T1: Add MCP_RECOMMENDATIONS constant
- [x] T2: Add _print_mcp_recommendations() helper
- [x] T3: Call helper after deploy() success
- [x] T4: Call helper after _deploy_plugin() success
- [x] T5: Create tests for AC1-AC4

### [BUG-027] Sprint Board Story 标题级别不一致导致归档失败
> Spec: docs/specs/BUG-027.md

- [x] 添加 create_board 函数到 scaffold.py
- [x] 修改 board.py 正则支持 #### 格式
- [x] 更新 project-init Phase 4 使用 scaffold 命令
- [x] 添加单元测试

### [STORY-063] PDCA Playbook Prompt Slimming
> Spec: docs/specs/STORY-063.md

- [x] R1: Extract shared protocols to rules.py
- [x] R2: Slim MCP tool signature teaching
- [x] R3: Slim inline tool teaching
- [x] R4: Rewrite Sprint to Protocol-Only
- [x] R5: Fix ghost DEV_REF/TEST_REF references
- [x] R6: Add Spec Lint to Design
- [x] R7: Write story tests

## 🔄 In Progress

## ✅ Done

### [BUG-028] Ghost DEV_REF Residual in Check and Review
> Spec: docs/specs/BUG-028.md

- [x] R1: Remove ghost DEV_REF from Check playbook
- [x] R2: Remove ghost DEV_REF from Review skill
- ~~R3: Clean up dead code in references.py~~ CANCELLED (33 tests protect these constants)
- [x] R3: Add regression guard tests

### BUG-029: project-init Stack Detection Fallback Causes CLI Hang
- **Priority**: High
- **Type**: Bug
- **Spec**: `docs/specs/BUG-029.md`
- **Tasks**:
  - [x] Replace "ask the user to specify" fallback with config-first detection in `src/pactkit/prompts/commands.py`
  - [x] Add regression tests for all 3 AC scenarios

### BUG-030: Spec Linter Path Not Found in External Projects
- **Priority**: High
- **Spec**: [BUG-030](../specs/BUG-030.md)
- **Summary**: Prompts use hardcoded `src/pactkit/skills/spec_linter.py` path which doesn't exist in external projects
- [x] R1: Add `pactkit spec-lint` CLI subcommand
- [x] R2: Update `commands.py` prompt references
- [x] R3: Update `workflows.py` prompt references

## 🔄 In Progress

### STORY-064: Persist Venv Config in CLAUDE.local.md Managed Block
- **Priority**: High
- **Spec**: [STORY-064](../specs/STORY-064.md)
- **Summary**: Write venv instructions to `CLAUDE.local.md` as a managed block so they persist even when venv detection fails on `pactkit update`
- [x] R1: Add `_upsert_venv_managed_block()` to `deployer.py`
- [x] R2: Block persists when venv detection fails on update
- [x] R3: Block updated when venv path changes
- [x] R4: User content outside markers preserved
- [x] R5: No block written when no venv
- [x] R6: `CLAUDE.md` venv section unchanged

### STORY-065: Sprint Stage A Model Consistency — Split Plan (opus) and Act (sonnet)
- **Priority**: High
- **Spec**: [STORY-065](../specs/STORY-065.md)
- **Summary**: Sprint Stage A doesn't pass `model` parameter → Plan runs on session default instead of opus; fix by splitting Stage A into A1-Plan (opus) + A2-Act (sonnet)
- [x] Add Phase 0 config-aware model resolution (agent_models from pactkit.yaml)
- [x] Split Stage A into A1-Plan (model: opus) + A2-Act (model: sonnet)
- [x] Update Subagent Reference table (separate Plan and Act rows)
- [x] Add tests (test_story065_sprint_model.py, 16 tests)

### BUG-031: CLAUDE.local.md Docstring Contradicts Managed Block Behavior
- **Priority**: P3
- **Spec**: [BUG-031](../specs/BUG-031.md)
- [x] R1: Update `_generate_claude_local_md_if_missing()` docstring
- [x] R2: Update template comment

### BUG-032: Missing E2E CLI Test for spec-lint Subcommand
- **Priority**: P3
- **Spec**: [BUG-032](../specs/BUG-032.md)
- [x] R1: Add E2E subprocess tests for `pactkit spec-lint`
- [x] R2: Verify exit code and output (pass + fail + no args)
- [x] R3: Follow existing `test_cli_e2e.py` patterns

### [BUG-034] Plan Command Missing Spec Metadata Table Template
> Spec: docs/specs/BUG-034.md

- [x] R1: Add metadata table template to Plan command playbook
- [x] R2: Match scaffold.py create_spec canonical format

## 🔄 In Progress


## ✅ Done

- [x] [BUG-033] scaffold.py create_spec() 生成的模板不符合 spec-lint 验证规则 `P1`

### [STORY-069] OpenCode Deployment Format Support
> Spec: docs/specs/STORY-069.md

- [x] R1: Add 'opencode' to VALID_FORMATS
- [x] R2: Global deployment structure (AGENTS.md, agents/, commands/, skills/)
- [x] R3: Project deployment (opencode.json)
- [x] R4: AGENTS.md with inline rules (no @import)
- [x] R5: Skills path rewriting to ~/.config/opencode/skills
- [x] R6: opencode.json generation with $schema and instructions
- [x] R11: CLI --format opencode option
- [x] All 19 unit tests passing

### [BUG-035] OpenCode Format Should Follow Dual-Layer Architecture
> Spec: docs/specs/BUG-035.md

- [x] R1:移除全局opencode.json
- [x] R2:更新project-init playbook
- [x] R3:更新测试

### [STORY-070] OpenCode Format Compliance: Fix Spec-Implementation Gaps
> Spec: docs/specs/STORY-070.md

- [x] R1 Command frontmatter 转换
- [x] R2 Agent mode:subagent
- [x] R3 移除 Agent name 字段
- [x] R4 清理 Claude Code 专有字段
- [x] R5 Agent model inherit 省略
- [x] R6 upgrade 支持 opencode
- [x] R7 更新测试

### [STORY-071] OpenCode Config Parity: Rules Modularization, Permission, MCP
> Spec: docs/specs/STORY-071.md

- [x] R1 opencode.json permission 配置
- [x] R2 opencode.json MCP 模板
- [x] R3 project-init pactkit.yaml 说明
- [x] R4 MCP 推荐打印更新
- [x] R5 opencode.json 保留用户配置
- [x] R6 全局 AGENTS.md 模块化拆分
- [x] R7 全局 opencode.json instructions
- [x] 测试

### [STORY-072] Multi-Developer Story ID Prefix for Merge-Safe Collaboration
> Spec: docs/specs/STORY-072.md

- [x] R1 load_config() 多路径查找 (.claude/ → .opencode/)
- [x] R2 pactkit.yaml 生成路径感知 (deployer.py)
- [x] R3 developer 字段 + 校验 (config.py)
- [x] R4 board.py snapshot() 路径修复
- [x] R5 commands.py playbook 路径引用更新 (6处)
- [x] R6 skills.py doctor 路径更新 (2处)
- [x] R7 workflows.py sprint 路径更新 (1处)
- [x] R8 /project-plan developer 前缀 ID 指令
- [x] R9 删除反向指令 "不要在.opencode/创建"
- [x] 测试

### [STORY-073] OpenCode Format Final Mile: Command Model Routing and Claude Code Residuals
> Spec: docs/specs/STORY-073.md

- [x] R1 Command frontmatter model 字段
- [x] R2 project-init 条件分支 CLAUDE.md vs AGENTS.md
- [x] R3 YAML 注释去 ~/.claude/
- [x] R4 源码文档字符串更新
- [x] 测试

### [STORY-slim-001] Tool Integration Guide: Checklist for New AI Tool Adaptation
> Spec: docs/specs/STORY-slim-001.md

- [x] R1 创建 10 维度集成检查清单
- [x] R2 Codex 预研模板
- [x] R3 /project-plan 提示引用

### [STORY-slim-013] Reduce Cognitive Overload in PDCA Command Prompts
> Spec: docs/specs/STORY-slim-013.md

- [x] Remove (Mandatory) labels from workflows.py Phase 0 headers
- [x] Add Execution Style directives to dense commands
- [x] Split Plan Phase 3 into sub-phases 3.1/3.2/3.3
- [x] Split Design Phase 1 into logical groups
- [x] Deploy and verify both targets

## 🔄 In Progress

## ✅ Done
- **STORY-slim-012**: Stack-Aware CI Pipeline Generation [P1]
  - [x] R1: Stack-aware 模板生成（python/node/go/java）
  - [x] R2: CI 模板参数化（runner, language_version）
  - [x] R3: GHE 兼容性（自动检测 + 注释提示）
  - [x] R4: CI 结果反馈集成（project-done Phase 4）
  - [x] R5: GitLab CI 同步更新
  - [x] R6: 向后兼容
  - [x] R7: OpenCode 部署路径 CI 支持
  - [x] R8: pactkit.yaml 配置可见性（完整 CI 字段注释）
  - [x] R9: actions_ref 前缀替换 + github_host 显式 GHE 配置
- **STORY-slim-011**: Rule-Command Mapping — Context-Aware Rule Loading [P1]
  - [x] R1: COMMAND_RULES_MAP constant in rules.py
  - [x] R2: 09-credential-safety forced in all commands
  - [x] R3: Classic @import injection in command files
  - [x] R4: OpenCode inline embedding in command files
  - [x] R5: CLAUDE.md / opencode.json updated per platform
  - [x] R6: command_rules config override support
  - [x] R8: Anti-regression tests (AC8/AC9/AC10)
- **STORY-slim-010**: Version Sync Fix & Deployer DRY Refactor [P2]
  - [x] Fix .claude/pactkit.yaml version 2.2.0 → 2.1.1
  - [x] Extract `_build_rule_id_to_key()` helper
  - [x] Extract `_build_rule_id_to_filename()` helper
  - [x] Extract `_render_skill_md()` helper
  - [x] Full test suite green (2338 passed) + ruff clean
- **STORY-slim-009**: Lazy Rule Loading [P0]
- **STORY-slim-007**: Document Schema Registry [P1]
- **STORY-slim-006**: Prompt Template Variables [P1]
- **STORY-slim-005**: FormatProfile Abstraction [P1]
- **STORY-slim-001**: Tool Integration Checklist [P2]
- **BUG-slim-001**: project-init creates .claude in OpenCode env

### [BUG-slim-002] Rules-Commands Instruction Collision Causes Plan/Act Stall
> Spec: docs/specs/BUG-slim-002.md

- [x] R1: PDCA exemption for Visual First
- [x] R2: Plan exemption for Operating Guidelines
- [x] R3: Init Guard downgrade to warn+STOP
- [x] R4: Clarify Gate threshold increase
- [x] R5: Act Consistency Check simplification
- [x] R6: Act Visualize deduplication

### [STORY-slim-016] Test Mapping & Stack-Aware Lint CLI
> Spec: docs/specs/STORY-slim-016.md

- [x] R1: pactkit test-map — source-to-test file mapping
- [x] R2: pactkit lint — stack-aware lint runner
- [x] R3: CLI wiring (test-map, lint)
- [x] R4: Prompt delegation to new CLI commands

### [STORY-slim-015] Doctor & Release CLI — Deterministic Diagnostics
> Spec: docs/specs/STORY-slim-015.md

- [x] R1: pactkit doctor — orphaned/missing spec detection
- [x] R2: pactkit doctor — config drift detection
- [x] R3: pactkit doctor — stale graph detection
- [x] R4: pactkit backfill-release — spec TBD replacement
- [x] R5: pactkit issue-sync — GitHub issue lifecycle
- [x] R6: CLI wiring (doctor, backfill-release, issue-sync)
- [x] R7: Prompt delegation to new CLI commands

### [BUG-slim-003] CLI Migration Gaps — Prompt Inconsistencies & Implementation Mismatches [#75](https://github.com/pactkit/pactkit/issues/75)
> Spec: docs/specs/BUG-slim-003.md

- [x] R1: Fix prompt inconsistency — pactkit next-id (sprint/hotfix/design)
- [x] R2: Fix prompt inconsistency — pactkit sec-scope (plan Phase 3.2)
- [x] R3: Fix prompt inconsistency — pactkit context (plan Phase 3.3, init Phase 6)
- [x] R4: Fix cleaners.py Java cleanup list
- [x] R5: Extend guards.py config completeness check
- [x] R6: Extend lint_lessons row format validation

### [STORY-slim-014] Code is the Law — Deterministic Rule Migration
> Spec: docs/specs/STORY-slim-014.md

- [x] R1: New CLI subcommands (guard, next-id, clean, regression, context, sec-scope)
- [x] R2: Document structure validators (lint-context, lint-lessons, lint-testcase)
- [x] R3: Eliminate dual-write (auto-generate routing table from Python constants)
- [x] R4: Slim prompt templates (replace deterministic blocks with CLI calls)
- [x] R5: Backward compatibility + all tests pass
- [x] R6: Security Scope auto-detection (pactkit sec-scope)
- [x] R7: Lazy Visualize CLI (pactkit visualize --lazy)

### [BUG-slim-004] Cross-Flow Integrity Gaps — Unreferenced CLI & Missing Lint in Hotfix [#76](https://github.com/pactkit/pactkit/issues/76)
> Spec: docs/specs/BUG-slim-004.md

- [x] R1: Add lint step to Hotfix flow
- [x] R2: Reference document validators in Done prompt
- [x] R3: Add --agent flag to upgrade subparser
- [x] R4: Forward --agent in upgrade handler
- [x] R5: Check Phase 3 use pactkit spec-lint for Spec structure
- [x] R6: Design must call pactkit context after board setup

### [STORY-slim-017] Done Phase Deterministic Gate Migration — Lessons, Invariants, Coverage
> Spec: docs/specs/STORY-slim-017.md

- [x] R1: pactkit lesson-append with dedup
- [x] R2: pactkit invariants-refresh test count
- [x] R3: pactkit coverage-gate verification
- [x] R4: CLI wiring (3 new subcommands)
- [x] R5: Prompt delegation to new CLI commands

### [BUG-slim-005] Cross-Flow Residual Gaps — Hotfix Context, Board Refs, Dead Code
> Spec: docs/specs/BUG-slim-005.md

- [x] R1: Hotfix add pactkit context Phase 3.5
- [x] R2: Hotfix board update ref {BOARD_CMD}
- [x] R3: Act board update ref {BOARD_CMD}
- [x] R4: Check add lint-testcase reference
- [x] R5: Remove 3 dead LANG_PROFILES keys

### BUG-slim-006: Post-Migration Cross-Flow Residual Gaps — Graphs, Board Schema, HOTFIX ID
- [x] R1: Fix sprint_board.md missing In Progress section
- [x] R2: Fix HOTFIX_PROMPT next-id --prefix broken reference
- [x] R3: Make pactkit visualize --lazy an end-to-end executor
- [x] R4: Add HLD module count check to pactkit doctor
- [x] R5: Fix rules.md ADR-008 table formatting
- [x] R6: Fix context.md Active Branches
- [x] R7: Remove dead cleanup key from LANG_PROFILES
- [x] R8: Update system_design.mmd HLD (one-time data fix)
- [x] R9: Update Done Phase 2 prompt to use pactkit doctor for HLD check

## 🔄 In Progress

## ✅ Done

### STORY-slim-018: Systemic Cross-Flow Guards — Automated Validation for Prompt-CLI Integrity
- [x] R1: Prompt-to-CLI cross-reference guard test
- [x] R2: Canonical LANG_PROFILE_REQUIRED_KEYS as SSoT
- [x] R3: Done flow MUST update Spec Status to Done
- [x] R4: Declarative cross-flow coverage matrix test

## 🔄 In Progress

## ✅ Done

### [STORY-slim-021] Sectional Write for large document generation
> Spec: docs/specs/STORY-slim-021.md

- [x] 1. Modify DESIGN_PROMPT Phase 1: sectional Write per Group
- [x] 2. Modify DESIGN_PROMPT Phase 3: batch checkpoint
- [x] 3. Add unit tests
- [x] 4. Deploy and verify

## 🔄 In Progress


## ✅ Done

- **STORY-slim-020**: Fix Explore subagent stall during Plan Phase 1 Archaeology [P1]
  - [x] Write tests (RED)
  - [x] Implement Phase 1 scope-limiting + delegation template
  - [x] Reduce code-explorer maxTurns 50 -> 15
  - [x] Regression pass (2702)
- **STORY-slim-019**: Split Plan Phase 3.2 into sub-steps to eliminate Spec-writing stall [P1]
  - [x] Write tests (RED)
  - [x] Implement prompt split (GREEN)
  - [x] Regression pass

### [STORY-slim-022] E2E Testing Framework — Config-Driven Check Phase
> Spec: docs/specs/STORY-slim-022.md

- [x] Add VALID_E2E_TYPES to config.py
- [x] Add e2e defaults to get_default_config
- [x] Add e2e to DEEP_MERGE_KEYS
- [x] Add e2e validation to validate_config
- [x] Add e2e to generate_default_yaml
- [x] Rewrite CHECK_PROMPT Phase 4 config-driven
- [x] Write unit tests for R1-R8

## 🔄 In Progress

## ✅ Done

### [HOTFIX-slim-023] Add --mode to pactkit visualize CLI
> Spec: docs/specs/HOTFIX-slim-023.md

- [x] Add --mode argument to visualize parser
- [x] Execute single or all modes in CLI handler

## 🔄 In Progress

## ✅ Done
