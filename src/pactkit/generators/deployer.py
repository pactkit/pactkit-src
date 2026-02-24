import json
import sys
from pathlib import Path

import yaml

# 确保能 import pactkit.prompts
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pactkit import __version__, prompts
from pactkit.config import (
    VALID_AGENTS,
    VALID_COMMANDS,
    VALID_RULES,
    VALID_SKILLS,
    auto_merge_config_file,
    generate_default_yaml,
    load_config,
    validate_config,
)
from pactkit.skills import load_script
from pactkit.utils import atomic_write

# Valid output formats
VALID_FORMATS = ('classic', 'plugin', 'marketplace')

# Path prefix constants for deploy-time rewriting (BUG-002)
CLASSIC_SKILLS_PREFIX = "~/.claude/skills"
PLUGIN_SKILLS_PREFIX = "${CLAUDE_PLUGIN_ROOT}/skills"


def _rewrite_skills_prefix(content, skills_prefix):
    """Rewrite ~/.claude/skills references to the target skills_prefix.

    No-op when skills_prefix is the classic default. For plugin mode,
    replaces all occurrences of ~/.claude/skills with ${CLAUDE_PLUGIN_ROOT}/skills.
    """
    if skills_prefix == CLASSIC_SKILLS_PREFIX:
        return content
    return content.replace(CLASSIC_SKILLS_PREFIX, skills_prefix)


def deploy(config=None, target=None, format="classic", **_kwargs):
    """Deploy PactKit configuration.

    Args:
        config: Optional config dict. If None, loads from pactkit.yaml or defaults.
        target: Optional target directory. If None, uses ~/.claude (classic) or
                ./pactkit-plugin (plugin) or ./pactkit-marketplace (marketplace).
        format: Output format — 'classic', 'plugin', or 'marketplace'.
    """
    if format not in VALID_FORMATS:
        raise ValueError(f"Unknown format: {format!r}. Valid: {', '.join(VALID_FORMATS)}")

    if format == "plugin":
        _deploy_plugin(target)
    elif format == "marketplace":
        _deploy_marketplace(target)
    else:
        _deploy_classic(config, target)


