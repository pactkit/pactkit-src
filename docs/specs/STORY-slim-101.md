# STORY-slim-101: Solution Design Protocol Rule

| Field | Value |
|-------|-------|
| ID | STORY-slim-101 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.5 |

## Background

LLM tends to implement features using "quick and dirty" approaches that work but have poor maintainability, robustness, and extensibility. Three core anti-patterns observed:

1. **Framework Blindness**: LLM doesn't know what native capabilities the framework provides, so it reinvents the wheel (e.g., writing custom context storage when LangGraph has memory store)
2. **Project Blindness**: LLM doesn't check what the project has already encapsulated, so it bypasses existing abstractions (e.g., instantiating AzureChatOpenAI directly instead of using `get_precise_llm()`)
3. **Hardcoded Dependencies**: LLM couples directly to framework internals instead of using project abstraction layers

Root cause: No protocol requires LLM to evaluate capability delta (framework native + project existing) before implementation. Information exists (Context7 for framework docs, grep for project code, call chain for dependencies) but LLM is not required to use it.

## Requirements

### R1: Rule File Creation (MUST)

Create `~/.claude/rules/12-solution-design.md` containing the Solution Design Protocol that defines capability assessment before implementation.

### R2: Framework Capability Query (MUST)

The protocol MUST define a prioritized query path for framework native capabilities:
1. Context7 MCP (if available) — real-time, authoritative
2. WebFetch official docs (if network available) — real-time, requires parsing
3. AI training data (fallback) — must declare framework version to avoid outdated APIs

### R3: Project Capability Discovery (MUST)

The protocol MUST define methods to discover project existing capabilities:
- Grep import statements to find framework usage
- Grep factory function patterns (`get_*`, `build_*`, `create_*`) to find encapsulated capabilities
- Pattern match wiring layer files (`wiring.py`, `deps.py`, `container.*`, `di.*`, `providers.*`)
- Use call chain visualization for dependency analysis

### R4: Delta Assessment Matrix (MUST)

The protocol MUST define a decision matrix based on capability delta:
- Framework has & project not used → prefer enabling framework capability
- Framework has & project encapsulated → reuse project abstraction, do not bypass
- Neither has → only then implement new

### R5: Decision Constraints (MUST)

The protocol MUST enforce:
- MUST NOT bypass project abstraction layer to use framework directly
- SHOULD prefer framework native over custom implementation
- MUST state reasoning if not using available framework capability

### R6: Output Format (SHOULD)

The protocol SHOULD define output format for:
- Plan phase: Technical Design section in Spec
- Act phase: Brief assessment output before implementation

### R7: Stack-Agnostic Design (MUST)

The protocol MUST be stack-agnostic, supporting dependency files for:
- Python: `pyproject.toml`, `requirements.txt`
- Node: `package.json`
- Go: `go.mod`
- Java: `pom.xml`, `build.gradle`
- Rust: `Cargo.toml`

### R8: Playbook Integration (MUST)

The rule MUST be integrated into PDCA playbooks:
- `project-plan.md`: Add `@~/.claude/rules/12-solution-design.md` import and reference protocol in Phase 1
- `project-act.md`: Add `@~/.claude/rules/12-solution-design.md` import and reference protocol in Phase 1

## Acceptance Criteria

### AC1: Rule File Exists (R1)

- **Given** PactKit rules directory at `~/.claude/rules/`
- **When** `pactkit init` or `pactkit deploy` is run
- **Then** `12-solution-design.md` is deployed with full protocol content

### AC2: Framework Query Fallback Chain (R2)

- **Given** A requirement involving a framework (e.g., LangGraph)
- **When** Solution Design Protocol is executed
- **Then** Framework capabilities are queried via Context7 → WebFetch → Training Data fallback chain

### AC3: Project Capability Discovery (R3)

- **Given** A project with `pyproject.toml` listing `langgraph>=0.4`
- **When** Solution Design Protocol Step 3 is executed
- **Then** Protocol identifies: (a) framework imports in src/, (b) factory functions like `get_*`/`build_*`, (c) wiring layer files

### AC4: Delta Assessment Decision (R4)

- **Given** Framework has memory store capability, project has checkpointer but not memory
- **When** Requirement is "add cross-session context"
- **Then** Protocol recommends "enable framework capability" not "implement custom"

### AC5: Abstraction Bypass Prevention (R5)

- **Given** Project has `get_precise_llm()` in wiring.py
- **When** LLM attempts to directly instantiate AzureChatOpenAI
- **Then** Protocol constraint blocks this and directs to use existing encapsulation

### AC6: Output Format in Spec (R6)

- **Given** Plan phase executes Solution Design Protocol
- **When** Capability assessment is complete
- **Then** Output is written to `## Technical Design` section with: capability table, reuse points, new implementation list

### AC7: Multi-Stack Support (R7)

- **Given** A Node.js project with `package.json`
- **When** Solution Design Protocol Step 1 is executed
- **Then** Protocol correctly reads dependencies from `package.json` not `pyproject.toml`

### AC8: Playbook References Protocol (R8)

- **Given** User runs `/project-plan` or `/project-act`
- **When** Phase 1 executes
- **Then** Solution Design Protocol is triggered for requirements involving frameworks

## Target Call Chain

Not applicable — this is a new rule file, not modifying existing code.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/rules.py` | Add `RULE_12_SOLUTION_DESIGN` constant with full protocol content | None | Low |
| 2 | `src/pactkit/config.py` | Add `12-solution-design` to `VALID_RULES` | Step 1 | Low |
| 3 | `src/pactkit/prompts/commands.py` | Update `COMMAND_PLAN` and `COMMAND_ACT` to import rule and reference protocol in Phase 1 | Step 1 | Medium |
| 4 | `tests/unit/test_rules.py` | Add test for new rule deployment | Steps 1-3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | No secrets — rule file contains only protocol text |
| SEC-2 | N/A | No user input handling — rule file is static content |
| SEC-3 | N/A | No database operations |
| SEC-4 | N/A | No frontend code |
| SEC-5 | N/A | No authentication logic |
| SEC-6 | N/A | No API endpoints |
| SEC-7 | N/A | No error handling code |
| SEC-8 | N/A | No dependency changes |

## Out of Scope

- Auto-generation of capability index files — protocol uses dynamic discovery
- Framework-specific capability lists — protocol relies on Context7/WebFetch for real-time data
