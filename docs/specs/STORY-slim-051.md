# STORY-slim-051: Skill scripts robustness hardening

| Field | Value |
|-------|-------|
| ID | STORY-slim-051 |
| Status | Done |
| Priority | P1 |
| Release | 2.5.0 |

## Background

Skill scripts (`board.py`, `scaffold.py`, `spec_linter.py`, `visualize.py`) replaced AI-flexible markdown operations with deterministic Python code. However, the code logic is fragile: exact-match-only lookups, missing existence guards, bare `except: pass`, silent `fix_board()` side-effects, and divergent regex patterns. These issues cause silent data loss (spec/test overwrite on retry), board corruption (wrong block deleted), and misleading error messages — all within normal PDCA workflow usage. Audit identified 18 issues across 4 files (7 High, 7 Medium, 4 Low).

## Requirements

### R1: scaffold `create_spec` existence guard (MUST)

`create_spec` MUST check if `docs/specs/{ID}.md` exists before writing. If it exists, return `"❌ Spec already exists"` without overwriting. Same guard pattern as `create_board()` and `create_skill()` in the same file. (SCAFFOLD-2)

### R2: scaffold `create_test_file` and `create_e2e` existence guard (MUST)

Both functions MUST check if the target test file exists before writing. If it exists, return `"❌ Test file already exists"`. Prevents irreversible loss of authored test code on AI retry. (SCAFFOLD-4)

### R3: scaffold `git_start` error handling (MUST)

Replace bare `except: pass` with proper error handling. If `git checkout -b` fails, return `"❌ Branch creation failed: {reason}"` instead of `"✅"`. Distinguish between "branch already exists" (non-fatal) and real errors (dirty worktree, not a git repo). (SCAFFOLD-1)

### R4: board `_write_board` stop calling `fix_board()` unconditionally (MUST)

Remove the unconditional `fix_board()` call from `_write_board()`. `fix_board` is a heavy restructuring operation that should only run explicitly, not as a side-effect of every task update. If retained, its return value MUST be checked and errors propagated. (BOARD-7)

### R5: board `fix_board` and `move_story` position-aware block removal (MUST)

Replace `str.find(block_text)` with position-aware removal using the match indices from `_parse_story_blocks`. When removing a block, use its known `(start, end)` position in the original content, not a substring search that can match the wrong occurrence. (BOARD-1, BOARD-2)

### R6: board `add_story` duplicate guard (MUST)

`add_story` MUST check if `{sid}` already exists on the board before inserting. If it exists, return `"❌ Story {sid} already on board"`. (BOARD-5)

### R7: board `archive_stories` use `ITEM_ID_RE` (SHOULD)

Replace the hardcoded regex in `archive_stories` with a pattern derived from `ITEM_ID_RE` to ensure new ID prefixes are automatically supported. (BOARD-4)

### R8: board `update_version` scope to top-level (SHOULD)

Limit the `re.sub` to only match the first/top-level `version:` key in `pactkit.yaml`, not nested `version:` fields. Use a more specific pattern or match only the first occurrence. (BOARD-6)

### R9: board `_parse_story_blocks` return position indices (SHOULD)

Return `(sid, block_text, start, end)` tuples so callers can use position-based removal instead of `str.find()`. This is a prerequisite for R5. (BOARD-3)

### R10: spec_linter `_find_section` heading-level tolerance (SHOULD)

When `## Heading` is not found but `### Heading` exists, report a specific warning (`"Section 'X' found at wrong heading level (### instead of ##)"`) instead of the misleading `"Missing section"` error. (LINT-1)

### R11: spec_linter `validate_spec` error handling and file filtering (SHOULD)

Wrap `read_text()` in `try/except FileNotFoundError`. When running `--all`, filter to files matching `ITEM_ID_RE` pattern only (skip `TEMPLATE.md`, `README.md`). (LINT-3)

### R12: spec_linter `_check_metadata` separator row filtering (MAY)

Filter out separator rows (`|---|---|`) from the parsed fields dict so `fields` only contains real metadata entries. (LINT-2)

### R13: visualize `_build_bridge_edges` exact node-ID matching (SHOULD)

