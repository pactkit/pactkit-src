# Project Context (Auto-generated)
> Last updated: 2026-08-13T19:04:29+08:00 by pactkit context

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
- Adding project-debug required updating VALID_COMMANDS in config.py, VALID_SKILLS, COMMANDS_CONTENT registration in commands.py, and COMMAND_RULES_MAP in rules.py — plus 6 test files with hardcoded count assertions
- Removing `model:` from COMMANDS_CONTENT frontmatter fixes Bedrock VS Code plugin errors — Claude Code resolves the alias to Anthropic's latest model ID, bypassing `ANTHROPIC_DEFAULT_SONNET_MODEL`; without it, commands inherit the session default model set by the user's env vars
- guardrail 测试（行数/字符数上限）触线时，优先把组装逻辑上移到 CLI 组合层而不是抬阈值——deployer 保持精简，init/update 的副作用归 cli 编排
- 配置副本同步 canonical 不能用键数启发式（默认值墙副本键数多但意图少，会覆盖手工配置），必须用显式优先级——见 config.py:sync_config_copies 的 CANONICAL_PREFERENCE
- 门禁词表扫描须先剥离 code fence/inline code span（done_verify.py:_strip_code_spans），否则词表元讨论自身误报

## Next Recommended Action
`/project-plan`

## Agent Continuation
No active work session.
