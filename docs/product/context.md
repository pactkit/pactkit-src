# Project Context (Auto-generated)
> Last updated: 2026-05-25T14:46:09+08:00 by pactkit context

## Sprint Status
Backlog: 2 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
+ claude/naughty-euclid-e6a787
  develop
* main

## Key Decisions
- Code Enforces implementation: pactkit interface-summary uses ast.parse() to physically output only signatures—AI receives truncated content, not a prompt instruction to self-truncate. Pattern: CLI tool as enforcement layer (interface_summary.py:generate_summary)
- Lifecycle gap pattern: when artifact has create+consume but no update mechanism, add conditional sync in the modifying command. Applied: Act Phase 4 Journey Sync step in commands.py COMMANDS_CONTENT['project-act.md']
- code_graph.mmd uses sanitized node IDs (src_pactkit_generators_deployer_py), not bare filenames — grep patterns for fan-in/fan-out must use .* wildcard or they silently never match
- When SCAN_EXCLUDES is a module-level constant shared across graph modes, add mode-specific exclusion logic at the call site rather than modifying the constant — pass call_extra_excludes = SCAN_EXCLUDES - {'tests'} only for call mode to avoid affecting file/class modes
- _write_sqlite_db reuses func_registry and rel_edges already in memory from _build_call_graph — no second AST scan; pactkit query reads db directly without touching pactkit.yaml

## Next Recommended Action
`/project-plan`

## Agent Continuation
No active work session.
