# HOTFIX-slim-062: visualize --lazy focus target 'cli' not found

| Field | Value |
|-------|-------|
| Status | Done |

## Background
`run_visualize_graphs` hardcodes `--focus cli` for focus graph refresh. Focus matching in `_build_file_graph` only checks exact path or `/cli` suffix, never matching `src/pactkit/cli.py`.

## Target
- `src/pactkit/lazy_visualize.py:113-120` — hardcoded focus refresh
- `src/pactkit/skills/visualize.py:603` — focus matching logic

## Fix
1. Remove hardcoded focus graph refresh from `run_visualize_graphs` (focus graphs are user-generated, not auto-maintained).
2. Add `f.stem == focus` to focus matching logic as defensive fix.
