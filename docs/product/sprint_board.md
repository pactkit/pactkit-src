# Sprint Board

## 📋 Backlog

## ✅ Done

### STORY-041: Test Pyramid Restructuring — E2E Layer & Unit Test Rationalization (https://github.com/pactkit/pactkit/issues/27)
- [x] R1: CLI E2E test suite (subprocess-based, 8+ scenarios)
- [x] R2: E2E directory restructure (remove api/browser, create cli/)
- [x] R3: Integration test separation (deploy-calling tests → tests/integration/)
- [x] R4: Prompt string test consolidation (~770 → ~100 structural checks)
- [x] R5: Shared test fixtures (conftest.py)
- [x] R6: CI tiered test execution config

### STORY-040: Project CLAUDE.md Layered Architecture — Separate Framework and User Content (https://github.com/pactkit/pactkit/issues/26)
- [x] R1: Remove skip-if-exists guard, rename function, always regenerate CLAUDE.md
- [x] R2: Add `@./.claude/CLAUDE.local.md` import to generated CLAUDE.md
- [x] R3: Create `_generate_claude_local_md_if_missing()` function
- [x] R4: Implement migration heuristic for existing user-modified CLAUDE.md
- [x] R5: Verify global CLAUDE.md behavior unchanged
- [x] R6: Preserve HOME and preview-mode guards


