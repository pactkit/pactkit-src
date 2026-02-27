"""PactKit configuration — load, validate, and generate pactkit.yaml."""
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

import yaml

# ---------------------------------------------------------------------------
# Valid identifiers (the registry of all known components)
# ---------------------------------------------------------------------------

VALID_AGENTS = frozenset({
    'system-architect',
    'senior-developer',
    'qa-engineer',
    'repo-maintainer',
    'system-medic',
    'security-auditor',
    'visual-architect',
    'code-explorer',
    'product-designer',
})

VALID_COMMANDS = frozenset({
    'project-plan',
    'project-act',
    'project-check',
    'project-done',
    'project-init',
    'project-sprint',
    'project-hotfix',
    'project-design',
    'project-clarify',
    'project-release',
    'project-pr',
})

VALID_SKILLS = frozenset({
    'pactkit-visualize',
    'pactkit-board',
    'pactkit-scaffold',
    'pactkit-trace',
    'pactkit-draw',
    'pactkit-status',
    'pactkit-doctor',
    'pactkit-review',
    'pactkit-release',
    'pactkit-analyze',
})

VALID_RULES = frozenset({
    '01-core-protocol',
    '02-hierarchy-of-truth',
    '03-file-atlas',
    '04-routing-table',
    '05-workflow-conventions',
    '06-mcp-integration',
})

VALID_STACKS = frozenset({'auto', 'python', 'node', 'go', 'java'})

VALID_MODELS = frozenset({'haiku', 'sonnet', 'opus', 'inherit'})

VALID_CI_PROVIDERS = frozenset({'github', 'gitlab', 'none'})

VALID_ISSUE_PROVIDERS = frozenset({'github', 'none'})

VALID_HOOK_TEMPLATES = frozenset({'pre_commit_lint', 'post_test_coverage', 'pre_push_check'})

# Commands deprecated in v1.2.0 — converted to skills (STORY-011)
DEPRECATED_COMMANDS = frozenset({
    'project-trace',
    'project-draw',
    'project-status',
    'project-doctor',
    'project-review',
})


# ---------------------------------------------------------------------------
# Enterprise configuration dataclasses (STORY-047)
# ---------------------------------------------------------------------------

@dataclass
class EnterpriseConfig:
    """Enterprise environment configuration flags.

    Supports air-gapped, TLS-inspected, CI/CD, and permission-restricted
    environments.  All flags default to False (standard behavior).
    """
    no_git: bool = False           # disable all git operations
    no_external: bool = False      # disable external network (MCP, gh CLI, pip install)
    non_interactive: bool = False  # non-interactive mode (CI/CD, auto-accept defaults)
    debug: bool = False            # verbose logging


@dataclass
class PactKitConfig:
    """Structured representation of pactkit.yaml configuration.

    Wraps the enterprise section as a typed EnterpriseConfig object.
    The raw dict form is still used throughout the codebase; this class
    is the typed interface for enterprise flag access.
    """
    enterprise: EnterpriseConfig = field(default_factory=EnterpriseConfig)


# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------

def get_default_config() -> dict:
    """Return the default config with all components enabled."""
    return {
        'version': '0.0.1',
        'stack': 'auto',
        'root': '.',
        'agents': sorted(VALID_AGENTS),
        'commands': sorted(VALID_COMMANDS),
        'skills': sorted(VALID_SKILLS),
        'rules': sorted(VALID_RULES),
        'ci': {'provider': 'none'},
        'issue_tracker': {'provider': 'none'},
        'hooks': {
            'pre_commit_lint': False,
            'post_test_coverage': False,
            'pre_push_check': False,
        },
        'lint_blocking': False,
        'auto_fix': False,
        'venv': {
            'auto_detect': True,
        },
    }


# ---------------------------------------------------------------------------
# Virtual environment detection (STORY-039)
# ---------------------------------------------------------------------------

# Common venv directory names in priority order
VENV_CANDIDATES = ('.venv', 'venv', 'env')


