# pactkit — Project Context

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
├── cli.py              ← CLI entry: pactkit init/update/version/upgrade
├── config.py           ← pactkit.yaml load/validate/generate
├── utils.py            ← atomic_write() utility
├── generators/
│   └── deployer.py     ← Core deployment orchestrator (classic/plugin/marketplace/opencode)
├── prompts/            ← All prompt templates and constants
│   ├── agents.py       ← 9 agent definitions
│   ├── commands.py     ← 11 command playbooks
│   ├── references.py   ← Reference checklists (SOLID/Security/Quality)
│   ├── rules.py        ← Constitution rule modules + AGENTS.md template
│   ├── skills.py       ← 10 skill definitions
│   └── workflows.py    ← PDCA workflow prompts + LANG_PROFILES
└── skills/             ← Skill script source files
    ├── board.py        ← Sprint board operations
    ├── scaffold.py     ← File scaffolding
    ├── spec_linter.py  ← Spec structural linter
    └── visualize.py    ← Code dependency graph (Mermaid)
```

## Project Governance
- Specs are in `docs/specs/` — they are the source of truth
- Sprint board: `docs/product/sprint_board.md`
- Architecture graphs: `docs/architecture/graphs/`
- Config: `.claude/pactkit.yaml` (PactKit deployment config)
- Global rules: `~/.config/opencode/AGENTS.md` (loaded automatically by OpenCode)

@./docs/product/context.md
