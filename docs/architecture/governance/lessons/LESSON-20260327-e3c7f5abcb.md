---
schema_version: 1
id: LESSON-20260327-e3c7f5abcb
date: '2026-03-27'
story_id: null
context: deployer.py:_deploy_commands
tags:
- legacy-import
legacy_source: docs/architecture/governance/archive/lessons_archive_202603.md
---

When migrating commands to skills (subdir/SKILL.md format), all path assertions in pre-existing tests must be updated in the same commit — 17 tests broke because they asserted flat commands/*.md paths
