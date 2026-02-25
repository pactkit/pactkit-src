# Project Context (Auto-generated)
> Last updated: 2026-02-25T18:00:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 54 items archived (STORY-001~038, BUG-001~016)
- **Current Version**: 1.3.0
- **Branch**: develop

## Recent Completions
- STORY-038: Add call_graph.mmd to standard PDCA update cycle and fix focus_graph.mmd collision
- STORY-037: Fix regression decision tree — replace unverifiable conditions with git-diff and fallback-tolerant checks
- STORY-036: Sync pactkit.dev documentation with current README and codebase

## Active Branches
- `develop` (current)

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Regression decision trees with unverifiable conditions become dead code — replace with git-diff checks and fallback thresholds | STORY-037 |
| 2026-02 | Shared output filenames across graph modes cause silent overwrites — use mode-specific names and ensure all three graph types are in Update Reality | STORY-038 |
| 2026-02 | Documentation drift accumulates silently across config changes — multi-repo docs require a sync checklist on every breaking change | STORY-036 |
| 2026-02 | All new features must be conditional/opt-in by default | STORY-025~030 |
| 2026-02 | Internal prompt iteration versions diverged silently from package versions — version hygiene requires a single grep audit at each release | BUG-014 |

## Next Recommended Action
Sprint board is empty. Use `/project-plan` to analyze new requirements or `/project-design` for greenfield product design.
