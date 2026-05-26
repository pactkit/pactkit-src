# STORY-slim-124: codegraph integration — read .codegraph/codegraph.db as graph provider

| Field | Value |
|-------|-------|
| ID | STORY-slim-124 |
| Status | Done |
| Priority | P1 |
| Release | 2.14.0 |

## Background

pactkit-visualize's `call_graph.db` has fundamental data quality limitations: suffix-match resolution produces 62% fewer edges than codegraph (2483 vs 6580 in pactsearch), cannot resolve instance method calls, and has no type information. codegraph (`@colbymchenry/codegraph`) uses tree-sitter + import-aware resolution to produce significantly more accurate call graphs with qualified names, line numbers, and 6 edge types.

This story:
1. **Removes** pactkit's own `_write_sqlite_db()` and `sqlite_output` config — pactkit no longer generates its own call graph db
2. **Adds** `graph_provider` config to `pactkit.yaml` — when set to `codegraph`, `pactkit query` reads `.codegraph/codegraph.db`
3. **Default** (no codegraph): continues using grep `.mmd` for call graph queries (existing behavior)
4. **Mermaid `.mmd` generation** continues regardless — humans need the visual graph

### codegraph Reference

**Setup workflow:**
- `codegraph init [path]` — first-time project initialization (creates `.codegraph/` + indexes)
- `codegraph init -i` / `codegraph init --index` — init + immediate full index
- `codegraph index [path]` — full re-index (also `--force` to rebuild everything)
- `codegraph sync [path]` — incremental sync after code changes (MCP server auto-syncs via file watcher with 2s debounce)
- `codegraph status [path]` — show file/symbol/edge counts, journal mode, last sync time
- `codegraph uninit [path]` — remove codegraph from project

**Query commands (CLI):**
- `codegraph callers <symbol>` — find callers (options: `--limit <n>`, `--json`)
- `codegraph callees <symbol>` — find callees (options: `--limit <n>`, `--json`)
- `codegraph impact <symbol>` — transitive impact radius (options: `--depth <n>`, `--json`)
- `codegraph query <search>` — FTS5 symbol search (options: `--kind <type>`, `--limit <n>`, `--json`)
- `codegraph context <task>` — task-focused context builder (options: `--format markdown`, `--max-nodes <n>`)
- `codegraph affected <files...>` — find affected test files (options: `--stdin`, `--depth <n>`, `--filter <glob>`, `--json`, `--quiet`)

**MCP server mode:**
- `codegraph serve --mcp` — stdio MCP server exposing tools: `codegraph_search`, `codegraph_callers`, `codegraph_callees`, `codegraph_impact`, `codegraph_context`, `codegraph_node`, `codegraph_explore`, `codegraph_trace`, `codegraph_files`, `codegraph_status`
- When running as MCP server, auto-syncs on file changes (no manual `codegraph sync` needed)

**Key characteristics:**
- Zero-config (no configuration files needed)
- Self-contained binary (bundles Node 24 runtime, no system Node.js required)
- 20+ languages supported (Python: full support via tree-sitter)
- Framework-aware: Django, Flask, FastAPI route recognition
- Incremental sync via OS file watchers (2-second debounce)
- SQLite with FTS5, WAL mode

## Requirements

### R1: Remove `_write_sqlite_db` and `sqlite_output` config (MUST)

- `_write_sqlite_db()` in `visualize.py` MUST be deleted entirely
- All calls to `_write_sqlite_db()` in `_build_call_graph()` MUST be removed
- `sqlite_output` field MUST be removed from `get_default_config()` and `_write_pactkit_yaml()`
- Mermaid `.mmd` generation MUST continue unchanged

### R2: pactkit.yaml `graph_provider` config (MUST)

`pactkit.yaml` MUST support `visualize.graph_provider: codegraph` (no default value written — absence means grep-mmd mode). When `codegraph`, `pactkit query` reads from `.codegraph/codegraph.db`. The field MUST be serialized by `_write_pactkit_yaml()` when present.

### R3: `pactkit query` reads codegraph.db (MUST)

When `graph_provider: codegraph`, `pactkit query --callers/--callees/--chain` MUST:
- Read from `{project_root}/.codegraph/codegraph.db`
- JOIN `edges` (filtered by `kind='calls'`) with `nodes` to resolve hash IDs to human-readable names
- Output format: `{name} ({file_path}:{start_line})` — one per line
- MUST fail with clear message if `.codegraph/codegraph.db` doesn't exist, instructing user to run `codegraph init` (first time) or `codegraph sync` (after code changes)

