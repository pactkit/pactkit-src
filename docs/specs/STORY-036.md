# STORY-036: Sync pactkit.dev documentation with current README and codebase

- **Release**: 1.3.0
- **Priority**: High
- **Type**: Documentation
- **Repo**: `pactkit/pactkit.dev` (external docs site)

## Problem

The official documentation at https://pactkit.dev/ has multiple outdated descriptions, missing content, and inaccurate configuration references. A comprehensive audit against the README (source of truth) and actual codebase reveals 23 discrepancies across 8 documentation pages.

## Requirements

### Critical Fixes

- **MUST** fix `pactkit.yaml` path on `installation.mdx` — change `~/.claude/pactkit.yaml` to `$CWD/.claude/pactkit.yaml` (BUG-013 change) [GAP-01]
- **MUST** fix Core Protocol description on `configuration.mdx` — replace stale "Think-hard mode, atomic tools preference, output conventions" with actual content: "Session Context, Visual First, Strict TDD, Language Matching" [GAP-02]

### High Priority Fixes

- **MUST** fix `root` field default on `configuration.mdx` — change `~/.claude` to `.` (current directory) to match `config.py` [GAP-03]
- **MUST** fix `exclude` field type on `configuration.mdx` — change from `list` / `[]` to `object` / `{}` with structure `exclude.agents: [...]`, `exclude.commands: [...]` [GAP-04]

### Medium Priority Fixes

- **SHOULD** complete MCP tool lists on `mcp-integration.mdx` [GAP-16~19]:
  - shadcn: add `get_item_examples_from_registries`
  - Memory: add `read_graph`
  - Playwright: add `browser_fill_form`
  - Chrome DevTools: add `take_snapshot`, `take_screenshot`
- **SHOULD** document `agent_models` config field on `configuration.mdx` [GAP-05]
- **SHOULD** add Memory MCP entity naming convention (`{STORY_ID}`, `entityType: "story"`) to `mcp-integration.mdx` [GAP-20]

### Low Priority Fixes

- **MAY** fix Repo Maintainer description consistency — "Git conventions" vs "architecture maintenance" [GAP-21]
- **MAY** add Test Cases to Tier 1 in README Hierarchy of Truth section [GAP-23]
- **MAY** backport Plugin installation method to README [GAP-09]

## Acceptance Criteria

### AC1: Config path corrected
- **Given** the `installation.mdx` page references `pactkit.yaml`
- **When** a user reads the selective deployment instructions
- **Then** the path reads `.claude/pactkit.yaml` (project-level) not `~/.claude/pactkit.yaml`

### AC2: Core Protocol description matches source
- **Given** the `configuration.mdx` "Constitution Rules" table
- **When** a user reads the Core Protocol row
- **Then** it lists "Session Context, Visual First, Strict TDD, Language Matching"

### AC3: Config field types are accurate
- **Given** the `configuration.mdx` pactkit.yaml reference table
- **When** a user reads `root` default and `exclude` type
- **Then** `root` shows `.` and `exclude` shows `object` / `{}`

### AC4: MCP tool lists complete
- **Given** the `mcp-integration.mdx` MCP server listings
- **When** compared with source code (`rules.py`)
- **Then** all tools are listed for each server (shadcn: 4, Memory: 5, Playwright: 5, Chrome DevTools: 5)

## Target Files

| File | Changes |
|------|---------|
| `content/docs/installation.mdx` | Fix pactkit.yaml path (line 81) |
| `content/docs/configuration.mdx` | Fix Core Protocol desc, root default, exclude type, add agent_models |
| `content/docs/mcp-integration.mdx` | Complete tool lists, add entity naming |
| `README.md` (pactkit repo) | Fix root default, exclude type, add Test Cases to Tier 1 |
