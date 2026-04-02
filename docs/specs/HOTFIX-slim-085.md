# HOTFIX-slim-085: Add Duplication Audit to Plan phase

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-085 |
| Status | Draft |
| Priority | P2 |
| Release | 2.9.13 |

## Background

Plan Phase 2 (Design) 缺少模式审查步骤。当新功能是"第 N 个同类实现"（新 adapter/format/provider）时，system-architect 没有检查现有代码是否已有可复用抽象，导致 adapter 间重复逻辑膨胀（STORY-slim-084 根因）。

## Fix

- `src/pactkit/prompts/agents.py` — system-architect prompt 增加 Duplication Audit 协议
- `src/pactkit/prompts/commands.py` — Plan Phase 2 增加一行引用
