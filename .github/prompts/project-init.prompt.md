---
mode: agent
description: "Initialize project scaffolding and governance structure"
---

# Command: Init (v1.3.0 Rich)
- **Usage**: `/project-init`
- **Agent**: System Architect

## 🧠 Phase 0: The Thinking Process
1.  **Environment Check**: Is this a fresh folder or legacy project?
2.  **Compliance**: Does the user need `.github/pactkit.yaml`?
3.  **Strategy**: If legacy, I must prioritize `visualize` to capture Reality.

## 🛡️ Phase 0.5: Git Repository Guard
> **INSTRUCTION**: Check if the directory is inside a git repository. This check is non-interactive — never prompt the user.
1.  **Check**: Run `git rev-parse --is-inside-work-tree` (suppress stderr).
2.  **If NOT a git repo** (command fails):
    - Print warning: "⚠️ No git repository detected. Git operations (commit, branch) will not work. Run `git init` to initialize one."
    - Continue with the rest of init. Do NOT prompt or block.
3.  **If already a git repo**: Skip silently to Phase 1.

## 🎬 Phase 1: Environment & Config
> **NOTE**: This playbook is pre-rendered per-format during deployment. All paths below are already resolved for **GitHub Copilot** (`copilot`). No runtime IDE detection needed.
1.  **Check CLI Availability**: Run `pactkit version` (terminal only) to check if CLI is available.
    - **If available**: Proceed to Step 2.
    - **If NOT available** (command fails): Print warning: "⚠️ pactkit CLI not found. Install with: `pip install pactkit`". Then manually create a minimal `.github/pactkit.yaml` in `.github/` with `stack: <detected>`, `version: 0.0.1`, `root: .`, `developer: ""` and skip to Step 3.
2.  **Generate Config**: Check if `.github/pactkit.yaml` exists.
    - **If missing**: Run `pactkit init --format copilot` from the terminal
    - **If exists**: Run `pactkit update --format copilot` from the terminal
3.  **Stack Detection** (config-first, then file-based fallback):
    - **Config-first**: If `.github/pactkit.yaml` exists and has a `stack` value set (including `auto`), use that value and skip file-based detection.
    - **File-based detection** (only if no config value):
      - Valid values: `python`, `node`, `go`, `java`, `auto`
      - If `pyproject.toml` or `requirements.txt` or `setup.py` exists → `stack: python`
      - If `package.json` exists → `stack: node`
      - If `go.mod` exists → `stack: go`
      - If `pom.xml` or `build.gradle` exists → `stack: java`
    - **Safe fallback**: If none match and no config exists, default to `stack: auto` and print warning: "⚠️ No stack detected, defaulting to auto. You can set `stack:` in `.github/pactkit.yaml` later."
    - Do NOT block on user input for stack selection mid-flow.
4.  **Project Instructions File**: Check/Create `./.github/copilot-instructions.md` if missing (do NOT overwrite).
    - Use the directory name as the project name. Fill test_runner and lint_command from the detected language stack in LANG_PROFILES.
    - Include: venv instructions (if detected), dev commands, `@./docs/product/context.md` reference for cross-session context.

## 🎬 Phase 2: Architecture Governance
1.  **Scaffold**: Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py init_arch`.
    - *Result*: Folders created. Placeholders (`system_design.mmd`) created.
2.  **Ensure**: `mkdir -p docs/product docs/specs docs/test_cases tests/e2e/api tests/e2e/browser tests/unit`.

## 🎬 Phase 3: Discovery (Reverse Engineering)
1.  **Scan Reality**: Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py visualize`.
    - *Goal*: If this is an existing project, overwrite the empty `code_graph.mmd` with the REAL class structure immediately.
2.  **Class Scan**: Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py visualize --mode class`.
3.  **Module Scan**: Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py visualize --mode module` to generate module-level overview for multi-module projects.
4.  **Verify**: Read `docs/architecture/graphs/code_graph.mmd` and `class_graph.mmd`.
    - *Check*: Is it still "No code yet"? If files exist in src, this graph MUST contain classes.

## 🎬 Phase 4: Project Skeleton
1.  **Board**: Run `python3 .github/skills/pactkit-scaffold/scripts/scaffold.py create_board` if `docs/product/sprint_board.md` does not exist.
    - This ensures the board has all three section headers: `## 📋 Backlog`, `## 🔄 In Progress`, `## ✅ Done`.

## 🎬 Phase 5: Knowledge Base (The Law)
1.  **Law**: Write `docs/architecture/governance/rules.md`.
2.  **History**: Write `docs/architecture/governance/lessons.md` with table header `| Date | Lesson | Context |` and separator `|------|--------|---------|`. The third column MUST be `Context`, not `Source`.

## 🎬 Phase 6: Session Context Bootstrap
1.  **Generate Context**: Generate `docs/product/context.md` manually (Sprint Status, Current Stories, Recent Completions, Active Branches, Key Decisions, Next Recommended Action) to generate `docs/product/context.md`. Set "Last updated by" to `/project-init`.

## 🎬 Phase 7: Handover
1.  **Output**: "✅ PactKit Initialized. Reality Graph captured. Knowledge Base ready."
2.  **Advice**: "⚠️ IMPORTANT: Run `/project-plan 'Reverse engineer'` to align the HLD."


---

## Rules Reference

# Core Protocol

