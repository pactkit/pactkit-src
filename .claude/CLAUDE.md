<!-- pactkit:start -->
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
```

## Code Intelligence (codegraph)
This project has codegraph enabled. Prefer codegraph over grep/find for code navigation:
- `codegraph callers <symbol>` — find callers
- `codegraph callees <symbol>` — find callees
- `codegraph impact <symbol> --depth 3` — impact analysis
- `codegraph query <keyword> --kind function` — symbol search
- `codegraph context "<task>"` — task-focused context

<!-- pactkit:end -->

@./docs/product/context.md
@./.claude/CLAUDE.local.md
