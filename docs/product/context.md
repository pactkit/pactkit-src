# Project Context (Auto-generated)
> Last updated: 2026-04-22T11:49:06+08:00 by pactkit context

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
- Plugin deployer (_deploy_commands in deployer.py:952-954) uses _rewrite_skills_prefix instead of _render_prompt, keeping raw placeholders like {BOARD_CMD} — not a deploy drift bug but by-design template behavior
- pactkit clean rglob patterns must exclude protected parent dirs (node_modules, .git) — recursive pattern matching deletes dependency internals
- Hotfix playbook lacked data-driven impact awareness — AI-only 'no side effects' checks miss high-fan-in functions. Adding lightweight .mmd graph reads makes the advisory concrete without blocking the fast-fix path.
- Version tracking in pactkit.yaml caused cross-project desync — moved to ~/.claude/.pactkit-version as single source of truth for deploy state. config.py get_default_config() no longer includes version field.
- When the same bug pattern recurs 3+ times across specs (BUG-010, BUG-slim-089, STORY-033, STORY-slim-054), promote the fix from spec-level to a standing rule in 08-architecture-principles.md — ad-hoc spec fixes do not prevent recurrence

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
