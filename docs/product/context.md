# Project Context (Auto-generated)
> Last updated: 2026-08-21T21:33:08+08:00 by pactkit context

## Sprint Status
Backlog: 5 | In Progress: 1 | Done: 0 stories

## Current Stories
- STORY-slim-145: Codex 部署命令语义完整性与 Adapter 兼容门禁

## Recent Completions
None

## Active Branches
+ claude/naughty-euclid-e6a787
  develop
* main

## Key Decisions
- 门禁词表扫描须先剥离 code fence/inline code span（done_verify.py:_strip_code_spans），否则词表元讨论自身误报
- check_deploy_parity 新增 hash 路径漏了 SEC-7 降级守卫（PermissionError/AttributeError 穿透 doctor）——Spec Security Scope 逐条自查 + 独立评审实重现能抓作者盲区
- deploy(format=all) 的 adapter 分支无视 target 直写真实 home——跨环境副作用必须显式审查 target/HOME 语义；测试通过 subprocess 调 CLI 时 HOME 未隔离即真实机器
- Baseline budget tests (test_story063_prompt_slimming.py BASELINE_TOTAL_CHARS) leave <100 chars headroom — new playbook instructions must compress hard or bump baseline with justification comment
- pactkit update only deploys to ~/.claude — in-repo pactkit-plugin/commands copies need manual sync from prompts/ source (verified by normalized diff)

## Next Recommended Action
`/project-act` (stories in progress)

## Agent Continuation
Last Command: /project-act STORY-slim-145
Phase Reached: Phase 4: complete (F1-F5 review fixes applied)

### Sprint Contract (STORY-slim-145)
- [ ] AC1: Codex Act 不再生成损坏文本 (R2, R3, R4)
- [ ] AC2: Codex 保留 PactKit CLI 的确定性语义 (R1, R2, R3)
- [ ] AC3: Classic/Codex Act 行为等价 (R4, R5)
- [ ] AC4: 语义损坏阻止部署测试通过
- [ ] AC5: Adapter 版本错配不再静默部署
- [ ] AC6: Editable install 元数据分裂可见
- [ ] AC7: 对齐版本后的迁移安全 (R7, R8)
- [ ] AC8: 回归兼容
- [ ] AC9: Copilot 消费共享 operation 契约 (R2, R3)