def detect_venv(project_root: Path) -> tuple[str, str] | None:
    """Detect virtual environment directory in project root.

    Checks common venv directory names in order: .venv, venv, env.
    Returns the first directory that contains bin/python3 (Unix)
    or Scripts/python.exe (Windows).

    Args:
        project_root: Project root directory to search.

    Returns:
        Tuple of (venv_directory_name, layout) where layout is 'unix' or 'windows',
        or None if no venv found.

        BUG-021: Now returns layout information for platform-aware command generation.
    """
    for candidate in VENV_CANDIDATES:
        venv_path = project_root / candidate
        # Check Unix-style venv (bin/python3 or bin/python)
        if (venv_path / 'bin' / 'python3').exists():
            return (candidate, 'unix')
        if (venv_path / 'bin' / 'python').exists():
            return (candidate, 'unix')
        # Check Windows-style venv (Scripts/python.exe)
        if (venv_path / 'Scripts' / 'python.exe').exists():
            return (candidate, 'windows')
    return None


# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

def load_config(path: Path | str | None = None) -> dict:
    """Load pactkit.yaml from *path*, merging with defaults.

    If *path* is ``None``, uses ``$CWD/.claude/pactkit.yaml`` (BUG-013).
    If the file does not exist, returns the full default config.
    Missing keys in the user file inherit from defaults.

    BUG-022: For nested dict sections (venv, ci, hooks, issue_tracker),
    performs deep merge to preserve default sub-keys when user specifies partial config.
    """
    if path is None:
        path = Path.cwd() / '.claude' / 'pactkit.yaml'
    else:
        path = Path(path)

    default = get_default_config()

    if not path.exists():
        return default

    raw = path.read_text(encoding='utf-8')
    user_data = yaml.safe_load(raw)

    # Empty file or YAML that parses to None
    if not isinstance(user_data, dict):
        return default

    # Keys that require deep merge (nested dict sections)
    DEEP_MERGE_KEYS = {'venv', 'ci', 'hooks', 'issue_tracker'}

    # Merge: user keys override defaults; missing keys inherit
    merged = dict(default)
    for key, value in user_data.items():
        if key in merged:
            # BUG-022: Deep merge for nested dict sections
            if key in DEEP_MERGE_KEYS and isinstance(merged[key], dict) and isinstance(value, dict):
                # Preserve default sub-keys, override with user values
                merged[key] = {**merged[key], **value}
            else:
                # Shallow override for non-dict keys (strings, lists, booleans)
                merged[key] = value
        else:
            # Pass through unknown/extension keys (e.g. multi_agent, enterprise)
            merged[key] = value

    return merged


# ---------------------------------------------------------------------------
# Auto-merge new components
# ---------------------------------------------------------------------------

def auto_merge_config_file(path: Union[Path, str]) -> list[str]:
    """Auto-merge new components and backfill missing sections in pactkit.yaml.

    For each list-type key (agents, commands, skills, rules), appends items
    from the VALID_* registry that are missing from the user's list and not
    present in the ``exclude`` section.

    For non-list config sections (ci, issue_tracker, hooks, lint_blocking,
    auto_fix), backfills missing sections with defaults from
    ``get_default_config()``.  Existing user values are never overwritten.

    Modifies the YAML file in-place.  Returns a list of ``"key: item"``
    or ``"section: key"`` strings describing what was added (empty list
    when nothing changed).
    """
    path = Path(path)
    if not path.exists():
        return []

    raw = path.read_text(encoding='utf-8')
    user_data = yaml.safe_load(raw)

    if not isinstance(user_data, dict):
        return []

    exclude = user_data.get('exclude', {})
    if not isinstance(exclude, dict):
        exclude = {}

    added: list[str] = []

    # --- List-type keys: merge new items ---
    for key, valid_set in _REGISTRY.items():
        user_list = user_data.get(key)
        if user_list is None:
            # BUG-013: key missing from user yaml → backfill full default list
            excluded_items = set(exclude.get(key, []) or [])
            new_items = sorted(
                item for item in valid_set if item not in excluded_items
            )
            user_data[key] = new_items
            added.append(f"section: {key}")
            continue
        if not isinstance(user_list, list):
            continue

        excluded_items = set(exclude.get(key, []) or [])
        user_set = set(user_list)
        new_items = sorted(
            item for item in valid_set
            if item not in user_set and item not in excluded_items
        )

        if new_items:
            user_data[key] = user_list + new_items
            for item in new_items:
                added.append(f"{key}: {item}")

    # --- Non-list sections: backfill missing with defaults (STORY-033, STORY-039) ---
    defaults = get_default_config()
    _BACKFILL_KEYS = ('ci', 'issue_tracker', 'hooks', 'lint_blocking', 'auto_fix', 'venv')
    for key in _BACKFILL_KEYS:
        if key not in user_data:
            user_data[key] = defaults[key]
            added.append(f"section: {key}")

    if added:
        _rewrite_yaml(path, user_data)

    return added