Replace `if skill_id in file_path_str` substring match with exact node-ID comparison or path-suffix matching to prevent false bridge edges (e.g., "auth" matching "oauth2_client.py"). (VIZ-2)

### R14: visualize reverse call graph output path (MAY)

When `reverse=True` and no `focus`, write to `reverse_call_graph.mmd` instead of overwriting `call_graph.mmd`. (VIZ-1)

### R15: visualize `workflow_impact` full node list (MAY)

When entry not found, show all available nodes (or suggest `--list-nodes`) instead of truncating to 20. (VIZ-3)

### R16: visualize silent YAML fallback warning (SHOULD)

When `pactkit.yaml` parse fails due to missing `pyyaml`, log a visible warning instead of silent `except: pass`. (VIZ-4)

### R17: scaffold `_inject_developer_prefix` stricter validation (MAY)

Validate that `rest` after prefix split is either pure numeric or matches `{known_dev}-{NNN}` pattern. Reject ambiguous inputs. (SCAFFOLD-3)

## Acceptance Criteria

### AC1: create_spec does not overwrite existing spec (R1)

- **Given** a spec file `docs/specs/STORY-slim-099.md` already exists with content
- **When** `create_spec("STORY-slim-099", "title")` is called
- **Then** the function returns an error message containing "already exists" and the file content is unchanged

### AC2: create_test_file does not overwrite existing tests (R2)

- **Given** a test file `tests/unit/test_story_slim099.py` exists with real test code
- **When** `create_test_file("STORY-slim-099")` is called
- **Then** the function returns an error message and the file content is unchanged

### AC3: create_e2e does not overwrite existing e2e tests (R2)

- **Given** an e2e file `tests/e2e/test_e2e_story_slim099.py` exists
- **When** `create_e2e("STORY-slim-099", "description")` is called
- **Then** the function returns an error message and the file content is unchanged

### AC4: git_start reports branch failure (R3)

- **Given** `git checkout -b` will fail (e.g., branch exists or dirty worktree)
- **When** `git_start("STORY-slim-099")` is called
- **Then** the function returns a message containing `"❌"` with the failure reason, not `"✅"`

### AC5: _write_board does not call fix_board (R4)

- **Given** `_write_board` is called via `update_task`
- **When** a task is marked done
- **Then** `fix_board()` is NOT called as a side-effect (verified by source inspection or mock)

### AC6: fix_board uses position-based removal (R5)

- **Given** a board with two stories that have similar block text
- **When** `fix_board()` relocates stories
- **Then** each story block is removed by its known position, not `str.find()`, and both stories survive correctly

### AC7: move_story uses position-based removal (R5)

- **Given** a board with a story to move
- **When** `move_story(sid, target)` is called
- **Then** the story is removed by its parsed position, not `str.find()`

### AC8: add_story rejects duplicates (R6)

- **Given** `STORY-slim-099` already exists on the board
- **When** `add_story("STORY-slim-099", "title", "task")` is called
- **Then** the function returns an error containing "already on board" and the board is unchanged

### AC9: archive_stories uses ITEM_ID_RE (R7)

- **Given** `archive_stories` splits board content to find story blocks
- **When** the split regex is examined
- **Then** it uses `ITEM_ID_RE` (or a pattern derived from it), not a hardcoded `STORY|HOTFIX|BUG` string

### AC10: update_version scoped to top-level (R8)

- **Given** a `pactkit.yaml` with a top-level `version: 2.4.0` and a nested `tools.version: 1.0`
- **When** `update_version("2.5.0")` is called
- **Then** only the top-level `version` is changed to `2.5.0`; the nested `tools.version` remains `1.0`

### AC11: _parse_story_blocks returns positions (R9)

- **Given** a board with multiple stories
- **When** `_parse_story_blocks(content)` is called
- **Then** each result tuple includes `(sid, block_text, start_pos, end_pos)`

### AC12: spec_linter detects wrong heading level (R10)

- **Given** a spec with `### Security Scope` instead of `## Security Scope`
- **When** `validate_spec` is run
- **Then** the error message mentions "wrong heading level" rather than "Missing section"

### AC13: spec_linter handles missing files and filters non-specs (R11)

