
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
