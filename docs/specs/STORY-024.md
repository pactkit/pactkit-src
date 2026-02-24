# STORY-024: Native Agent Enhancement — Smart Model, Hooks, and Memory

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | 1.2.0 |

## Context

PactKit already deploys 9 agent roles as `.claude/agents/` files with proper YAML frontmatter (since STORY-012). However, several Claude Code native agent capabilities remain underutilized:

1. **Model defaults to `sonnet` for all agents** — regardless of task complexity. Read-only exploration agents (Code Explorer, System Medic, Security Auditor) could use `haiku` for faster/cheaper execution, while the default should be `inherit` (use whatever model the user is running) so PactKit works with any subscription tier.

2. **No agent-scoped hooks** — agents rely on prompt-based "boundaries" (e.g., "do not write code") which the LLM can ignore. Claude Code native hooks enforce constraints at the tool level (block Write/Edit via PreToolUse).

3. **Persistent memory only on Code Explorer** — other agents (System Architect, QA Engineer) would benefit from cross-session knowledge accumulation (design patterns discovered, recurring issues found, codebase conventions learned).

4. **No user-configurable model overrides** — `pactkit.yaml` has no mechanism for users to customize per-agent model selection.

### Competitive Gap

Cursor, Roo Code, and Claude Code native subagents all support model routing per agent type. Aider uses `--weak-model` for less capable tasks. PactKit's flat `model: sonnet` wastes tokens on simple tasks and prevents users from leveraging their preferred model tier.

## Target Call Chain

```
pactkit init / pactkit update
  → deployer.deploy()
    → _deploy_agents(agents_dir, enabled_agents)
      → Read AGENTS_EXPERT[name]
        → Read per-agent model from pactkit.yaml overrides (NEW)
        → Generate frontmatter with hooks (NEW)
        → Generate frontmatter with memory scope (ENHANCED)
      → atomic_write(agent_path, content)
```

## Requirements

### R1: Smart Model Default
- The deployer MUST set `model: inherit` as the default for all agents (replacing the current hardcoded `sonnet`).
- Each agent definition in `AGENTS_EXPERT` MAY include a `model` field with a recommended model (e.g., `haiku` for read-only agents).
- The deployer MUST use the agent-level model if present, otherwise `inherit`.

### R2: User-Configurable Model Overrides in pactkit.yaml
- `pactkit.yaml` MUST support an optional `agent_models` section for per-agent model overrides.
- Format:
  ```yaml
  agent_models:
    code-explorer: haiku
    system-medic: haiku
    security-auditor: haiku
  ```
- The override priority MUST be: `pactkit.yaml agent_models` > `AGENTS_EXPERT[name].model` > `inherit` (default).
- Valid model values MUST be: `haiku`, `sonnet`, `opus`, `inherit`.
- The `validate_config()` function MUST warn on invalid model values.

### R3: Agent-Scoped Hooks for Constraint Enforcement
- Read-only agents (QA Engineer, Security Auditor, Code Explorer, System Medic) MUST include a `PreToolUse` hook that blocks `Write` and `Edit` tool calls.
- The hook SHOULD be a lightweight inline prompt-type hook (not a command script) to avoid file dependencies.
- The hook specification MUST be added to `AGENTS_EXPERT` as a `hooks` dict field.
- The deployer MUST serialize the `hooks` field into the agent frontmatter as valid YAML.

### R4: Expanded Persistent Memory
- The following agents MUST have `memory: project` scope:
  - `system-architect` — remembers design decisions, architecture patterns, tech debt across sessions
  - `qa-engineer` — remembers test patterns, recurring issues, code quality trends
- The following agents MUST have `memory: user` scope (cross-project):
  - `code-explorer` — already has this (no change)
- Other agents SHOULD NOT have memory enabled (their tasks are ephemeral: commit, deploy, draw).

### R5: Permission Mode Enforcement
- `system-architect` MUST have `permissionMode: plan` (design-only, no code execution).
- `qa-engineer` already has `permissionMode: plan` (no change).
- `security-auditor` MUST have `permissionMode: plan` (audit-only).
- `system-medic` SHOULD have `permissionMode: default` (needs Bash for diagnostics).

### R6: Deployer YAML Serialization
- The deployer `_deploy_agents()` MUST correctly serialize nested YAML structures (`hooks`, `agent_models`).
- The deployer MUST NOT break existing frontmatter fields when adding new ones.
- Hooks MUST be serialized using PyYAML or equivalent to ensure valid YAML indentation.

## Acceptance Criteria

### AC1: Model Default
- **Given** a fresh `pactkit init`
- **When** agent files are deployed
- **Then** all agents without explicit model config have `model: inherit` in frontmatter

### AC2: Model Override
- **Given** `pactkit.yaml` contains `agent_models: { code-explorer: haiku }`
- **When** agents are deployed
- **Then** `code-explorer.md` frontmatter has `model: haiku`
- **And** other agents without overrides have their default model

### AC3: Invalid Model Warning
- **Given** `pactkit.yaml` contains `agent_models: { code-explorer: gpt-4 }`
- **When** config is validated
- **Then** a warning is emitted about invalid model value

### AC4: Read-Only Agent Hooks
- **Given** agent `security-auditor` is deployed
- **When** the agent frontmatter is parsed
- **Then** a `hooks.PreToolUse` entry exists that blocks `Write|Edit` tools

### AC5: Memory Scopes
- **Given** agents are deployed
- **When** `system-architect.md` is read
- **Then** frontmatter contains `memory: project`
- **And** `code-explorer.md` contains `memory: user`
- **And** `repo-maintainer.md` does NOT contain a `memory` field

### AC6: Permission Modes
- **Given** agents are deployed
- **When** `system-architect.md` is read
- **Then** frontmatter contains `permissionMode: plan`

### AC7: Backward Compatibility
- **Given** an existing `pactkit.yaml` without `agent_models`
- **When** `pactkit update` is run
- **Then** all agents deploy successfully with `model: inherit` default
- **And** no errors or unexpected behavior

### AC8: Hooks YAML Validity
- **Given** agents with hooks are deployed
- **When** the generated .md file is parsed
- **Then** the YAML frontmatter is valid and parseable by standard YAML parsers
