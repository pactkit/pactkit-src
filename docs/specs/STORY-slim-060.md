# STORY-slim-060: Convert pactkit-codex from full fork to thin adapter

| Field | Value |
|-------|-------|
| ID | STORY-slim-060 |
| Status | Done |
| Priority | P1 |
| Release | 2.7.0 |

## Background

`pactkit-codex` (v0.2.3) is a full fork of pactkit core — 15,356 lines of code where only ~591 lines (4%) are Codex-specific. The remaining 96% duplicates core code (prompts, schemas, config, CLI, skills, utils, etc.), creating a maintenance nightmare: every core bugfix or feature must be manually ported.

With the DeployerProtocol/DeployerBase architecture (STORY-slim-057) and proven thin adapter pattern (pactkit-opencode, 307 lines), pactkit-codex can be converted to a thin adapter package that:
- Depends on `pactkit>=2.7.0` for all shared infrastructure
- Contains only `CodexDeployer(DeployerBase)` with Codex-specific deployment logic
- Registers via `pactkit.deployers` entry point for auto-discovery
- Eliminates ~14,700 lines of duplicated code

## Requirements

### R1: CodexDeployer thin adapter class (MUST)

Create `CodexDeployer(DeployerBase)` in `~/workspaces/pactkit-codex/src/pactkit_codex/deployer.py` that:
- Inherits from `pactkit.generators.deploy_base.DeployerBase`
- Sets `profile = get_profile("codex")` where `get_profile` is imported from core
- Implements `deploy(config, target)` orchestrating Codex-specific deployment
- Contains all 21 Codex-specific functions from the current fork's `generators/deployer.py`
- Registers via `register_deployer("codex", CodexDeployer, force=True)` at module level

### R2: FormatProfile "codex" registration in core (MUST)

Add the "codex" `FormatProfile` entry to `src/pactkit/profiles.py:FORMAT_PROFILES` so that `get_profile("codex")` works from core. The profile contains all Codex-specific paths (`~/.codex/`, `.codex/`, `AGENTS.md`, etc.).

### R3: Delete duplicated core modules (MUST)

Remove all modules from pactkit-codex that are pure copies of core code:
- `config.py`, `schemas.py`, `profiles.py`, `utils.py`, `cli.py`
- `prompts/` (entire directory — agents.py, commands.py, rules.py, skills.py, workflows.py, references.py)
- `skills/` (board.py, visualize.py, scaffold.py, spec_linter.py, `__init__.py`)
- `generators/` directory structure (flatten to single `deployer.py`)
- All CLI subcommand modules (doctor.py, guards.py, validators.py, cleaners.py, etc.)
- Replace with imports from `pactkit` core package

### R4: Entry point auto-registration (MUST)

Configure `pyproject.toml` with `[project.entry-points."pactkit.deployers"]` so that `pip install pactkit-codex` auto-registers the CodexDeployer. Pattern: `codex = "pactkit_codex:CodexDeployer"`.

### R5: Dependency on pactkit core (MUST)

Change `pyproject.toml` dependencies from `pyyaml>=6.0` (standalone) to `pactkit>=2.7.0` (adapter). The package MUST NOT duplicate any pactkit core dependencies.

### R6: Version sync to 2.7.0 (MUST)

Set pactkit-codex version to 2.7.0 to match core release, consistent with pactkit-opencode versioning strategy.

### R7: Codex-specific prompt adjustments (MUST)

Preserve all Codex-specific transformations that are NOT in core:
- `_strip_model_references()`: Claude→Codex brand replacement
- `_strip_model_selection_table()`: Remove subagent model table (single-agent)
- `_inject_playbook_prerequisites()`: Add rule prerequisites to playbook headers
- `_deploy_codex_playbooks()`: Full playbook deployment with path replacement
- `_deploy_codex_prompts()`: Thin wrapper prompts with description frontmatter
- `_deploy_codex_agents_md()`: Single-agent AGENTS.md with 10KB budget + truncation
- `_generate_codex_config_toml()`: TOML config generation/merge (not JSON/YAML)
- `_generate_codex_project_files()`: Project-level `.codex/` structure

### R8: CI/CD pipeline (SHOULD)

Create `.github/workflows/publish.yml` (OIDC PyPI publish on v* tags) and `.github/workflows/ci.yml` (test matrix) following the pactkit-opencode pattern.

### R9: Test migration (MUST)

Migrate existing pactkit-codex tests to import from `pactkit` core for shared functionality and from `pactkit_codex.deployer` for Codex-specific code. Update all `from pactkit_codex.generators.deployer import` to `from pactkit_codex.deployer import`.

## Acceptance Criteria

### AC1: CodexDeployer inherits DeployerBase and registers (R1, R4)

- **Given** pactkit-codex is installed via `pip install pactkit-codex`
- **When** Python imports `pactkit_codex`
- **Then** `get_deployer("codex")` returns `CodexDeployer` class AND `isinstance(CodexDeployer(), DeployerBase)` is True

### AC2: Codex profile available from core (R2)

- **Given** pactkit core `profiles.py` contains a "codex" `FormatProfile` entry
- **When** `get_profile("codex")` is called
- **Then** returns a `FormatProfile` with `name="codex"`, `global_config_dir="~/.codex"`, `display_name="Codex CLI"`

### AC3: Full deployment produces correct file structure (R1, R7)