When `graph_provider` is absent (default), `pactkit query` MUST fail with message instructing user to either:
- Configure `visualize.graph_provider: codegraph` in `pactkit.yaml` and run `codegraph init`
- Or use grep on `.mmd` files directly

### R4: Graph Query Protocol updated (MUST)

`SKILL_VISUALIZE_MD` in `src/pactkit/prompts/skills.py` MUST be updated to two modes:

```
### Codegraph Mode (when graph_provider: codegraph in pactkit.yaml)
  → setup: codegraph init (first time), codegraph sync (after code changes)
  → unified: pactkit query --callers/--callees/--chain <func> (reads .codegraph/codegraph.db)
  → direct CLI: codegraph callers <symbol>
  → direct CLI: codegraph callees <symbol>
  → direct CLI: codegraph impact <symbol> [--depth N]
  → direct CLI: codegraph query <search> [--kind <type>]
  → direct CLI: codegraph context <task> (task-focused context builder)
  → direct CLI: codegraph affected <files...> (find affected test files)
  → MCP tools (if codegraph MCP server configured): codegraph_callers, codegraph_callees, codegraph_impact, codegraph_trace, codegraph_context
  → diagnostics: codegraph status (check index health)

### Grep Mode (default — when graph_provider not set, use .mmd files)
  → use: grep patterns on docs/architecture/graphs/*.mmd
```

Note: When codegraph MCP server is running (`codegraph serve --mcp`), file changes are auto-synced (2-second debounce). Manual `codegraph sync` is only needed when MCP server is not running.

### R5: PDCA command/skill prompts updated (MUST)

All references to `call_graph.db` / "SQLite Mode" / "pactkit sqlite" in prompts MUST be removed. Impact analysis instructions MUST be updated:
- When `graph_provider: codegraph`: use `pactkit query` or codegraph CLI directly
- Default: grep `.mmd` (unchanged from current behavior)

Files affected:
- `src/pactkit/prompts/skills.py` — Graph Query Protocol section
- `src/pactkit/prompts/commands.py` — Plan/Act/Check impact analysis
- `~/.claude/skills/project-hotfix/SKILL.md` — Phase 0.5 Impact Check
- `~/.claude/skills/project-act/SKILL.md` — Phase 1 trace, Phase 3 IMPACT
- `~/.claude/skills/pactkit-trace/SKILL.md` — "Read call_graph.mmd" instructions

### R6: Remove pactkit-generated call_graph.db references (MUST)

All code paths and prompts that reference `docs/architecture/graphs/call_graph.db` MUST be removed or updated. The only `.db` file pactkit reads is `.codegraph/codegraph.db` (upstream-generated).

## Acceptance Criteria

### AC1: _write_sqlite_db removed (R1)

- **Given** current codebase has `_write_sqlite_db()` in `visualize.py`
- **When** this story is implemented
- **Then** the function is deleted; `sqlite_output` config is removed; `pactkit visualize --mode call` only writes `.mmd`

### AC2: codegraph query works (R3)

- **Given** `graph_provider: codegraph` in `pactkit.yaml` AND `.codegraph/codegraph.db` exists with known edges
- **When** `pactkit query --callers execute` is run
- **Then** output lists callers with file path and line number from codegraph.db

### AC3: query error when codegraph.db missing (R3)

- **Given** `graph_provider: codegraph` AND `.codegraph/codegraph.db` does NOT exist
- **When** `pactkit query --callers foo` is run
- **Then** exit code 1; stderr instructs user to run `codegraph init` or `codegraph sync`

### AC4: query error when no provider configured (R3)

- **Given** `graph_provider` is absent in `pactkit.yaml`
- **When** `pactkit query --callers foo` is run
- **Then** exit code 1; stderr instructs user to configure codegraph or use grep on `.mmd`

### AC5: chain query works with codegraph schema (R3)

- **Given** `graph_provider: codegraph` AND `.codegraph/codegraph.db` exists
- **When** `pactkit query --chain execute` (upstream) is run
- **Then** recursive CTE traverses `edges` (kind='calls') JOINed with `nodes`; returns transitive callers with names

