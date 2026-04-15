# STORY-slim-088: Slim dependencies and robust CLI fallback

| Field | Value |
|-------|-------|
| ID | STORY-slim-088 |
| Status | Done |
| Priority | P1 |
| Release | 2.9.13 |

## Background

When a user installs PactKit via `pip install pactkit`, all adapter packages (`pactkit-opencode`, `pactkit-codex`) and tree-sitter language bindings are pulled in as hard dependencies. This causes:

1. **Unwanted adapter installation**: Users who only use Claude Code still get Codex and OpenCode adapters installed, adding unnecessary packages and potential version conflicts.
2. **Heavy install for core usage**: tree-sitter + 3 language grammars (~50MB compiled) are required even for users who never use the `visualize` skill. The code already guards these imports with `try/except`.
3. **CLI not-on-PATH failure**: Playbooks invoke `pactkit spec-lint` assuming the CLI is on `$PATH`. In container environments (Codex, remote dev containers) where PactKit is installed as a library but not on PATH, this fails silently — the AI agent then performs a "manual lint" which violates P.A.C.T. (deterministic ops MUST be code, not prompt).
4. **Incomplete add_story documentation**: The Plan playbook Phase 3.3 says "Add Story using `add_story`" without showing the required `tasks` argument, causing board.py argument errors.

## Requirements

### R1: Slim core dependencies (MUST)

`pyproject.toml` `[project].dependencies` MUST contain only packages required for the core CLI to start and run basic commands (`init`, `deploy`, `guard`, `spec-lint`, `context`, `next-id`). Currently this means only `pyyaml>=6.0`.

### R2: Optional dependency groups (MUST)

Adapter packages and tree-sitter bindings MUST be moved to `[project.optional-dependencies]` with the following extras:
- `opencode` → `pactkit-opencode>=2.9.0`
- `codex` → `pactkit-codex>=2.9.0`
- `visualize` → `tree-sitter>=0.25`, `tree-sitter-go>=0.25`, `tree-sitter-java>=0.23`, `tree-sitter-typescript>=0.23`
- `all` → `pactkit[opencode,codex,visualize]`

### R3: Spec-lint CLI fallback (MUST)

All playbooks that invoke `pactkit spec-lint` MUST include a fallback invocation `python3 -m pactkit spec-lint` when `pactkit` is not found on `$PATH`. The fallback MUST execute the same code path — no AI-based "manual lint" is acceptable (P.A.C.T. violation).

### R4: Board add_story call signature (SHOULD)

The Plan playbook Phase 3.3 SHOULD include the full `add_story` invocation with all required arguments (ID, title, tasks), consistent with the skill documentation in `skills.py:98-104`.

## Acceptance Criteria

### AC1: Core install has no adapter packages (R1, R2)

- **Given** a clean virtual environment
- **When** `pip install pactkit` is executed (without extras)
- **Then** `pactkit-opencode` and `pactkit-codex` are NOT installed, and `pactkit --version` still works

### AC2: Core install has no tree-sitter (R1, R2)

- **Given** a clean virtual environment
- **When** `pip install pactkit` is executed (without extras)
- **Then** `tree-sitter`, `tree-sitter-go`, `tree-sitter-java`, `tree-sitter-typescript` are NOT installed, and `pactkit spec-lint --help` still works

### AC3: Extras install the right packages (R2)

- **Given** a clean virtual environment
- **When** `pip install pactkit[all]` is executed
- **Then** all adapter packages and tree-sitter bindings are installed

### AC4: Spec-lint fallback in playbook (R3)

- **Given** a deployed playbook in an environment where `pactkit` is not on `$PATH` but `python3 -m pactkit` works
- **When** the Plan Phase 3.2d or Act Phase 0.5 spec-lint step is executed
- **Then** the fallback `python3 -m pactkit spec-lint` is used and produces the same exit code and output

### AC5: Board add_story has complete signature (R4)

- **Given** the Plan playbook Phase 3.3 text
- **When** an AI agent reads the playbook to add a story
- **Then** the playbook shows the full command `{BOARD_CMD} add_story "{STORY_ID}" "{title}" "{tasks}"` with all three required arguments

## Target Call Chain

```
pip install pactkit
  → pyproject.toml [project].dependencies  ← R1, R2: trim here
  → pyproject.toml [project.optional-dependencies]  ← R2: add extras here

pactkit spec-lint (playbook invocation)
  → commands.py Plan Phase 3.2d (line 116)  ← R3: add fallback
  → commands.py Act Phase 0.5 (line 153)  ← R3: add fallback
  → commands.py Check Phase 3 (line 282)  ← R3: add fallback
  → workflows.py Sprint Phase 3 (line 743)  ← R3: add fallback

board.py add_story (playbook invocation)
  → commands.py Plan Phase 3.3 (line 122)  ← R4: add full signature
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `pyproject.toml` | Move adapter + tree-sitter to `[project.optional-dependencies]` | None | Medium (downstream install scripts) |
| 2 | `src/pactkit/prompts/commands.py` | Add `python3 -m pactkit spec-lint` fallback to 3 locations | Step 1 | Low |
| 3 | `src/pactkit/prompts/workflows.py` | Add same fallback to Sprint spec-lint call | Step 1 | Low |
| 4 | `src/pactkit/prompts/commands.py` | Fix Plan Phase 3.3 add_story to include full signature | None | Low |
| 5 | `tests/` | Unit tests for optional-dependency isolation | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Changes are to pyproject.toml metadata and prompt template strings, not runtime code paths |
| SEC-2 | N/A | No user input handling changed |
| SEC-3 | N/A | No database operations |
| SEC-4 | N/A | No frontend files |
| SEC-5 | N/A | No auth/session logic |
| SEC-6 | N/A | No API routes |
| SEC-7 | N/A | No error handling changes |
| SEC-8 | Yes | Dependency manifest restructured — verify `pactkit[all]` still resolves correctly; verify no supply-chain risk from removing hard deps |

## Out of Scope

- Adding new adapter packages (e.g., `pactkit-copilot`) — that's a separate story
- Changing the spec_linter.py logic itself — only the invocation path is affected
- CI/CD pipeline changes — downstream install scripts may need updating but are out of scope for this story
- README install instructions update — tracked separately if needed
