# STORY-slim-100: Hotfix impact check via .mmd call graph

| Field | Value |
|-------|-------|
| ID | STORY-slim-100 |
| Status | Done |
| Priority | P1 |
| Release | 2.10.4 |

## Background

The `/project-hotfix` playbook locates target code via `Grep`/`Glob` (Phase 0) and immediately proceeds to fix (Phase 1) without consulting the project's `.mmd` call graph files. This means "No Side Effects" (Phase 1.3) is enforced purely by AI judgment, not data. In contrast, `/project-act` uses `pactkit-trace` (Phase 1) and `code_graph.mmd` importer counts (Phase 3) to detect high-fan-in functions before modifying them. A hotfix that changes a function with 5+ callers can silently break upstream consumers.

## Requirements

### R1: Lightweight Impact Check Phase (MUST)

Insert a new **Phase 0.5: Impact Check** between Phase 0 (Locate & Register) and Phase 1 (Fix) in the `HOTFIX_PROMPT`. This phase reads existing `.mmd` call graph files (`call_graph.mmd`, `reverse_call_graph.mmd`, or `code_graph.mmd`) to identify callers of the target function/file.

### R2: High-Fan-In Warning (SHOULD)

If the target function/file has **3+ callers** in the call graph, the playbook SHOULD warn the user about potential impact scope and suggest considering `/project-act` for the full PDCA workflow.

### R3: Graceful Degradation (MUST)

If `.mmd` files do not exist in `docs/architecture/graphs/`, the impact check MUST skip silently with a log message ("No call graph available — skipping impact check"). This preserves hotfix's lightweight nature for projects without visualize data.

### R4: Non-Blocking (MUST)

The impact check MUST NOT block the hotfix workflow — it is advisory only (L3 signal). The user can acknowledge the warning and proceed.

## Acceptance Criteria

### AC1: Impact Check Phase Exists in Prompt (R1)

- **Given** the `HOTFIX_PROMPT` string in `workflows.py`
- **When** the prompt text is inspected
- **Then** it contains "Phase 0.5" and "Impact Check" and references `.mmd` call graph files

### AC2: High-Fan-In Warning Text Present (R2)

- **Given** the `HOTFIX_PROMPT` string
- **When** the prompt text is inspected
- **Then** it contains a threshold (e.g., "3+ callers") and a suggestion to consider `/project-act`

### AC3: Graceful Skip When No Graphs (R3)

- **Given** the `HOTFIX_PROMPT` string
- **When** the prompt text is inspected
- **Then** it contains instructions to skip silently if `.mmd` files do not exist

### AC4: Non-Blocking Advisory Signal (R4)

- **Given** the `HOTFIX_PROMPT` string
- **When** the prompt text is inspected
- **Then** the impact check is described as advisory (not a gate), and the phase does not use "MUST STOP" or blocking language

## Target Call Chain

`HOTFIX_PROMPT` (workflows.py:543) → imported by `commands.py:3` → registered in `COMMANDS_CONTENT["project-hotfix.md"]` (commands.py:750) → deployed by `deployer.py` via `_render_prompt()` → output to `pactkit-plugin/commands/project-hotfix.md` and `.github/prompts/project-hotfix.prompt.md`

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/workflows.py` | Add Phase 0.5 Impact Check text to `HOTFIX_PROMPT` between Phase 0 and Phase 1 | None | Low |
| 2 | `tests/unit/test_hotfix_command.py` | Add test class verifying Phase 0.5 keywords exist in prompt | Step 1 | Low |
| 3 | Deploy verification | Run `pactkit deploy` and verify `pactkit-plugin/commands/project-hotfix.md` contains the new phase | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Prompt text only, no executable injection surface |
| SEC-2 | N/A | No user input processing — playbook instruction text |
| SEC-3 | N/A | No database patterns |
| SEC-4 | N/A | No frontend files |
| SEC-5 | N/A | No auth/session handling — false positive on keyword match |
| SEC-6 | N/A | No API/route files |
| SEC-7 | N/A | No error handling patterns |
| SEC-8 | N/A | No dependency manifests |

## Out of Scope

- Full `pactkit-trace` integration (too heavy for hotfix; Act already handles it)
- Updating `code_graph.mmd` or `call_graph.mmd` during hotfix (hotfix is read-only on graphs)
- Blocking hotfix workflow based on impact check results
