# STORY-slim-118: codegraph MCP Integration for Semantic Code Queries

| Field | Value |
|-------|-------|
| ID | STORY-slim-118 |
| Status | Draft |
| Priority | P1 |
| Release | 2.14.0 |

## Background

`pactkit-visualize` generates Mermaid `.mmd` graphs (file deps, call graph, class diagram) by doing a full AST scan of the project on every invocation. This works well for visualization and is deeply integrated with `pactkit regression`, `impact`, `blast_radius`, and `complexity`. However, the scan is stateless — each run re-parses every file from scratch.

[codegraph](https://github.com/colbymchenry/codegraph) is a complementary tool that maintains an **incremental SQLite-backed semantic graph** (tree-sitter, 21 languages) and exposes it as an **MCP server**. Its capabilities overlap with pactkit-visualize's query operations (callers, importers, impact radius) but it does NOT produce Mermaid output — so it cannot replace pactkit-visualize as a visualization generator.

The opportunity is to wire codegraph as an **MCP server** alongside Claude Code so that agents can perform semantic code queries (callers, impact, routes) without invoking a full `visualize` regeneration. pactkit-visualize remains authoritative for `.mmd` generation; codegraph becomes the fast query layer.

## Capability Comparison

| Dimension | pactkit-visualize | codegraph |
|-----------|------------------|-----------|
| Output | Mermaid `.mmd` files | SQLite DB + JSON/text to stdout |
| Languages | Python, Go, TypeScript, Java | 21 languages (tree-sitter) |
| Graph types | file, class, call, module, workflow | callers, imports, inheritance, routes, impact |
| Integration | Agent invokes script → `.mmd` file written | MCP server or CLI |
| Incremental | No (full scan each run) | Yes (`watch()` API) |
| pactkit deps | `regression`, `test-map`, `impact`, `blast_radius` all consume `.mmd` | No pactkit integration yet |
| Replaces visualize? | — | **No** — no Mermaid output; downstream pipeline breaks |
| Complements visualize? | — | **Yes** — faster semantic queries via MCP |

## Requirements

### R1: Feasibility Decision (MUST)

Document the replacement vs. augmentation decision with evidence. The Spec itself IS the R1 deliverable — a written capability comparison that answers "can codegraph replace pactkit-visualize?" with reasoning.

### R2: MCP Configuration (SHOULD)

If augmentation is chosen, provide the `codegraph serve --mcp` invocation in `pactkit.yaml` MCP config section so agents can query it alongside the existing visualize skill.

### R3: SKILL.md Update (SHOULD)

Update `pactkit-visualize` SKILL.md `## Graph Query Protocol` section to note that codegraph MCP (if configured) can be used for real-time semantic queries as a faster alternative to `grep` on `.mmd` files. Add a conditional note: "If codegraph MCP is available (`codegraph_search` tool present), prefer it for caller/callee queries."

### R4: pactkit-visualize Retained (MUST NOT)

MUST NOT remove or deprecate `pactkit-visualize` — it remains the authoritative source for `.mmd` graph generation, which is consumed by `pactkit regression`, `pactkit test-map`, `impact`, `blast_radius`, and `complexity`.

## Acceptance Criteria

### AC1: Replacement Verdict Documented (R1)

- **Given** a comparison of pactkit-visualize and codegraph capabilities
- **When** the Spec is reviewed
- **Then** it contains a capability matrix with clear verdict: "codegraph cannot replace pactkit-visualize (no Mermaid output); it augments it as a semantic query layer"

### AC2: MCP Config Snippet Available (R2)

- **Given** codegraph is installed (`npm install -g @colbymchenry/codegraph` or similar)
- **When** user adds the MCP config snippet from this Spec to their Claude Code MCP settings
- **Then** the `codegraph_search`, `codegraph_callers`, `codegraph_trace` tools become available to the agent

### AC3: SKILL.md Updated (R3)

- **Given** the pactkit-visualize SKILL.md `## Graph Query Protocol` section
- **When** codegraph MCP is available in the session
- **Then** the section notes: use `codegraph_search` / `codegraph_callers` for real-time queries; fall back to `grep` on `.mmd` if codegraph not available

### AC4: Existing .mmd Pipeline Unchanged (R4)

- **Given** changes from this story are applied
- **When** `pactkit regression`, `pactkit test-map`, or `pactkit impact` are run
- **Then** they continue to operate on `.mmd` files unchanged — no behavior regression

## Target Call Chain

This story is primarily a documentation + prompt-update story. The implementation path:

```
pactkit update
  └── deployer._render_skill_md("pactkit-visualize")
        └── SKILL_VISUALIZE_MD (src/pactkit/prompts/skills.py)
              └── ## Graph Query Protocol  ← R3: add codegraph MCP note here
```

No source logic changes. Only `src/pactkit/prompts/skills.py` (SKILL_VISUALIZE_MD) is modified.

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/prompts/skills.py` | Edit `SKILL_VISUALIZE_MD` — add codegraph MCP conditional note to `## Graph Query Protocol` | None | Low |
| 2 | Run `pactkit update` | Redeploy `pactkit-visualize` SKILL.md to `~/.claude/skills/pactkit-visualize/SKILL.md` | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 (Input Validation) | N/A | docs/prompts only — no user input boundary |
| SEC-2 (Auth) | N/A | no auth changes |
| SEC-3 (SQL Injection) | N/A | no SQL |
| SEC-4 (Path Traversal) | N/A | no file path operations |
| SEC-5 (Secret Leakage) | N/A | MCP config snippet uses no credentials |
| SEC-6 (Dependency) | Low | codegraph is an optional external tool — not bundled into pactkit |
| SEC-7 (SSRF) | N/A | no URL fetching |
| SEC-8 (XSS) | N/A | no web UI |

## Technical Design

### Lateral Scan Results

- Operation: "code dependency graph generation / semantic code query"
- Existing: `pactkit-visualize` (1 implementation — `visualize.py:2462`)
- Assessment: Reuse existing for Mermaid output; codegraph augments with semantic query layer
- No duplication risk — different output formats, different integration modes

### Capability Assessment

| Need | Source | Decision |
|------|--------|----------|
| Mermaid graph generation | pactkit-visualize (existing) | Retain — codegraph has no Mermaid output |
| Semantic code queries (callers, impact) | codegraph MCP (new) | Augment — add conditional note to SKILL.md |
| pactkit regression / test-map pipeline | pactkit-visualize `.mmd` files (existing) | No change — R4 hard constraint |

### codegraph MCP Config Snippet

Add to Claude Code MCP settings (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "codegraph": {
      "command": "codegraph",
      "args": ["serve", "--mcp"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

Install: `npm install -g @colbymchenry/codegraph` then `codegraph init` in project root.

MCP tools available after configuration: `codegraph_search`, `codegraph_callers`, `codegraph_trace`, `codegraph_context`, `codegraph_explore`, `codegraph_impact`, `codegraph_affected`.

## Out of Scope

- Replacing pactkit-visualize with codegraph (not feasible — no Mermaid output)
- Bundling codegraph into pactkit (optional external tool, not a pactkit dependency)
- Auto-indexing (codegraph must be installed and `codegraph init` run by the user)
- Changes to `pactkit regression`, `pactkit test-map`, `impact`, `blast_radius` — these continue to use `.mmd` files
