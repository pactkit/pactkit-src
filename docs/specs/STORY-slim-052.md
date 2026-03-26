# STORY-slim-052: Skill scripts call-chain robustness hardening round 2

| Field | Value |
|-------|-------|
| ID | STORY-slim-052 |
| Status | Done |
| Priority | P1 |
| Release | 2.5.0 |

## Background

Deep call-chain audit of 4 PactKit skill scripts (`board.py`, `scaffold.py`, `spec_linter.py`, `visualize.py`) revealed 20 robustness issues across position arithmetic, regex boundary handling, template rendering, Mermaid output safety, error propagation, and algorithmic performance. These issues range from data-corruption risks (position mismatch in block removal) to silent failures (swallowed exceptions) to O(N×E) performance bottlenecks.

This story addresses all 20 findings grouped by severity: 3 HIGH (data integrity / output corruption), 10 MEDIUM (correctness / edge-case failures), 7 LOW (style / performance / defensive improvements).

## Requirements

### R1: Fix `_mark_done` position mismatch in board.py (MUST)

`_mark_done` builds `story_block` from `story_match.group()` then uses `story_match.start()/end()` to splice the result back into `content`. If string operations on `story_block` change its length (e.g., checkbox replacement), the splice boundaries no longer match, risking content corruption. Fix: derive output position from actual replacement length, not original match span.

### R2: Fix `fix_board` rstrip offset compensation in board.py (MUST)

`_parse_story_blocks` returns `content[start:end].rstrip()` as `block_text`, but `(start, end)` reflects the pre-rstrip range. `fix_board` removes blocks using `(start, end)` offsets but accumulates `len(block_text)` — the rstrip'd length — into `offset`, leaving trailing whitespace undeleted. Fix: use `end - start` (original span) for offset compensation, not `len(block_text)`.

### R3: Fix `update_task` story_pat missing section boundary in board.py (MUST)

`story_pat` regex `(?=\n#{3,4} |\Z)` doesn't match `\n## ` (level-2 section headers). If a story block is the last entry before a `## ` section, the regex overshoots and captures content from the next section. Fix: broaden lookahead to `(?=\n#{2,4} |\Z)`.

### R4: Fix `_parse_story_blocks` position inconsistency in board.py (SHOULD)

The function returns `(block_text.rstrip(), start, end)` where `len(block_text) != end - start`. All callers must know whether to use `block_text` length or span length. Fix: either return the un-rstrip'd text, or adjust `end` to match the rstrip'd length. Document the contract.

### R5: Add atomic write to `update_version` in board.py (SHOULD)

`update_version` (L241) calls `path.write_text()` directly. If the process is interrupted mid-write, the file is corrupted. Fix: use tmp+rename atomic write pattern consistent with other file-writing functions.

### R6: Unify parsing logic — eliminate `re.split` in `archive_stories` in board.py (MAY)

`archive_stories` uses `re.split()` to extract story blocks while all other functions use `_parse_story_blocks`. Dual parsing logic risks divergent behavior. Fix: refactor `archive_stories` to use `_parse_story_blocks`.

### R7: Fix `create_spec` str.format template injection in scaffold.py (MUST)

`create_spec` (L185) uses `_SPEC_TEMPLATE.format(id=i, title=t)`. If `title` contains `{` or `}` characters, Python raises `KeyError` or `ValueError`. This violates Architecture Principle 7 (use sequential `str.replace()`, not `str.format()`). Fix: replace `.format()` with sequential `.replace('{id}', i).replace('{title}', t)`.

### R8: Replace bare except in `_read_developer_prefix` in scaffold.py (SHOULD)

`_read_developer_prefix` (L89) uses `except Exception: pass`, silently swallowing all errors including `PermissionError`, `UnicodeDecodeError`, etc. Fix: catch specific exceptions (`FileNotFoundError`, `KeyError`) and log/warn on unexpected ones.

