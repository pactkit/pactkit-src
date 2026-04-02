# STORY-063: PDCA Playbook Prompt Slimming

| Field | Value |
|-------|-------|
| ID | STORY-063 |
| Status | Draft |
| Priority | Medium |
| Release | 1.6.3 |
| Author | System Architect |
| Created | 2026-03-04 |

## Background

PactKit playbooks in `commands.py` and `workflows.py` total ~1150 lines of prompt text. A significant portion teaches AI tool usage (MCP signatures, CLI syntax, visualize parameters) that Claude Code now natively understands, or repeats the same logic across multiple playbooks (Lazy Visualize, test_map_pattern lookup, context.md format).

Additionally, three real issues were discovered during audit:
1. DEV_REF / TEST_REF are referenced in playbooks but never injected into runtime context (ghost references)
2. `/project-design` does not run Spec Lint on generated Specs, causing Act Phase 0.5 gate failures
3. `context.md` canonical format is defined only in Done Phase 4.5 and fragile cross-referenced by Init and Plan

## Constraints

- **150+ existing test assertions** check for specific keywords in playbook text (see test constraint inventory below)
- All keyword-asserted content MUST be preserved verbatim or the assertion MUST be updated with a co-located Spec justification
- Pre-existing tests that are NOT owned by this Story MUST NOT be modified per Hierarchy of Truth
- PDCA upstream/downstream data contracts MUST remain intact

## Test Constraint Summary

Critical assertions that block removal of specific content:

| Playbook | Constrained Keywords | Test File |
|----------|---------------------|-----------|
| project-act | `DEV_REF` or `TEST_REF` or `Stack Reference` | test_stack_references.py:219 |
| project-act | `detect`/`identify` + `stack`/`language` | test_stack_references.py:213 |
| project-check | `XSS`, `Injection`, `SSRF`, `Race Condition`, `TOCTOU` | test_check_command.py:21-25 |
| project-check | `N+1`, `boundary`, `error handling` | test_check_command.py:32-41 |
| project-check | `P0`, `P1`, `P2`, `P3` | test_check_command.py:47-50 |
| project-sprint | `TeamCreate`, `TaskCreate`, `SendMessage`, `TeamDelete` | test_sprint_command.py:76-88 |
| project-sprint | `Orchestrator` | test_prompt_structural_invariants.py:34 |
| project-done | `Regression`, `Git Commit` | test_prompt_structural_invariants.py:32 |
| project-done | `Lint Gate` or `Smart Lint` | test_story051_workflow_streamlining.py:169 |
| project-done | `source_dirs` or `LANG_PROFILES` | test_story051_workflow_streamlining.py:192 |
| project-design | `cdn.tailwindcss.com`, `lucide` | test_design_command.py:328-333 |
| project-design | `mcp__playwright__` or `Playwright` | test_design_command.py:351 |

## Requirements

### R1: Extract Shared Protocols to rules.py (MUST)

Add a new `shared` key to `RULES_MODULES` in `rules.py` containing:

1. **Lazy Visualize Protocol**: "If source files changed (per LANG_PROFILES.source_dirs) OR code_graph.mmd missing, run visualize in all 3 modes (file, class, call). Else skip with log 'Graph up-to-date'."
2. **Test Mapping Protocol**: "Map changed source files to test files via LANG_PROFILES.test_map_pattern."
3. **Context.md Canonical Format**: The full template (Sprint Status, Current Stories, Recent Completions, Active Branches, Key Decisions, Next Recommended Action) currently defined only in Done Phase 4.5.

Each playbook that currently duplicates this logic MUST reference the shared protocol name instead of inlining the full logic.

Rationale: Reduces maintenance risk when logic changes. Currently, Lazy Visualize is duplicated in Act Phase 4 and Done Phase 2 (identical 6 lines each). Test mapping is duplicated in Act, Check, Done, and Hotfix (4 places). Context.md format is fragile cross-referenced by Done → Init → Plan.

### R2: Slim MCP Tool Signature Teaching (MUST)

For each MCP tool call in playbooks, replace the tool parameter teaching with a one-line business intent. Examples:

| Before | After |
|--------|-------|
| `Use mcp__memory__create_entities with: name: "{STORY_ID}", entityType: "story", observations: [...]` | `Store design context (decisions, target files, rationale) to Memory MCP under entity {STORY_ID}` |
| `Use mcp__memory__search_nodes with the STORY_ID to retrieve...` | `Load prior context for {STORY_ID} from Memory MCP` |
| `Use browser_navigate to load...` + `browser_snapshot to capture...` + `browser_click for...` (4 lines) | `Use Playwright MCP for browser-level verification if available` |

