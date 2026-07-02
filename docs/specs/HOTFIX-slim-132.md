# HOTFIX-slim-132: Add explicit board.py move_story command to project-act playbook

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-132 |
| Status | Done |
| Priority | P2 |
| Release | 2.16.0 |

## Background

AI consistently guesses wrong board.py subcommand syntax (tries `move_to_in_progress`, `"In Progress"`) because project-act Phase 0.6 only says "move it to In Progress" without giving the exact CLI invocation.

## Fix

In `project-act/SKILL.md` Phase 0.6 step 3, replace vague instruction with explicit command template:
```
python3 ~/.claude/skills/pactkit-board/scripts/board.py move_story "{STORY_ID}" "in_progress"
```

## Target

`~/.claude/skills/project-act/SKILL.md:46`
