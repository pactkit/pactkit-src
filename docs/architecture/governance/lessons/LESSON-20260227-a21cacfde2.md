---
schema_version: 1
id: LESSON-20260227-a21cacfde2
date: '2026-02-27'
story_id: STORY-055
context: STORY-055
tags:
- legacy-import
legacy_source: docs/architecture/governance/archive/lessons_archive_202602.md
---

Adding new config sections requires 7 coordinated config.py touch points (get_default_config, DEEP_MERGE_KEYS, _BACKFILL_KEYS, KNOWN_KEYS, _rewrite_yaml, validate_config, generate_default_yaml) plus 2 full-config fixture updates; when restructuring prose into a structured checklist, preserve pre-existing keyword tests by adding OWASP context notes below the table rather than modifying the tests (score: 22/25)
