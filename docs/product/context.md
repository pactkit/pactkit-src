# Project Context (Auto-generated)
> Last updated: 2026-06-10T11:01:04+08:00 by pactkit context

## Sprint Status
Backlog: 3 | In Progress: 0 | Done: 1 stories

## Current Stories
None

## Recent Completions
- STORY-slim-128: Engineering Concerns: Guide-based NFR enforcement

## Active Branches
+ claude/naughty-euclid-e6a787
  develop
* main

## Key Decisions
- When SCAN_EXCLUDES is a module-level constant shared across graph modes, add mode-specific exclusion logic at the call site rather than modifying the constant — pass call_extra_excludes = SCAN_EXCLUDES - {'tests'} only for call mode to avoid affecting file/class modes
- _write_sqlite_db reuses func_registry and rel_edges already in memory from _build_call_graph — no second AST scan; pactkit query reads db directly without touching pactkit.yaml
- SKILL.md model: frontmatter is passed through by deployer without transformation — source prompts in commands.py/workflows.py are the single source of truth for deployed skill metadata
- codegraph sync must be enforced by code (pactkit visualize/sync), not by prompt instructions — prompt-only enforcement is unreliable for deterministic operations
- Managed-block pattern (start/end markers + regex replace) is the canonical way to update mixed-ownership files — same pattern for CLAUDE.md and CLAUDE.local.md

## Next Recommended Action
`/project-plan`

## Agent Continuation
Last Command: /project-act STORY-slim-128
Phase Reached: Phase 4: complete

### Sprint Contract (STORY-slim-128)
- [ ] AC1: Trigger Index Deployed (R1, R6)
- [ ] AC2: All 13 Guides Deployed (R2, R3)
- [ ] AC3: Plan Phase Triggers NFR Questions
- [ ] AC4: Act Phase Loads Relevant Guides Only
- [ ] AC5: OpenCode/Codex/Copilot Parity
