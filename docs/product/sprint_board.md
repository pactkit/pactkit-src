# Sprint Board

## 📋 Backlog

## 🔄 In Progress
- **STORY-slim-005**: FormatProfile Abstraction [P1]
  - [x] 创建 src/pactkit/profiles.py — FormatProfile dataclass + FORMAT_PROFILES 注册表
  - [x] 重构 config.py — PACTKIT_YAML_CANDIDATES 自动生成 + resolve() 无 if-else
  - [x] 重构 deployer.py — 消除 opencode_format bool + skills_prefix 手动路由 + CLAUDE_ONLY_FIELDS
  - [x] 30 个新测试全部通过，2239 全量测试 0 失败
  - [ ] prompts 40+ 硬编码路径 → {SKILLS_PATH} 占位符 (STORY-slim-006 延续)

## ✅ Done
- **STORY-slim-001**: Tool Integration Checklist [P2]
- **BUG-slim-001**: project-init creates .claude in OpenCode env
- **scaffold developer prefix**: create_spec 自动注入 developer 前缀
