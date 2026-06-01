# STORY-slim-126: codegraph sync code enforcement

| Field | Value |
|-------|-------|
| ID | STORY-slim-126 |
| Status | Done |
| Priority | P1 |
| Release | 2.15.0 |

## Background

`codegraph sync` is currently enforced only via prompt instructions in 4 PDCA skill templates (Act Phase 4, Done Phase 2, Hotfix Phase 3.6, Plan Phase 1 auto-setup). This violates the "Code Enforces, Prompt Instructs" principle — if the AI ignores the prompt instruction, the codegraph index becomes stale and `pactkit query` returns outdated results.

The fix: integrate `codegraph sync` into the `pactkit visualize --lazy` code path so it runs automatically whenever source files changed. Remove the corresponding prompt instructions afterward.

## Requirements

### R1: Auto-sync codegraph in visualize path (MUST)

When `pactkit visualize --lazy` determines that source files changed (should_visualize returns True) AND `.codegraph/` directory exists in project root AND `codegraph` is on `$PATH`, automatically run `codegraph sync` after graph generation completes.

### R2: Standalone sync function (MUST)

Extract a reusable `codegraph_sync(project_root)` function in `lazy_visualize.py` that:
- Checks `.codegraph/` exists
- Checks `codegraph` binary is available via `shutil.which`
- Runs `codegraph sync <path>` with subprocess
- Returns a status tuple: `(synced: bool, message: str)`
- Fails silently (returns False + reason) when codegraph is unavailable

### R3: CLI integration for non-visualize paths (MUST)

Add `--sync` flag to `pactkit visualize` that forces codegraph sync even when `--lazy` skips graph regeneration. This covers the Hotfix use case where visualize is not run but codegraph still needs syncing.

Also: expose `pactkit sync` as a standalone subcommand that only runs codegraph sync (no mermaid graphs). This is the minimal replacement for prompt instructions in Hotfix flow.

### R4: Remove prompt instructions (MUST)

Remove all "If `.codegraph/` exists, run `codegraph sync`" instructions from:
- `commands.py:248` (Act Phase 4)
- `commands.py:505` (Done Phase 2)
- `workflows.py:614` (Hotfix Phase 3.6)

Replace with a note that `pactkit visualize --lazy` and `pactkit sync` handle this automatically.

### R5: Output feedback (SHOULD)

When codegraph sync runs, print a brief status line: `"🔄 codegraph synced (N files updated)"` or `"codegraph: skipped (not installed)"`. Silent when `.codegraph/` doesn't exist (user hasn't opted in).

## Acceptance Criteria

### AC1: visualize --lazy triggers codegraph sync when source changed (R1)

- **Given** project has `.codegraph/` directory and `codegraph` is on PATH
- **When** `pactkit visualize --lazy` runs and source files have changed
- **Then** `codegraph sync` is executed after mermaid graph generation, output includes sync status

### AC2: visualize --lazy skips codegraph sync when no .codegraph/ (R1, R2)

- **Given** project does NOT have `.codegraph/` directory
- **When** `pactkit visualize --lazy` runs
- **Then** no codegraph sync is attempted, no error is raised

### AC3: codegraph_sync returns gracefully when binary missing (R2)

- **Given** project has `.codegraph/` directory but `codegraph` is NOT on PATH
- **When** `codegraph_sync(project_root)` is called
- **Then** returns `(False, "codegraph not installed")` without raising

### AC4: pactkit sync standalone command (R3)

- **Given** project has `.codegraph/` and `codegraph` on PATH
- **When** user runs `pactkit sync`
- **Then** codegraph sync runs and reports status

### AC5: prompt instructions removed (R4)

- **Given** the updated codebase
- **When** `grep -rn "codegraph sync" src/pactkit/prompts/` is run
- **Then** zero matches for "If .codegraph/ exists, run codegraph sync" pattern (only informational references like skills.py docs remain)

### AC6: output feedback on sync (R5)

- **Given** project has `.codegraph/` and codegraph is on PATH
- **When** `pactkit visualize --lazy` runs and triggers sync
- **Then** stdout includes a status line like "🔄 codegraph synced" or "codegraph: skipped (not installed)"

## Target Call Chain

```
CLI main() → args.command == "visualize"
  → lazy_visualize.should_visualize()
  → run_visualize_graphs() / run_visualize_single()
  → [NEW] codegraph_sync(project_root)
      → shutil.which("codegraph")
      → subprocess.run(["codegraph", "sync", str(project_root)])

CLI main() → args.command == "sync"  [NEW]
  → codegraph_sync(project_root)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/lazy_visualize.py` | Add `codegraph_sync(project_root) -> tuple[bool, str]` function | None | Low |
| 2 | `src/pactkit/lazy_visualize.py` | Call `codegraph_sync()` at end of `run_visualize_graphs()` and `run_visualize_single()` | Step 1 | Low |
| 3 | `src/pactkit/cli.py` | Add `sync` subcommand that calls `codegraph_sync()` | Step 1 | Low |
| 4 | `src/pactkit/cli.py` | In `visualize` handler, call `codegraph_sync()` after lazy check passes | Step 1 | Low |
| 5 | `src/pactkit/prompts/commands.py` | Remove "If .codegraph/ exists, run codegraph sync" from Act & Done prompts | None | Low |
| 6 | `src/pactkit/prompts/workflows.py` | Remove Hotfix Phase 3.6 codegraph sync prompt instruction | None | Low |
| 7 | `tests/unit/` | Unit tests for `codegraph_sync()` with mocked subprocess | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | No user input — project_root from cwd |
| SEC-2 Authentication | N/A | Local CLI tool |
| SEC-3 Authorization | N/A | Local CLI tool |
| SEC-4 Data Exposure | N/A | No secrets involved |
| SEC-5 Injection | N/A | subprocess uses list args, not shell=True |
| SEC-6 Dependencies | N/A | No new dependencies |
| SEC-7 Cryptography | N/A | Not applicable |
| SEC-8 Logging | N/A | No sensitive data logged |

## Out of Scope

- codegraph MCP server auto-start (out of scope — user manages MCP servers independently)
- codegraph init auto-setup (already handled in Plan Phase 1 prompt, keep as-is)
- Modifying `pactkit query` behavior (already works correctly)
