# HOTFIX-slim-107: Remove residual pactkit.yaml version field operations

## Background
STORY-slim-102 migrated version checking from pactkit.yaml to `~/.claude/.pactkit-version` global marker, but left 4 residual references that still read/write version in pactkit.yaml.

## Target Files
| File | Line(s) | Issue |
|------|---------|-------|
| `src/pactkit/skills/board.py` | 239-256, 401-402, 417-418 | `update_version()` function + CLI entry |
| `src/pactkit/cli.py` | 146 | `--if-needed` help text references pactkit.yaml |
| `src/pactkit/prompts/commands.py` | 659 | Manual pactkit.yaml creation includes `version: 0.0.1` |
| `src/pactkit/prompts/agents.py` | 29 | "Release field (from pactkit.yaml version)" |
| `src/pactkit/prompts/skills.py` | 127-130, 152, 699 | `update_version` docs and usage |
| `src/pactkit/prompts/agents.py` | 145 | "Use update_version to update version number" |

## Fix
- Remove `update_version()` function and CLI subcommand from board.py
- Update help text, prompts, and agent docs to remove pactkit.yaml version references
- Version is now managed in pyproject.toml + __init__.py only; deploy marker at ~/.claude/.pactkit-version
