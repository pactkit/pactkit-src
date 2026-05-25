# STORY-slim-116: Skill Model Precision and Graph Query Optimization

| Field | Value |
|-------|-------|
| ID | STORY-slim-116 |
| Status | Draft |
| Priority | P1 |
| Release | 2.14.0 |

## Background

Three architecture graphs have grown large: `call_graph.mmd` (118K/2226 lines), `code_graph.mmd` (101K/1223 lines), `class_graph.mmd` (48K/1872 lines). PactKit's `lazy_visualize` controls regeneration via git-diff but does NOT control how Claude reads them — Claude reads full files during Plan/Act phases, burning 1000–2000+ tokens per graph before any work begins.

Separately, only 7 of 35 skills carry an explicit `model:` field (`project-act`, `project-done`, `project-check`, `project-pr`, `project-init`, `project-hotfix`, `project-release` — all set to `sonnet`). The remaining 28 skills have no model field, meaning they inherit context defaults rather than being matched to their actual complexity level. Simple extraction or formatting skills that run as haiku-equivalent work are burning sonnet credits.

Two orthogonal fixes are needed:
1. **Graph Query Protocol** — replace full `.mmd` reads with targeted symbol queries via the SKILL.md instruction layer.
2. **Skill Model Precision** — add explicit `model:` fields to all 35 skills, matched to task complexity.

## Technical Design

### Capability Assessment
| Need | Source | Decision |
|------|--------|----------|
| Graph symbol lookup | `.mmd` file (full read today) | New: SKILL.md instruction — grep/awk targeted extraction instead of full Read |
| Model field in skills | SKILL.md frontmatter `model:` | Extend existing pattern — 7 skills already use it |
| Model tier assignment | CLAUDE.md Subagent Model Selection table | Reuse existing haiku/sonnet/opus tier definitions |

### Reuse Points
- `model: sonnet` pattern already established in 7 SKILL.md files — extend to all 35
- CLAUDE.md `## Subagent Model Selection` table defines the 3-tier logic — reference, do not duplicate

### Lateral Scan Results

- Operation: `model:` field in SKILL.md frontmatter
- Existing implementations: 7 (`project-act`, `project-done`, `project-check`, `project-pr`, `project-init`, `project-hotfix`, `project-release` — all `model: sonnet`)
- Assessment: Extend existing pattern to all 35 skills — no new abstraction needed

- Operation: Graph query (how Claude reads `.mmd` files during Plan/Act)
- Existing implementations: 0 — no query mechanism exists; all reads are implicit full-file
- Assessment: New instruction block in SKILL.md is justified; no existing pattern to reuse

### New Implementation Required
- Graph Query Protocol instruction block in `project-act/SKILL.md` and `project-plan/SKILL.md`
- Model assignments for 28 skills currently missing the `model:` field

## Requirements

### R1: Graph Query Protocol in Act and Plan Skills (MUST)

In `project-act/SKILL.md` Phase 1 and `project-plan/SKILL.md` Phase 1, replace the instruction to `Read <graph>.mmd` with a targeted query protocol:
- When Claude needs to understand a module's dependencies, use `grep` on the relevant `.mmd` to extract only the edges/nodes matching the target module name.
- Full `.mmd` Read is permitted ONLY when the query returns 0 results (module not yet indexed) or when generating a new graph.
- Add an explicit instruction: "MUST NOT `Read` a full `.mmd` graph file — use `grep <module> docs/architecture/graphs/<graph>.mmd` instead."

### R2: Explicit Model Assignment for All Skills (MUST)

Every skill in `~/.claude/skills/` MUST have an explicit `model:` field in its SKILL.md frontmatter. Assignment follows the tier logic from CLAUDE.md:

| Tier | Model | Criteria |
|------|-------|----------|
| Haiku | `haiku` | File search, format checks, info extraction, pure I/O (read + write structured content) |
| Sonnet | `sonnet` | Code implementation, test writing, analysis, multi-step reasoning (default) |
| Opus | `opus` | Architecture decisions, deep multi-file reasoning, spec creation, system design |

Assignments by skill:

