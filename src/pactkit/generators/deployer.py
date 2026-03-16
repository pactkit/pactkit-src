import json
import re
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
    detect_venv,
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


# STORY-062: MCP server recommendations
MCP_RECOMMENDATIONS = [
    {"name": "Context7", "purpose": "Library docs lookup (Act phase)"},
    {"name": "Memory", "purpose": "Cross-session context (Plan/Act/Done)"},
    {"name": "Playwright", "purpose": "Browser testing (Check phase)"},
    {"name": "Draw.io", "purpose": "Diagram editing (Plan phase)"},
    {"name": "shadcn", "purpose": "UI components (frontend projects)"},
    {"name": "Chrome DevTools", "purpose": "Performance tracing (Check phase)"},
]


def _print_mcp_recommendations():
    """Print recommended MCP servers after deployment."""
    print("\n📦 Recommended MCP Servers (optional, enhance PactKit features):")
    for mcp in MCP_RECOMMENDATIONS:
        print(f"   • {mcp['name']:15} — {mcp['purpose']}")
    print("   Configure in Claude Code settings.json → mcpServers")


def deploy(config=None, target=None, format="classic",
           no_git=False, no_external=False, non_interactive=False,
           mode=None):
    """Deploy PactKit configuration.

    Args:
        config: Optional config dict. If None, loads from pactkit.yaml or defaults.
        target: Optional target directory. If None, uses ~/.claude (classic) or
                ./pactkit-plugin (plugin) or ./pactkit-marketplace (marketplace).
        format: Output format — 'classic', 'plugin', or 'marketplace'.
        no_git: Disable all git operations (enterprise: air-gapped environments).
        no_external: Disable external network calls (enterprise).
        non_interactive: Non-interactive mode: auto-accept defaults (CI/CD).
        mode: Deprecated, ignored. Kept for backward compatibility.
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

    # Load config from project-level $CWD/.claude/pactkit.yaml (BUG-013)
    if config is None:
        project_yaml = Path.cwd() / ".claude" / "pactkit.yaml"
        # Auto-merge new components before loading (STORY-009)
        auto_added = auto_merge_config_file(project_yaml)
        for item in auto_added:
            print(f"  -> Auto-added: {item}")
        config = load_config(project_yaml)

    validate_config(config)

    # Warn about orphaned global config (BUG-013)
    global_yaml = claude_root / "pactkit.yaml"
    if global_yaml.exists() and global_yaml != Path.cwd() / ".claude" / "pactkit.yaml":
        print(f"  ⚠️  Found orphaned {global_yaml} — config is now read from $CWD/.claude/pactkit.yaml")

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
    rule_scopes = config.get('rule_scopes', {})
    n_rules = _deploy_rules(claude_root, enabled_rules, rule_scopes=rule_scopes)
    _deploy_claude_md(claude_root, enabled_rules)
    agent_models = config.get('agent_models', {})
    n_agents = _deploy_agents(agents_dir, enabled_agents, agent_models=agent_models)
    n_commands = _deploy_commands(commands_dir, enabled_commands)

    # Deploy CI pipeline if configured (STORY-025)
    ci_config = config.get('ci', {})
    ci_provider = ci_config.get('provider', 'none') if isinstance(ci_config, dict) else 'none'
    project_root = Path.cwd()
    _deploy_ci(ci_provider, project_root, config)

    # Deploy hooks if configured (STORY-027)
    hooks_config = config.get('hooks', {})
    _deploy_hooks(claude_root / 'hooks', hooks_config, stack=config.get('stack', 'auto'))

    # Generate pactkit.yaml at project-level if it doesn't exist (BUG-013)
    _generate_config_if_missing()

    # Generate project-level CLAUDE.md (always regenerate) and CLAUDE.local.md (if missing) (STORY-040)
    # Skip when target is specified (preview mode) to avoid modifying real project
    if target is None:
        _generate_project_claude_md(config)

    # Summary
    total_agents = len(VALID_AGENTS)
    total_commands = len(VALID_COMMANDS)
    total_skills = len(VALID_SKILLS)
    total_rules = len(VALID_RULES)

    print(f"\n✅ Deployed: {n_agents}/{total_agents} Agents, "
          f"{n_commands}/{total_commands} Commands, "
          f"{n_skills}/{total_skills} Skills, "
          f"{n_rules}/{total_rules} Rules")
    _print_mcp_recommendations()


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
    _print_mcp_recommendations()


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
        {'name': 'pactkit-analyze', 'skill_md': prompts.SKILL_ANALYZE_MD},
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


def _deploy_rules(claude_root, enabled_rules, rule_scopes=None):
    """Deploy rule modules filtered by config.

    Args:
        rule_scopes: Optional dict of rule_id -> glob pattern for includeFiles.
    """
    if rule_scopes is None:
        rule_scopes = {}
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
        content = prompts.RULES_MODULES[key]

        # Add includeFiles frontmatter if scope is defined (STORY-028)
        scope = rule_scopes.get(rule_id)
        if scope:
            if isinstance(scope, list):
                include_lines = '\n'.join(f'  - "{p}"' for p in scope)
                frontmatter = f"---\nincludeFiles:\n{include_lines}\n---\n\n"
            else:
                frontmatter = f'---\nincludeFiles: ["{scope}"]\n---\n\n'
            content = frontmatter + content

        atomic_write(rules_dir / filename, content)
        deployed += 1

    return deployed


def _deploy_claude_md(claude_root, enabled_rules):
    """Generate CLAUDE.md with @import only for enabled rules."""
    # Build reverse map: rule identifier -> filename
    rule_id_to_filename = {}
    for key, filename in prompts.RULES_FILES.items():
        rule_id = filename.removesuffix('.md')
        rule_id_to_filename[rule_id] = filename

    lines = [f"# PactKit Global Constitution (v{__version__} Modular)", ""]
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


# ---------------------------------------------------------------------------
# CI/CD pipeline generation (STORY-025)
# ---------------------------------------------------------------------------

_GITHUB_WORKFLOW_TEMPLATE = """\
name: PactKit CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]" || pip install -e .
          pip install pytest ruff
          pactkit init

      - name: Lint
        run: {lint_command}

      - name: Test
        run: pytest tests/ -v
