# Sprint Board

## 📋 Backlog

### [STORY-slim-015] Doctor & Release CLI — Deterministic Diagnostics
> Spec: docs/specs/STORY-slim-015.md

- [ ] R1: pactkit doctor — orphaned/missing spec detection
- [ ] R2: pactkit doctor — config drift detection
- [ ] R3: pactkit doctor — stale graph detection
- [ ] R4: pactkit backfill-release — spec TBD replacement
- [ ] R5: pactkit issue-sync — GitHub issue lifecycle
- [ ] R6: CLI wiring (doctor, backfill-release, issue-sync)
- [ ] R7: Prompt delegation to new CLI commands

### [STORY-slim-016] Test Mapping & Stack-Aware Lint CLI
> Spec: docs/specs/STORY-slim-016.md

- [ ] R1: pactkit test-map — source-to-test file mapping
- [ ] R2: pactkit lint — stack-aware lint runner
- [ ] R3: CLI wiring (test-map, lint)
- [ ] R4: Prompt delegation to new CLI commands

## ✅ Done

### [BUG-slim-003] CLI Migration Gaps — Prompt Inconsistencies & Implementation Mismatches [#75](https://github.com/pactkit/pactkit/issues/75)
> Spec: docs/specs/BUG-slim-003.md

- [x] R1: Fix prompt inconsistency — pactkit next-id (sprint/hotfix/design)
- [x] R2: Fix prompt inconsistency — pactkit sec-scope (plan Phase 3.2)
- [x] R3: Fix prompt inconsistency — pactkit context (plan Phase 3.3, init Phase 6)
- [x] R4: Fix cleaners.py Java cleanup list
- [x] R5: Extend guards.py config completeness check
- [x] R6: Extend lint_lessons row format validation

### [STORY-slim-014] Code is the Law — Deterministic Rule Migration
> Spec: docs/specs/STORY-slim-014.md

- [x] R1: New CLI subcommands (guard, next-id, clean, regression, context, sec-scope)
- [x] R2: Document structure validators (lint-context, lint-lessons, lint-testcase)
- [x] R3: Eliminate dual-write (auto-generate routing table from Python constants)
- [x] R4: Slim prompt templates (replace deterministic blocks with CLI calls)
- [x] R5: Backward compatibility + all tests pass
- [x] R6: Security Scope auto-detection (pactkit sec-scope)
- [x] R7: Lazy Visualize CLI (pactkit visualize --lazy)