MUST preserve the business intent (what to store / what to load / when to use). MUST NOT preserve MCP tool parameter details.

Exception: Design's `mcp__playwright__` reference MUST be preserved as keyword (test constraint: test_design_command.py:351).

### R3: Slim Inline Tool Teaching (MUST)

Remove the following inline teaching content that is redundant with skill SKILL.md documentation or AI native knowledge:

1. **visualize parameter explanations** in Plan Phase 1 and Act Phase 1 (e.g., "--mode call for logic modification" — SKILL_VISUALIZE_MD already documents this)
2. **"Large Codebase Heuristic: 50+ files"** in Plan Phase 1 (obsolete with 1M context window)
3. **OWASP supplementary list** in Check Phase 1 ("SSRF, Race Condition..." line) — MUST keep keywords `SSRF`, `Race Condition`, `TOCTOU` due to test constraints but MAY slim surrounding prose
4. **Regression Decision Logging templates** in Done Phase 2.5 Step 2.3 (6 log format templates — AI generates appropriate log messages natively)
5. **LANG_PROFILES cleanup file list** in Done Phase 2 (replace with reference to Lazy Visualize Protocol)

MUST NOT remove any keyword listed in the Test Constraint Summary above.

### R4: Slim Sprint to Protocol-Only (MUST)

Rewrite SPRINT_PROMPT to remove all tool API teaching while preserving:
- PDCA stage sequence and dependency logic (Build → Check → Close)
- Agent type assignments (system-architect, qa-engineer, security-auditor, repo-maintainer)
- Keywords: `TeamCreate`, `TaskCreate`, `SendMessage`, `TeamDelete`, `$ARGUMENTS`, `Orchestrator`, `docs/specs/`
- Worktree isolation intent (not the mechanics)
- Error handling strategy (STOP on failure)
- Playbook file references (commands/project-plan.md, etc.)

Target: ~40-50 lines (from current ~160 lines)

### R5: Fix Ghost DEV_REF/TEST_REF References (MUST)

The references `DEV_REF_BACKEND`, `DEV_REF_FRONTEND`, `TEST_REF_PYTHON`, `TEST_REF_NODE`, `TEST_REF_GO`, `TEST_REF_JAVA` defined in `references.py` are exported by `prompts/__init__.py` but never injected into any deployment artifact by `deployer.py`.

Two options (choose one):
- **Option A**: Inject references into the senior-developer agent definition (the agent that runs Act)
- **Option B**: Remove the playbook text referencing them and update the 2 test assertions in `test_stack_references.py`

MUST NOT leave ghost references (defined but unreachable at runtime).

### R6: Add Spec Lint to Design (SHOULD)

Add a Spec Lint Self-Check step to Design Phase 3 (Story Decomposition), matching the existing pattern in Plan Phase 3:

After each Spec is generated by `create_spec`, run `python3 src/pactkit/skills/spec_linter.py docs/specs/{STORY_ID}.md`. If ERRORs found, self-correct and re-run.

Rationale: Design generates N Specs that feed into Act Phase 0.5 Spec Lint Gate. Without self-checking, malformed Specs block the entire Sprint pipeline.

### R7: Do NOT Remove Content Protected by Tests (MUST)

The following content was previously identified as "deletable" but is protected by test assertions:

