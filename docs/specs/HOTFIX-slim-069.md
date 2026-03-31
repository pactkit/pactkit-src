# HOTFIX-slim-069: Fix duplicate edges and cycle false positives in nested call graph

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-069 |
| Status | Done |
| Priority | P2 |

## Background

`_render_nested_call_graph()` (STORY-slim-067) has two rendering bugs: (1) duplicate edges not deduplicated — same caller→callee repeated N times if called N times in function body; (2) cycle detection falsely marks same-depth utility calls (e.g., `nl()`) as ↻ when they are just shared helpers, not true back-edges.

## Fix

- **File**: `src/pactkit/skills/visualize.py:889-927` (`_render_nested_call_graph`)
- **Issue 1**: Deduplicate edges with `Counter`, render count as `-->|×N|` when N > 1
- **Issue 2**: Only mark as cycle when target is an ancestor of source in the BFS tree (depth < source depth AND reachable via forward_reach from target includes source)
