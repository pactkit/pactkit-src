# Project Context (Auto-generated)
> Last updated: 2026-03-16 by /project-done

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: STORY-069 (archived)

## Current Stories
- None active

## Recent Completions
- STORY-069: OpenCode Deployment Format Support — `--format opencode` deployment mode
- BUG-034: Plan command playbook now includes explicit metadata table template
- BUG-033: scaffold.py create_spec() template updated to pass spec-lint

## Active Branches
- `opencode-test` — OpenCode deployment format (STORY-069 committed)
- `codex-test` — Codex deployment artifacts (pending Responses API)

## Key Decisions
- OpenCode format uses `AGENTS.md` (not CLAUDE.md) with inline rules
- Skills path prefix: `~/.config/opencode/skills` (not ~/.claude/skills)
- opencode.json excludes provider/apiKey (user-managed)
- Multi-format deployment reuses existing helpers with path prefix parameter

## Next Recommended Action
Merge `opencode-test` branch to main, or run `/project-release` if ready for version bump.