## Session Context
On new session, check `.github/pactkit.yaml` exists. If not, run `pactkit init --format copilot` from the terminal.
If `.github/pactkit.yaml` does not exist (check `.github/`), run `pactkit init --format copilot` from the terminal to create it before proceeding.
Then read `docs/product/context.md` to understand project state before taking action.
If the file is missing, suggest `/project-init` to bootstrap the project.
If "Last updated" date is before today, suggest running `$daily-retro`.

## Visual First
Before modifying code:
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py` to view file dependency graph
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode class` for class inheritance
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode call --entry <func>` to trace call chains
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode module` for module-level architectural overview
- **PDCA Exemption**: When a PDCA command is active, the command's own visualize phases take precedence — skip Visual First.

## Strict TDD
- Write tests first (RED), then write implementation (GREEN)
- The agent MUST NOT skip TDD except when running `/project-hotfix`
- All tests MUST pass before committing

## Language Matching
- Match the user's language (Chinese→Chinese, English→English).
- Technical terms (function names, file paths, git commands) stay in original form.

## Signal Strength Convention
All rules and playbooks MUST use signal keywords consistently per this 4-level hierarchy:

| Level | Keywords | Semantics | Use When |
|-------|----------|-----------|----------|
| **L1 Absolute** | `NEVER` / `MUST NOT` | Violation = bug, zero tolerance | Security red lines, data loss, Spec tampering |
| **L2 Strong** | `CRITICAL` / `MUST` / `ALWAYS` | Violation = must-fix issue | Phase gates, TDD enforcement, regression blocking |
| **L3 Recommended** | `IMPORTANT` / `SHOULD` | Violation = warning, non-blocking | Best practices, performance advice, style |
| **L4 Advisory** | `Prefer` / `Consider` / `If possible` | Suggestion, skip by judgment | Optimization hints, optional enhancements |

- `NEVER` and `MUST NOT` are reserved for L1 — do not use them for anything less than absolute prohibition.
- `DO NOT` is ambiguous — replace with `NEVER` (L1) or `MUST NOT` (L1) for prohibitions, or rephrase as `SHOULD NOT` (L3) for recommendations.
- When writing an L1 or L2 rule, append a consequence clause: `— {what goes wrong if violated}`.

# Sectional Write Protocol

## Rule
When generating **any file** (code, document, test, HTML, etc.) that will exceed **300 lines**:

1. **Write skeleton first**: Create the file with the structural framework (imports, class/function signatures, section headings) via a single Write call
2. **Edit block-by-block**: Fill in one logical block at a time, using Edit after each block before starting the next
3. **Checkpoint between blocks**: After each Edit, print a brief progress message (e.g., "Block 2/5 written.")
4. **Never accumulate**: Do NOT compose the entire file in reasoning before writing — write as you go

## Applies To — any file type over 300 lines
- Documents: PRD, specs, README, architecture guides
- Source code: large modules, multi-endpoint API files, data models
- Tests: test files with many test classes or scenarios
- HTML/templates: prototypes, page templates

## Does NOT Apply To
- Short files (< 300 lines): single Write is fine
- Small config files (YAML, JSON, TOML)

## Anti-Pattern (DO NOT)
```
Compose entire file in head → one Write call at the end
```

## Correct Pattern
```
Write skeleton → Edit block 1 → checkpoint → Edit block 2 → checkpoint → ...
```

# File Atlas

| Path | Purpose |
|------|---------|
| `docs/specs/{ID}.md` | **The Law** -- Requirement Specifications (Spec) |
| `commands/*.md` | **The Playbooks** -- Command Execution Logic |
| `docs/product/sprint_board.md` | Sprint Board -- Current Iteration Board |
| `docs/test_cases/{ID}_case.md` | Test Cases -- Gherkin Acceptance Scenarios |
| `docs/architecture/graphs/*.mmd` | Architecture Graphs -- Mermaid Architecture Diagrams |
| `tests/unit/` | Unit Tests |
| `tests/e2e/` | E2E Integration Tests |
| `docs/product/archive/` | Archived Stories |
| `docs/product/prd.md` | Product Requirements Document (PRD) |

# Shared Protocols

## Lazy Visualize Protocol
> Referenced by: Act Phase 4, Done Phase 2

If source files changed (per `LANG_PROFILES[stack].source_dirs`) OR `code_graph.mmd` is missing, run visualize in all 3 modes (file, class, call). Else skip with log: "Graph up-to-date — no source changes".

## Test Mapping Protocol
> Referenced by: Act Phase 3, Check Phase 5, Done Phase 2.5, Hotfix Phase 2

Map changed source files to test files via `LANG_PROFILES[stack].test_map_pattern`. If no mapping can be determined, fall back to the full test suite.

## Context.md Canonical Format
> Referenced by: Init Phase 6, Plan Phase 3, Done Phase 4.5

Write `docs/product/context.md` using this format:
```markdown
# Project Context (Auto-generated)
> Last updated: {ISO timestamp} by {command}

## Sprint Status
{In Progress stories with IDs | Backlog count | Done count}

## Current Stories
{Active stories with brief descriptions}

## Recent Completions
{Last 3 completed stories, one line each}

## Active Branches
{git branch output, or "None" if no feature/fix branches}

## Key Decisions
{Last 5 lessons from lessons.md}

## Next Recommended Action
{If In Progress: `/project-act STORY-XXX` | If Backlog only: `/project-plan` | If empty: `/project-design`}
```

### Credential Safety

NEVER print passwords, keys, or tokens to stdout.
NEVER commit secrets to version control.
