# STORY-slim-020: Fix Explore Subagent Stall During Plan Phase 1 Archaeology

| Field | Value |
|-------|-------|
| ID | STORY-slim-020 |
| Status | Done |
| Priority | P1 |
| Release | 2.3.0 |

## Background

When running `/project-plan` on a PactKit-instrumented project, the main agent (Opus) delegates Phase 1 Archaeology research to an `Explore` subagent. The subagent frequently stalls — producing no output for an extended period or never returning. This is reproducible.

Root causes identified:
1. **Context overload**: The Explore subagent inherits the full PactKit context (8 rules, 11 commands, 9 agents, 10 skills, CLAUDE.md). Processing this massive prompt before starting actual search creates a reasoning bottleneck.
2. **Unbounded task scope**: Plan Phase 1 says "use pactkit-trace skill" without specifying a search scope or file limit, leading the Explore agent to attempt an exhaustive trace of the entire codebase.
3. **Excessive maxTurns**: `code-explorer` has `maxTurns: 50`, allowing an unbounded exploration chain that may never converge to a return.

## Target Call Chain

```
User invokes /project-plan
  -> Main agent (Opus) reads Phase 1: Archaeology
    -> Agent(subagent_type="Explore", prompt="trace the codebase...")
      -> Explore agent inherits full PactKit context
        -> Starts extended thinking to plan all 50 possible turns
          -> STALLS (no incremental output)
```

Source:
- `src/pactkit/prompts/commands.py` lines 66-71 (Phase 1 instructions)
- `src/pactkit/prompts/agents.py` lines 248-276 (code-explorer definition)
- `.claude/pactkit.yaml` agent_models section (code-explorer: haiku)

## Requirements

### R1: Add scope-limiting instructions to Plan Phase 1
1. **MUST** add explicit scope guidance to Phase 1 that instructs the main agent to provide a focused, bounded prompt when delegating to Explore subagents.
2. **MUST** include a file-count limit recommendation (e.g., "limit initial search to 5-10 key files").
3. **MUST** instruct the main agent to provide the Explore subagent with: (a) specific function/class name to trace, (b) specific directory scope, (c) expected output format.

### R2: Reduce code-explorer maxTurns
4. **MUST** reduce `code-explorer` `maxTurns` from 50 to 15.
5. **SHOULD** add a comment in the agent definition explaining the rationale for the limit.

### R3: Add structured delegation template to Phase 1
6. **MUST** add a "Delegation Template" to Phase 1 that shows the main agent exactly how to formulate the Explore subagent prompt:
   - Include: target function/class, directory scope, max files to read, expected output
   - Example: `Agent(subagent_type="Explore", prompt="Find the entry point for pactkit deploy in src/pactkit/. Trace the call chain from deploy() to file writes. Read at most 8 files. Return: entry file, call chain list, key data transformations.")`

### R4: No side effects
7. **MUST NOT** change the Explore agent's core protocol or boundaries (read-only, no code writes).
8. **MUST NOT** alter any Phase other than Phase 1 in project-plan.

## Acceptance Criteria

### Scenario 1: Plan Phase 1 includes delegation template
- **Given** a user runs `/project-plan "some feature"`
- **When** the main agent reaches Phase 1 Archaeology
- **Then** the prompt contains a structured delegation template with scope, file limit, and expected output format

### Scenario 2: Explore subagent receives bounded prompt
- **Given** the main agent delegates to an Explore subagent during Phase 1
- **When** the Explore subagent starts
- **Then** it has a specific function/directory target (not "trace the whole codebase")
- **And** a file-count limit is specified in the prompt

### Scenario 3: code-explorer maxTurns reduced
- **Given** `pactkit update` deploys agent definitions
- **When** `code-explorer.md` is generated
- **Then** `maxTurns` is 15 (not 50)

### Scenario 4: Other phases unchanged
- **Given** the project-plan prompt is modified
- **When** comparing Phase 0, 0.5, 0.7, 2, 3.1, 3.2a-d, 3.3
- **Then** none of these phases are altered

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Rewrite Phase 1 with scope-limiting instructions and delegation template | None | Low |
| 2 | `src/pactkit/prompts/agents.py` | Reduce code-explorer maxTurns from 50 to 15 | None | Low |

## Non-Goals
- Changing the Claude Code Explore built-in subagent behavior (out of PactKit's control)
- Modifying the `code-explorer.md` agent prompt content beyond maxTurns
- Adding timeout mechanisms (Claude Code runtime responsibility, not prompt-level)

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Prompt text and agent config change only |
| SEC-2 | N/A | No user input handling |
| SEC-3 | N/A | No data layer |
| SEC-4 | N/A | No frontend |
| SEC-5 | N/A | No auth |
| SEC-6 | N/A | No API routes |
| SEC-7 | N/A | No error handling changes |
| SEC-8 | N/A | No dependency changes |
