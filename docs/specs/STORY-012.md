# STORY-012: Docs Sync — 同步文档站和 GitHub 元数据至 PDCA Slim 架构

- **Status**: Backlog
- **Priority**: 4.0 (Impact 4 / Effort 1)
- **Release**: 1.1.1
- **Author**: System Architect
- **Created**: 2026-02-13

## Background

STORY-011 reduced PactKit's command surface from 14 to 8 and expanded skills from 3 to 9. The source code, README, and local deployment are updated, but the external-facing documentation site (pactkit.dev on Cloudflare) and GitHub repo metadata still reference the old "13 commands × 3 skills" architecture.

## Scope

This is a **docs-only** story. No source code changes — only documentation site content, GitHub repo descriptions, and plugin repo updates.

## Target Repositories

| Repo | Host | Stale Content |
|------|------|---------------|
| `pactkit/pactkit` | GitHub | Repo description says "13 commands" |
| `pactkit/pactkit.dev` | Cloudflare Pages | 7 MDX files reference old counts |
| `pactkit/claude-code-plugin` | GitHub | Plugin contents may need regeneration |

## Requirements

### R1: GitHub Repo Description (MUST)
- `pactkit/pactkit` description MUST be updated from "9 agents × 13 commands" to "9 agents × 8 commands × 9 skills"

### R2: Docs Site — index.mdx (MUST)
- "At a Glance" table MUST show "8 Commands" and "9 Skills"
- "all 13 commands" link text MUST be updated

### R3: Docs Site — commands.mdx (MUST)
- Title/description MUST say "8 commands" (not 13)
- The 6 removed commands (trace, draw, doctor, status, review, release) MUST be removed from the command table
- A note SHOULD explain these are now available as skills
- The command detail sections for removed commands MUST be removed or redirected to skills.mdx

### R4: Docs Site — skills.mdx (MUST)
- MUST list all 9 skills (add the 6 new prompt-only skills)
- SHOULD distinguish between scripted skills (3) and prompt-only skills (6)

### R5: Docs Site — installation.mdx (MUST)
- All references to "13 commands" MUST be changed to "8 commands"
- All references to "3 skills" MUST be changed to "9 skills"

### R6: Docs Site — configuration.mdx (MUST)
- Deployed files table MUST show "8 command playbooks" and "9 skill tools"

### R7: Docs Site — workflow.mdx (SHOULD)
- Plan phase description SHOULD reference pactkit-trace as a skill, not `/project-trace` as a command

### R8: Plugin Repo Update (SHOULD)
- `pactkit/claude-code-plugin` SHOULD be regenerated with `pactkit init --format marketplace`
- `marketplace.json` version SHOULD be bumped

## Acceptance Criteria

### Scenario 1: GitHub Description
Given a visitor views https://github.com/pactkit/pactkit
When they read the repo description
Then it says "8 commands" (not 13 or 14)

### Scenario 2: Docs Landing Page
Given a visitor opens https://pactkit.dev
When they view the "At a Glance" section
Then it shows "8 Commands" and "9 Skills"

### Scenario 3: Commands Page
Given a visitor opens the Commands reference page
When they view the command table
Then only 8 commands are listed
And removed commands are not present

### Scenario 4: Skills Page
Given a visitor opens the Skills page
When they view the skills list
Then all 9 skills are listed with descriptions

### Scenario 5: Installation Page
Given a visitor reads the installation guide
When they see deployment counts
Then it says "8 commands" and "9 skills"
