# Project Context (Auto-generated)
> Last updated: 2026-06-01T10:43:16+08:00 by pactkit context

## Sprint Status
Backlog: 3 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
+ claude/naughty-euclid-e6a787
  develop
* main

## Key Decisions
- code_graph.mmd uses sanitized node IDs (src_pactkit_generators_deployer_py), not bare filenames — grep patterns for fan-in/fan-out must use .* wildcard or they silently never match
- When SCAN_EXCLUDES is a module-level constant shared across graph modes, add mode-specific exclusion logic at the call site rather than modifying the constant — pass call_extra_excludes = SCAN_EXCLUDES - {'tests'} only for call mode to avoid affecting file/class modes
- _write_sqlite_db reuses func_registry and rel_edges already in memory from _build_call_graph — no second AST scan; pactkit query reads db directly without touching pactkit.yaml
- SKILL.md model: frontmatter is passed through by deployer without transformation — source prompts in commands.py/workflows.py are the single source of truth for deployed skill metadata
- codegraph sync must be enforced by code (pactkit visualize/sync), not by prompt instructions — prompt-only enforcement is unreliable for deterministic operations

## Next Recommended Action
`/project-plan`

## Agent Continuation
No active work session.