### AC6: config round-trips (R2)

- **Given** `visualize.graph_provider: codegraph` in `pactkit.yaml`
- **When** `load_config()` is called
- **Then** `config['visualize']['graph_provider']` is `'codegraph'`

### AC7: Graph Query Protocol updated (R4)

- **Given** `SKILL_VISUALIZE_MD` in `src/pactkit/prompts/skills.py`
- **When** the prompt content is read
- **Then** it documents two modes: Codegraph Mode (with full CLI/MCP reference) and Grep Mode (default fallback); no "Pactkit SQLite Mode" exists

### AC8: PDCA prompts updated (R5)

- **Given** prompts in `commands.py` and skill SKILL.md files
- **When** they reference call graph querying
- **Then** codegraph mode uses `pactkit query` / codegraph CLI; default mode uses grep `.mmd`; no references to `call_graph.db` remain

### AC9: no call_graph.db references remain (R6)

- **Given** implementation is complete
- **When** `grep -rn "call_graph.db" src/pactkit/` is run
- **Then** zero matches (all references to pactkit-generated db are removed)

### AC10: mmd generation unchanged (R1)

- **Given** any `graph_provider` setting (or absent)
- **When** `pactkit visualize --mode call` runs
- **Then** `.mmd` files are generated as before

## Target Call Chain

**Query path (codegraph mode):**
```
main() [cli.py] → query subcommand
  └── _query_command(args) [cli.py]
        └── read graph_provider from pactkit.yaml
              ├── if codegraph: open .codegraph/codegraph.db
              │     └── SELECT ns.name, ns.file_path, ns.start_line
              │         FROM edges e JOIN nodes ns ON e.source = ns.id
              │         JOIN nodes nt ON e.target = nt.id
              │         WHERE e.kind = 'calls' AND nt.name LIKE '%func%'
              ├── if absent: error "configure graph_provider or use grep .mmd"
              └── (no pactkit db path — removed)
```

**Visualize path (simplified):**
```
_build_call_graph() [visualize.py]
  ├── builds func_registry + call_edges (unchanged)
  ├── writes .mmd (unchanged)
  └── (no _write_sqlite_db — removed)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/config.py` | Remove `sqlite_output` from defaults; add `graph_provider` field (optional, not written by default) | None | Low |
| 2 | `src/pactkit/skills/visualize.py` | Delete `_write_sqlite_db()` function and all its call sites | Step 1 | Low |
| 3 | `src/pactkit/cli.py` | Rewrite query command: only codegraph path (JOIN edges+nodes); error if no provider or db missing | Step 1 | Medium |
| 4 | `src/pactkit/prompts/skills.py` | Rewrite Graph Query Protocol: Codegraph Mode + Grep Mode (no SQLite Mode) | Step 3 | Low |
| 5 | `src/pactkit/prompts/commands.py` | Update Plan/Act/Check impact analysis: codegraph preferred, grep fallback | Step 3 | Low |
| 6 | `~/.claude/skills/project-hotfix/SKILL.md` | Phase 0.5: prefer `pactkit query` when codegraph configured, else grep .mmd | Step 4 | Low |
| 7 | `~/.claude/skills/project-act/SKILL.md` | Phase 1/3: same update as Step 6 | Step 4 | Low |
| 8 | `~/.claude/skills/pactkit-trace/SKILL.md` | Remove "Read call_graph.mmd", prefer `pactkit query` / codegraph CLI | Step 4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Path Traversal | Low | `.codegraph/codegraph.db` path is relative to project root; no user input in path construction |
| SEC-2 SQL Injection | N/A | All query parameters use parameterized queries (LIKE ?) |
| SEC-3 Secrets | N/A | No credentials involved |
| SEC-4 Auth | N/A | Local file only |
| SEC-5 Input Validation | Low | `graph_provider` value validated against `{'codegraph'}` |
| SEC-6-8 | N/A | No web interface |

## Out of Scope

- Modifying codegraph itself (upstream project)
- Auto-running `codegraph init` / `codegraph sync` from pactkit (user must run these manually)
- Configuring codegraph MCP server from pactkit (user configures separately via `codegraph install`)
- Wrapping `codegraph affected` / `codegraph context` in pactkit CLI (use codegraph directly)
- Changing Mermaid graph generation logic
- Supporting other graph providers (only codegraph supported; absence = grep mmd)
