# Spec STORY-060: Fix /project-init Hang — Non-interactive Guard & Scan Limits

## Metadata
| Field | Value |
|-------|-------|
| ID | STORY-060 |
| Title | Fix /project-init Hang — Non-interactive Guard & Scan Limits |
| Status | Draft |
| Priority | P1 |
| Author | System Architect |
| Created | 2026-03-02 |
| Release | 1.6.0 |

## Summary
The `/project-init` command can hang in two scenarios: (1) Phase 0.5 Git Repository Guard issues an interactive prompt that blocks in non-interactive contexts (subagent execution, CI/CD), and (2) Phase 3 Visualize AST scan runs unbounded `rglob + ast.parse` on large repos with no file limit or timeout. Additionally, STORY-047 enterprise flags (`--no-git`, `--no-external`, `--non-interactive`) are parsed by argparse but never forwarded to `deploy()` — they are dead code.

## Background
When running `/project-init` as a Claude Code slash command, Phase 0.5 instructs the agent to "Ask the user: No git repository detected. Initialize one with `git init`?" — in non-interactive contexts this blocks indefinitely. The `visualize.py` `_scan_files()` function does `root.rglob('*.py')` with no file count ceiling, causing perceived hangs on large codebases. The STORY-047 enterprise flags (`--no-git`, `--no-external`, `--non-interactive`) defined in `cli.py:43-61` are silently discarded at `cli.py:128` and never reach `deploy()`.

## Target Call Chain
```
CLI path:   cli.py:main() → deployer.py:deploy()   [flags lost at line 128]
Playbook:   commands.py:PROJECT_INIT_PROMPT → Phase 0.5 (line 702-709) → interactive block
Visualize:  visualize.py:_scan_files() (line 33-58) → rglob → ast.parse (4 passes, unbounded)
```

## Requirements

### R1: Make Phase 0.5 Git Guard Non-interactive by Default
The playbook text in `commands.py` MUST replace the interactive "Ask the user" prompt with auto-detect behavior:
- If inside a git repo → skip silently (no change).
- If NOT a git repo → print a warning and **continue without blocking**. Do NOT prompt the user.
- The playbook MUST NOT contain any "Ask the user" instruction in Phase 0.5.

### R2: Wire Enterprise Flags Through cli.py to deploy()
`cli.py` line 128 MUST pass `no_git`, `no_external`, and `non_interactive` flags from `args` to `deploy()`.

### R3: Accept Enterprise Flags in deploy()
`deployer.py:deploy()` MUST accept `no_git`, `no_external`, and `non_interactive` keyword arguments (with `False` defaults). The function MUST store them for downstream consumption. The `**_kwargs` catch-all MUST be removed.

### R4: Add upgrade Subparser Enterprise Flags
The `upgrade` subparser in `cli.py` MUST define the same `--no-git`, `--no-external`, `--non-interactive` flags as `init` and `update` for consistency.

### R5: Add File Count Ceiling to _scan_files()
`visualize.py:_scan_files()` MUST enforce a maximum file count (default: `MAX_SCAN_FILES = 500`). When the limit is reached, scanning MUST stop and print a warning to stderr: `"⚠️ Scan truncated at {MAX_SCAN_FILES} files. Use --focus <module> to narrow scope."`.

### R6: Narrow Bare Except Clauses
All `except: pass` blocks in `visualize.py` (`_scan_files`, `_build_file_graph`, `_build_class_graph`, `_build_call_graph`, `_scan_call_edges`) MUST be narrowed to `except (SyntaxError, UnicodeDecodeError, ValueError): pass` to avoid swallowing catastrophic errors like `MemoryError`.

## Acceptance Criteria

### AC1: Phase 0.5 Non-interactive
- **Given** the `/project-init` playbook is loaded
- **When** the target directory is NOT a git repository
- **Then** the playbook text instructs the agent to print a warning and continue, without any interactive prompt

### AC2: Enterprise Flags Forwarded
- **Given** a user runs `pactkit init --no-git --non-interactive`
- **When** `cli.py:main()` parses arguments and calls `deploy()`
- **Then** `deploy()` receives `no_git=True` and `non_interactive=True`

### AC3: deploy() Signature Updated
- **Given** the `deploy()` function in `deployer.py`
- **When** called with `no_git=True`, `no_external=True`, `non_interactive=True`
- **Then** the function accepts all three without error and does not use `**_kwargs`

### AC4: upgrade Subparser Parity
- **Given** the `upgrade` subparser in `cli.py`
- **When** a user runs `pactkit upgrade --no-git`
- **Then** argparse accepts the flag without error

### AC5: Scan Truncation
- **Given** a project with more than 500 `.py` files (excluding `SCAN_EXCLUDES`)
- **When** `_scan_files()` is called
- **Then** it returns at most 500 files and prints a warning to stderr

### AC6: Narrow Exception Handling
- **Given** `visualize.py` exception handlers
- **When** a `.py` file triggers a `MemoryError` during `ast.parse()`
- **Then** the error propagates instead of being silently swallowed

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/commands.py` | Rewrite Phase 0.5 text: remove interactive prompt, add auto-skip with warning | None | Low |
| 2 | `src/pactkit/cli.py` | Pass `no_git`, `no_external`, `non_interactive` from args to `deploy()` | None | Low |
| 3 | `src/pactkit/cli.py` | Add enterprise flags to `upgrade` subparser | None | Low |
| 4 | `src/pactkit/generators/deployer.py` | Update `deploy()` signature: add `no_git=False`, `no_external=False`, `non_interactive=False`; remove `**_kwargs` | Step 2 | Low |
| 5 | `src/pactkit/skills/visualize.py` | Add `MAX_SCAN_FILES = 500` and truncation logic in `_scan_files()` | None | Medium |
| 6 | `src/pactkit/skills/visualize.py` | Narrow all `except: pass` to `except (SyntaxError, UnicodeDecodeError, ValueError): pass` | None | Low |