### R9: Add existence check in `create_prd` in scaffold.py (MAY)

`create_prd` (L283) writes without checking if a PRD already exists, silently overwriting user content. Fix: check `path.exists()` and warn or skip if already present.

### R10: Fix unclosed code fence handling in `_strip_code_blocks` in spec_linter.py (SHOULD)

`_strip_code_blocks` (L79) regex requires paired backtick fences. An unclosed fence leaves everything after it unstripped, causing false-positive lint errors on content that should be ignored. Fix: add a fallback pattern that strips from unclosed fence to EOF.

### R11: Fix pipe-in-cell regex in `_check_metadata` in spec_linter.py (SHOULD)

`_METADATA_ROW` regex uses `(.+?)` which stops at the first `|` character inside a cell value. Metadata values containing pipes (e.g., descriptions with OR conditions) are truncated. Fix: use a non-pipe-greedy pattern or parse cells by splitting on ` | ` delimiter.

### R12: Fix raw/body AC count alignment in spec_linter.py (MAY)

`_check_acceptance_criteria` (L212-227) counts `raw_ac_matches` on full content and `ac_matches` on code-stripped content. If a code block contains an AC-like header (e.g., `### ACN:`), the counts diverge, causing a spurious warning. Fix: count both on the same (stripped) content, or document the intentional discrepancy.

### R13: Extend `_find_section` wrong-level detection in spec_linter.py (MAY)

`_find_section` (L104) only checks for `###` wrong-level headings, missing `#` (level 1) and `####` (level 4) false matches. Fix: check all heading levels that could cause confusion.

### R14: Fix Mermaid double-quote injection in visualize.py (MUST)

`_build_call_graph` (L704) and `_build_file_graph` (L514) emit labels as `["{fn}"]`. If a function or file name contains double quotes, the Mermaid syntax breaks. Fix: escape or strip double quotes in all label strings before emitting.

### R15: Fix O(N×E) `_resolve_callee` performance in visualize.py (MUST)

`_resolve_callee` (L762-768) does a linear scan of all modules for each callee name, called once per edge. For large codebases this is O(N×E). Fix: build a `module_index` dict once (module_name → full_path) and use dict lookup for O(1) resolution.

### R16: Fix `_scan_files` module index collision in visualize.py (SHOULD)

`_scan_files` (L155-168) uses `module_index[module_name] = p` where `module_name` is the stem. Multiple files with the same stem (e.g., `utils.py` in different directories) overwrite each other. Fix: use qualified module names or store a list per key.

### R17: Fix focus graph substring match in visualize.py (SHOULD)

`_build_file_graph` (L551) uses `any(rid in line for rid in relevant_ids)` — substring match instead of exact token match. A file named `auth.py` would match `oauth.py`. Fix: use word-boundary matching or exact ID comparison.

### R18: Fix delayed `_edge_keys` init in `WorkflowGraph` in visualize.py (SHOULD)

`WorkflowGraph.add_edge` (L1020-1023) initializes `_edge_keys` lazily via `hasattr` instead of in `__init__`. This is fragile and violates standard Python object initialization patterns. Fix: initialize `_edge_keys = set()` in `__init__`.

### R19: Fix swallowed exceptions in `regression_workflow_impact` in visualize.py (MAY)

`regression_workflow_impact` (L1881) uses `except Exception: return []`, silently hiding all errors. Fix: catch specific expected exceptions and log unexpected ones before returning the empty fallback.

### R20: Replace BFS `list.pop(0)` with `deque.popleft()` in visualize.py (MAY)

Multiple BFS implementations (L689, 811, 1107, 1124) use `queue.pop(0)` which is O(N) per pop. Fix: use `collections.deque` for O(1) popleft. This is a performance improvement, not a correctness fix.

## Acceptance Criteria

### AC1: _mark_done splice safety (R1)

