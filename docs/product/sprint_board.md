# Sprint Board

## 📋 Backlog
- **STORY-slim-007**: Document Schema Registry — Centralize Document Structure Rules [P1]
  - [ ] 创建 src/pactkit/schemas.py 文档结构常量注册表
  - [ ] spec_linter.py 引用 schemas 常量
  - [ ] scaffold.py / board.py 标注 source of truth
  - [ ] playbook 中 context.md/lessons.md 格式统一引用
  - [ ] 新增 `pactkit schema` CLI 子命令
  - [ ] 测试覆盖
- **STORY-slim-008**: Deploy Chain Parity — Align OpenCode with Classic [P1]
  - [ ] _deploy_opencode() 读取 pactkit.yaml (selective deploy)
  - [ ] 添加 auto_merge_config_file() 调用
  - [ ] 添加 _cleanup_legacy() 调用
  - [ ] 新增 _generate_project_agents_md() (项目级 AGENTS.md)
  - [ ] _generate_config_if_missing() 感知 format
  - [ ] 测试覆盖

## ✅ Done
- **STORY-slim-006**: Prompt Template Variables [P1]
- **STORY-slim-005**: FormatProfile Abstraction [P1]
- **STORY-slim-001**: Tool Integration Checklist [P2]
- **BUG-slim-001**: project-init creates .claude in OpenCode env