def _rewrite_yaml(path: Path, data: dict) -> None:
    """Rewrite pactkit.yaml preserving the standard section layout.

    BUG-023: Preserves unknown user-defined keys in a separate section.
    """
    # Known keys that PactKit manages
    KNOWN_KEYS = {
        'version', 'stack', 'root',
        'agents', 'commands', 'skills', 'rules',
        'exclude', 'ci', 'issue_tracker', 'hooks',
        'lint_blocking', 'auto_fix', 'venv',
        'agent_models', 'rule_scopes',
    }

    lines = [
        '# PactKit Configuration',
        '# Edit this file to customize which components are deployed.',
        '# Remove items from a list to disable them. Default: all enabled.',
        '',
        f'version: "{data.get("version", "0.0.1")}"',
        f'stack: {data.get("stack", "auto")}',
        f'root: {data.get("root", ".")}',
        '',
    ]

    section_comments = {
        'agents': '# Agents — AI role definitions deployed to ~/.claude/agents/',
        'commands': '# Commands — PDCA playbooks deployed to ~/.claude/commands/',
        'skills': '# Skills — tool scripts deployed to ~/.claude/skills/',
        'rules': '# Rules — constitution modules deployed to ~/.claude/rules/',
    }

    for key in ('agents', 'commands', 'skills', 'rules'):
        items = data.get(key)
        if items is None:
            continue
        comment = section_comments.get(key, '')
        if comment:
            lines.append(comment)
        lines.append(f'{key}:')
        for item in items:
            lines.append(f'  - {item}')
        lines.append('')

    # Write exclude section if present
    exclude = data.get('exclude', {})
    if exclude and isinstance(exclude, dict):
        lines.append('# Exclude — components that should NOT be auto-added on upgrade')
        lines.append('exclude:')
        for key in ('agents', 'commands', 'skills', 'rules'):
            items = exclude.get(key)
            if items:
                lines.append(f'  {key}:')
                for item in items:
                    lines.append(f'    - {item}')
        lines.append('')

    # Write CI/CD section
    ci = data.get('ci', {})
    if isinstance(ci, dict):
        lines.append('# CI/CD — set provider to github or gitlab to generate pipeline config')
        lines.append('ci:')
        lines.append(f'  provider: {ci.get("provider", "none")}')
        lines.append('')

    # Write issue tracker section
    issue_tracker = data.get('issue_tracker', {})
    if isinstance(issue_tracker, dict):
        lines.append('# Issue Tracker — set provider to github to link stories to issues')
        lines.append('issue_tracker:')
        lines.append(f'  provider: {issue_tracker.get("provider", "none")}')
        lines.append('')

    # Write hooks section
    hooks = data.get('hooks', {})
    if isinstance(hooks, dict):
        lines.append('# Hooks — safe, report-only hook templates (command-type only)')
        lines.append('hooks:')
        for hook_name in sorted(hooks.keys()):
            lines.append(f'  {hook_name}: {"true" if hooks[hook_name] else "false"}')
        lines.append('')

    # Write lint/auto_fix settings
    lines.append('# Lint — configure lint behavior in /project-done')
    lines.append(f'lint_blocking: {"true" if data.get("lint_blocking") else "false"}')
    lines.append(f'auto_fix: {"true" if data.get("auto_fix") else "false"}')
    lines.append('')

    # Write venv section (STORY-039)
    venv = data.get('venv', {})
    if isinstance(venv, dict):
        lines.append('# Virtual Environment — configure venv detection and paths')
        lines.append('venv:')
        auto_detect = venv.get('auto_detect', True)
        lines.append(f'  auto_detect: {"true" if auto_detect else "false"}')
        if 'path' in venv:
            lines.append(f'  path: {venv["path"]}')
        lines.append('')

    # Write agent_models section if present (BUG-010)
    agent_models = data.get('agent_models', {})
    if agent_models and isinstance(agent_models, dict):
        lines.append('# Agent Models — override default model per agent (inherit = use account default)')
        lines.append('agent_models:')
        for agent_name in sorted(agent_models.keys()):
            lines.append(f'  {agent_name}: {agent_models[agent_name]}')
        lines.append('')

    # Write rule_scopes section if present (BUG-010)
    rule_scopes = data.get('rule_scopes', {})
    if rule_scopes and isinstance(rule_scopes, dict):
        lines.append('# Rule Scopes — map rule IDs to glob patterns for context-aware scoping')
        lines.append('rule_scopes:')
        for rule_id in sorted(rule_scopes.keys()):
            pattern = rule_scopes[rule_id]
            if isinstance(pattern, list):
                lines.append(f'  {rule_id}:')
                for p in pattern:
                    lines.append(f'    - "{p}"')
            else:
                lines.append(f'  {rule_id}: "{pattern}"')
        lines.append('')

    # BUG-023: Preserve unknown user-defined keys
    unknown_keys = {k: v for k, v in data.items() if k not in KNOWN_KEYS}
    if unknown_keys:
        lines.append('# Custom — user-defined keys (preserved by PactKit)')
        for key in sorted(unknown_keys.keys()):
            value = unknown_keys[key]
            # Serialize using PyYAML for nested structures
            serialized = yaml.dump({key: value}, default_flow_style=False, allow_unicode=True)
            lines.append(serialized.rstrip())
        lines.append('')

    path.write_text('\n'.join(lines), encoding='utf-8')


