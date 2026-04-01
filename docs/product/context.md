# Project Context (Auto-generated)
> Last updated: 2026-04-01T20:36:00+08:00 by pactkit context

## Sprint Status
Backlog: 0 | In Progress: 0 | Done: 0 stories

## Current Stories
None

## Recent Completions
None

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
- DETECTED_ENV in commands.py init playbook was unnecessary — _render_prompt(template, profile) already resolves per-format at deploy time. Added FORMAT_NAME to deployer.py var_map to enable pactkit init --format {FORMAT_NAME}.
- Graduated safety language: retire MANDATORY keyword across prompts/commands.py, workflows.py, skills.py — use CRITICAL for safety gates (T1) and MUST for required steps (T2). Consistency prevents AI from treating all-caps keywords as equally urgent.
- Multi-stack visualize: _detect_stack() returning single str masks Go/TS/Java files in mixed projects; _build_class_graph hardcoded ast.parse() silently skips non-Python via except. Fix: _detect_stacks() returns list, extract_classes() ABC on all 4 analyzers.
- Monorepo stack detection requires depth-1 subdir scan; cleaners.py and visualize.py _STACK_MARKERS must scan root/* not just root
- When splitting a monolithic file into submodules with deploy-time inlining via load_script(), relative imports (from .foo) in exec() context raise KeyError not ImportError — guard with except (ImportError, KeyError)

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
