# Project Context (Auto-generated)
> Last updated: 2026-04-16T14:07:16+08:00 by pactkit context

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
- Borrowed Claude Code P3 (graduated safety language) + P6 (NO_TOOLS) patterns; applied to 01-core-protocol.md, 02-hierarchy-of-truth.md, 10-safety.md, project-act.md, project-check.md
- pyproject.toml [project].dependencies must only include packages needed for core CLI startup (pyyaml); adapter and tree-sitter packages go in [project.optional-dependencies] with extras (opencode, codex, visualize, all)
- _deploy_claude_md must read-before-write: user-modified global CLAUDE.md was silently destroyed on every pactkit init/update. Project-level _generate_project_claude_md had 3 protection layers; global had zero.
- TreeSitterAnalyzer._compute_complexity() can serve as a universal base for all tree-sitter languages; only PythonAnalyzer needs a separate implementation using stdlib ast
- Parsing Mermaid .mmd files to JSON (nodes+edges) is straightforward with regex; the D3 force-directed HTML template works well as a single-file self-contained skill

## Next Recommended Action
`/project-design`
