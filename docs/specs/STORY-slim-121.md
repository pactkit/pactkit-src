# STORY-slim-121: call graph SQLite output with pactkit query CLI

| Field | Value |
|-------|-------|
| ID | STORY-slim-121 |
| Status | Done |
| Priority | P1 |
| Release | 2.13.0 |

## Background

`pactkit visualize --mode call` currently outputs only a `.mmd` Mermaid file. Querying the call graph requires `grep` against the Mermaid text, which only supports single-hop exact-string matching and cannot express multi-hop traversal, fan-in aggregation, or transitive dependency chains. This story adds two complementary capabilities: (1) an optional SQLite output (`visualize.sqlite_output: true` in `pactkit.yaml`) that persists the call graph as a queryable database, and (2) a `pactkit query` CLI subcommand that wraps common graph queries (fan-in, fan-out, transitive chain) so developers and AI agents don't need to write raw SQL. Default behavior is unchanged — `.mmd` only.

## Requirements

### R1: pactkit.yaml toggle (MUST)

`pactkit.yaml` MUST support a new field `visualize.sqlite_output: true/false` (default: `false`). When `false`, behavior is identical to the current version — only `.mmd` is written. The field MUST be serialized by `_write_pactkit_yaml()` and included in `get_default_config()`.

### R2: SQLite output on call graph generation (MUST)

When `visualize.sqlite_output: true`, `visualize --mode call` MUST write `docs/architecture/graphs/call_graph.db` alongside the existing `.mmd` file. The database MUST contain:
- `nodes` table: `id TEXT PRIMARY KEY, file TEXT, kind TEXT`
- `edges` table: `caller TEXT, callee TEXT`
- Index on `edges(callee)` for fan-in queries
- Index on `edges(caller)` for fan-out queries

The `.db` file MUST be regenerated atomically (write to `.tmp` then rename).

### R3: .gitignore exclusion (MUST)