def _deploy_classic(config=None, target=None):
    """Classic deployment — write files to ~/.claude/ (original behavior)."""
    # Resolve target directory
    if target is not None:
        claude_root = Path(target)
    else:
        claude_root = Path.home() / ".claude"

    # Migrate legacy scafpy remnants before anything else
    _migrate_from_scafpy(claude_root)

    # Load config if not provided
    if config is None:
        yaml_path = claude_root / "pactkit.yaml"
        # Auto-merge new components before loading (STORY-009)
        auto_added = auto_merge_config_file(yaml_path)
        for item in auto_added:
            print(f"  -> Auto-added: {item}")
        config = load_config(yaml_path)

    validate_config(config)

    print("🚀 PactKit DevOps Deployment")

    # Prepare directories
    agents_dir = claude_root / "agents"
    commands_dir = claude_root / "commands"
    skills_dir = claude_root / "skills"

    for d in [claude_root, agents_dir, commands_dir, skills_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Deploy components filtered by config
    enabled_skills = config.get('skills', [])
    enabled_rules = config.get('rules', [])
    enabled_agents = config.get('agents', [])
    enabled_commands = config.get('commands', [])

    n_skills = _deploy_skills(skills_dir, enabled_skills)
    _cleanup_legacy(skills_dir)
    n_rules = _deploy_rules(claude_root, enabled_rules)
    _deploy_claude_md(claude_root, enabled_rules)
    agent_models = config.get('agent_models', {})
    n_agents = _deploy_agents(agents_dir, enabled_agents, agent_models=agent_models)
    n_commands = _deploy_commands(commands_dir, enabled_commands)

    # Generate pactkit.yaml if it doesn't exist
    _generate_config_if_missing(claude_root)

    # Summary
    total_agents = len(VALID_AGENTS)
    total_commands = len(VALID_COMMANDS)
    total_skills = len(VALID_SKILLS)
    total_rules = len(VALID_RULES)

    print(f"\n✅ Deployed: {n_agents}/{total_agents} Agents, "
          f"{n_commands}/{total_commands} Commands, "
          f"{n_skills}/{total_skills} Skills, "
          f"{n_rules}/{total_rules} Rules")


def _deploy_plugin(target=None):
    """Plugin deployment — generate a self-contained Claude Code plugin directory."""
    plugin_root = Path(target) if target else Path("pactkit-plugin")

    print("🚀 PactKit Plugin Deployment")

    # Prepare directories
    agents_dir = plugin_root / "agents"
    commands_dir = plugin_root / "commands"
    skills_dir = plugin_root / "skills"
    plugin_meta_dir = plugin_root / ".claude-plugin"

    for d in [plugin_root, agents_dir, commands_dir, skills_dir, plugin_meta_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Full deployment — all components enabled
    all_agents = sorted(VALID_AGENTS)
    all_commands = sorted(VALID_COMMANDS)
    all_skills = sorted(VALID_SKILLS)

    # Deploy components (BUG-002: rewrite paths for plugin mode)
    prefix = PLUGIN_SKILLS_PREFIX
    n_skills = _deploy_skills(skills_dir, all_skills, skills_prefix=prefix)
    _deploy_claude_md_inline(plugin_root, skills_prefix=prefix)
    n_agents = _deploy_agents(agents_dir, all_agents, skills_prefix=prefix)
    n_commands = _deploy_commands(commands_dir, all_commands, skills_prefix=prefix)
    _deploy_plugin_json(plugin_meta_dir)

    print(f"\n✅ Plugin: {n_agents} Agents, {n_commands} Commands, "
          f"{n_skills} Skills → {plugin_root}")


def _deploy_marketplace(target=None):
    """Marketplace deployment — generate a marketplace repo with plugin subdirectory."""
    marketplace_root = Path(target) if target else Path("pactkit-marketplace")
    marketplace_root.mkdir(parents=True, exist_ok=True)

    print("🚀 PactKit Marketplace Deployment")

    # Deploy plugin into subdirectory
    plugin_subdir = marketplace_root / "pactkit-plugin"
    _deploy_plugin(target=str(plugin_subdir))

    # Generate marketplace.json
    _deploy_marketplace_json(marketplace_root)

    print(f"\n✅ Marketplace → {marketplace_root}")


def _deploy_skills(skills_dir, enabled_skills, skills_prefix=CLASSIC_SKILLS_PREFIX):
    """Deploy skill directories filtered by config.

    Args:
        skills_prefix: Path prefix for skill script references.
            Classic: ~/.claude/skills (default). Plugin: ${CLAUDE_PLUGIN_ROOT}/skills.
    """
    # Skills with executable scripts
    scripted_skill_defs = [
        {
            'name': 'pactkit-visualize',
            'skill_md': prompts.SKILL_VISUALIZE_MD,
            'script_name': 'visualize.py',
            'script_source': load_script('visualize.py'),
        },
        {
            'name': 'pactkit-board',
            'skill_md': prompts.SKILL_BOARD_MD,
            'script_name': 'board.py',
            'script_source': load_script('board.py'),
        },
        {
            'name': 'pactkit-scaffold',
            'skill_md': prompts.SKILL_SCAFFOLD_MD,
            'script_name': 'scaffold.py',
            'script_source': load_script('scaffold.py'),
        },
    ]

    # Prompt-only skills (SKILL.md only, no executable script) — STORY-011
    prompt_only_skill_defs = [
        {'name': 'pactkit-trace', 'skill_md': prompts.SKILL_TRACE_MD},
        {'name': 'pactkit-draw', 'skill_md': prompts.SKILL_DRAW_MD},
        {'name': 'pactkit-status', 'skill_md': prompts.SKILL_STATUS_MD},
        {'name': 'pactkit-doctor', 'skill_md': prompts.SKILL_DOCTOR_MD},
        {'name': 'pactkit-review', 'skill_md': prompts.SKILL_REVIEW_MD},
        {'name': 'pactkit-release', 'skill_md': prompts.SKILL_RELEASE_MD},
    ]

    enabled_set = set(enabled_skills)
    deployed = 0

    # Deploy scripted skills (SKILL.md + script)
    for sd in scripted_skill_defs:
        if sd['name'] not in enabled_set:
            continue
        skill_dir = skills_dir / sd['name']
        scripts_dir = skill_dir / 'scripts'
        scripts_dir.mkdir(parents=True, exist_ok=True)

        skill_md = _rewrite_skills_prefix(sd['skill_md'], skills_prefix)
        atomic_write(skill_dir / 'SKILL.md', skill_md)
        atomic_write(scripts_dir / sd['script_name'], sd['script_source'])
        deployed += 1

    # Deploy prompt-only skills (SKILL.md only)
    for sd in prompt_only_skill_defs:
        if sd['name'] not in enabled_set:
            continue
        skill_dir = skills_dir / sd['name']
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = _rewrite_skills_prefix(sd['skill_md'], skills_prefix)
        atomic_write(skill_dir / 'SKILL.md', skill_md)
        deployed += 1

    return deployed


def _cleanup_legacy(skills_dir):
    """Clean up legacy pactkit_tools.py."""
    legacy = skills_dir / 'pactkit_tools.py'
    if legacy.exists():
        legacy.unlink()


def _migrate_from_scafpy(claude_root):
    """Migrate legacy scafpy-* remnants to pactkit-* naming.

    - Removes old scafpy-visualize/, scafpy-board/, scafpy-scaffold/ skill dirs
    - Renames scafpy.yaml → pactkit.yaml (or deletes if pactkit.yaml already exists)
    """
    import shutil

    # Clean up legacy skill directories
    skills_dir = claude_root / "skills"
    for old_name in ('scafpy-visualize', 'scafpy-board', 'scafpy-scaffold'):
        old_dir = skills_dir / old_name
        if old_dir.is_dir():
            shutil.rmtree(old_dir)

    # Migrate config file
    old_yaml = claude_root / "scafpy.yaml"
    new_yaml = claude_root / "pactkit.yaml"
    if old_yaml.is_file():
        if not new_yaml.exists():
            old_yaml.rename(new_yaml)
        else:
            old_yaml.unlink()


def _deploy_rules(claude_root, enabled_rules):
    """Deploy rule modules filtered by config."""
    rules_dir = claude_root / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    # Build reverse map: rule identifier -> config key
    # e.g. '01-core-protocol' -> 'core'
    rule_id_to_key = {}
    for key, filename in prompts.RULES_FILES.items():
        rule_id = filename.removesuffix('.md')
        rule_id_to_key[rule_id] = key

    # Clean managed rule files
    for f in rules_dir.glob('*.md'):
        if any(f.name.startswith(p) for p in prompts.RULES_MANAGED_PREFIXES):
            f.unlink()

    # Write only enabled rules
    deployed = 0
    for rule_id in enabled_rules:
        key = rule_id_to_key.get(rule_id)
        if key is None:
            continue
        filename = prompts.RULES_FILES[key]
        atomic_write(rules_dir / filename, prompts.RULES_MODULES[key])
        deployed += 1

    return deployed


def _deploy_claude_md(claude_root, enabled_rules):
    """Generate CLAUDE.md with @import only for enabled rules."""
    # Build reverse map: rule identifier -> filename
    rule_id_to_filename = {}
    for key, filename in prompts.RULES_FILES.items():
        rule_id = filename.removesuffix('.md')
        rule_id_to_filename[rule_id] = filename

    lines = ["# PactKit Global Constitution (v23.0 Modular)", ""]
    for rule_id in sorted(enabled_rules):
        filename = rule_id_to_filename.get(rule_id)
        if filename:
            lines.append(f"@~/.claude/rules/{filename}")

    lines.append("")
    lines.append("@./docs/product/context.md")
    lines.append("")  # trailing newline
    atomic_write(claude_root / "CLAUDE.md", "\n".join(lines))


def _deploy_agents(agents_dir, enabled_agents, skills_prefix=CLASSIC_SKILLS_PREFIX,
                    agent_models=None):
    """Deploy agent definitions filtered by config.

    Args:
        skills_prefix: Path prefix for skill script references.
            Classic: ~/.claude/skills (default). Plugin: ${CLAUDE_PLUGIN_ROOT}/skills.
        agent_models: Optional dict of agent_name -> model overrides from pactkit.yaml.
    """
    if agent_models is None:
        agent_models = {}
    enabled_set = set(enabled_agents)

    # Clean up managed agent files not in enabled set
    managed_agent_files = {f"{name}.md" for name in prompts.AGENTS_EXPERT}
    if agents_dir.exists():
        for f in agents_dir.glob('*.md'):
            if f.name in managed_agent_files and f.stem not in enabled_set:
                f.unlink()

    # Fields serialized as simple key: value (no nesting)
    SIMPLE_OPTIONAL_FIELDS = ['permissionMode', 'disallowedTools', 'maxTurns', 'memory', 'skills']
    # Fields that require YAML serialization (nested structures)
    NESTED_FIELDS = ['hooks']

    deployed = 0
    for name, cfg in prompts.AGENTS_EXPERT.items():
        if name not in enabled_set:
            continue
        agent_path = agents_dir / f"{name}.md"

        # Resolve model: agent_models override > AGENTS_EXPERT default > 'inherit'
        model = agent_models.get(name, cfg.get('model', 'inherit'))

        content = [
            "---",
            f"name: {name}",
            f"description: {cfg['desc']}",
            f"tools: {cfg['tools']}",
            f"model: {model}",
        ]
        for field in SIMPLE_OPTIONAL_FIELDS:
            if field in cfg:
                content.append(f"{field}: {cfg[field]}")
        # Serialize nested fields using PyYAML for correct indentation
        for field in NESTED_FIELDS:
            if field in cfg:
                nested_yaml = yaml.dump(
                    {field: cfg[field]},
                    default_flow_style=False,
                    allow_unicode=True,
                ).rstrip()
                content.append(nested_yaml)
        content.extend([
            "---",
            "",
            cfg['prompt'],
            "",
            "Please refer to ~/.claude/CLAUDE.md for routing."
        ])
        rewritten = _rewrite_skills_prefix("\n".join(content), skills_prefix)
        atomic_write(agent_path, rewritten)
        deployed += 1

    return deployed


def _deploy_commands(commands_dir, enabled_commands, skills_prefix=CLASSIC_SKILLS_PREFIX):
    """Deploy command playbooks filtered by config.

    Args:
        skills_prefix: Path prefix for skill script references.
            Classic: ~/.claude/skills (default). Plugin: ${CLAUDE_PLUGIN_ROOT}/skills.
    """
    enabled_set = set(enabled_commands)

    # Build map: command name -> filename
    # e.g. 'project-plan' -> 'project-plan.md'
    enabled_filenames = {f"{cmd}.md" for cmd in enabled_commands}

    # Clean managed command files not in enabled set
    if commands_dir.exists():
        for f in commands_dir.glob('*.md'):
            if f.name.startswith("project-") and f.name not in enabled_filenames:
                f.unlink()

    # Deploy enabled commands
    deployed = 0
    for filename, content in prompts.COMMANDS_CONTENT.items():
        cmd_name = filename.removesuffix('.md')
        if cmd_name not in enabled_set:
            continue
        rewritten = _rewrite_skills_prefix(content, skills_prefix)
        atomic_write(commands_dir / filename, rewritten)
        deployed += 1

    return deployed


def _generate_config_if_missing(claude_root):
    """Generate pactkit.yaml with defaults if it doesn't exist."""
    yaml_path = claude_root / "pactkit.yaml"
    if not yaml_path.exists():
        atomic_write(yaml_path, generate_default_yaml())


# ---------------------------------------------------------------------------
# Plugin-format helpers
# ---------------------------------------------------------------------------

def _deploy_plugin_json(plugin_meta_dir):
    """Generate .claude-plugin/plugin.json manifest."""
    manifest = {
        "name": "pactkit",
        "version": __version__,
        "description": "Spec-driven agentic DevOps toolkit — PDCA workflows, "
                       "role-based agents, and behavioral governance for Claude Code",
        "author": {
            "name": "PactKit",
            "url": "https://github.com/pactkit",
        },
        "homepage": "https://pactkit.dev",
        "repository": "https://github.com/pactkit/pactkit",
        "license": "MIT",
        "keywords": [
            "devops", "pdca", "spec-driven", "tdd", "governance",
            "claude-code", "ai-agent", "multi-agent",
        ],
    }
    content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    atomic_write(plugin_meta_dir / "plugin.json", content)


def _deploy_claude_md_inline(plugin_root, skills_prefix=CLASSIC_SKILLS_PREFIX):
    """Generate CLAUDE.md with all rules inlined (no @import references)."""
    # Build reverse map: rule_id -> key for ordered iteration
    rule_id_to_key = {}
    for key, filename in prompts.RULES_FILES.items():
        rule_id = filename.removesuffix('.md')
        rule_id_to_key[rule_id] = key

    lines = ["# PactKit Global Constitution (v23.0 Modular)", ""]

    # Inline all rule modules in sorted order
    for rule_id in sorted(rule_id_to_key.keys()):
        key = rule_id_to_key[rule_id]
        module_content = prompts.RULES_MODULES[key].strip()
        lines.append(module_content)
        lines.append("")  # blank line between modules

    # Add TIP for cross-session context (plugin mode has no context.md by default)
    lines.append("> **TIP**: Run `/project-init` to set up project governance"
                 " and enable cross-session context.")
    lines.append("")

    rewritten = _rewrite_skills_prefix("\n".join(lines), skills_prefix)
    atomic_write(plugin_root / "CLAUDE.md", rewritten)


def _deploy_marketplace_json(marketplace_root):
    """Generate marketplace.json for Claude Code plugin marketplace."""
    manifest = {
        "name": "pactkit",
        "owner": {
            "name": "PactKit",
        },
        "metadata": {
            "description": "Spec-driven agentic DevOps toolkit for Claude Code",
            "homepage": "https://pactkit.dev",
        },
        "plugins": [
            {
                "name": "pactkit",
                "source": "./pactkit-plugin",
                "version": __version__,
                "description": "PDCA workflows, role-based agents, "
                               "and behavioral governance",
            },
        ],
    }
    content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    atomic_write(marketplace_root / "marketplace.json", content)
