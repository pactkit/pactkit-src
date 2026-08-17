# Project Context (Auto-generated)
> Last updated: 2026-08-17T17:57:13+08:00 by pactkit context

## Sprint Status
Backlog: 5 | In Progress: 0 | Done: 0 stories

## Current Stories
None

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
`/project-plan`

## Agent Continuation
No active work session.
