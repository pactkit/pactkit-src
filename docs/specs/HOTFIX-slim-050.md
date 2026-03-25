# HOTFIX-slim-050: Auto-split unified graph only for large projects

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-050 |
| Status | Done |

## Background

STORY-slim-049 `--split` always generates focus sub-graphs regardless of graph size. Small projects don't need splitting — the full graph is already human-readable.

## Fix

Target: `src/pactkit/skills/visualize.py:889` — change `if split:` to `if split or len(graph.nodes) > MAX_WORKFLOW_NODES:`, so focus graphs are auto-generated for large projects (>500 nodes) and only on explicit `--split` for small ones.