- **Given** a fresh temp directory as target
- **When** `CodexDeployer().deploy(target=tmp_dir)` is called
- **Then** the following files exist: `AGENTS.md`, `config.toml`, `rules/*.md`, `playbooks/*.md`, `prompts/*.md`, `skills/pactkit-*/SKILL.md`

### AC4: No duplicated core modules (R3)

- **Given** the converted pactkit-codex source tree
- **When** listing `src/pactkit_codex/` contents
- **Then** ONLY these files remain: `__init__.py`, `deployer.py`, and optionally `prompts/rules.py` (for Codex-specific COMMAND_RULES_MAP). No `config.py`, `schemas.py`, `profiles.py`, `cli.py`, `utils.py`, or `skills/` directory.

### AC5: Brand replacement preserves Codex identity (R7)

- **Given** deployed `AGENTS.md` and `playbooks/*.md`
- **When** searching for "Claude Code", "claude-sonnet", "Anthropic", "~/.claude/"
- **Then** zero matches — all replaced with "Codex CLI", "capable-model", "OpenAI", "~/.codex/"

### AC6: Entry point auto-discovery works (R4, R5)

- **Given** pactkit core is installed AND pactkit-codex is installed
- **When** running `pactkit init --format codex --target /tmp/test`
- **Then** deployment succeeds using CodexDeployer from the adapter package

### AC7: Config.toml generation/merge (R7)

- **Given** an existing `config.toml` with user-defined settings
- **When** `CodexDeployer().deploy(target=dir)` runs
- **Then** user settings are preserved, pactkit-managed sections are updated, and no API keys are written

### AC8: Dependency chain correct (R5, R6)

- **Given** a clean virtualenv
- **When** `pip install pactkit-codex`
- **Then** `pactkit>=2.7.0` is auto-installed as dependency AND `pactkit-codex` version is `2.7.0`

### AC9: Tests pass with core imports (R9)

- **Given** migrated tests importing from `pactkit` core and `pactkit_codex.deployer`
- **When** running `pytest tests/` in the pactkit-codex repo
- **Then** all tests pass

## Target Call Chain

```
pactkit init --format codex
  → cli.py:main() → init(format="codex")
    → _load_entry_point_deployers()  # discovers pactkit-codex via entry_points
    → get_deployer("codex")          # returns CodexDeployer from registry
    → CodexDeployer().deploy(config, target)
      → _deploy_codex_rules()        # Codex-specific: Claude→Codex path/brand replace
      → _deploy_codex_agents_md()    # Codex-specific: single-agent AGENTS.md + 10KB truncation
      → _deploy_codex_playbooks()    # Codex-specific: full playbooks + prereq injection
      → _deploy_codex_prompts()      # Codex-specific: thin wrapper prompts with frontmatter
      → _generate_codex_config_toml() # Codex-specific: TOML config (not YAML/JSON)
      → _generate_codex_project_files() # Codex-specific: project AGENTS.md + .codex/ layout
      → DeployerBase.deploy_skills()  # Shared via core
      → DeployerBase.deploy_rules()   # Shared via core (base deployment)
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `pactkit/src/pactkit/profiles.py` | Add "codex" FormatProfile entry to FORMAT_PROFILES | None | Low |
| 2 | `pactkit-codex/src/pactkit_codex/deployer.py` | Create CodexDeployer(DeployerBase) with all 21 Codex-specific functions | Step 1 | Medium |
| 3 | `pactkit-codex/src/pactkit_codex/__init__.py` | Update to import and re-export CodexDeployer; set version 2.7.0 | Step 2 | Low |
| 4 | `pactkit-codex/pyproject.toml` | Change deps to pactkit>=2.7.0, add entry_points, version 2.7.0 | Step 2 | Low |
| 5 | `pactkit-codex/src/pactkit_codex/` | Delete duplicated modules: config.py, schemas.py, profiles.py, cli.py, utils.py, skills/, prompts/, generators/, and all CLI subcommand modules | Step 2 | High |
| 6 | `pactkit-codex/tests/` | Migrate test imports from pactkit_codex.* to pactkit.* for shared code | Step 5 | Medium |
| 7 | `pactkit-codex/.github/workflows/` | Create publish.yml and ci.yml following opencode pattern | Step 4 | Low |
| 8 | `pactkit-codex/tests/` | Run full test suite, fix broken imports | Step 6 | Medium |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | CodexDeployer writes files to `~/.codex/`; uses atomic_write() from core |
| SEC-2 | N/A | No user input handling — config comes from pactkit.yaml |
| SEC-3 | N/A | No database operations |
| SEC-4 | N/A | No frontend files |
| SEC-5 | N/A | No auth patterns — config.toml FORBIDDEN_KEYS already strips API keys |
| SEC-6 | N/A | No API/route files |
| SEC-7 | N/A | Error handling inherited from core DeployerBase |
| SEC-8 | Yes | pyproject.toml dependency change: standalone → pactkit>=2.7.0 |

## Out of Scope

- Codex CLI own `pactkit-codex` CLI binary (removed — users run `pactkit init --format codex` from core)
- PyPI publishing of pactkit-codex (handled separately after conversion)
- Adding pactkit-codex as core dependency (unlike opencode — codex is niche, on-demand install)
- Backporting codex fork improvements to core (board.py robustness, visualize.py atomic I/O — already landed in v2.5.0)
- New Codex-specific features — this story is pure extraction/conversion