- **Given** a board with a story block containing a checkbox task `- [ ] Task`
- **When** `_mark_done` replaces the checkbox with `[x]` and splices back into content
- **Then** the surrounding content (before and after the block) is unchanged, and no characters are lost or duplicated

### AC2: fix_board offset compensation (R2)

- **Given** a board with a story block that has trailing whitespace/newlines after the block text
- **When** `fix_board` removes the block using offset compensation
- **Then** the trailing whitespace is fully removed, and subsequent block offsets remain correct

### AC3: update_task section boundary (R3)

- **Given** a board where a story block is immediately followed by a `## ` level-2 section header
- **When** `update_task` matches the story block via `story_pat`
- **Then** the match does NOT extend past the `## ` boundary into the next section

### AC4: parse position contract (R4)

- **Given** `_parse_story_blocks` returns `(block_text, start, end)`
- **When** any caller uses the returned values
- **Then** `len(block_text)` equals `end - start` (no rstrip mismatch)

### AC5: atomic update_version (R5)

- **Given** `update_version` is called with valid content
- **When** the write operation is performed
- **Then** the write uses a tmp+rename atomic pattern (no partial-write risk)

### AC6: unified archive parsing (R6)

- **Given** `archive_stories` processes a board with completed stories
- **When** it extracts story blocks
- **Then** it uses `_parse_story_blocks` (not `re.split`) for consistency with all other board functions

### AC7: scaffold template safety (R7)

- **Given** a story title containing `{curly}` braces
- **When** `create_spec` renders the spec template with this title
- **Then** the title is rendered literally without raising `KeyError` or `ValueError`

### AC8: developer prefix error handling (R8)

- **Given** `_read_developer_prefix` encounters a `PermissionError` or `UnicodeDecodeError`
- **When** the error is caught
- **Then** the error is logged (not silently swallowed) and the function falls back gracefully

### AC9: PRD existence guard (R9)

- **Given** a PRD file already exists at the target path
- **When** `create_prd` is called
- **Then** the function warns the user and does NOT overwrite the existing file

### AC10: unclosed code fence (R10)

- **Given** a spec file with an unclosed code fence (triple backticks without a closing fence)
- **When** `_strip_code_blocks` processes the content
- **Then** everything from the unclosed fence to EOF is stripped, preventing false-positive lint errors

### AC11: pipe in metadata cell (R11)

- **Given** a metadata row with a value containing a pipe character (e.g., `| Description | A | B |`)
- **When** `_check_metadata` parses the row
- **Then** the full cell value (including the pipe) is captured correctly

### AC12: AC count consistency (R12)

- **Given** a spec with a code block that contains an AC-like header (e.g., `### ACN:`)
- **When** `_check_acceptance_criteria` counts AC sections
- **Then** the count is based on code-stripped content only, not raw content

### AC13: wrong-level heading detection (R13)

- **Given** a spec where a required `## Section` is written as `# Section` or `#### Section`
- **When** `_find_section` searches for the section
- **Then** the wrong-level heading is detected and reported (not just `###` level)

### AC14: Mermaid label escaping (R14)

- **Given** a function named `parse"data` or a file with double quotes in its path
- **When** `_build_call_graph` or `_build_file_graph` emits a Mermaid node label
- **Then** double quotes are escaped or stripped so the Mermaid output is syntactically valid

### AC15: callee resolution performance (R15)

- **Given** a codebase with N modules and E edges
- **When** `_resolve_callee` resolves all callees
- **Then** the total resolution time is O(N+E) via dict lookup, not O(N×E) via linear scan

### AC16: module index uniqueness (R16)

- **Given** two files with the same stem (e.g., `pkg_a/utils.py` and `pkg_b/utils.py`)
- **When** `_scan_files` builds the module index
- **Then** both files are indexed (no silent overwrite) using qualified names or list storage

### AC17: exact ID match in focus graph (R17)

- **Given** a file graph with IDs `auth.py` and `oauth.py`
- **When** `_build_file_graph` checks edge relevance for a focus on `auth.py`
- **Then** `oauth.py` is NOT matched (no substring false positive)

