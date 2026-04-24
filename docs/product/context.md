# Project Context (Auto-generated)
> Last updated: 2026-04-24T22:43:35+08:00 by pactkit context

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
- When the same bug pattern recurs 3+ times across specs (BUG-010, BUG-slim-089, STORY-033, STORY-slim-054), promote the fix from spec-level to a standing rule in 08-architecture-principles.md — ad-hoc spec fixes do not prevent recurrence
- Signal Strength L3 SHOULD semantics in rules.py:RULES_MODULES['core'] must use RFC 2119 wording — 'warning, non-blocking' caused AI to systematically defer all SHOULD tasks during Act
- Rule files deploy from src/pactkit/prompts/rules.py via pactkit deploy — never edit ~/.claude/rules/ directly
- Plan Phase横向扫描(Lateral Scan)比纵向trace更重要——PactSearch的10个技术债中60%源于缺少水平重复检测。修复方向是改Plan playbook引导Architect用已有工具(LSP/visualize/grep)做横向扫描，而非新建CLI
- When migrating functionality (e.g., version checking from pactkit.yaml to global marker), grep all references across source, prompts, tests, and CLI help text — partial migration leaves ghost behavior

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
