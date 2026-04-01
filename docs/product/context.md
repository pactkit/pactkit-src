# Project Context (Auto-generated)
> Last updated: 2026-04-01T18:18:25+08:00 by pactkit context

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
- config.py load_config() deep merge was single-level; adding check.pactguard (nested dict inside check) required upgrading to two-level merge to preserve sub-dict defaults like mode and blocking
- Adding pactkit-garden to VALID_SKILLS broke 5 hardcoded count assertions in test_config.py, test_pdca_slim.py, test_selective_deploy.py, test_prompt_structural_invariants.py, test_story_slim063.py — grep == 21 and == 10 in tests before releasing a new skill
- DETECTED_ENV in commands.py init playbook was unnecessary — _render_prompt(template, profile) already resolves per-format at deploy time. Added FORMAT_NAME to deployer.py var_map to enable pactkit init --format {FORMAT_NAME}.
- Graduated safety language: retire MANDATORY keyword across prompts/commands.py, workflows.py, skills.py — use CRITICAL for safety gates (T1) and MUST for required steps (T2). Consistency prevents AI from treating all-caps keywords as equally urgent.
- Multi-stack visualize: _detect_stack() returning single str masks Go/TS/Java files in mixed projects; _build_class_graph hardcoded ast.parse() silently skips non-Python via except. Fix: _detect_stacks() returns list, extract_classes() ABC on all 4 analyzers.

## Next Recommended Action
`/project-design`

## Agent Continuation
No active work session.
