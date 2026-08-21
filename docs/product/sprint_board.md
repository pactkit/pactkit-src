# Sprint Board

## 📋 Backlog

### [STORY-slim-118] codegraph MCP Integration for Semantic Code Queries
> Spec: docs/specs/STORY-slim-118.md

- [ ] Document replacement vs augmentation decision
- [ ] Add codegraph MCP conditional note to SKILL_VISUALIZE_MD Graph Query Protocol
- [ ] Run pactkit update to redeploy

### [STORY-slim-119] Improve Python Call Graph Coverage
> Spec: docs/specs/STORY-slim-119.md

- [ ] Extend _extract_calls to capture non-self attribute method calls (R1)
- [ ] Capture function references in list/assignment contexts (R2)
- [ ] Use ast.walk to scan nested functions (R3)
- [ ] Write TDD tests for AC1-AC4
- [ ] Run pactkit update to redeploy

### [HOTFIX-slim-127] Add codegraph sync to PDCA command source templates
> Spec: docs/specs/HOTFIX-slim-127.md

- [ ] Fix project-plan
- [ ] Fix project-act
- [ ] Fix project-done
- [ ] Fix project-hotfix

### [HOTFIX-slim-131] Fix deployer @ refs before frontmatter
> Spec: docs/specs/HOTFIX-slim-131.md

- [ ] Fix _deploy_commands prepend order

### [HOTFIX-slim-132] Add explicit board.py move_story command to project-act
> Spec: docs/specs/HOTFIX-slim-132.md

- [ ] Add move_story command template to Phase 0.6

## 🔄 In Progress

### [STORY-slim-145] Codex 部署命令语义完整性与 Adapter 兼容门禁
> Spec: docs/specs/STORY-slim-145.md

- [x] 建立 CLI policy 与结构化操作渲染契约
- [x] 移除 pactkit-codex 有损命令前缀替换
- [x] 增加 prompt 完整性与 Classic/Codex parity 门禁
- [x] 阻止不兼容 Core/adapter 组合静默部署
- [ ] 完成隔离迁移、双仓回归与同版本发布验证

## ✅ Done
