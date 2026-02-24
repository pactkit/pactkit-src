# Project Context (Auto-generated)
> Last updated: 2026-02-24T22:30:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 21 stories (STORY-001 through STORY-018, BUG-001 through BUG-005)

## Recent Completions
- STORY-018: Architecture docs staleness prevention
- STORY-017: project-init CLAUDE.md generation
- STORY-016: CLAUDE.md hygiene — language matching rule & project context cleanup

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Local PDCA must mirror CI checks — adding `lint_command` to `LANG_PROFILES` and a conditional CI Lint Gate closes the gap | STORY-015 |
| 2026-02 | Constitution rules are the cheapest way to change agent behavior — a 3-line language-matching rule makes all PDCA output respect user's language | STORY-016 |
| 2026-02 | Project-level CLAUDE.md should be scaffolded by init — prompt-only changes to command templates are the cheapest way to add new init artifacts without touching runtime code | STORY-017 |
| 2026-02 | Architecture docs that are written once at Init (rules.md, system_design.mmd) drift silently — close the loop by adding verification/refresh steps to the Done command so staleness is caught every commit cycle | STORY-018 |

## Next Recommended Action
`/project-design` — Board is empty. Design new features or improvements.