# ---------------------------------------------------------------------------
# Validate config
# ---------------------------------------------------------------------------

_REGISTRY = {
    'agents': VALID_AGENTS,
    'commands': VALID_COMMANDS,
    'skills': VALID_SKILLS,
    'rules': VALID_RULES,
}


def validate_config(config: dict) -> None:
    """Warn (never raise) about unknown component names or invalid values."""
    # Validate stack
    stack = config.get('stack', 'auto')
    if stack not in VALID_STACKS:
        warnings.warn(f"Unknown stack: {stack}. Valid: {', '.join(sorted(VALID_STACKS))}")

    # Validate component lists
    for key, valid_set in _REGISTRY.items():
        user_list = config.get(key, [])
        if not isinstance(user_list, list):
            warnings.warn(f"Config key '{key}' should be a list, got {type(user_list).__name__}")
            continue
        for name in user_list:
            if not isinstance(name, str):
                warnings.warn(f"Config key '{key}' contains non-string value: {name!r}")
            elif key == 'commands' and name in DEPRECATED_COMMANDS:
                skill_name = f"pactkit-{name.removeprefix('project-')}"
                warnings.warn(
                    f"Deprecated command '{name}' — converted to skill "
                    f"'{skill_name}' in v1.2.0. Remove from commands list."
                )
            elif name not in valid_set:
                warnings.warn(f"Unknown {key.rstrip('s')}: {name}")

    # Validate agent_models (STORY-024)
    agent_models = config.get('agent_models', {})
    if isinstance(agent_models, dict):
        for agent_name, model_val in agent_models.items():
            if agent_name not in VALID_AGENTS:
                warnings.warn(f"Unknown agent in agent_models: {agent_name}")
            if model_val not in VALID_MODELS:
                warnings.warn(
                    f"Invalid model '{model_val}' for agent '{agent_name}'. "
                    f"Valid: {', '.join(sorted(VALID_MODELS))}"
                )

    # Validate ci section (STORY-025)
    ci = config.get('ci', {})
    if isinstance(ci, dict):
        provider = ci.get('provider', 'none')
        if provider not in VALID_CI_PROVIDERS:
            warnings.warn(
                f"Invalid CI provider '{provider}'. "
                f"Valid: {', '.join(sorted(VALID_CI_PROVIDERS))}"
            )

    # Validate issue_tracker section (STORY-026)
    issue_tracker = config.get('issue_tracker', {})
    if isinstance(issue_tracker, dict):
        provider = issue_tracker.get('provider', 'none')
        if provider not in VALID_ISSUE_PROVIDERS:
            warnings.warn(
                f"Invalid issue tracker provider '{provider}'. "
                f"Valid: {', '.join(sorted(VALID_ISSUE_PROVIDERS))}"
            )

    # Validate hooks section (STORY-027)
    hooks = config.get('hooks', {})
    if isinstance(hooks, dict):
        for hook_name in hooks:
            if hook_name not in VALID_HOOK_TEMPLATES:
                warnings.warn(
                    f"Unknown hook template '{hook_name}'. "
                    f"Valid: {', '.join(sorted(VALID_HOOK_TEMPLATES))}"
                )

    # Validate rule_scopes section (STORY-028)
    rule_scopes = config.get('rule_scopes', {})
    if isinstance(rule_scopes, dict):
        for rule_id, pattern in rule_scopes.items():
            if rule_id not in VALID_RULES:
                warnings.warn(f"Unknown rule in rule_scopes: {rule_id}")
            if isinstance(pattern, str) and '[' in pattern and ']' not in pattern:
                warnings.warn(
                    f"Invalid glob pattern for rule '{rule_id}': {pattern}"
                )

    # Validate venv section (STORY-039)
    venv = config.get('venv', {})
    if isinstance(venv, dict):
        venv_path = venv.get('path')
        if venv_path is not None and not isinstance(venv_path, str):
            warnings.warn(f"venv.path should be a string, got {type(venv_path).__name__}")

    # enterprise section (STORY-047) — accepted without warnings
    # multi_agent field (STORY-046) — accepted without warnings