"""

_GITLAB_CI_TEMPLATE = """\
stages:
  - lint
  - test

lint:
  stage: lint
  image: python:3.11
  script:
    - pip install ruff
    - {lint_command}

test:
  stage: test
  image: python:3.11
  script:
    - pip install -e ".[dev]" || pip install -e .
    - pip install pytest
    - pytest tests/ -v
"""


def _deploy_ci(provider, project_root, config):
    """Deploy CI pipeline config based on provider setting.

    Args:
        provider: CI provider name ('github', 'gitlab', 'none').
        project_root: Project root directory (parent of .claude/).
        config: Full pactkit config dict.
    """
    if provider == 'none' or provider not in ('github', 'gitlab'):
        return

    # Detect lint command from LANG_PROFILES
    from pactkit.prompts.workflows import LANG_PROFILES
    stack = config.get('stack', 'auto')
    if stack == 'auto':
        stack = 'python'  # default fallback
    profile = LANG_PROFILES.get(stack, LANG_PROFILES.get('python', {}))
    lint_command = profile.get('lint_command', 'ruff check src/ tests/')

    if provider == 'github':
        workflows_dir = project_root / '.github' / 'workflows'
        workflows_dir.mkdir(parents=True, exist_ok=True)
        content = _GITHUB_WORKFLOW_TEMPLATE.format(lint_command=lint_command)
        atomic_write(workflows_dir / 'pactkit.yml', content)
        print("  -> CI: .github/workflows/pactkit.yml")
    elif provider == 'gitlab':
        content = _GITLAB_CI_TEMPLATE.format(lint_command=lint_command)
        atomic_write(project_root / '.gitlab-ci.yml', content)
        print("  -> CI: .gitlab-ci.yml")


# ---------------------------------------------------------------------------
# Hook deployment (STORY-027)
# ---------------------------------------------------------------------------

_HOOK_PRE_COMMIT_LINT = """\
#!/bin/sh
# PactKit pre-commit lint hook (report-only, non-blocking)
# Runs linter and reports findings. Does NOT block the commit.

