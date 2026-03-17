# pactkit — Project Context

## Credential Safety Rules (MANDATORY)

> **INCIDENT**: v2.1.0 release leaked an API key via `docker/opencode/opencode.json` committed to git.
> These rules exist to prevent recurrence. Violation = P0 bug.

### NEVER do
1. **NEVER** read files from `~/.config/`, `~/.claude/`, `~/.codex/`, `~/.ssh/`, `~/.aws/` and write their content into any git-tracked file.
2. **NEVER** hardcode API keys, tokens, passwords, or credentials in any file — including Dockerfiles, docker-compose.yml, JSON configs, YAML configs, shell scripts.
3. **NEVER** use a real credential value as a default/fallback (e.g., `${VAR:-real-key-here}`).

### ALWAYS do
1. **ALWAYS** use environment variable references (`${VAR}`, `${VAR:?error msg}`) for secrets in docker-compose and config files.
2. **ALWAYS** provide `.env.example` with placeholder values (`your-key-here`) — never `.env` with real values.
3. **ALWAYS** verify `.gitignore` covers any directory containing credentials before creating files in it.
4. **ALWAYS** run a credential scan before `git add`: check for patterns like `apiKey`, `token`, `secret`, `password`, `sk-ant-`, UUID-like strings.

### Before writing any file that MIGHT contain credentials
```
STOP and check:
1. Is the source path under ~/.<config_dir>/ ? → DO NOT copy verbatim
2. Does the content contain apiKey/token/secret/password fields? → Replace with ${ENV_VAR}
3. Is the target file in a git-tracked directory? → Verify .gitignore first
4. Am I creating a docker/ or config/ file? → Use .env.example pattern, never inline secrets
```

## Virtual Environment
Always use the project's virtual environment:
- **Activate**: `source .venv/bin/activate`
- **Python**: `.venv/bin/python3`
- **Pytest**: `.venv/bin/pytest`
- **Pip**: `.venv/bin/pip`

## Dev Commands

```bash
# Run tests
.venv/bin/pytest tests/ -v

# Lint
ruff check src/ tests/

# Install in dev mode
pip install -e .

# Test CLI
pactkit version
pactkit init -t /tmp/preview
pactkit init --format opencode -t /tmp/oc-preview
```

## Architecture

```
src/pactkit/
├── cli.py              ← CLI entry: pactkit init/update/version/upgrade/schema
├── config.py           ← pactkit.yaml load/validate/generate + re-exports from profiles
├── profiles.py         ← FormatProfile registry (OCP: new format = one entry)
├── schemas.py          ← Document structure schemas (DRY: single source of truth)
├── utils.py            ← atomic_write() utility
├── generators/
│   └── deployer.py     ← Core deployment orchestrator (classic/opencode/plugin/marketplace)
├── prompts/            ← All prompt templates and constants
│   ├── agents.py       ← 9 agent definitions
│   ├── commands.py     ← 11 command playbooks (use {TEMPLATE_VAR} placeholders)
│   ├── references.py   ← Reference checklists (SOLID/Security/Quality)
│   ├── rules.py        ← 8 rule modules + CLAUDE_MD_TEMPLATE (auto-generated from RULES_FILES)
│   ├── skills.py       ← 10 skill definitions (use {TEMPLATE_VAR} placeholders)
│   └── workflows.py    ← PDCA workflow prompts + LANG_PROFILES
└── skills/             ← Skill script source files (deployed as standalone scripts)
    ├── board.py        ← Sprint board operations
    ├── scaffold.py     ← File scaffolding + SPEC_TEMPLATE (inline copy, see schemas.py)
    ├── spec_linter.py  ← Spec structural linter (imports from schemas.py)
    └── visualize.py    ← Code dependency graph (Mermaid)
```

## Key Architecture Files
- `profiles.py` — Add new tool format here. See `FormatProfile` docstring for template variables.
- `schemas.py` — Add new document type here. See `SCHEMA_REGISTRY` for discovery.
- `deployer.py` — `_render_prompt(template, profile)` resolves all `{VAR}` placeholders at deploy time.

## Project Governance
- Specs are in `docs/specs/` — they are the source of truth
- Sprint board: `docs/product/sprint_board.md`
- Architecture graphs: `docs/architecture/graphs/`
- Config: `.opencode/pactkit.yaml` or `.claude/pactkit.yaml` (auto-detected, OpenCode preferred)
- Global rules: `~/.config/opencode/AGENTS.md` (loaded automatically by OpenCode)
- Architecture principles: `~/.config/opencode/rules/08-architecture-principles.md`

@./docs/product/context.md
output MUST use Chinese