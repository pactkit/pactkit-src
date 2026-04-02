# HOTFIX-slim-023: Add --mode argument to pactkit visualize CLI

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-023 |
| Status | Draft |
| Priority | P1 |
| Release | 2.3.2 |

## Background
`pactkit visualize --mode class` and `--mode call` fail with "unrecognized arguments" because the CLI subcommand parser only defines `--lazy` and `--stack`, not `--mode`.

## Target
- `src/pactkit/cli.py` lines 241-248 (parser) and 431-448 (handler)

## Fix
- Add `--mode` argument with choices `file`, `class`, `call` (default: all three)
- In non-lazy mode: execute `run_visualize_graphs` or single-mode run based on `--mode`
- In lazy mode: pass `--mode` through to control which modes run
