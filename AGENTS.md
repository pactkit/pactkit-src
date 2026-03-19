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

## PDCA Execution Lessons

- **/project-done 不要重复跑回归测试**：如果 `/project-act` 阶段刚跑过全量测试且全绿，Done 阶段直接引用该结果，不要再跑一次。只有在 Done 阶段有额外文件修改（非 doc-only）时才重新跑。
- **大文件一次读完**：`lessons.md` 等治理文件直接一次性读取，不要分多次小范围读取再拼凑。
- **并行写多个独立文件**：rules.md、lessons.md、context.md、sprint_board.md 的更新互不依赖，应并行执行，不要串行。
- **流程指令是指导，不是死板清单**：当上下文已经包含某个步骤的结果时（如测试结果、lint 结果），直接复用，不要机械重复执行。