echo "[PactKit] Running pre-commit lint check..."
{lint_command} 2>&1 || true
echo "[PactKit] Lint check complete (report-only, commit proceeds)."
exit 0
"""

_HOOK_POST_TEST_COVERAGE = """\
#!/bin/sh
# PactKit post-test coverage hook (report-only)
# Prints coverage summary if available. Does NOT block anything.

echo "[PactKit] Checking test coverage..."
if command -v coverage >/dev/null 2>&1; then
    coverage report --show-missing 2>&1 || true
elif command -v pytest >/dev/null 2>&1; then
    echo "[PactKit] Run 'pytest --cov' for coverage data."
fi
echo "[PactKit] Coverage check complete."
exit 0
"""

_HOOK_PRE_PUSH_CHECK = """\
#!/bin/sh
# PactKit pre-push check hook (report-only, non-blocking)
# Warns about uncommitted changes and branch status.

echo "[PactKit] Running pre-push checks..."
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    echo "[PactKit] WARNING: You have uncommitted changes."
fi
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo "[PactKit] WARNING: Pushing directly to $BRANCH branch."
fi
echo "[PactKit] Pre-push check complete (report-only, push proceeds)."
exit 0
"""

_HOOK_TEMPLATES = {
    'pre_commit_lint': ('pre-commit-lint', _HOOK_PRE_COMMIT_LINT),
    'post_test_coverage': ('post-test-coverage', _HOOK_POST_TEST_COVERAGE),
    'pre_push_check': ('pre-push-check', _HOOK_PRE_PUSH_CHECK),
}


def _deploy_hooks(hooks_dir, hooks_config, stack='python'):
    """Deploy enabled hook scripts.

    Args:
        hooks_dir: Target directory for hook scripts (.claude/hooks/).
        hooks_config: Dict of hook_name -> bool from pactkit.yaml.
        stack: Project stack for resolving lint command (default: 'python').
    """
    if not isinstance(hooks_config, dict):
        return

    enabled = [name for name, val in hooks_config.items() if val]
    if not enabled:
        return

    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Detect lint command from LANG_PROFILES using the project's stack (BUG-010)
    from pactkit.prompts.workflows import LANG_PROFILES
    if stack == 'auto':
        stack = 'python'  # default fallback
    profile = LANG_PROFILES.get(stack, LANG_PROFILES.get('python', {}))
    lint_command = profile.get('lint_command', 'echo "No linter configured"')

    for hook_name in enabled:
        if hook_name not in _HOOK_TEMPLATES:
            continue
        filename, template = _HOOK_TEMPLATES[hook_name]
        content = template.format(lint_command=lint_command)
        script_path = hooks_dir / filename
        atomic_write(script_path, content)
        script_path.chmod(0o755)
        print(f"  -> Hook: {filename}")


def _generate_config_if_missing():
    """Generate pactkit.yaml at $CWD/.claude/ with defaults if it doesn't exist (BUG-013)."""
    yaml_path = Path.cwd() / ".claude" / "pactkit.yaml"
    if not yaml_path.exists():
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(yaml_path, generate_default_yaml())


_VENV_BLOCK_START = "<!-- pactkit:venv:start -->"
_VENV_BLOCK_END = "<!-- pactkit:venv:end -->"


