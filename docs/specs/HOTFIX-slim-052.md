# HOTFIX-slim-052: Add move_story command to board.py

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-052 |
| Status | In Progress |

## Background

`/project-act` Phase 1 tries to call `board.py move_story STORY-XXX in_progress` to move a story from Backlog to In Progress. The command doesn't exist, forcing manual board editing every time.

## Fix

Add `move_story(sid, target)` function and CLI subcommand to `src/pactkit/skills/board.py`. Target accepts: `backlog`, `in_progress`, `done`. Moves the story block between sections regardless of checkbox state.
