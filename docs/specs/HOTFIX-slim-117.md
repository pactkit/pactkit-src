# HOTFIX-slim-117: Fix Graph Query Protocol grep patterns for code_graph.mmd

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-117 |
| Status | Done |
| Release | 2.14.0 |

## Background

Graph Query Protocol (added in STORY-slim-116) uses `grep " --> deployer"` and `grep "deployer --> "` to filter edges in `code_graph.mmd`. However, nodes in `code_graph.mmd` are sanitized IDs (`src_pactkit_generators_deployer_py`), not bare filenames. These patterns never match — silent no-op. Correct patterns require `.*` wildcard: `grep " --> .*deployer"` (fan-in) and `grep "deployer.* --> "` (fan-out).

Same issue in `project-act.md` Phase 3 importer-count: `grep " --> <file>"` → `grep " --> .*<file>"`.

## Target Files

- `src/pactkit/prompts/skills.py` — SKILL_VISUALIZE_MD lines 93, 96, 99
- `src/pactkit/prompts/commands.py` — project-act.md Phase 3 line 237
