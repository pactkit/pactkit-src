# Project Context (Auto-generated)
> Last updated: 2026-04-16T17:59:42+08:00 by pactkit context

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
- Parsing Mermaid .mmd files to JSON (nodes+edges) is straightforward with regex; the D3 force-directed HTML template works well as a single-file self-contained skill
- D3 force graph selectNode() computes blast radius via in-browser BFS — no backend needed; folder-based coloring via d3.scaleOrdinal on path prefix gives CodeFlow-quality visuals
- H1-H7 harness audit aggregator pattern: each _check_hN() function is self-contained with its own L0-L3 criteria, making it easy to add new checks per layer without touching scoring logic
- File-level hotspot aggregation (complexity_avg × blast_pct × fan_in) reduces 141 per-function findings to ~10 actionable items; _suggest_action() maps dominant signal to Split/Stabilize/Isolate/Decompose verb
- Weighted hotspot formula (complexity 25% + docstring 15% + smells 15% + layers 10% + test 20% + blast 15%) gives meaningful scores across different project profiles; _generate_suggested_tasks auto-scaffolds BUG/HOTFIX specs with Done-completed filter for idempotency

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
