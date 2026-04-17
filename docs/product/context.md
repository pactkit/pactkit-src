# Project Context (Auto-generated)
> Last updated: 2026-04-17T11:03:11+08:00 by pactkit context

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
- H1-H7 harness audit aggregator pattern: each _check_hN() function is self-contained with its own L0-L3 criteria, making it easy to add new checks per layer without touching scoring logic
- File-level hotspot aggregation (complexity_avg × blast_pct × fan_in) reduces 141 per-function findings to ~10 actionable items; _suggest_action() maps dominant signal to Split/Stabilize/Isolate/Decompose verb
- Weighted hotspot formula (complexity 25% + docstring 15% + smells 15% + layers 10% + test 20% + blast 15%) gives meaningful scores across different project profiles; _generate_suggested_tasks auto-scaffolds BUG/HOTFIX specs with Done-completed filter for idempotency
- Dual-dimension audit (config+code 50/50) gives accurate project health picture; scanning ~/.claude/ global config catches harness setup invisible at project level
- Dual-anchor pattern: declare principle in RULES_MODULES['core'] (01-core-protocol.md), detail in dedicated module (11-pdca-nudge.md). Prevents attention dilution when rules/ has 10+ files — Core Protocol acts as behavioral constitution anchor.

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
