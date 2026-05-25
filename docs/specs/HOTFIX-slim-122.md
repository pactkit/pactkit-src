# HOTFIX-slim-122: prevent focus/entry mode from overwriting full call_graph.db

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-122 |
| Status | In Progress |
| Priority | P2 |
| Release | 2.13.0 |

## Background

`_build_call_graph()` writes `call_graph.db` unconditionally when `sqlite_output: true`, including when running in `--focus` or `--entry` mode. These modes produce a subgraph (not the full call graph), so writing them to `call_graph.db` overwrites the complete dataset with a partial one.

## Fix

Only write `call_graph.db` when both `focus` and `entry` are falsy (i.e., full graph mode).

- **Target**: `src/pactkit/skills/visualize.py`
- **Line 855**: Add `and not focus` guard (BFS/entry path)
- **Line 891**: Add `and not focus` guard (full graph path with focus filter)