| Content | Protected By | MUST Keep |
|---------|-------------|-----------|
| Stack Detection in Act Phase 0 | test_stack_references.py:210-213 | Yes (keywords `detect`/`stack`) |
| DEV_REF reference in Act Phase 0 | test_stack_references.py:219 | Yes (keyword `DEV_REF`) |
| Severity Levels P0-P3 in Check | test_check_command.py:47-50 | Yes |
| `SSRF`, `Race Condition`, `TOCTOU` in Check | test_check_command.py:21-25 | Yes |
| `N+1`, `boundary`, `error handling` in Check | test_check_command.py:32-41 | Yes |
| Code Quality checklist in Check Phase 2 | test_check_command.py:32-41 | Yes |
| `Playwright` reference in Design | test_design_command.py:351 | Yes |
| `cdn.tailwindcss.com` in Design | test_design_command.py:328 | Yes |

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/rules.py` | Add `shared` key to RULES_MODULES with 3 shared protocols | None | Low |
| 2 | `src/pactkit/prompts/workflows.py` | Rewrite SPRINT_PROMPT to Protocol-Only (~40 lines) | None | Medium |
| 3 | `src/pactkit/prompts/commands.py` | Slim project-plan.md: remove visualize teaching, MCP signatures; reference shared protocols | Step 1 | Medium |
| 4 | `src/pactkit/prompts/commands.py` | Slim project-act.md: remove MCP signatures, inline tool teaching; reference shared protocols; keep DEV_REF keyword | Step 1 | Medium |
| 5 | `src/pactkit/prompts/commands.py` | Slim project-check.md: remove MCP teaching, slim prose around OWASP keywords; keep all test-constrained keywords | Step 1 | Medium |
| 6 | `src/pactkit/prompts/commands.py` | Slim project-done.md: remove decision logging templates, cleanup teaching; reference shared protocols | Step 1 | Medium |
| 7 | `src/pactkit/prompts/workflows.py` | Add Spec Lint step to DESIGN_PROMPT Phase 3 | None | Low |
| 8 | `src/pactkit/prompts/commands.py` | Slim project-init, project-hotfix, project-pr: remove redundant teaching | Step 1 | Low |
| 9 | Decision on R5 | Either inject DEV_REF into agent or clean up references + tests | Step 4 | Medium |
| 10 | `tests/unit/test_story063_*.py` | Write tests for new shared protocols and Sprint rewrite | Steps 1-8 | Low |

## Acceptance Criteria

### AC1: Shared Protocols Exist
Given RULES_MODULES in rules.py
When the `shared` key is read
Then it MUST contain "Lazy Visualize Protocol", "Test Mapping Protocol", and "Context.md Format" sections

### AC2: Sprint is Protocol-Only
Given SPRINT_PROMPT in workflows.py
When character count is measured
Then it MUST be less than 3000 characters (roughly ~50 lines)
And it MUST still contain `TeamCreate`, `TaskCreate`, `SendMessage`, `TeamDelete`, `$ARGUMENTS`, `Orchestrator`

### AC3: MCP Signatures Removed
Given all playbooks in COMMANDS_CONTENT
When searched for `mcp__memory__create_entities with:` or `mcp__memory__search_nodes with`
Then zero matches MUST be found
And the business intent phrases (`Store design context`, `Load prior context`) MUST be present

### AC4: All Pre-existing Tests Pass
Given all tests in `tests/unit/test_*command*.py`, `test_stack_references.py`, `test_prompt_structural_invariants.py`, and `test_story0*`
When `pytest` is run
Then ALL pre-existing tests MUST pass without modification

### AC5: Design Runs Spec Lint
Given DESIGN_PROMPT in workflows.py
When Phase 3 content is read
Then it MUST contain `spec_linter` or `Spec Lint` reference

### AC6: DEV_REF Ghost Resolved
Given the project codebase
When `DEV_REF` appears in a playbook
Then it MUST also be injected into a deployment artifact reachable at runtime
OR the playbook reference and corresponding test assertions MUST be removed

### AC7: Total Prompt Size Reduced
Given all content in COMMANDS_CONTENT values + SPRINT_PROMPT + HOTFIX_PROMPT + DESIGN_PROMPT
When total character count is measured
Then it MUST be at least 15% less than the pre-change baseline

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (prompts/*.py) |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database queries |
| SEC-4 | No | No frontend rendering |
| SEC-5 | No | No auth/session handling |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No exception handling changes |
| SEC-8 | No | No dependency changes |

## Out of Scope

- NOT changing any skill scripts (board.py, scaffold.py, visualize.py, spec_linter.py)
- NOT changing deployer.py deployment logic
- NOT changing agent definitions (agents.py)
- NOT changing LANG_PROFILES data structure (workflows.py)
- NOT changing pactkit.yaml config schema
- NOT removing any playbook command entirely (all 11 commands remain)

## Target Call Chain

```
deployer.py::_deploy_commands()
  → reads prompts.COMMANDS_CONTENT dict
    → project-plan.md, project-act.md, project-check.md, project-done.md, etc.
  → calls _rewrite_skills_prefix() on each
  → calls atomic_write() to deploy

deployer.py::_deploy_rules()
  → reads prompts.RULES_MODULES dict
    → includes new 'shared' key
  → calls atomic_write() to deploy

commands.py
  → imports SPRINT_PROMPT, HOTFIX_PROMPT, DESIGN_PROMPT from workflows.py
  → registers into COMMANDS_CONTENT dict
```
