
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
