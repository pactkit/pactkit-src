# Lessons Learned

| Date | Lesson | Context |
|------|--------|---------|
| 2025-01 | Brand rename (ScafPy -> PactKit) touched 306 references — automate with `replace_all` | Migration |
| 2025-02 | Selective deployment needs cleanup of stale files when config changes | STORY-002 |
| 2025-02 | `pactkit.yaml` must be generated on first `init` with sensible defaults | STORY-001 |
| 2025-02 | Cross-session value comes from persistent artifacts (context.md, lessons.md), not from more rules — prompt changes are the cheapest high-impact mechanism | STORY-006 |
| 2025-02 | Adding a new command touches 3 files (config.py, commands.py, rules.py) plus count assertions in existing tests — keep count tests data-driven to reduce churn | STORY-007 |
| 2025-02 | Removing rules that overlap with LLM native behavior (55% token reduction) improves signal-to-noise — fewer rules = higher compliance on the ones that matter | STORY-008 |
| 2025-02 | Auto-merge new components via separate function (not load_config) preserves existing contract — exclude section in yaml handles user opt-out without version diffing | STORY-009 |
| 2025-02 | Release prep is a good time to catch stale numbers in docs — embed counts as tests to prevent future drift | STORY-010 |
| 2026-02 | Demoting commands to skills is a prompt-only refactor (no Python scripts needed for prompt-only skills) — but updating 25+ test files with hardcoded counts is the real cost; prefer data-driven assertions | STORY-011 |
| 2026-02 | Multi-repo docs sync is cheap via gh CLI + git clone/push — but tests reading deployed files (not source) can hide regressions until redeployment | STORY-012 |
| 2026-02 | Integrating an external MCP server is a prompt-only change — add conditional instructions to rules, skills, agents, and workflows; no runtime code needed. The conditional pattern (IF tool available → use it; ELSE → fallback) is now proven across 6 MCP integrations | STORY-013 |
| 2026-02 | Skill SKILL.md prompts must use absolute paths for script invocations — the LLM runs bash from project cwd, not the skill base directory; match the pattern already used in workflows.py and commands.py (~/.claude/skills/{name}/scripts/{script}.py) | BUG-001 |
| 2026-02 | Deploy-time path rewriting (template stays canonical, deployer rewrites at write time) is the correct pattern for multi-mode deployment — adding a simple `_rewrite_skills_prefix()` helper keeps templates DRY while supporting classic/plugin/marketplace modes with different path conventions | BUG-002 |
| 2026-02 | When iterating `ast.Import.names`, each alias must be processed individually — a `for` loop that overwrites a single variable silently drops all but the last import; collect into a list instead. Also deduplicate edges with a `seen` set to avoid Mermaid rendering issues | BUG-003 |
| 2026-02 | Dead code from refactors (`set(x)` as standalone expression) passes all tests because it's a no-op — use AST-based source inspection tests to catch dead code that linters miss in generated/deployed scripts | BUG-004 |
| 2026-02 | When two functions classify the same data (board stories), they must use the same logic — `archive_stories` used absence-of-todo as "done" while `_classify_story` required presence-of-done; align both to require `- [x]` for archival | BUG-005 |
| 2026-02 | Release hygiene requires syncing 5 artifacts (CHANGELOG, pyproject.toml, __init__.py, plugin repo, PyPI) — missing any one creates version drift; a release Story with explicit per-artifact tasks prevents omissions | STORY-014 |
| 2026-02 | Local PDCA must mirror CI checks — if CI runs lint, the Done command must too; adding `lint_command` to `LANG_PROFILES` and a conditional CI Lint Gate step closes the gap between local green and CI green | STORY-015 |