### AC18: _edge_keys init in __init__ (R18)

- **Given** a new `WorkflowGraph` instance
- **When** the object is created (before any `add_edge` call)
- **Then** `_edge_keys` is initialized as `set()` in `__init__`, not lazily via `hasattr`

### AC19: regression_workflow_impact error visibility (R19)

- **Given** `regression_workflow_impact` encounters an unexpected error (e.g., `TypeError`)
- **When** the exception is caught
- **Then** the error is logged/warned before returning the empty fallback list

### AC20: BFS deque performance (R20)

- **Given** any BFS traversal in visualize.py (forward_reach, reverse_reach, etc.)
- **When** the queue is used for BFS
- **Then** `collections.deque` is used with `popleft()` instead of `list.pop(0)`

## Target Call Chain

### board.py
```
CLI → move_story → _mark_done → content splice (R1)
CLI → fix_board → _parse_story_blocks → offset loop (R2, R4)
CLI → update_task → story_pat regex → section capture (R3)
CLI → update_version → path.write_text (R5)
CLI → archive_stories → re.split (R6)
```

### scaffold.py
```
CLI → create_spec → _SPEC_TEMPLATE.format(id=, title=) (R7)
CLI → next_id → _read_developer_prefix → except Exception: pass (R8)
CLI → create_prd → path.write_text (R9)
```

### spec_linter.py
```
CLI → lint_spec → _strip_code_blocks → paired-fence regex (R10)
CLI → lint_spec → _check_metadata → _METADATA_ROW regex (R11)
CLI → lint_spec → _check_acceptance_criteria → raw vs body count (R12)
CLI → lint_spec → _find_section → wrong-level detection (R13)
```

### visualize.py
```
CLI → build_call_graph → _build_call_graph → label emit ["{fn}"] (R14)
CLI → build_call_graph → _resolve_callee → linear scan × edges (R15)
CLI → _scan_files → module_index[stem] = p (R16)
CLI → _build_file_graph → substring rid match (R17)
WorkflowGraph.__init__ → (missing _edge_keys) → add_edge hasattr (R18)
CLI → regression_workflow_impact → except Exception: return [] (R19)
forward_reach / reverse_reach → queue.pop(0) (R20)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/board.py` | Fix R1 (_mark_done splice), R2 (rstrip offset), R3 (story_pat boundary), R4 (parse contract), R5 (atomic write), R6 (unify archive parsing) | None | High |
| 2 | `src/pactkit/skills/scaffold.py` | Fix R7 (str.replace), R8 (specific except), R9 (PRD existence check) | None | Medium |
| 3 | `src/pactkit/skills/spec_linter.py` | Fix R10 (unclosed fence), R11 (pipe regex), R12 (AC count), R13 (heading levels) | None | Medium |
| 4 | `src/pactkit/skills/visualize.py` | Fix R14 (Mermaid escape), R15 (dict lookup), R16 (module index), R17 (exact match), R18 (_edge_keys init), R19 (exception logging), R20 (deque) | None | High |
| 5 | `tests/unit/test_story_slim052.py` | Unit tests for all 20 requirements | Steps 1-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modifications in 4 skill scripts |
| SEC-2 | Yes | Input handling: regex patterns, template rendering, file content parsing |
| SEC-3 | No | No database patterns |
| SEC-4 | No | No frontend files |
| SEC-5 | No | No auth patterns |
| SEC-6 | No | No API/route files |
| SEC-7 | Yes | Error handling improvements (R8, R10, R19) |
| SEC-8 | No | No dependency manifests changed |

## Out of Scope

- CLI layer changes (all fixes are in skill script internals)
- New features or behavioral changes — this is a pure robustness/correctness hardening pass
- Performance optimization beyond the specific O(N×E) fix in R15 and deque in R20
- Refactoring skill scripts into smaller files — structural changes are deferred
