# HOTFIX-slim-061: board.py update_task fails for Done-section stories

| Field | Value |
|-------|-------|
| Status | Done |

## Background
`update_task` regex only matches `### [STORY-xxx]` heading format. Stories in Done section use plain bullet `- **STORY-xxx**:` format, causing "Story not found" error.

## Target
`src/pactkit/skills/board.py:191` — `update_task()` function

## Fix
Add fallback: when heading-format search fails, scan Done section for bullet-format story ID. Return "Already done" instead of "not found".