def _upsert_venv_managed_block(local_md_path, venv_info):
    """Write or update the pactkit-managed venv block in CLAUDE.local.md (STORY-064).

    - If venv_info is None: leave any existing block unchanged (R2 — persist on detection failure).
    - If venv_info provided and block exists: replace block content only (R3 — update on path change).
    - If venv_info provided and no block yet: prepend block to file (R1 — write on first init).
    - User content outside the markers is always preserved (R4).
    - If venv_info is None and no block exists: do nothing (R5 — no empty block).
    """
    if not local_md_path.exists():
        return

    if venv_info is None:
        return  # R2: detection failed — leave existing block (or absence of block) unchanged

    venv_path, layout = venv_info
    if layout == 'unix':
        instructions = (
            f"## Virtual Environment\n"
            f"Always use the project's virtual environment:\n"
            f"- **Activate**: `source {venv_path}/bin/activate`\n"
            f"- **Python**: `{venv_path}/bin/python3`\n"
            f"- **Pytest**: `{venv_path}/bin/pytest`\n"
            f"- **Pip**: `{venv_path}/bin/pip`\n"
        )
    else:  # windows
        instructions = (
            f"## Virtual Environment\n"
            f"Always use the project's virtual environment:\n"
            f"- **Activate**: `{venv_path}/Scripts/activate`\n"
            f"- **Python**: `{venv_path}/Scripts/python.exe`\n"
            f"- **Pytest**: `{venv_path}/Scripts/pytest.exe`\n"
            f"- **Pip**: `{venv_path}/Scripts/pip.exe`\n"
        )

    managed_block = f"{_VENV_BLOCK_START}\n{instructions}{_VENV_BLOCK_END}\n"

    content = local_md_path.read_text(encoding="utf-8")

    if _VENV_BLOCK_START in content:
        # R3: Replace existing block, preserve everything outside
        new_content = re.sub(
            re.escape(_VENV_BLOCK_START) + r'.*?' + re.escape(_VENV_BLOCK_END) + r'\n?',
            managed_block,
            content,
            flags=re.DOTALL,
        )
    else:
        # R1: Prepend managed block, preserve existing user content
        new_content = managed_block + "\n" + content

    atomic_write(local_md_path, new_content)


def _generate_claude_local_md_if_missing(claude_dir):
    """Create CLAUDE.local.md with template if it doesn't exist (STORY-040 R3).

    User content is preserved. PactKit manages a venv block at the top
    via _upsert_venv_managed_block() (STORY-064).
    """
    local_md_path = claude_dir / "CLAUDE.local.md"
    if local_md_path.exists():
        return

    template = """# Project Local Instructions
# Add your custom Claude Code instructions below.
# PactKit manages a venv block at the top; user content below is preserved.
"""
    atomic_write(local_md_path, template)


def _is_user_modified_claude_md(content, project_name):
    """Detect if CLAUDE.md was user-modified vs unmodified PactKit template (STORY-040 R4).

    Simple heuristic: if file doesn't start with # {project_name}, treat as user-modified.
    """
    expected_start = f"# {project_name}"
    first_line = content.split('\n')[0] if content else ''
    return not first_line.startswith(expected_start)


