# Project Context (Auto-generated)
> Last updated: 2026-02-25T18:25:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 55 items archived (STORY-001~038, BUG-001~017)
- **Current Version**: 1.3.0
- **Branch**: develop

## Recent Completions
- BUG-017: /project-init playbook generates incomplete pactkit.yaml
- STORY-038: Add call_graph.mmd to standard PDCA update cycle
- STORY-037: Fix regression decision tree

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Playbook instructions must invoke CLI tools, not duplicate their logic — /project-init manually created 3-field pactkit.yaml while pactkit init CLI generates 70-line config | BUG-017 |
| 2026-02 | Shared output filenames across graph modes cause silent overwrites — use mode-specific names | STORY-038 |
| 2026-02 | Regression decision trees with unverifiable conditions become dead code — replace with git-diff checks | STORY-037 |
| 2026-02 | Documentation drift accumulates silently across config changes — multi-repo docs require sync checklist | STORY-036 |
| 2026-02 | All new features must be conditional/opt-in by default | STORY-025~030 |

## Next Recommended Action
Sprint board is empty. Use `/project-plan` to analyze new requirements or `/project-design` for greenfield product design.
