# Project Context (Auto-generated)
> Last updated: 2026-04-16T15:20:08+08:00 by pactkit context

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

## Active Branches
develop
* main

## Key Decisions
- pyproject.toml [project].dependencies must only include packages needed for core CLI startup (pyyaml); adapter and tree-sitter packages go in [project.optional-dependencies] with extras (opencode, codex, visualize, all)
- _deploy_claude_md must read-before-write: user-modified global CLAUDE.md was silently destroyed on every pactkit init/update. Project-level _generate_project_claude_md had 3 protection layers; global had zero.
- TreeSitterAnalyzer._compute_complexity() can serve as a universal base for all tree-sitter languages; only PythonAnalyzer needs a separate implementation using stdlib ast
- Parsing Mermaid .mmd files to JSON (nodes+edges) is straightforward with regex; the D3 force-directed HTML template works well as a single-file self-contained skill
- D3 force graph selectNode() computes blast radius via in-browser BFS — no backend needed; folder-based coloring via d3.scaleOrdinal on path prefix gives CodeFlow-quality visuals

## Next Recommended Action
`/project-design`
