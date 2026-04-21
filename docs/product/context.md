# Project Context (Auto-generated)
> Last updated: 2026-04-21T16:23:34+08:00 by pactkit context

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
develop
* main

## Key Decisions
- Dual-anchor pattern: declare principle in RULES_MODULES['core'] (01-core-protocol.md), detail in dedicated module (11-pdca-nudge.md). Prevents attention dilution when rules/ has 10+ files — Core Protocol acts as behavioral constitution anchor.
- Version comparison guards must use semantic (tuple) comparison, not string equality — string != treats 2.10.1 != 2.5.0 without direction, giving wrong upgrade advice
- Plugin deployer (_deploy_commands in deployer.py:952-954) uses _rewrite_skills_prefix instead of _render_prompt, keeping raw placeholders like {BOARD_CMD} — not a deploy drift bug but by-design template behavior
- pactkit clean rglob patterns must exclude protected parent dirs (node_modules, .git) — recursive pattern matching deletes dependency internals
- Hotfix playbook lacked data-driven impact awareness — AI-only 'no side effects' checks miss high-fan-in functions. Adding lightweight .mmd graph reads makes the advisory concrete without blocking the fast-fix path.

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
