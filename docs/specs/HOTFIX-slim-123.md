# HOTFIX-slim-123: call_graph.db dedup edges and filter orphan nodes

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-123 |
| Status | Done |
| Priority | P1 |

## Background

`_write_sqlite_db()` had two data quality issues: (1) duplicate edges (35.8% in pactsearch) because `rel_edges` was inserted without dedup, and (2) orphan edges referencing nodes not in `func_registry` (e.g., `__module__` synthetic callers).

## Fix

- Target: `src/pactkit/skills/visualize.py:_write_sqlite_db()`
- Dedup `rel_edges` via set conversion before INSERT
- Filter edges to only include caller/callee pairs where both exist in `func_registry`
