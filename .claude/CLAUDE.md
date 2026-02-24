# PactKit — Project Context

PactKit is a spec-driven agentic DevOps toolkit for AI coding assistants. It compiles development workflows, role definitions, and behavioral rules into executable "constitutions" and "playbooks" for Claude Code.

- **PyPI**: https://pypi.org/project/pactkit/
- **GitHub**: https://github.com/pactkit/pactkit
- **Plugin repo**: https://github.com/pactkit/claude-code-plugin

## Architecture

```
src/pactkit/
├── cli.py              ← CLI entry: pactkit init/update/version (--format classic|plugin|marketplace)
├── config.py           ← pactkit.yaml load/validate/generate
├── utils.py            ← atomic_write() utility
├── scripts.py          ← Legacy script templates
├── generators/
│   └── deployer.py     ← Core deployment orchestrator (classic/plugin/marketplace)
├── prompts/            ← All prompt templates and constants
│   ├── agents.py       ← 9 agent definitions
│   ├── commands.py     ← 8 command playbooks
│   ├── references.py   ← Reference checklists (SOLID/Security/Quality)
│   ├── rules.py        ← 6 constitution rule modules + CLAUDE_MD_TEMPLATE
│   ├── skills.py       ← 9 skill definitions
│   └── workflows.py    ← PDCA workflow prompts + LANG_PROFILES
└── skills/             ← Skill script source files
    ├── board.py        ← Sprint board operations
    ├── scaffold.py     ← File scaffolding
    └── visualize.py    ← Code dependency graph (Mermaid)
```

## Dev Commands

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Install in dev mode
pip install -e .

# Test CLI
pactkit version
pactkit init -t /tmp/preview
pactkit init --format plugin -t /tmp/plugin-preview
```

@./docs/product/context.md
