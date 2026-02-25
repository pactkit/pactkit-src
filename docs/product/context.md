# Project Context (Auto-generated)
> Last updated: 2026-02-25T23:00:00+08:00 by /project-done

## Sprint Status
- **Backlog**: 0 stories
- **In Progress**: 0 stories
- **Done**: 58 items archived (STORY-001~039, BUG-001~019)
- **Current Version**: 1.3.1
- **Branch**: main

## Recent Completions
- BUG-019: Venv detection integration in deployer
- BUG-018: Issue Tracker verification backfill in Done command
- STORY-039: Virtual Environment Configuration Support

## Active Branches
None

## Key Decisions
| Date | Lesson | Context |
|------|--------|---------|
| 2026-02 | Config schema + function without deployment integration = dead code — detect_venv() existed but was never called; _generate_project_claude_md_if_missing() completes the feature | BUG-019 |
| 2026-02 | Conditional steps marked "IF available" may be skipped by weaker models — add verification phase as safety net | BUG-018 |
| 2026-02 | Playbook instructions must invoke CLI tools, not duplicate their logic | BUG-017 |
| 2026-02 | Shared output filenames across graph modes cause silent overwrites | STORY-038 |
| 2026-02 | Regression decision trees with unverifiable conditions become dead code | STORY-037 |

## Next Recommended Action
Sprint board is empty. Use `/project-plan` to analyze new requirements or `/project-design` for greenfield product design.
