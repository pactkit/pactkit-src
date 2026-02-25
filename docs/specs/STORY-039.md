# STORY-039: Virtual Environment Configuration Support

| Field | Value |
|-------|-------|
| ID | STORY-039 |
| Title | Virtual Environment Configuration Support |
| Status | Draft |
| Release | 1.3.2 |

## Context

When running PDCA commands, pactkit uses hardcoded `python3`, `pytest`, `ruff` etc. commands that resolve to the system's global Python environment. Even when a project has a local virtual environment (`.venv/`, `venv/`, etc.), the prompts do not instruct Claude to activate or use it.

This causes issues when:
- Project dependencies are only installed in the virtual environment
- Different Python versions are needed for different projects
- CI/CD environments expect virtual environment usage

## Requirements

### R1: Config Schema Extension
- The `pactkit.yaml` schema MUST support a `venv` configuration section.
- The `venv` section MUST have a `path` field (string) specifying the virtual environment directory relative to project root.
- The `venv` section SHOULD have an `auto_detect` field (boolean, default: true) that enables automatic detection of common venv directories.

### R2: Auto-Detection and Fallback Logic
- When `venv.auto_detect` is true (default), pactkit SHOULD check for common venv directories in order: `.venv`, `venv`, `env`.
- The first existing directory containing a `bin/python3` (Unix) or `Scripts/python.exe` (Windows) MUST be used.
- **Fallback scenarios**:
  - If `venv.path` is set but the directory does not exist → print warning, fallback to system `python3`
  - If `auto_detect` is true but no venv found → silently fallback to system `python3`
  - If no `venv` config at all → use system `python3` (current behavior, backward compatible)
- The resolved `python_bin` value MUST be either `{venv_path}/bin/python3` or `python3` (never empty/null).

### R3: Prompt Template Updates
- The generated project `.claude/CLAUDE.md` MUST include a "Virtual Environment" section when venv is configured.
- The section MUST specify the activation command and direct python/pip paths.
- All PDCA commands that invoke Python tools SHOULD reference the venv-aware paths.

### R4: LANG_PROFILES Enhancement
- Each language profile MAY define a `python_bin` field that resolves to the venv python if configured.
- The `test_runner` and `lint_command` SHOULD be prefixed with the venv activation when applicable.

## Acceptance Criteria

### AC1: Config Schema Validation
**Given** a `pactkit.yaml` with `venv.path: .venv`
**When** `pactkit init` is run
**Then** the config is accepted without validation errors

### AC2: Auto-Detection
**Given** a project with a `.venv/bin/python` directory
**And** no explicit `venv.path` in config
**When** `pactkit init` is run with `venv.auto_detect: true`
**Then** the venv is automatically detected and configured

### AC3: Project CLAUDE.md Generation
**Given** a configured `venv.path: .venv`
**When** `pactkit init` is run
**Then** the generated `.claude/CLAUDE.md` includes:
```markdown
## Virtual Environment
Always use the project's virtual environment:
- **Activate**: `source .venv/bin/activate`
- **Python**: `.venv/bin/python3`
- **Pytest**: `.venv/bin/pytest`
- **Pip**: `.venv/bin/pip`
```

### AC4: Fallback When Venv Not Found
**Given** a `pactkit.yaml` with `venv.path: .venv`
**And** no `.venv/` directory exists in project
**When** `pactkit init` is run
**Then** a warning is printed: "⚠️ venv.path=.venv not found, using system python"
**And** the generated CLAUDE.md does NOT include venv section
**And** `python_bin` resolves to `python3`

### AC5: Silent Fallback for Auto-Detect
**Given** a project with no virtual environment directories
**And** `venv.auto_detect: true` (default)
**When** `pactkit init` is run
**Then** no warning is printed (silent fallback)
**And** `python_bin` resolves to `python3`

### AC6: Backward Compatibility
**Given** a `pactkit.yaml` without `venv` section
**When** `pactkit init` is run
**Then** behavior is unchanged (use system Python)

## Design

### Config Schema

```yaml
# pactkit.yaml
version: "1.0.0"
stack: python
venv:
  auto_detect: true    # default: true
  path: .venv          # optional, overrides auto-detect
```

### Target Call Chain

```
cli.py:main()
  → config.py:load_config()
    → config.py:_detect_venv()  # NEW
  → deployer.py:deploy()
    → deployer.py:_generate_project_claude_md()  # MODIFY
      → prompts/rules.py:PROJECT_CLAUDE_MD_TEMPLATE  # MODIFY
```

### Implementation Notes

1. **config.py**: Add `_detect_venv()` function, add `venv` to `get_default_config()`, add validation for `venv.path`.

2. **deployer.py**: Read venv config, pass to template generation.

3. **prompts/rules.py**: Add conditional venv section to project CLAUDE.md template.

4. **prompts/workflows.py**: Update `LANG_PROFILES` to support venv-aware commands.

## Test Plan

- [ ] Unit test: `venv` config validation (valid path, invalid path)
- [ ] Unit test: auto-detection finds `.venv` when present
- [ ] Unit test: auto-detection returns `python3` when no venv found
- [ ] Unit test: explicit `venv.path` not found → warning + fallback
- [ ] Integration test: `pactkit init` generates correct CLAUDE.md with venv section
- [ ] Integration test: `pactkit init` without venv → no venv section in CLAUDE.md
- [ ] Integration test: backward compat - no venv config, no change