- **Given** `docs/specs/` contains `TEMPLATE.md` alongside real specs
- **When** `spec_linter --all` is run
- **Then** `TEMPLATE.md` is skipped, and a deleted spec does not crash the run

### AC14: metadata parser filters separator rows (R12)

- **Given** a spec with a `|-------|-------|` separator row
- **When** `_check_metadata` parses the metadata table
- **Then** the separator row is not included in the `fields` dict

### AC15: bridge edges use exact matching (R13)

- **Given** a skill node named "auth" and source files `oauth2_client.py`, `auth_handler.py`
- **When** `_build_bridge_edges` runs
- **Then** only `auth_handler.py` gets a bridge edge, not `oauth2_client.py`

### AC16: reverse call graph has separate output (R14)

- **Given** `visualize --mode call --entry foo --reverse` is run
- **When** the output is written
- **Then** it writes to `reverse_call_graph.mmd`, not overwriting `call_graph.mmd`

### AC17: workflow_impact shows full node list (R15)

- **Given** a workflow graph with 50+ nodes and an invalid entry ID
- **When** `workflow_impact --entry invalid` runs
- **Then** all available node IDs are shown (or a hint to list them), not truncated to 20

### AC18: YAML parse failure logs warning (R16)

- **Given** `pyyaml` is not available or `pactkit.yaml` is malformed
- **When** `_load_scan_excludes` or `_detect_stack` runs
- **Then** a visible warning is logged (not silent `pass`)

### AC19: developer prefix injection validates rest segment (R17)

- **Given** developer prefix is `slim` and input is `STORY-slim2-001`
- **When** `_inject_developer_prefix` runs
- **Then** it does NOT produce `STORY-slim-slim2-001`; it either passes through unchanged or rejects the ambiguous input

## Target Call Chain

```
src/pactkit/skills/
  ├── board.py      → add_story, update_task, move_story, fix_board, archive_stories,
  │                    update_version, _parse_story_blocks, _write_board
  ├── scaffold.py   → create_spec, create_test_file, create_e2e, git_start,
  │                    _inject_developer_prefix
  ├── spec_linter.py → validate_spec, _find_section, _check_metadata, main
  └── visualize.py  → _build_bridge_edges, workflow_impact, visualize,
                       _load_scan_excludes, _detect_stack
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/scaffold.py` | Add existence guards to `create_spec`, `create_test_file`, `create_e2e` (R1, R2). Fix `git_start` error handling (R3). Validate `_inject_developer_prefix` (R17). | None | Low |
| 2 | `src/pactkit/skills/board.py` | Refactor `_parse_story_blocks` to return positions (R9). Update `fix_board` and `move_story` to use position-based removal (R5). Remove `fix_board()` from `_write_board` (R4). Add duplicate guard to `add_story` (R6). Scope `update_version` (R8). Use `ITEM_ID_RE` in `archive_stories` (R7). | None | Medium |
| 3 | `src/pactkit/skills/spec_linter.py` | Add heading-level tolerance (R10). Add file filtering and error handling (R11). Filter separator rows (R12). | None | Low |
| 4 | `src/pactkit/skills/visualize.py` | Fix `_build_bridge_edges` matching (R13). Add reverse output path (R14). Expand node list in error (R15). Add YAML warning (R16). | None | Low |
| 5 | `tests/unit/test_story_slim051.py` | Tests for all 19 ACs | Steps 1-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | Internal tool robustness, no user input handling changes |
| SEC-2 | N/A | No authentication/authorization changes |
| SEC-3 | N/A | No data storage changes |
| SEC-4 | N/A | No API endpoint changes |
| SEC-5 | N/A | No dependency changes |
| SEC-6 | Applicable | File existence checks added to prevent unintended overwrites (improvement) |
| SEC-7 | N/A | No network operations added |
| SEC-8 | N/A | No credential handling changes |

## Out of Scope

- Rewriting board.py to use a structured data format (YAML/JSON) instead of markdown parsing — that is a separate architectural decision
- Adding transactional rollback to board operations — out of proportion for the current issue
- Performance optimization of `fix_board` — this story only addresses correctness