`*.db` MUST be added to `.gitignore` (or the project's gitignore) automatically when SQLite output is first enabled — binary files MUST NOT be committed to git.

### R4: `pactkit query` CLI subcommand (MUST)

`src/pactkit/cli.py` MUST register a new `query` subparser with the following interface:

```
pactkit query --callers <func>          # fan-in: who calls <func>
pactkit query --callees <func>          # fan-out: what <func> calls
pactkit query --chain <func>            # transitive: all upstream callers (recursive CTE)
pactkit query --chain <func> --down     # transitive: all downstream callees
```

- MUST read `call_graph.db` from `docs/architecture/graphs/call_graph.db` (relative to project root)
- MUST fail with a clear message if `call_graph.db` does not exist, instructing the user to enable `visualize.sqlite_output: true` and re-run `pactkit visualize --mode call`
- MUST output one result per line (plain text, no formatting)
- MAY support `--db <path>` to override the default db path

### R5: SKILL.md Graph Query Protocol updated (MUST)

`SKILL_VISUALIZE_MD` in `src/pactkit/prompts/skills.py` MUST be updated so the Graph Query Protocol checks `call_graph.db` existence (not `pactkit.yaml`) to decide query method:

```
If docs/architecture/graphs/call_graph.db exists:
  → use: pactkit query --callers <func>
  → use: pactkit query --callees <func>
  → use: pactkit query --chain <func>
Else (mmd-only mode):
  → use: grep " --> .*<func>" docs/architecture/graphs/call_graph.mmd
```

The db file's existence is self-evident — no config check needed at query time.

### R6: No performance regression (SHOULD)

SQLite write MUST reuse the `func_registry` and `call_edges` already in memory — MUST NOT re-parse source files a second time. `pactkit query` reads from the pre-built `.db` file only — no re-scan.

## Acceptance Criteria

### AC1: Default behavior unchanged (R1)

- **Given** `visualize.sqlite_output` is absent or `false` in `pactkit.yaml`
- **When** `visualize --mode call` runs on any project
- **Then** only `call_graph.mmd` is written; no `.db` file is created

### AC2: SQLite file created when enabled (R2)

- **Given** `visualize.sqlite_output: true` in `pactkit.yaml`
- **When** `visualize --mode call` runs
- **Then** `docs/architecture/graphs/call_graph.db` exists with `nodes` and `edges` tables populated; edge count matches the number of resolved edges in the `.mmd` output

### AC3: Fan-in query returns correct callers (R2)

- **Given** `call_graph.db` has been generated for a project with known call relationships
- **When** `sqlite3 call_graph.db "SELECT caller FROM edges WHERE callee LIKE '%atomic_write%'"` is run
- **Then** all callers of `atomic_write` are returned (matches grep output against `.mmd`)

### AC4: Multi-hop recursive query works (R2)

- **Given** `call_graph.db` has been generated
- **When** a recursive CTE query (`WITH RECURSIVE chain ...`) is run to find all transitive callers of a function
- **Then** the query returns results without error and is a superset of single-hop fan-in results

### AC5: .gitignore updated (R3)

- **Given** SQLite output is enabled and `call_graph.db` is generated
- **When** `git status` is run in the project
- **Then** `call_graph.db` does NOT appear as an untracked file (`.gitignore` excludes `*.db` or the specific path)

### AC7: fan-in query via pactkit query (R4)

- **Given** `call_graph.db` exists with known edges (e.g., A → B, C → B)
- **When** `pactkit query --callers B` is run
- **Then** stdout contains `A` and `C`, one per line; exit code 0

### AC8: fan-out query via pactkit query (R4)

- **Given** `call_graph.db` exists with known edges (e.g., A → B, A → C)
- **When** `pactkit query --callees A` is run
- **Then** stdout contains `B` and `C`, one per line; exit code 0

### AC9: transitive chain query (R4)

- **Given** `call_graph.db` exists with chain A → B → C
- **When** `pactkit query --chain C` (upstream) is run
- **Then** stdout contains both `A` and `B`; `pactkit query --chain A --down` contains both `B` and `C`

### AC10: missing db gives helpful error (R4)

- **Given** `call_graph.db` does not exist
- **When** `pactkit query --callers foo` is run
- **Then** exit code 1; stderr contains instruction to enable `visualize.sqlite_output` and re-run visualize

### AC11: SKILL.md updated with db-existence check (R5)

- **Given** `src/pactkit/prompts/skills.py` has been updated
- **When** `SKILL_VISUALIZE_MD` is read
- **Then** the Graph Query Protocol checks whether `call_graph.db` exists (not pactkit.yaml) — if exists: use `pactkit query`; else: use grep fallback

### AC12: No extra source scan on SQLite write (R6)

- **Given** SQLite output is enabled
- **When** `visualize --mode call` completes
- **Then** `_write_sqlite_db` receives `func_registry` and `rel_edges` already computed by `_build_call_graph` — no second call to `extract_functions_and_calls` occurs

### AC6: config round-trips through yaml (R1)

- **Given** `visualize.sqlite_output: true` in `pactkit.yaml`
- **When** `load_config()` is called
- **Then** `config['visualize']['sqlite_output']` is `True`; `get_default_config()['visualize']['sqlite_output']` is `False`

## Target Call Chain

**Write path (visualize):**
```
visualize() [visualize.py:main entry]
  └── _build_call_graph(root, all_files, focus, entry, analyzer)  [visualize.py:739]
        ├── builds func_registry {qualified_name → file}
        ├── builds call_edges {caller → [callees]}
        ├── _resolve_callee() for each edge
        ├── _atomic_mmd_write(dest, content)  [visualize.py:18]
        └── [NEW] if _load_sqlite_config(root):
                    _write_sqlite_db(graphs_dir / 'call_graph.db', func_registry, rel_edges)
                      └── sqlite3.connect(.tmp) → CREATE TABLE → INSERT → COMMIT → rename

```

**Query path (pactkit query):**
```
main() [cli.py] → query subcommand
  └── _query_command(args) [cli.py, NEW]
        └── _run_query(db_path, mode, func, down=False) [NEW module or inline]
              ├── fan-in:  SELECT caller FROM edges WHERE callee LIKE '%{func}%'
              ├── fan-out: SELECT callee FROM edges WHERE caller LIKE '%{func}%'
              └── chain:   WITH RECURSIVE ... SELECT DISTINCT node FROM chain
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/config.py` | Add `sqlite_output: false` to `visualize` section in `get_default_config()`; serialize in `_write_pactkit_yaml()` | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Add `_load_sqlite_config(root)` helper (same pattern as `_load_scan_excludes`) | Step 1 | Low |
| 3 | `src/pactkit/skills/visualize.py` | Add `_write_sqlite_db(db_path, func_registry, rel_edges)` — atomic write via `.tmp` rename; CREATE TABLE nodes + edges + indexes | None | Low |
| 4 | `src/pactkit/skills/visualize.py` | In `_build_call_graph()` both return paths, after `_atomic_mmd_write`, call `_write_sqlite_db` if `_load_sqlite_config(root)` is true | Steps 2,3 | Low |
| 5 | `src/pactkit/cli.py` | Add `query` subparser with `--callers`, `--callees`, `--chain`, `--down`, `--db` args; implement `_query_command(args)` with fan-in/fan-out/chain SQL; helpful error when db missing | Steps 3,4 | Low |
| 6 | `src/pactkit/prompts/skills.py` | Update `SKILL_VISUALIZE_MD` Graph Query Protocol: add `pactkit query` as primary path when sqlite enabled; keep grep as mmd-only fallback | Step 5 | Low |
| 7 | `.gitignore` | Add `*.db` exclusion | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Path Traversal | Yes | `db_path` is constructed from `root` + fixed relative path — verify no `..` escape; use `Path.resolve()` |
| SEC-2 SQL Injection | N/A | All data is project-internal qualified function names from AST; no user input enters SQL |
| SEC-3 Secrets | N/A | No credentials involved |
| SEC-4 Auth | N/A | Local file only |
| SEC-5 Input Validation | Low | `visualize.sqlite_output` is a boolean — coerce to bool, don't eval |
| SEC-6 XSS | N/A | No web interface |
| SEC-7 CSRF | N/A | No web interface |
| SEC-8 Dependency | N/A | `sqlite3` is Python standard library, no new dependency |

## Out of Scope

- SQLite output for file graph or class graph modes — call graph only in this story
- Automatic `.gitignore` injection at runtime — `*.db` is added to `.gitignore` manually as part of this story
- Module-level coupling statistics (GROUP BY queries) — future story
- `pactkit query` result formatting (JSON/table output) — plain text only in this story
