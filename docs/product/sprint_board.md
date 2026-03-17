# Sprint Board

## 📋 Backlog

## 🔄 In Progress
- **STORY-slim-006**: Prompt Template Variables — Replace Hardcoded Paths [P1]
  - [x] `_render_prompt()` in deployer.py — sequential replace, SafeFormatMap approach abandoned
  - [x] profiles.py docstring — Template Variable Reference table
  - [x] skills.py — 29 hardcoded paths → {VISUALIZE_CMD}/{BOARD_CMD}/{SCAFFOLD_CMD}/{SKILLS_ROOT}
  - [x] workflows.py — 7 paths replaced + JSON braces handled
  - [x] commands.py — 5 paths replaced + JSON block rendered safely
  - [x] agents.py — 1 path replaced
  - [x] deployer _deploy_skills/agents/commands use _render_prompt()
  - [x] 30 new tests (test_render_prompt.py) — 2269 total passed

## ✅ Done
- **STORY-slim-005**: FormatProfile Abstraction [P1]
- **STORY-slim-001**: Tool Integration Checklist [P2]
- **BUG-slim-001**: project-init creates .claude in OpenCode env
- **scaffold developer prefix**: create_spec 自动注入 developer 前缀
