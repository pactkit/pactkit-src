# Project Context (Auto-generated)
> Last updated: 2026-05-05T22:41:41+08:00 by pactkit context

## Sprint Status
Backlog: 4 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
+ claude/naughty-euclid-e6a787
  develop
* main

## Key Decisions
- Signal Strength L3 SHOULD semantics in rules.py:RULES_MODULES['core'] must use RFC 2119 wording — 'warning, non-blocking' caused AI to systematically defer all SHOULD tasks during Act
- Rule files deploy from src/pactkit/prompts/rules.py via pactkit deploy — never edit ~/.claude/rules/ directly
- Plan Phase横向扫描(Lateral Scan)比纵向trace更重要——PactSearch的10个技术债中60%源于缺少水平重复检测。修复方向是改Plan playbook引导Architect用已有工具(LSP/visualize/grep)做横向扫描，而非新建CLI
- When migrating functionality (e.g., version checking from pactkit.yaml to global marker), grep all references across source, prompts, tests, and CLI help text — partial migration leaves ghost behavior
- When extracting project-specific rules into a framework, generalize by removing project names, library references, and spec IDs — keep only the anti-pattern/fix-pattern structure that applies to any codebase

## Next Recommended Action
`/project-plan`

## Agent Continuation
No active work session.
