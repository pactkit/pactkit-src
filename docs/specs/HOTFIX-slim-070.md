# HOTFIX-slim-070: Expose --entry/--focus/--reverse in pactkit visualize CLI

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-070 |
| Status | Done |
| Priority | P2 |

## Background

`visualize.py` standalone argparse supports `--entry`, `--focus`, `--reverse`, `--depth`, `--max-nodes` but `pactkit visualize` CLI in `cli.py` only exposes `--lazy`, `--stack`, `--mode`. Users cannot access nested call graph (STORY-slim-067) or reverse trace features from the CLI.

## Fix

- **File 1**: `src/pactkit/cli.py:248-254` — add 5 arguments to viz_parser, pass to `run_visualize_single`
- **File 2**: `src/pactkit/lazy_visualize.py:83-94` — extend `run_visualize_single` signature and subprocess args
