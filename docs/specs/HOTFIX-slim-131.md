# HOTFIX-slim-131: Fix deployer prepending @ references before YAML frontmatter

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-131 |
| Status | In Progress |
| Priority | P0 |
| Release | 2.15.2 |

## Background

`_deploy_commands()` in deployer.py prepends `_build_command_rules_header()` output (@ reference lines) before the command content which includes YAML frontmatter. This pushes frontmatter away from line 1, causing Claude Code to not parse `model:`, `description:`, and `allowed-tools:` fields. The `model:` frontmatter (added in STORY-slim-125) never takes effect at runtime.

## Fix

Insert @ references after the closing `---` of frontmatter, not before the opening `---`.

## Target

- File: `src/pactkit/generators/deployer.py`
- Function: `_deploy_commands()` (line ~1008)
