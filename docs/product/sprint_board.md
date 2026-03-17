# Sprint Board

## 📋 Backlog
- **STORY-slim-008**: Deploy Chain Parity — Align OpenCode with Classic [P1]
  - [ ] _deploy_opencode() 读取 pactkit.yaml (selective deploy)
  - [ ] 添加 auto_merge_config_file() 调用
  - [ ] 添加 _cleanup_legacy() 调用
  - [ ] 新增 _generate_project_agents_md() (项目级 AGENTS.md)
  - [ ] _generate_config_if_missing() 感知 format
  - [ ] 测试覆盖

## ✅ Done
- **STORY-slim-007**: Document Schema Registry [P1]
  - [x] 创建 src/pactkit/schemas.py 文档结构常量注册表
  - [x] spec_linter.py 引用 schemas 常量
  - [x] scaffold.py SPEC_TEMPLATE 统一 + source of truth 标注
  - [x] board.py 内联常量 + source of truth 标注
  - [x] commands.py context.md/lessons.md 格式统一引用 {CONTEXT_SECTIONS}/{LESSONS_ROW_FORMAT}
  - [x] deployer _render_prompt 添加 {CONTEXT_SECTIONS} + {LESSONS_ROW_FORMAT}
  - [x] cli.py 新增 `pactkit schema` 子命令
  - [x] 19 个新测试 + 2288 全量通过
- **STORY-slim-006**: Prompt Template Variables [P1]
- **STORY-slim-005**: FormatProfile Abstraction [P1]
- **STORY-slim-001**: Tool Integration Checklist [P2]
- **BUG-slim-001**: project-init creates .claude in OpenCode env
