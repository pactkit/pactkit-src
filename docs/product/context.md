# Project Context (Auto-generated)
> Last updated: 2026-04-01T22:14:43+08:00 by pactkit context

## Sprint Status
Backlog: 1 | In Progress: 0 | Done: 3 stories

## Current Stories
None

## Recent Completions
- STORY-slim-082: Sync prompt templates for --mode module and --focus scoping
- STORY-slim-081: Two-tier module graph with scoped focus for large codebases
- STORY-slim-080: Deep monorepo scanning: nearest-ancestor config discovery for all analyzers

## Active Branches
codex-integration
  codex-test
  codex/analyze-features-for-codex-integration
  develop
  feature/cython-build
* main
  opencode-test
  worktree-agent-a1c545fc
  worktree-agent-a2a614d9
  worktree-agent-a2c72eb4
  worktree-agent-a2d37818
  worktree-agent-a31efa03
+ worktree-agent-a69e176d
  worktree-agent-a8a58db3
  worktree-agent-ace1a8fe
  worktree-agent-aeb84ca4
  worktree-agent-af6334c9

## Key Decisions
- Graduated safety language: retire MANDATORY keyword across prompts/commands.py, workflows.py, skills.py — use CRITICAL for safety gates (T1) and MUST for required steps (T2). Consistency prevents AI from treating all-caps keywords as equally urgent.
- Multi-stack visualize: _detect_stack() returning single str masks Go/TS/Java files in mixed projects; _build_class_graph hardcoded ast.parse() silently skips non-Python via except. Fix: _detect_stacks() returns list, extract_classes() ABC on all 4 analyzers.
- Monorepo stack detection requires depth-1 subdir scan; cleaners.py and visualize.py _STACK_MARKERS must scan root/* not just root
- When splitting a monolithic file into submodules with deploy-time inlining via load_script(), relative imports (from .foo) in exec() context raise KeyError not ImportError — guard with except (ImportError, KeyError)
- TSAnalyzer._load_tsconfig_paths must search depth-1 subdirs like _detect_stacks does because visualize.py always passes monorepo root as root param, not stack subdir — tsconfig in frontend/ is invisible if only root is searched

## Next Recommended Action
`/project-plan`

## Agent Continuation
No active work session.