# ---------------------------------------------------------------------------
# YAML generation
# ---------------------------------------------------------------------------

def generate_default_yaml() -> str:
    """Return the default config as a commented YAML string."""
    cfg = get_default_config()
    lines = [
        '# PactKit Configuration',
        '# Edit this file to customize which components are deployed.',
        '# Remove items from a list to disable them. Default: all enabled.',
        '',
        f'version: "{cfg["version"]}"',
        f'stack: {cfg["stack"]}',
        f'root: {cfg["root"]}',
        '',
        '# Agents — AI role definitions deployed to ~/.claude/agents/',
        'agents:',
    ]
    for a in cfg['agents']:
        lines.append(f'  - {a}')

    lines.extend(['', '# Commands — PDCA playbooks deployed to ~/.claude/commands/'])
    lines.append('commands:')
    for c in cfg['commands']:
        lines.append(f'  - {c}')

    lines.extend(['', '# Skills — tool scripts deployed to ~/.claude/skills/'])
    lines.append('skills:')
    for s in cfg['skills']:
        lines.append(f'  - {s}')

    lines.extend(['', '# Rules — constitution modules deployed to ~/.claude/rules/'])
    lines.append('rules:')
    for r in cfg['rules']:
        lines.append(f'  - {r}')

    lines.extend(['', '# CI/CD — set provider to github or gitlab to generate pipeline config'])
    lines.append('ci:')
    lines.append(f'  provider: {cfg.get("ci", {}).get("provider", "none")}')

    lines.extend(['', '# Issue Tracker — set provider to github to link stories to issues'])
    lines.append('issue_tracker:')
    lines.append(f'  provider: {cfg.get("issue_tracker", {}).get("provider", "none")}')

    hooks = cfg.get('hooks', {})
    lines.extend(['', '# Hooks — safe, report-only hook templates (command-type only)'])
    lines.append('hooks:')
    for hook_name in sorted(hooks.keys()):
        lines.append(f'  {hook_name}: {"true" if hooks[hook_name] else "false"}')

    lines.extend(['', '# Lint — configure lint behavior in /project-done'])
    lines.append(f'lint_blocking: {"true" if cfg.get("lint_blocking") else "false"}')
    lines.append(f'auto_fix: {"true" if cfg.get("auto_fix") else "false"}')

    # Write venv section (STORY-039)
    venv = cfg.get('venv', {})
    lines.extend(['', '# Virtual Environment — configure venv detection and paths'])
    lines.append('venv:')
    lines.append(f'  auto_detect: {"true" if venv.get("auto_detect", True) else "false"}')
    # Don't include path in default — let auto_detect find it

    lines.append('')  # trailing newline
    return '\n'.join(lines)