def _generate_project_claude_md(config):
    """Generate project-level .claude/CLAUDE.md (always regenerate) and CLAUDE.local.md (if missing).

    STORY-040: Dual-file layered architecture:
    - CLAUDE.md: PactKit-managed, regenerated on every deploy
    - CLAUDE.local.md: User-owned, created once and never modified

    Uses LANG_PROFILES for stack-aware lint and test commands.
    Uses platform-aware venv paths (Unix vs Windows).
    """
    import warnings

    from pactkit.prompts.workflows import LANG_PROFILES

    project_root = Path.cwd()

    # R6: Skip if cwd equals home (avoids overwriting global CLAUDE.md in test scenarios)
    if project_root.resolve() == Path.home().resolve():
        return

    claude_dir = project_root / ".claude"
    claude_md_path = claude_dir / "CLAUDE.md"
    claude_local_path = claude_dir / "CLAUDE.local.md"
    project_name = project_root.name

    # STORY-040 R4: Migration heuristic
    # If CLAUDE.md exists but CLAUDE.local.md doesn't, check for user modifications
    if claude_md_path.exists() and not claude_local_path.exists():
        existing_content = claude_md_path.read_text()
        if _is_user_modified_claude_md(existing_content, project_name):
            # Migrate user content to CLAUDE.local.md
            atomic_write(claude_local_path, existing_content)

    # STORY-040 R3: Create CLAUDE.local.md if missing (after migration check)
    claude_dir.mkdir(parents=True, exist_ok=True)
    _generate_claude_local_md_if_missing(claude_dir)

    # Resolve stack and get profile from LANG_PROFILES (BUG-021 R3, R4)
    stack = config.get('stack', 'auto')
    if stack == 'auto':
        stack = 'python'  # default fallback
    profile = LANG_PROFILES.get(stack, LANG_PROFILES.get('python', {}))
    lint_command = profile.get('lint_command', 'ruff check src/ tests/')
    test_runner = profile.get('test_runner', 'pytest')

    # Resolve venv path and layout (BUG-021 R2)
    venv_config = config.get('venv', {})
    venv_info = None  # (path, layout) or None

    # Priority: explicit path > auto-detect
    explicit_path = venv_config.get('path')
    if explicit_path:
        # Check if explicit path exists and determine layout
        explicit_full = project_root / explicit_path
        if (explicit_full / 'bin' / 'python3').exists() or \
           (explicit_full / 'bin' / 'python').exists():
            venv_info = (explicit_path, 'unix')
        elif (explicit_full / 'Scripts' / 'python.exe').exists():
            venv_info = (explicit_path, 'windows')
        else:
            warnings.warn(f"venv.path={explicit_path} not found, using system python")
    elif venv_config.get('auto_detect', True):
        # Auto-detect (detect_venv now returns tuple or None)
        detected = detect_venv(project_root)
        if detected:
            venv_info = detected

    # STORY-064: Persist venv config in CLAUDE.local.md managed block
    _upsert_venv_managed_block(claude_local_path, venv_info)

    # Generate CLAUDE.md content (framework content)
    lines = [f"# {project_name} — Project Context", ""]

    # BUG-021 R2: Platform-aware venv commands
    if venv_info:
        venv_path, layout = venv_info
        if layout == 'unix':
            lines.extend([
                "## Virtual Environment",
                "Always use the project's virtual environment:",
                f"- **Activate**: `source {venv_path}/bin/activate`",
                f"- **Python**: `{venv_path}/bin/python3`",
                f"- **Pytest**: `{venv_path}/bin/pytest`",
                f"- **Pip**: `{venv_path}/bin/pip`",
                "",
            ])
        else:  # windows
            lines.extend([
                "## Virtual Environment",
                "Always use the project's virtual environment:",
                f"- **Activate**: `{venv_path}/Scripts/activate`",
                f"- **Python**: `{venv_path}/Scripts/python.exe`",
                f"- **Pytest**: `{venv_path}/Scripts/pytest.exe`",
                f"- **Pip**: `{venv_path}/Scripts/pip.exe`",
                "",
            ])

    lines.extend([
        "## Dev Commands",
        "",
        "```bash",
        "# Run tests",
    ])

    # BUG-021 R4: Stack-aware test runner with optional venv prefix
    if venv_info:
        venv_path, layout = venv_info
        if stack == 'python':
            # Python with venv: prefix the test runner
            if layout == 'unix':
                lines.append(f"{venv_path}/bin/{test_runner} tests/ -v")
            else:
                lines.append(f"{venv_path}/Scripts/{test_runner}.exe tests/ -v")
        else:
            # Non-Python stacks (node, go, java) don't use venv prefix
            if stack in ('go',):
                lines.append(test_runner)  # 'go test ./...'
            else:
                lines.append(f"{test_runner}")
    else:
        # No venv: use bare test runner
        if stack in ('go',):
            lines.append(test_runner)  # 'go test ./...'
        elif stack == 'python':
            lines.append(f"{test_runner} tests/ -v")
        else:
            lines.append(test_runner)

    lines.extend([
        "",
        "# Lint",
        lint_command,  # BUG-021 R3: Stack-aware lint command from LANG_PROFILES
        "```",
        "",
        "@./docs/product/context.md",
        "@./.claude/CLAUDE.local.md",  # STORY-040 R2: Import user content
        "",
    ])

    # R1: Always write CLAUDE.md (no skip-if-exists guard)
    claude_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(claude_md_path, "\n".join(lines))


# Backward compatibility alias for existing tests
_generate_project_claude_md_if_missing = _generate_project_claude_md


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

    lines = [f"# PactKit Global Constitution (v{__version__} Modular)", ""]

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
