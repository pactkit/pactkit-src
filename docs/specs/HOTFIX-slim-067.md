# HOTFIX-slim-067: Conditional pactkit update in Done + auto-init guard

## Status: In Progress

## Background
Two prompt-level issues: (1) project-done Phase 4 step 0.5 runs `pactkit update` unconditionally — this is only needed when developing pactkit itself, not for user projects. (2) Core Protocol Session Context doesn't auto-create pactkit.yaml when missing — it only suggests `/project-init`, leaving PDCA commands without config.

## Target Files
- `~/.claude/skills/project-done/SKILL.md` — Phase 4 step 0.5
- `~/.claude/rules/01-core-protocol.md` — Session Context section

## Fix
1. Done Phase 4 step 0.5: Add condition — only run `pactkit update` + deploy verification when `pyproject.toml` name == "pactkit". Otherwise skip with log.
2. Core Protocol: After `pactkit update --if-needed`, add guard — if no `pactkit.yaml` found (check `.claude/`, `.opencode/`, `.codex/`), auto-run `pactkit init` before proceeding.
