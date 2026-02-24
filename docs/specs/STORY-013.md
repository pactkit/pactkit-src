# STORY-013: Draw.io MCP Integration — pactkit-draw 接入官方 MCP 实现即时预览

| Field       | Value |
|-------------|-------|
| ID          | STORY-013 |
| Title       | Draw.io MCP Integration |
| Status      | Backlog |
| Priority    | Medium |
| Release     | 1.1.2 |
| Author      | System Architect |

## Background

The official Draw.io MCP server (`@drawio/mcp` by jgraph) has been released. It provides 3 MCP tools:

- `open_drawio_xml` — Opens Draw.io editor with XML content
- `open_drawio_csv` — Converts CSV data to diagrams
- `open_drawio_mermaid` — Renders Mermaid.js syntax in Draw.io editor

Currently, `pactkit-draw` generates `.drawio` XML files written to disk with no preview capability. The agent writes XML following a 600+ line prompt of style dictionaries and anti-bug rules, but verification requires the user to manually open the file in Draw.io.

With Draw.io MCP, generated diagrams can be **instantly opened** in the Draw.io editor for visual verification and interactive editing. The Mermaid support also means existing `.mmd` files (system_design.mmd, code_graph.mmd, etc.) can be visualized via Draw.io.

## Requirements

### R1: Add Draw.io MCP to the MCP Integration rule module
- The `rules.py` MCP section MUST add a new `### Draw.io MCP` entry following the existing conditional pattern (`mcp__drawio__*`).
- The trigger condition MUST be: "If `mcp__drawio__open_drawio_xml` tool is available in the current runtime."
- The PDCA phase mapping MUST include: Plan (diagram generation), Design (architecture visualization).

### R2: Update pactkit-draw skill to conditionally use MCP
- The `SKILL_DRAW_MD` in `skills.py` MUST add a "## MCP Mode (Conditional)" section.
- When Draw.io MCP tools are available, the skill SHOULD call `open_drawio_xml` after generating XML (instead of only writing to disk).
- When Draw.io MCP tools are NOT available, the skill MUST fall back to the current behavior (write `.drawio` file to disk).
- The skill MAY also support calling `open_drawio_mermaid` to open existing `.mmd` files in Draw.io.

### R3: Update visual-architect agent to be MCP-aware
- The `visual-architect` agent prompt in `agents.py` MUST mention Draw.io MCP as a conditional output channel.
- The agent SHOULD prefer MCP preview when available (generate XML → call `open_drawio_xml` → write file to disk as backup).

### R4: Update DRAW_PROMPT_TEMPLATE to include MCP output step
- The `DRAW_PROMPT_TEMPLATE` in `workflows.py` MUST add a Phase 5 (or final step in Execution Protocol) for MCP output.
- The step MUST be conditional: "IF `mcp__drawio__open_drawio_xml` tool is available, call it with the generated XML content."
- The existing file-write step MUST remain as the primary output (MCP preview is additive, not replacing).

### R5: Update system_design.mmd
- The system design graph SHOULD be updated to show Draw.io MCP as an optional output channel from the Draw command.

### R6: Tests
- Unit tests MUST verify the new MCP rule text is present in the deployed output.
- Unit tests MUST verify the skill definition includes the conditional MCP section.
- Unit tests MUST verify the agent prompt mentions Draw.io MCP.
- Unit tests MUST verify the DRAW_PROMPT_TEMPLATE includes the MCP output step.

## Acceptance Criteria

### Scenario 1: MCP rule is deployed
- **Given** a user runs `pactkit init`
- **When** the rules are deployed to `~/.claude/rules/06-mcp-integration.md`
- **Then** the file contains a `### Draw.io MCP` section with tool prefix `mcp__drawio__*`

### Scenario 2: Skill includes conditional MCP mode
- **Given** a user runs `pactkit init`
- **When** the pactkit-draw skill is deployed
- **Then** the skill file contains "open_drawio_xml" and conditional MCP instructions

### Scenario 3: Agent is MCP-aware
- **Given** a user runs `pactkit init`
- **When** the visual-architect agent is deployed
- **Then** the agent prompt contains Draw.io MCP conditional instructions

### Scenario 4: Draw prompt includes MCP output step
- **Given** a user runs `pactkit init`
- **When** the draw command playbook is deployed
- **Then** the playbook contains an MCP output step with `open_drawio_xml`

### Scenario 5: Fallback when MCP unavailable
- **Given** Draw.io MCP tools are NOT available in the runtime
- **When** the pactkit-draw skill is invoked
- **Then** it falls back to writing a `.drawio` file to disk (existing behavior unchanged)

## Target Files

| File | Change |
|------|--------|
| `src/pactkit/prompts/rules.py` | Add Draw.io MCP to MCP section |
| `src/pactkit/prompts/skills.py` | Update SKILL_DRAW_MD with conditional MCP mode |
| `src/pactkit/prompts/agents.py` | Update visual-architect prompt |
| `src/pactkit/prompts/workflows.py` | Add MCP output step to DRAW_PROMPT_TEMPLATE |
| `docs/architecture/graphs/system_design.mmd` | Add Draw.io MCP node |
| `tests/unit/test_drawio_mcp.py` | New test file for STORY-013 |

## Target Call Chain

```
pactkit init
  → deployer.deploy()
    → deployer._deploy_rules()
      → rules.py RULES_MODULES['mcp']  ← Add Draw.io MCP entry
    → deployer._deploy_skills()
      → skills.py SKILL_DRAW_MD  ← Add MCP conditional section
    → deployer._deploy_agents()
      → agents.py AGENTS['visual-architect']  ← Update prompt
    → deployer._deploy_commands()
      → workflows.py DRAW_PROMPT_TEMPLATE  ← Add MCP output step
```

## Notes

- The Draw.io MCP tool names use prefix `mcp__drawio__` (consistent with how other MCP servers are referenced in PactKit).
- The actual MCP server name may vary per user's configuration. The skill should reference the tool by its function name (`open_drawio_xml`), not by server name.
- This is a prompt-only change — no Python runtime code is modified, only prompt template strings.