| Skill | Assigned Model | Rationale |
|-------|---------------|-----------|
| `project-plan` | `opus` | Architecture decisions, Spec creation, multi-file reasoning |
| `project-design` | `opus` | Greenfield PRD, multi-story decomposition |
| `project-act` | `sonnet` | Code implementation (already set) |
| `project-check` | `sonnet` | QA analysis (already set) |
| `project-done` | `sonnet` | Cleanup + commit (already set) |
| `project-init` | `sonnet` | Project scaffolding (already set) |
| `project-hotfix` | `sonnet` | Fast-path code fix (already set) |
| `project-release` | `sonnet` | Release orchestration (already set) |
| `project-pr` | `sonnet` | PR creation (already set) |
| `project-sprint` | `opus` | Multi-story orchestration, subagent coordination |
| `project-clarify` | `sonnet` | Requirement clarification dialogue |
| `pactkit-trace` | `sonnet` | Call chain tracing, code reading |
| `pactkit-visualize` | `haiku` | Run script, output graph — pure execution |
| `pactkit-scaffold` | `haiku` | File generation from template — pure I/O |
| `pactkit-board` | `haiku` | Sprint board CRUD — structured data ops |
| `pactkit-analyze` | `sonnet` | Cross-artifact consistency analysis |
| `pactkit-audit` | `sonnet` | AI Readiness assessment with scoring |
| `pactkit-doctor` | `haiku` | Health check — read + report |
| `pactkit-status` | `haiku` | State overview — read + format |
| `pactkit-release` | `sonnet` | Release orchestration with judgment |
| `pactkit-review` | `sonnet` | Code review with SOLID/security checklist |
| `pactkit-report` | `haiku` | HTML dashboard from graph — template render |
| `pactkit-garden` | `sonnet` | Dead code / pattern detection |
| `pactkit-draw` | `haiku` | Generate Draw.io XML — structured output |
| `pactkit-trace` | `sonnet` | Deep execution flow analysis |
| `architecture-diagram` | `haiku` | Generate HTML diagram — structured output |
| `software-architecture` | `opus` | High-level system design reasoning |
| `huashu-design` | `sonnet` | UI/UX prototype generation |
| `daily-retro` | `sonnet` | Retrospective synthesis, insight extraction |
| `profile` | `haiku` | Load and format profile data |
| `find-skills` | `haiku` | Search and list skills |
| `docx` | `haiku` | Document generation — structured I/O |
| `pdf` | `haiku` | PDF processing — structured I/O |
| `pptx` | `haiku` | Presentation generation — structured I/O |
| `xlsx` | `haiku` | Spreadsheet processing — structured I/O |

### R3: Graph Query Protocol Documentation (SHOULD)

Add a `## Graph Query Protocol` section to `pactkit-visualize/SKILL.md` documenting the grep-based query pattern so all skills can reference it consistently.

## Acceptance Criteria

### AC1: Graph Full-Read is Blocked in Act and Plan Skills (R1)

- **Given** Claude is executing Phase 1 of `project-act` or `project-plan` and needs to understand module dependencies
- **When** the SKILL.md instruction is followed
- **Then** Claude uses `grep <module> docs/architecture/graphs/code_graph.mmd` (not `Read code_graph.mmd`) to extract only relevant edges, consuming <50 tokens instead of 1000+

### AC2: Full Read Fallback is Documented (R1)

- **Given** a grep query on a `.mmd` graph returns 0 results for the target module
- **When** Claude follows the Graph Query Protocol
- **Then** the fallback to full `Read` is explicitly permitted with a note explaining why

### AC3: All 35 Skills Have Explicit Model Field (R2)

- **Given** any skill in `~/.claude/skills/`
- **When** the skill's `SKILL.md` frontmatter is read
- **Then** a `model:` field is present with value `haiku`, `sonnet`, or `opus`
- **And** `grep -r "^model:" ~/.claude/skills/*/SKILL.md | wc -l` returns 35 (or the current skill count)

### AC4: Model Assignments Match Complexity Tier (R2)

- **Given** the tier criteria in R2
- **When** each skill's model assignment is reviewed
- **Then** pure I/O / extraction skills are assigned `haiku`, implementation/analysis skills are `sonnet`, architecture/multi-story orchestration skills are `opus`
- **And** no implementation skill (project-act, project-check) is demoted to `haiku`

### AC5: Graph Query Protocol Documented in pactkit-visualize (R3)

- **Given** `pactkit-visualize/SKILL.md` is opened
- **When** the `## Graph Query Protocol` section is read
- **Then** a grep-based query example is present showing how to extract targeted module edges

## Target Call Chain

All changes are in SKILL.md instruction files (no Python source code):

```
User invokes /project-act or /project-plan
  → Claude loads SKILL.md from ~/.claude/skills/{skill}/SKILL.md
  → Phase 1 instruction: "use grep on .mmd" (NEW — replaces implicit full Read)
  → Claude executes grep instead of Read on graph files

User invokes any skill
  → Claude loads SKILL.md
  → Frontmatter model: field (NEW) → FleetView selects model tier
  → Skill runs at assigned model (haiku/sonnet/opus)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `~/.claude/skills/pactkit-visualize/SKILL.md` | Add `## Graph Query Protocol` section with grep examples | None | Low |
| 2 | `~/.claude/skills/project-act/SKILL.md` | Replace Phase 1 graph read instruction with Graph Query Protocol reference + MUST NOT full-Read rule | Step 1 | Low |
| 3 | `~/.claude/skills/project-plan/SKILL.md` | Same as Step 2 for Phase 1 Visual Scan | Step 1 | Low |
| 4 | 28 skills missing `model:` field | Add `model: <tier>` to SKILL.md frontmatter per R2 assignment table | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | docs/tests only |
| SEC-2 | No | docs/tests only |
| SEC-3 | No | docs/tests only |
| SEC-4 | No | docs/tests only |
| SEC-5 | No | docs/tests only |
| SEC-6 | No | docs/tests only |
| SEC-7 | No | docs/tests only |
| SEC-8 | No | docs/tests only |

## Out of Scope

- Modifying pactkit Python source code — all changes are SKILL.md instruction files only
- CodeGraph MCP integration — the grep-based approach solves the immediate cost problem without adding an MCP dependency; CodeGraph MCP can be evaluated separately
- Model field for `_rules/` directory — these are shared rule files, not invocable skills
