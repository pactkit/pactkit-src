"""PactKit configuration — load, validate, and generate pactkit.yaml."""
import warnings
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

# Commands deprecated in v1.2.0 — converted to skills (STORY-011)
DEPRECATED_COMMANDS = frozenset({
    'project-trace',
    'project-draw',
    'project-status',
    'project-doctor',
    'project-review',
    'project-release',
})


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
    }


# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

def load_config(path: Path | str | None = None) -> dict:
    """Load pactkit.yaml from *path*, merging with defaults.

    If *path* is ``None``, uses ``~/.claude/pactkit.yaml``.
    If the file does not exist, returns the full default config.
    Missing keys in the user file inherit from defaults.
    """
    if path is None:
        path = Path.home() / '.claude' / 'pactkit.yaml'
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

    # Merge: user keys override defaults; missing keys inherit
    merged = dict(default)
    for key, value in user_data.items():
        if key in merged:
            merged[key] = value

    return merged


# ---------------------------------------------------------------------------
# Auto-merge new components
# ---------------------------------------------------------------------------

def auto_merge_config_file(path: Union[Path, str]) -> list[str]:
    """Auto-merge new components into an existing pactkit.yaml.

    For each list-type key (agents, commands, skills, rules), appends items
    from the VALID_* registry that are missing from the user's list and not
    present in the ``exclude`` section.

    Modifies the YAML file in-place.  Returns a list of ``"key: item"``
    strings describing what was added (empty list when nothing changed).
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

    for key, valid_set in _REGISTRY.items():
        user_list = user_data.get(key)
        if user_list is None:
            # Key not in user yaml → will inherit defaults via load_config
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

    if added:
        _rewrite_yaml(path, user_data)

    return added


def _rewrite_yaml(path: Path, data: dict) -> None:
    """Rewrite pactkit.yaml preserving the standard section layout."""
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

    lines.append('')  # trailing newline
    return '\n'.join(lines)
