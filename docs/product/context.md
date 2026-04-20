# Project Context (Auto-generated)
> Last updated: 2026-04-20T10:21:11+08:00 by pactkit context

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
- Weighted hotspot formula (complexity 25% + docstring 15% + smells 15% + layers 10% + test 20% + blast 15%) gives meaningful scores across different project profiles; _generate_suggested_tasks auto-scaffolds BUG/HOTFIX specs with Done-completed filter for idempotency
- Dual-dimension audit (config+code 50/50) gives accurate project health picture; scanning ~/.claude/ global config catches harness setup invisible at project level
- Dual-anchor pattern: declare principle in RULES_MODULES['core'] (01-core-protocol.md), detail in dedicated module (11-pdca-nudge.md). Prevents attention dilution when rules/ has 10+ files — Core Protocol acts as behavioral constitution anchor.
- Version comparison guards must use semantic (tuple) comparison, not string equality — string != treats 2.10.1 != 2.5.0 without direction, giving wrong upgrade advice
- Plugin deployer (_deploy_commands in deployer.py:952-954) uses _rewrite_skills_prefix instead of _render_prompt, keeping raw placeholders like {BOARD_CMD} — not a deploy drift bug but by-design template behavior

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
