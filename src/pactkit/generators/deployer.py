import json
import re
import sys
import warnings
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
from pactkit.generators.deploy_base import (
    _DEPLOYER_REGISTRY,
    DeployerBase,
    register_deployer,
)
from pactkit.profiles import (
    _DEPLOYMENT_MODES,
    VALID_FORMATS,
    FormatProfile,
    get_profile,
)
from pactkit.skills import load_script
from pactkit.utils import atomic_write

# Path prefix constants — kept for plugin/marketplace modes only
# For classic/opencode: use profile.skills_path_var instead
CLASSIC_SKILLS_PREFIX = "~/.claude/skills"
PLUGIN_SKILLS_PREFIX = "${CLAUDE_PLUGIN_ROOT}/skills"


def _warn_deploy_violations(content: str, profile: FormatProfile, label: str) -> None:
    """Run validate_deployed_content and emit warnings for any violations (STORY-slim-084 R3)."""
    violations = DeployerBase.validate_deployed_content(content, profile)
    if violations:
        detail = "; ".join(violations)
        warnings.warn(f"[{label}] Deploy content violations for {profile.name}: {detail}", stacklevel=3)


def _render_prompt(template: str, profile: FormatProfile) -> str:
    """Render a prompt template by replacing {VAR} placeholders with profile values.

    All available template variables are defined in FormatProfile docstring.
    See docs/specs/STORY-slim-006.md 'Template Variable Reference' for the full list.

    Usage:
        - Use {VAR_NAME} in prompt source files.
        - JSON literal braces must be escaped as {{ and }}.
        - Unknown {PLACEHOLDERS} (e.g. {STORY_ID}) are left unchanged.
    """
    skills_root = profile.skills_dir
    _backtick = "```"  # M variable used in legacy f-string prompts (TRACE_PROMPT)

    # Document schema variables (STORY-slim-007)
    from pactkit.schemas import CONTEXT_SECTIONS_TEXT, LESSONS_ROW_FORMAT

    var_map = {
        "SKILLS_ROOT": skills_root,
        "RULES_ROOT": profile.rules_dir or "",
        "GLOBAL_CONFIG_DIR": profile.global_config_dir,
        "PROJECT_CONFIG_DIR": profile.project_config_dir,
        "INSTRUCTIONS_FILE": profile.project_instructions_file,
        "PACTKIT_YAML": profile.pactkit_yaml_path,
        "DISPLAY_NAME": profile.display_name,
        "FORMAT_NAME": profile.name,
        # Derived variables
        "VISUALIZE_CMD": f"python3 {skills_root}/pactkit-visualize/scripts/visualize.py",
        "BOARD_CMD": f"python3 {skills_root}/pactkit-board/scripts/board.py",
        "SCAFFOLD_CMD": f"python3 {skills_root}/pactkit-scaffold/scripts/scaffold.py",
        "REPORT_CMD": f"python3 {skills_root}/pactkit-report/scripts/report.py",
        "GLOBAL_INSTRUCTIONS": f"{profile.global_config_dir}/{profile.global_instructions_file}",
        # Engineering guides path (STORY-slim-128)
        "GUIDES_PATH": f"{skills_root}/_rules/guides",
        # Document schema variables (STORY-slim-007)
        "CONTEXT_SECTIONS": CONTEXT_SECTIONS_TEXT,
        "LESSONS_ROW_FORMAT": LESSONS_ROW_FORMAT,
        # Backtick escape for prompts converted from f-string (M = "```")
        "M": _backtick,
    }
    # Replace only known variables via sequential string replacement.
    # This avoids str.format_map() issues with complex keys like {R1, R2, ...}
    # or {some description with commas} that appear in user-facing prompt text.
    result = template
    for key, value in var_map.items():
        result = result.replace("{" + key + "}", value)

    # Strip references to excluded commands (e.g., project-sprint for non-Claude formats)
    if profile.excluded_commands:
        from pactkit.generators.deploy_base import DeployerBase
        result = DeployerBase.strip_excluded_command_references(result, profile)

    return result


def _insert_after_frontmatter(content: str, header: str) -> str:
    """Insert header text after the YAML frontmatter block.

    If content starts with '---', finds the closing '---' and inserts header
    after it. Otherwise prepends header (legacy fallback).
    """
    if content.startswith("---\n"):
        close_idx = content.index("\n---\n", 1)
        insert_pos = close_idx + len("\n---\n")
        return content[:insert_pos] + header + content[insert_pos:]
    return header + content


def _rewrite_skills_prefix(content, profile_or_prefix):
    """Rewrite ~/.claude/skills references to the target skills_prefix.

    DEPRECATED for environment formats (classic/opencode): use _render_prompt() instead.
    This function is retained for plugin/marketplace legacy mode only (_legacy_prefix parameter).

    Accepts either a FormatProfile or a raw string prefix (plugin/marketplace mode).

    No-op when the target is already the classic default.
    """
    if isinstance(profile_or_prefix, FormatProfile):
        skills_prefix = profile_or_prefix.skills_path_var
    else:
        skills_prefix = profile_or_prefix  # legacy string path for plugin/marketplace

    if skills_prefix == CLASSIC_SKILLS_PREFIX:
        return content
    return content.replace(CLASSIC_SKILLS_PREFIX, skills_prefix)


def _build_rule_id_to_key() -> dict:
    """Build reverse map: rule_id -> config key.

    Example: 'pactkit' -> 'pactkit', '01-workflow-conventions' -> 'workflow'

    Used by _deploy_rules() and _deploy_claude_md_inline().
    """
    return {filename.removesuffix(".md"): key for key, filename in prompts.RULES_FILES.items()}


def _build_rule_id_to_filename() -> dict:
    """Build reverse map: rule_id -> filename.

    Example: 'pactkit' -> 'pactkit.md', '01-workflow-conventions' -> '01-workflow-conventions.md'

    Used by _deploy_claude_md().
    """
    return {filename.removesuffix(".md"): filename for filename in prompts.RULES_FILES.values()}


def _render_skill_md(sd: dict, profile, _prefix: str) -> str:
    """Render a skill's SKILL.md content from its definition dict.

    Args:
        sd: Skill definition dict with at least a 'skill_md' key.
        profile: FormatProfile if deploying with a named format; None for plugin/marketplace.
        _prefix: Skills prefix string used only when profile is None.

    Returns:
        Rendered SKILL.md content string.
    """
    if profile is not None:
        return _render_prompt(sd["skill_md"], profile)
    return _rewrite_skills_prefix(_render_prompt(sd["skill_md"], get_profile("classic")), _prefix)


# STORY-062: MCP server recommendations
MCP_RECOMMENDATIONS = [
    {"name": "Context7", "purpose": "Library docs lookup (Act phase)"},
    {"name": "Memory", "purpose": "Cross-session context (Plan/Act/Done)"},
]


def _print_mcp_recommendations():
    """Print recommended MCP servers after deployment."""
    print("\n📦 Recommended MCP Servers (optional, enhance PactKit features):")
    for mcp in MCP_RECOMMENDATIONS:
        print(f"   • {mcp['name']:15} — {mcp['purpose']}")
    print("   Configure in Claude Code settings.json → mcpServers")


# ---------------------------------------------------------------------------
# Deployer classes (STORY-slim-057)
# ---------------------------------------------------------------------------


class ClassicDeployer(DeployerBase):
    """Claude Code (classic) deployer — writes files to ~/.claude/."""

    profile = get_profile("classic")

    def deploy(self, config=None, target=None):
        _deploy_classic(config, target)


class PluginDeployer(DeployerBase):
    """Plugin deployer — generates a self-contained Claude Code plugin directory."""

    profile = get_profile("classic")  # Plugin uses classic profile as base

    def deploy(self, config=None, target=None):
        _deploy_plugin(target)


# Register built-in deployers
register_deployer("classic", ClassicDeployer)
register_deployer("plugin", PluginDeployer)


def _load_entry_point_deployers():
    """Discover and register deployers from entry_points (STORY-slim-058).

    Scans the 'pactkit.deployers' entry_point group. Each entry point should
    reference a DeployerBase subclass. Already-registered formats are skipped.
    """
    try:
        from importlib.metadata import entry_points
    except ImportError:
        return  # Python < 3.9 fallback (shouldn't happen with >=3.10)

    eps = entry_points(group="pactkit.deployers")
    for ep in eps:
        if ep.name in _DEPLOYER_REGISTRY:
            continue  # built-in or already loaded via self-registration
        try:
            deployer_cls = ep.load()
            # ep.load() may trigger adapter's self-registration (force=True).
            # Re-check registry — adapter may have registered itself during import.
            if ep.name not in _DEPLOYER_REGISTRY:
                register_deployer(ep.name, deployer_cls)
        except Exception:
            pass  # graceful degradation — adapter package may be broken


# Lazy discovery: avoid module-level ep.load() which triggers circular imports
# when adapter packages (pactkit-opencode, pactkit-codex) import from deployer.py.
_ep_loaded = False


def _ensure_entry_point_deployers():
    """Lazy wrapper — loads entry_point deployers on first deploy() call."""
    global _ep_loaded
    if not _ep_loaded:
        _load_entry_point_deployers()
        _ep_loaded = True


def deploy(
    config=None, target=None, format="classic", agent="claude",
    no_git=False, no_external=False, non_interactive=False, mode=None
):
    """Deploy PactKit configuration.

    Args:
        config: Optional config dict. If None, loads from pactkit.yaml or defaults.
        target: Optional target directory. If None, uses format-specific default.
        format: Output format — 'classic' (default for Python API), 'all'
                (deploy all installed IDEs, CLI default), or a specific format
                ('opencode', 'codex', 'plugin', 'marketplace').
        agent: Target agent format (claude, cursor, copilot, generic, all).
        no_git: Disable all git operations (enterprise: air-gapped environments).
        no_external: Disable external network calls (enterprise).
        non_interactive: Non-interactive mode: auto-accept defaults (CI/CD).
        mode: Deprecated, ignored. Kept for backward compatibility.
    """
    _ensure_entry_point_deployers()

    # "all" deploys every IDE environment (classic + installed adapters).
    # Skips deployment modes (plugin, marketplace) — those are distribution
    # formats, not IDE targets.  Canonical source: profiles._DEPLOYMENT_MODES
    if format == "all":
        for fmt_name in sorted(_DEPLOYER_REGISTRY):
            if fmt_name in _DEPLOYMENT_MODES:
                continue
            deployer_cls = _DEPLOYER_REGISTRY[fmt_name]
            deployer_instance = deployer_cls()
            # Classic respects -t target; adapters always deploy to their own default
            fmt_target = target if fmt_name == "classic" else None
            deployer_instance.deploy(config=config, target=fmt_target)
        return

    if format not in VALID_FORMATS:
        raise ValueError(f"Unknown format: {format!r}. Valid: {', '.join(VALID_FORMATS)}")

    # Marketplace is a meta-mode that wraps plugin
    if format == "marketplace":
        _deploy_marketplace(target)
        return

    # STORY-slim-057: Registry-based dispatch for environment formats
    if format in _DEPLOYER_REGISTRY:
        deployer_cls = _DEPLOYER_REGISTRY[format]
        deployer_instance = deployer_cls()
        deployer_instance.deploy(config=config, target=target)
        return

    # Fallback: format is in VALID_FORMATS but no deployer registered
    # (e.g., "opencode" without pactkit-opencode installed)
    raise ValueError(
        f"No deployer registered for format '{format}'. "
        f"Install the adapter package: pip install pactkit-{format}"
    )


def _deploy_classic(config=None, target=None):
    """Classic deployment — write files to ~/.claude/ (original behavior)."""
    # Resolve target directory
    if target is not None:
        claude_root = Path(target)
    else:
        claude_root = Path.home() / ".claude"

    # Migrate legacy scafpy remnants before anything else
    _migrate_from_scafpy(claude_root)

    # Load config from project-level pactkit.yaml (STORY-072: multi-path lookup)
    if config is None:
        from pactkit.config import find_pactkit_yaml

        project_yaml = find_pactkit_yaml()
        if project_yaml is None:
            project_yaml = Path.cwd() / ".claude" / "pactkit.yaml"
        # Auto-merge new components before loading (STORY-009)
        auto_added = auto_merge_config_file(project_yaml)
        for item in auto_added:
            print(f"  -> Auto-added: {item}")
        # STORY-slim-077: Re-detect stacks for monorepo support
        if project_yaml.exists() and _update_stack_if_stale(project_yaml, Path.cwd()):
            print("  -> Stack re-detected from project markers")
        config = load_config(project_yaml)

    validate_config(config)

    # Warn about orphaned global config (BUG-013)
    global_yaml = claude_root / "pactkit.yaml"
    from pactkit.config import find_pactkit_yaml as _find_yaml

    active_yaml = _find_yaml()
    if global_yaml.exists() and active_yaml and global_yaml.resolve() != active_yaml.resolve():
        print(f"  ⚠️  Found orphaned {global_yaml} — config is now read from {active_yaml}")

    print("🚀 PactKit DevOps Deployment")

    # Prepare directories
    agents_dir = claude_root / "agents"
    commands_dir = claude_root / "commands"
    skills_dir = claude_root / "skills"

    for d in [claude_root, agents_dir, commands_dir, skills_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Deploy components filtered by config
    enabled_skills = config.get("skills", sorted(VALID_SKILLS))
    enabled_rules = config.get("rules", sorted(VALID_RULES))
    enabled_agents = config.get("agents", sorted(VALID_AGENTS))
    enabled_commands = config.get("commands", sorted(VALID_COMMANDS))

    classic_profile = get_profile("classic")
    n_skills = _deploy_skills(skills_dir, enabled_skills, profile=classic_profile)
    _cleanup_legacy(skills_dir)
    rule_scopes = config.get("rule_scopes", {})
    n_rules = _deploy_rules(claude_root, enabled_rules, rule_scopes=rule_scopes, profile=classic_profile)
    _deploy_guides(claude_root, profile=classic_profile)
    _deploy_claude_md(claude_root, enabled_rules)
    agent_models = config.get("agent_models", {})
    n_agents = _deploy_agents(agents_dir, enabled_agents, profile=classic_profile, agent_models=agent_models)
    # STORY-slim-063: Deploy commands as skills (to skills_dir, not commands_dir)
    _cleanup_legacy_commands(commands_dir)
    n_commands = _deploy_commands(skills_dir, enabled_commands, profile=classic_profile, config=config)

    # Deploy CI pipeline if configured (STORY-025)
    ci_config = config.get("ci", {})
    ci_provider = ci_config.get("provider", "none") if isinstance(ci_config, dict) else "none"
    project_root = Path.cwd()
    _deploy_ci(ci_provider, project_root, config)

    # Generate pactkit.yaml at project-level if it doesn't exist (BUG-013)
    _generate_config_if_missing()

    # Generate project-level CLAUDE.md (always regenerate) and CLAUDE.local.md (if missing) (STORY-040)
    # Skip when target is specified (preview mode) to avoid modifying real project
    if target is None:
        _generate_project_claude_md(config)

    # Summary — STORY-slim-063: commands are now deployed as skills
    total_agents = len(VALID_AGENTS)
    total_skills = len(VALID_SKILLS)
    total_rules = len(VALID_RULES)

    print(
        f"\n✅ Deployed: {n_agents}/{total_agents} Agents, "
        f"{n_skills + n_commands}/{total_skills} Skills "
        f"({n_skills} embedded + {n_commands} commands), "
        f"{n_rules}/{total_rules} Rules"
    )

    # STORY-slim-102: Write global version marker
    atomic_write(claude_root / ".pactkit-version", f"{__version__}\n")

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
    n_skills = _deploy_skills(skills_dir, all_skills, _legacy_prefix=prefix)
    _deploy_claude_md_inline(plugin_root, skills_prefix=prefix)
    n_agents = _deploy_agents(agents_dir, all_agents, _legacy_prefix=prefix)
    n_commands = _deploy_commands(commands_dir, all_commands, _legacy_prefix=prefix)
    _deploy_plugin_json(plugin_meta_dir)

    print(f"\n✅ Plugin: {n_agents} Agents, {n_commands} Commands, {n_skills} Skills → {plugin_root}")
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



def _deploy_skills(skills_dir, enabled_skills, profile=None, _legacy_prefix=None):
    """Deploy skill directories filtered by config.

    Args:
        profile: FormatProfile (STORY-slim-005). Derives skills prefix automatically.
        _legacy_prefix: Internal raw string prefix for plugin/marketplace modes only.
            If profile is provided, this is ignored.
    """
    # Resolve skills prefix from profile or legacy string
    if profile is not None:
        _prefix = profile.skills_path_var
    elif _legacy_prefix is not None:
        _prefix = _legacy_prefix
    else:
        _prefix = CLASSIC_SKILLS_PREFIX
    # Skills with executable scripts
    scripted_skill_defs = [
        {
            "name": "pactkit-visualize",
            "skill_md": prompts.SKILL_VISUALIZE_MD,
            "script_name": "visualize.py",
            "script_source": load_script("visualize.py"),
        },
        {
            "name": "pactkit-board",
            "skill_md": prompts.SKILL_BOARD_MD,
            "script_name": "board.py",
            "script_source": load_script("board.py"),
        },
        {
            "name": "pactkit-scaffold",
            "skill_md": prompts.SKILL_SCAFFOLD_MD,
            "script_name": "scaffold.py",
            "script_source": load_script("scaffold.py"),
        },
        {
            "name": "pactkit-report",
            "skill_md": prompts.SKILL_REPORT_MD,
            "script_name": "report.py",
            "script_source": load_script("report.py"),
        },
    ]

    # Prompt-only skills (SKILL.md only, no executable script) — STORY-011
    prompt_only_skill_defs = [
        {"name": "pactkit-trace", "skill_md": prompts.SKILL_TRACE_MD},
        {"name": "pactkit-draw", "skill_md": prompts.SKILL_DRAW_MD},
        {"name": "pactkit-status", "skill_md": prompts.SKILL_STATUS_MD},
        {"name": "pactkit-doctor", "skill_md": prompts.SKILL_DOCTOR_MD},
        {"name": "pactkit-garden", "skill_md": prompts.SKILL_GARDEN_MD},
        {"name": "pactkit-review", "skill_md": prompts.SKILL_REVIEW_MD},
        {"name": "pactkit-release", "skill_md": prompts.SKILL_RELEASE_MD},
        {"name": "pactkit-analyze", "skill_md": prompts.SKILL_ANALYZE_MD},
        {"name": "pactkit-audit", "skill_md": prompts.SKILL_AUDIT_MD},
    ]

    enabled_set = set(enabled_skills)
    deployed = 0

    # Deploy scripted skills (SKILL.md + script)
    for sd in scripted_skill_defs:
        if sd["name"] not in enabled_set:
            continue
        skill_dir = skills_dir / sd["name"]
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        skill_md = _render_skill_md(sd, profile, _prefix)
        if profile is not None:
            _warn_deploy_violations(skill_md, profile, f"skill:{sd['name']}")
        atomic_write(skill_dir / "SKILL.md", skill_md)
        atomic_write(scripts_dir / sd["script_name"], sd["script_source"])
        deployed += 1

    # Deploy prompt-only skills (SKILL.md only)
    for sd in prompt_only_skill_defs:
        if sd["name"] not in enabled_set:
            continue
        skill_dir = skills_dir / sd["name"]
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = _render_skill_md(sd, profile, _prefix)
        if profile is not None:
            _warn_deploy_violations(skill_md, profile, f"skill:{sd['name']}")
        atomic_write(skill_dir / "SKILL.md", skill_md)
        deployed += 1

    return deployed


def _cleanup_legacy(skills_dir):
    """Clean up legacy pactkit_tools.py."""
    legacy = skills_dir / "pactkit_tools.py"
    if legacy.exists():
        legacy.unlink()


def _cleanup_legacy_commands(commands_dir):
    """Remove legacy project-*.md files from commands/ (STORY-slim-063).

    After migration, commands are deployed as skills. Old flat .md files
    in commands/ would be shadowed but should be cleaned up.
    Non-PactKit files (e.g., ultra-think.md) are preserved.
    """
    if not commands_dir.exists():
        return
    for f in commands_dir.glob("project-*.md"):
        f.unlink()


def _migrate_from_scafpy(claude_root):
    """Migrate legacy scafpy-* remnants to pactkit-* naming.

    - Removes old scafpy-visualize/, scafpy-board/, scafpy-scaffold/ skill dirs
    - Renames scafpy.yaml → pactkit.yaml (or deletes if pactkit.yaml already exists)
    """
    import shutil

    # Clean up legacy skill directories
    skills_dir = claude_root / "skills"
    for old_name in ("scafpy-visualize", "scafpy-board", "scafpy-scaffold"):
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


def _deploy_rules(claude_root, enabled_rules, rule_scopes=None, profile=None):
    """Deploy rule modules filtered by config.

    STORY-slim-112: Writes to two directories:
    - Global rules  → claude_root/rules/         (always auto-loaded by Claude Code harness)
    - On-demand rules → claude_root/skills/_rules/  (loaded via @import in skill commands only)

    Args:
        rule_scopes: Optional dict of rule_id -> glob pattern for includeFiles.
        profile: Optional FormatProfile for template variable rendering.
    """
    if rule_scopes is None:
        rule_scopes = {}
    rules_dir = claude_root / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    # On-demand directory: skills/_rules/
    ondemand_dir = claude_root / "skills" / prompts.RULES_ONDEMAND_DIR
    ondemand_dir.mkdir(parents=True, exist_ok=True)

    # Build reverse map: rule identifier -> config key
    # e.g. 'pactkit' -> 'pactkit', '01-workflow-conventions' -> 'workflow'
    rule_id_to_key = _build_rule_id_to_key()

    # OLD filenames from before the merge refactor — remove on upgrade.
    _legacy_global_filenames = {
        "01-core-protocol.md",
        "02-hierarchy-of-truth.md",
        "03-file-atlas.md",
        "04-routing-table.md",
        "05-principles.md",
        "11-pdca-nudge.md",
    }
    _legacy_ondemand_filenames = {
        "05-workflow-conventions.md",
        "06-mcp-integration.md",
        "07-shared-protocols.md",
        "08-architecture-principles.md",
        "09-sectional-write.md",
        "12-solution-design.md",
    }

    # Clean managed rule files from global rules/ dir.
    # Includes current filename (pactkit.md) and legacy filenames (upgrade path).
    global_managed_filenames = set(prompts.RULES_CORE_FILES.values())
    cleanup_from_global = global_managed_filenames | _legacy_global_filenames | _legacy_ondemand_filenames
    for f in rules_dir.glob("*.md"):
        if f.name in cleanup_from_global:
            f.unlink()

    # Clean managed rule files from on-demand dir.
    # Includes current filenames (01-06) and legacy filenames (05-12, upgrade path).
    ondemand_managed_filenames = set(prompts.RULES_ONDEMAND_FILES.values())
    cleanup_from_ondemand = ondemand_managed_filenames | _legacy_ondemand_filenames
    for f in ondemand_dir.glob("*.md"):
        if f.name in cleanup_from_ondemand:
            f.unlink()

    # Determine which filenames belong to global vs on-demand
    global_filenames = set(prompts.RULES_CORE_FILES.values())

    # Write only enabled rules to the appropriate directory
    deployed = 0
    for rule_id in enabled_rules:
        key = rule_id_to_key.get(rule_id)
        if key is None:
            continue
        filename = prompts.RULES_FILES[key]
        content = prompts.RULES_MODULES[key]

        # Render template variables if profile provided
        if profile is not None:
            content = _render_prompt(content, profile)

        # Add includeFiles frontmatter if scope is defined (STORY-028)
        scope = rule_scopes.get(rule_id)
        if scope:
            if isinstance(scope, list):
                include_lines = "\n".join(f'  - "{p}"' for p in scope)
                frontmatter = f"---\nincludeFiles:\n{include_lines}\n---\n\n"
            else:
                frontmatter = f'---\nincludeFiles: ["{scope}"]\n---\n\n'
            content = frontmatter + content

        # Route to correct directory
        dest_dir = rules_dir if filename in global_filenames else ondemand_dir

        if profile is not None:
            _warn_deploy_violations(content, profile, f"rule:{rule_id}")
        atomic_write(dest_dir / filename, content)
        deployed += 1

    return deployed


def _deploy_guides(claude_root, profile=None):
    """Deploy engineering guide files to skills/_rules/guides/ (STORY-slim-128).

    Guides are on-demand reference files loaded by Act Phase 1.5 based on
    Spec's engineering concerns. Not loaded into context unless explicitly read.
    """
    from pactkit.prompts.guides import GUIDES_DIR, GUIDES_FILES

    guides_dir = claude_root / "skills" / prompts.RULES_ONDEMAND_DIR / GUIDES_DIR
    guides_dir.mkdir(parents=True, exist_ok=True)

    # Clean existing managed guide files (upgrade path)
    for f in guides_dir.glob("*.md"):
        if f.name in GUIDES_FILES:
            f.unlink()

    deployed = 0
    for filename, content in GUIDES_FILES.items():
        if profile is not None:
            content = _render_prompt(content, profile)
        atomic_write(guides_dir / filename, content)
        deployed += 1

    return deployed


def _is_pactkit_managed_global_md(content):
    """Detect if CLAUDE.md content is a PactKit-managed template (BUG-slim-089).

    Returns True if the first line starts with '# PactKit Global Constitution'.
    """
    first_line = content.split("\n", 1)[0] if content else ""
    return first_line.startswith("# PactKit Global Constitution")


def _deploy_claude_md(claude_root, enabled_rules):
    """Generate global CLAUDE.md — header only (STORY-slim-011).

    Rules are auto-loaded by Claude Code from ~/.claude/rules/.
    Context.md reference removed — invalid at global level (BUG-slim-089).

    BUG-slim-089: Read-before-write guard to preserve user-modified content.
    """
    claude_md_path = claude_root / "CLAUDE.md"
    new_header = f"# PactKit Global Constitution (v{__version__} Modular)"
    new_content = f"{new_header}\n"

    # Fresh install — no existing file
    if not claude_md_path.exists():
        atomic_write(claude_md_path, new_content)
        return

    # Read existing content
    try:
        existing = claude_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Unreadable file — overwrite as fresh install
        atomic_write(claude_md_path, new_content)
        return

    # User-modified content — do not touch (R1)
    if not _is_pactkit_managed_global_md(existing):
        return

    # PactKit-managed — update version header in-place if changed (R2)
    updated = re.sub(
        r"^# PactKit Global Constitution \(v[^\)]+\)",
        new_header,
        existing,
        count=1,
    )
    if updated != existing:
        atomic_write(claude_md_path, updated)
    # else: idempotent — skip write (AC5)


def _deploy_agents(
    agents_dir,
    enabled_agents,
    profile=None,
    agent_models=None,
    # Legacy params for plugin/marketplace — ignored when profile is provided
    _legacy_prefix=None,
    _legacy_opencode=None,
):
    """Deploy agent definitions filtered by config.

    Args:
        profile: FormatProfile (STORY-slim-005). Replaces skills_prefix + opencode_format.
        agent_models: Optional dict of agent_name -> model overrides from pactkit.yaml.
        _legacy_prefix: DEPRECATED. Use profile instead.
        _legacy_opencode: DEPRECATED. Use profile instead.
    """
    # Resolve profile (STORY-slim-005: prefer profile over legacy params)
    if profile is None:
        # Legacy fallback: reconstruct from old params
        if _legacy_opencode:
            profile = get_profile("opencode")
        else:
            profile = get_profile("classic")
    _opencode_format = profile.agent_format == "md" and profile.name != "classic"
    # Legacy prefix override (plugin/marketplace only)
    _effective_prefix = _legacy_prefix if _legacy_prefix is not None else profile
    if agent_models is None:
        agent_models = {}
    enabled_set = set(enabled_agents)

    # Clean up managed agent files not in enabled set
    managed_agent_files = {f"{name}.md" for name in prompts.AGENTS_EXPERT}
    if agents_dir.exists():
        for f in agents_dir.glob("*.md"):
            if f.name in managed_agent_files and f.stem not in enabled_set:
                f.unlink()

    # Fields serialized as simple key: value (no nesting) — Claude Code format
    SIMPLE_OPTIONAL_FIELDS = ["permissionMode", "disallowedTools", "maxTurns", "memory", "skills"]
    # STORY-slim-005: excluded_agent_fields from profile (replaces hardcoded CLAUDE_ONLY_FIELDS)
    excluded_fields = profile.excluded_agent_fields
    deployed = 0
    for name, cfg in prompts.AGENTS_EXPERT.items():
        if name not in enabled_set:
            continue
        agent_path = agents_dir / f"{name}.md"

        # Resolve model: agent_models override > AGENTS_EXPERT default > 'inherit'
        model = agent_models.get(name, cfg.get("model", "inherit"))

        content = ["---"]

        # STORY-070 R3: OpenCode uses filename as agent name — omit 'name' field
        if not _opencode_format:
            content.append(f"name: {name}")

        content.append(f"description: {cfg['desc']}")

        # STORY-070 R2: OpenCode requires mode field for custom agents
        if _opencode_format:
            content.append("mode: subagent")

        # STORY-069 R7: Convert tools format for OpenCode
        if _opencode_format:
            # OpenCode expects tools as record: { read: true, write: true, ... }
            tools_str = cfg["tools"]
            # Parse "Read, Write, Edit, Bash" or "[Read, Write]" format
            tools_str = tools_str.strip("[]")
            tool_names = [t.strip().lower() for t in tools_str.split(",")]
            tools_record = {t: True for t in tool_names if t}
            tools_yaml = yaml.dump({"tools": tools_record}, default_flow_style=False).rstrip()
            content.append(tools_yaml)
        else:
            content.append(f"tools: {cfg['tools']}")

        # STORY-070 R5: Omit 'model: inherit' in OpenCode (default behavior = inherit)
        if _opencode_format and model == "inherit":
            pass  # OpenCode inherits model from parent agent by default
        else:
            content.append(f"model: {model}")

        # STORY-slim-005: Skip excluded fields from profile (replaces CLAUDE_ONLY_FIELDS hardcode)
        for field in SIMPLE_OPTIONAL_FIELDS:
            if field in cfg:
                if field in excluded_fields:
                    continue
                content.append(f"{field}: {cfg[field]}")
        # Routing reference: from profile.global_instructions_file (STORY-slim-005)
        routing_ref = f"{profile.global_config_dir}/{profile.global_instructions_file}"
        content.extend(["---", "", cfg["prompt"], "", f"Please refer to {routing_ref} for routing."])
        raw = "\n".join(content)
        # Use _render_prompt for environment profiles; fallback to string replace for legacy
        rendered = (
            _render_prompt(raw, profile) if _legacy_prefix is None else _rewrite_skills_prefix(raw, _effective_prefix)
        )
        _warn_deploy_violations(rendered, profile, f"agent:{name}")
        atomic_write(agent_path, rendered)
        deployed += 1

    return deployed


def _get_command_rules(cmd_name, config=None):
    """Resolve the rule list for a command (STORY-slim-011).

    Priority: config['command_rules'][cmd] > COMMAND_RULES_MAP default.
    SEC-1: 'credential' is always forced into the result.

    Args:
        cmd_name: Command name (e.g. 'project-act').
        config: Optional config dict with 'command_rules' override.

    Returns:
        List of rule keys (e.g. ['core', 'hierarchy', 'credential']).
    """
    if config and "command_rules" in config and cmd_name in config["command_rules"]:
        rules = list(config["command_rules"][cmd_name])
    else:
        rules = list(prompts.COMMAND_RULES_MAP.get(cmd_name, []))

    # SEC-1: Force credential safety
    if "credential" not in rules:
        rules.append("credential")

    return rules


def _build_command_rules_header(cmd_name, profile, config=None):
    """Build rule injection header for a command file (STORY-slim-011, R6: STORY-slim-083).

    Dispatches on profile.rules_import_style (OCP-compliant):
    - "@import": @reference lines for each rule (e.g., classic)
    - "inline": embed rule content directly (e.g., opencode, copilot)
    - "instructions": no injection — rules loaded via global config (e.g., codex)

    Args:
        cmd_name: Command name.
        profile: FormatProfile.
        config: Optional config dict for user overrides.

    Returns:
        Header string to prepend to command content, or empty string.
    """
    rules = _get_command_rules(cmd_name, config)
    if not rules:
        return ""

    style = profile.rules_import_style

    if style == "@import":
        rule_id_to_filename = _build_rule_id_to_filename()
        global_filenames = set(prompts.RULES_CORE_FILES.values())
        ondemand_dir = prompts.RULES_ONDEMAND_DIR
        rules_prefix = profile.rules_dir  # e.g. "~/.claude/rules"
        skills_prefix = profile.skills_dir  # e.g. "~/.claude/skills"
        lines = []
        for key in sorted(rules):
            if key == "credential":
                lines.append(f"@{rules_prefix}/{prompts.CREDENTIAL_SAFETY_FILE}")
            else:
                filename = rule_id_to_filename.get(key) if key in rule_id_to_filename else prompts.RULES_FILES.get(key)
                if filename:
                    if filename in global_filenames:
                        pass
                    else:
                        lines.append(f"@{skills_prefix}/{ondemand_dir}/{filename}")
        lines.append("")  # blank line before command content
        return "\n".join(lines) + "\n"

    elif style == "inline":
        # Inline content embedding — credential handled externally, not inlined
        parts = []
        for key in sorted(rules):
            if key == "credential":
                continue
            content = prompts.RULES_MODULES.get(key)
            if content:
                parts.append(content.strip())
        if parts:
            # Use comment separator (not ---) to avoid clashing with YAML frontmatter
            header = "\n\n".join(parts) + "\n\n<!-- rules-end -->\n\n"
            return header

    # "instructions" or unknown: no injection (rules handled globally)
    return ""


def _deploy_commands(
    commands_dir,
    enabled_commands,
    profile=None,
    config=None,
    # Legacy params for plugin/marketplace — ignored when profile is provided
    _legacy_prefix=None,
    _legacy_opencode=None,
):
    """Deploy command playbooks filtered by config.

    Args:
        profile: FormatProfile (STORY-slim-005). Replaces _legacy_prefix + _legacy_opencode.
        config: Optional config dict for command_rules overrides (STORY-slim-011).
        _legacy_prefix: DEPRECATED. Use profile instead.
        _legacy_opencode: DEPRECATED. Use profile instead.
    """
    # Resolve profile (STORY-slim-005)
    if profile is None:
        if _legacy_opencode:
            profile = get_profile("opencode")
        else:
            profile = get_profile("classic")
    _opencode_format = profile.name != "classic" and profile.has_custom_commands
    # Legacy prefix override (plugin/marketplace only)
    _effective_prefix = _legacy_prefix if _legacy_prefix is not None else profile

    enabled_set = set(enabled_commands)

    # Build map: command name -> filename
    # e.g. 'project-plan' -> 'project-plan.md'
    enabled_filenames = {f"{cmd}.md" for cmd in enabled_commands}

    # STORY-slim-063: For classic format, commands deploy as skills (subdirectory/SKILL.md).
    # For other formats (plugin/marketplace), keep flat .md files.
    _deploy_as_skill = profile.name == "classic" and _legacy_prefix is None

    # Clean managed command files/dirs not in enabled set
    if commands_dir.exists():
        if _deploy_as_skill:
            # Clean skill subdirectories for commands no longer enabled
            for d in commands_dir.iterdir():
                if d.is_dir() and d.name.startswith("project-") and d.name not in enabled_set:
                    import shutil
                    shutil.rmtree(d)
        else:
            for f in commands_dir.glob("*.md"):
                if f.name.startswith("project-") and f.name not in enabled_filenames:
                    f.unlink()

    # Deploy enabled commands
    deployed = 0
    for filename, content in prompts.COMMANDS_CONTENT.items():
        cmd_name = filename.removesuffix(".md")
        if cmd_name not in enabled_set:
            continue

        # STORY-070 R1: Convert frontmatter for OpenCode
        if _opencode_format:
            content = _convert_command_frontmatter_opencode(content)

        # STORY-slim-011: Inject rule header after YAML frontmatter (HOTFIX-slim-131)
        # Must go AFTER frontmatter so Claude Code parses model:/description:/allowed-tools:
        if _legacy_prefix is None:
            rules_header = _build_command_rules_header(cmd_name, profile, config)
            if rules_header:
                content = _insert_after_frontmatter(content, rules_header)

        rendered = (
            _render_prompt(content, profile)
            if _legacy_prefix is None
            else _rewrite_skills_prefix(content, _effective_prefix)
        )
        _warn_deploy_violations(rendered, profile, f"command:{cmd_name}")

        if _deploy_as_skill:
            # STORY-slim-063: Write as skills_dir/{name}/SKILL.md
            atomic_write(commands_dir / cmd_name / "SKILL.md", rendered)
        else:
            atomic_write(commands_dir / filename, rendered)
        deployed += 1

    return deployed


def _convert_command_frontmatter_opencode(content, cmd_name=None, command_models=None, providers=None):
    """Convert Claude Code command frontmatter to OpenCode format (STORY-070 R1).

    Replaces 'allowed-tools: [...]' with 'agent: build' in the YAML frontmatter.
    Note: Model routing is NOT written to frontmatter (provider-specific IDs should not
    be baked into shared files). Instead, model routing is configured in opencode.json
    via the 'command' section by _update_global_opencode_json().
    """
    if not content.startswith("---"):
        return content

    # Split into frontmatter and body
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content

    frontmatter_lines = parts[1].strip().split("\n")
    new_lines = []
    has_agent = False

    for line in frontmatter_lines:
        stripped = line.strip()
        if stripped.startswith("allowed-tools:"):
            # Replace with agent: build
            if not has_agent:
                new_lines.append("agent: build")
                has_agent = True
        else:
            if stripped.startswith("agent:"):
                has_agent = True
            new_lines.append(line)

    return "---\n" + "\n".join(new_lines) + "\n---" + parts[2]


# ---------------------------------------------------------------------------
# CI/CD pipeline generation (STORY-025, STORY-slim-012)
# ---------------------------------------------------------------------------


def _detect_ghe(project_root):
    """Detect if the project remote points to GitHub Enterprise (non-github.com)."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=str(project_root), timeout=5,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            if "github.com" not in url and ("github" in url.lower() or "git" in url.lower()):
                return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def _build_github_workflow(stack, ci_config, lang_profile, is_ghe=False):
    """Build GitHub Actions workflow YAML content for the given stack."""
    from pactkit.prompts.workflows import CI_PROFILES

    ci_prof = CI_PROFILES.get(stack, CI_PROFILES["python"])
    runner = ci_config.get("runner", "ubuntu-latest")
    version = ci_config.get("language_version", ci_prof["default_version"])
    lint_command = lang_profile.get("lint_command", "ruff check src/ tests/")
    actions_ref = ci_config.get("actions_ref", "")

    # Apply actions_ref prefix: "my-org/" -> "my-org/actions/checkout@v4"
    checkout_action = f"{actions_ref}actions/checkout@v4"
    setup_action = ci_prof["setup_action"]
    if actions_ref:
        setup_action = f"{actions_ref}{setup_action}"

    lines = []
    if is_ghe:
        lines.append("# NOTE: GHE detected — verify action availability on your instance")
    lines.append("name: PactKit CI")
    lines.append("")
    lines.append("on:")
    lines.append("  push:")
    lines.append("    branches: [main]")
    lines.append("  pull_request:")
    lines.append("    branches: [main]")
    lines.append("")
    lines.append("jobs:")
    lines.append("  test:")
    lines.append(f"    runs-on: {runner}")
    lines.append("    steps:")
    lines.append(f"      - uses: {checkout_action}")
    lines.append("")
    lines.append(f"      - name: Set up {ci_prof['setup_name']}")
    lines.append(f"        uses: {setup_action}")
    lines.append("        with:")
    lines.append(f'          {ci_prof["setup_key"]}: "{version}"')
    if "extra_setup" in ci_prof:
        for key, val in ci_prof["extra_setup"].items():
            lines.append(f"          {key}: {val}")
    lines.append("")
    install_cmd = ci_config.get("install_cmd", ci_prof["install_cmd"])
    lines.append("      - name: Install dependencies")
    lines.append("        run: |")
    lines.append(f"          {install_cmd}")
    lines.append("")
    lines.append("      - name: Lint")
    lines.append(f"        run: {lint_command}")
    lines.append("")
    lines.append("      - name: Test")
    lines.append(f"        run: {ci_prof['test_cmd']}")
    lines.append("")

    return "\n".join(lines)


def _build_gitlab_ci(stack, ci_config, lang_profile):
    """Build GitLab CI YAML content for the given stack."""
    from pactkit.prompts.workflows import CI_PROFILES

    ci_prof = CI_PROFILES.get(stack, CI_PROFILES["python"])
    version = ci_config.get("language_version", ci_prof["default_version"])
    lint_command = lang_profile.get("lint_command", "ruff check src/ tests/")
    image = f"{ci_prof['docker_image']}:{version}"

    lines = []
    lines.append("stages:")
    lines.append("  - lint")
    lines.append("  - test")
    lines.append("")
    lines.append("lint:")
    lines.append("  stage: lint")
    lines.append(f"  image: {image}")
    lines.append("  script:")
    lines.append(f"    - {lint_command}")
    lines.append("")
    lines.append("test:")
    lines.append("  stage: test")
    lines.append(f"  image: {image}")
    lines.append("  script:")
    lines.append(f"    - {ci_prof['docker_install']}")
    lines.append(f"    - {ci_prof['test_cmd']}")
    lines.append("")

    return "\n".join(lines)


def _deploy_ci(provider, project_root, config):
    """Deploy CI pipeline config based on provider setting.

    Args:
        provider: CI provider name ('github', 'gitlab', 'none').
        project_root: Project root directory (parent of .claude/).
        config: Full pactkit config dict.
    """
    if provider == "none" or provider not in ("github", "gitlab"):
        return

    from pactkit.prompts.workflows import LANG_PROFILES

    stack = config.get("stack", "auto")
    if stack == "auto":
        stack = "python"
    lang_profile = LANG_PROFILES.get(stack, LANG_PROFILES.get("python", {}))
    ci_config = config.get("ci", {})
    if not isinstance(ci_config, dict):
        ci_config = {}

    # GHE detection priority: _ghe_override (testing) > github_host (explicit) > auto-detect
    is_ghe = ci_config.get("_ghe_override")
    if is_ghe is None:
        github_host = ci_config.get("github_host", "")
        if github_host:
            is_ghe = True
        elif provider == "github":
            is_ghe = _detect_ghe(project_root)
        else:
            is_ghe = False

    if provider == "github":
        workflows_dir = project_root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        content = _build_github_workflow(stack, ci_config, lang_profile, is_ghe=is_ghe)
        atomic_write(workflows_dir / "pactkit.yml", content)
        print("  -> CI: .github/workflows/pactkit.yml")
    elif provider == "gitlab":
        content = _build_gitlab_ci(stack, ci_config, lang_profile)
        atomic_write(project_root / ".gitlab-ci.yml", content)
        print("  -> CI: .gitlab-ci.yml")


def _generate_config_if_missing(format: str | None = None):
    """Generate pactkit.yaml if it doesn't exist (STORY-072: env-aware path, STORY-slim-008 R7: format-aware).

    Args:
        format: Optional format string ('classic', 'opencode').
                When provided, writes to the format-specific directory.
                When None, auto-detects from existing directories.

    Writes to the appropriate directory based on environment:
    - format='opencode' → .opencode/pactkit.yaml
    - format='classic'  → .claude/pactkit.yaml
    - auto (format=None): .opencode/ exists → .opencode/, else .claude/
    """
    from pactkit.config import find_pactkit_yaml, resolve_pactkit_yaml_dir

    # If already exists anywhere, skip
    if find_pactkit_yaml() is not None:
        return

    # STORY-slim-076: Auto-detect stacks for new projects
    from pactkit.cleaners import detect_stacks
    stacks = detect_stacks(Path.cwd())

    yaml_path = resolve_pactkit_yaml_dir(format=format)
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(yaml_path, generate_default_yaml(stack=stacks))


def _update_stack_if_stale(yaml_path: Path, project_root: Path) -> bool:
    """Re-detect stacks and update yaml if changed (STORY-slim-077).

    Returns True if yaml was updated, False otherwise.
    """
    import yaml as _yaml

    from pactkit.cleaners import detect_stacks
    from pactkit.config import update_yaml_stack

    data = _yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    old_stack = data.get("stack", "auto")

    new_stacks = detect_stacks(project_root)
    # Normalize old value to list for comparison
    if isinstance(old_stack, list):
        old_list = old_stack
    elif old_stack == "auto":
        old_list = []  # force update
    else:
        old_list = [old_stack]

    if sorted(new_stacks) == sorted(old_list):
        return False

    update_yaml_stack(yaml_path, new_stacks)
    return True


_VENV_BLOCK_START = "<!-- pactkit:venv:start -->"
_VENV_BLOCK_END = "<!-- pactkit:venv:end -->"

_CLAUDE_MD_START = "<!-- pactkit:start -->"
_CLAUDE_MD_END = "<!-- pactkit:end -->"


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
    if layout == "unix":
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
            re.escape(_VENV_BLOCK_START) + r".*?" + re.escape(_VENV_BLOCK_END) + r"\n?",
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
    first_line = content.split("\n")[0] if content else ""
    return not first_line.startswith(expected_start)


def _build_claude_md_managed_content(config, project_root):
    """Build the content that goes inside the managed block of CLAUDE.md (STORY-slim-127).

    Returns a string (no markers included — caller wraps in markers).
    """
    import warnings

    from pactkit.prompts.workflows import LANG_PROFILES

    project_name = project_root.name

    # Resolve stack and get profile from LANG_PROFILES (BUG-021 R3, R4)
    stack = config.get("stack", "auto")
    if isinstance(stack, list):
        stack = stack[0] if stack else "python"
    if stack == "auto":
        stack = "python"  # default fallback
    profile = LANG_PROFILES.get(stack, LANG_PROFILES.get("python", {}))
    lint_command = profile.get("lint_command", "ruff check src/ tests/")
    test_runner = profile.get("test_runner", "pytest")

    # Resolve venv path and layout (BUG-021 R2)
    venv_config = config.get("venv", {})
    venv_info = None  # (path, layout) or None

    explicit_path = venv_config.get("path")
    if explicit_path:
        explicit_full = project_root / explicit_path
        if (explicit_full / "bin" / "python3").exists() or (explicit_full / "bin" / "python").exists():
            venv_info = (explicit_path, "unix")
        elif (explicit_full / "Scripts" / "python.exe").exists():
            venv_info = (explicit_path, "windows")
        else:
            warnings.warn(f"venv.path={explicit_path} not found, using system python")
    elif venv_config.get("auto_detect", True):
        detected = detect_venv(project_root)
        if detected:
            venv_info = detected

    lines = [f"# {project_name} — Project Context", ""]

    if venv_info:
        venv_path, layout = venv_info
        if layout == "unix":
            lines.extend(
                [
                    "## Virtual Environment",
                    "Always use the project's virtual environment:",
                    f"- **Activate**: `source {venv_path}/bin/activate`",
                    f"- **Python**: `{venv_path}/bin/python3`",
                    f"- **Pytest**: `{venv_path}/bin/pytest`",
                    f"- **Pip**: `{venv_path}/bin/pip`",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "## Virtual Environment",
                    "Always use the project's virtual environment:",
                    f"- **Activate**: `{venv_path}/Scripts/activate`",
                    f"- **Python**: `{venv_path}/Scripts/python.exe`",
                    f"- **Pytest**: `{venv_path}/Scripts/pytest.exe`",
                    f"- **Pip**: `{venv_path}/Scripts/pip.exe`",
                    "",
                ]
            )

    lines.extend(["## Dev Commands", "", "```bash", "# Run tests"])

    if venv_info:
        venv_path, layout = venv_info
        if stack == "python":
            if layout == "unix":
                lines.append(f"{venv_path}/bin/{test_runner} tests/ -v")
            else:
                lines.append(f"{venv_path}/Scripts/{test_runner}.exe tests/ -v")
        else:
            if stack in ("go",):
                lines.append(test_runner)
            else:
                lines.append(f"{test_runner}")
    else:
        if stack in ("go",):
            lines.append(test_runner)
        elif stack == "python":
            lines.append(f"{test_runner} tests/ -v")
        else:
            lines.append(test_runner)

    lines.extend(["", "# Lint", lint_command, "```", ""])

    if (project_root / ".codegraph").is_dir():
        lines.extend(
            [
                "## Code Intelligence (codegraph)",
                "This project has codegraph enabled. Prefer codegraph over grep/find for code navigation:",
                "- `codegraph callers <symbol>` — find callers",
                "- `codegraph callees <symbol>` — find callees",
                "- `codegraph impact <symbol> --depth 3` — impact analysis",
                "- `codegraph query <keyword> --kind function` — symbol search",
                "- `codegraph context \"<task>\"` — task-focused context",
                "",
            ]
        )

    return "\n".join(lines), venv_info


def _upsert_claude_md_managed_block(claude_md_path, managed_content, project_name):
    """Write or update the pactkit-managed block in CLAUDE.md (STORY-slim-127).

    Four paths:
    - File missing: create fresh (markers + @imports)
    - Has markers: regex replace between markers
    - Legacy PactKit template (has project header): replace with managed block
    - User content (no PactKit header): append managed block at end
    """
    at_imports = "\n@./docs/product/context.md\n@./.claude/CLAUDE.local.md\n"
    managed_block = f"{_CLAUDE_MD_START}\n{managed_content}\n{_CLAUDE_MD_END}\n"

    if not claude_md_path.exists():
        # Fresh install
        atomic_write(claude_md_path, managed_block + at_imports)
        return

    content = claude_md_path.read_text(encoding="utf-8")

    if _CLAUDE_MD_START in content:
        # Has markers — replace managed block, preserve everything else
        new_content = re.sub(
            re.escape(_CLAUDE_MD_START) + r".*?" + re.escape(_CLAUDE_MD_END) + r"\n?",
            managed_block,
            content,
            flags=re.DOTALL,
        )
        # Ensure @imports exist after the end marker
        if "@./docs/product/context.md" not in new_content:
            new_content = new_content.rstrip("\n") + "\n" + at_imports
        atomic_write(claude_md_path, new_content)
        return

    # No markers — check if legacy PactKit template or user content
    expected_header = f"# {project_name} — Project Context"
    first_line = content.split("\n")[0] if content else ""

    if first_line.strip() == expected_header:
        # Legacy PactKit template — replace entirely with managed block
        atomic_write(claude_md_path, managed_block + at_imports)
    else:
        # User-modified content — append managed block
        preserved = content.rstrip("\n")
        atomic_write(claude_md_path, preserved + "\n\n" + managed_block + at_imports)


def _generate_project_claude_md(config):
    """Generate project-level .claude/CLAUDE.md and CLAUDE.local.md (STORY-slim-127).

    STORY-040: Dual-file layered architecture:
    - CLAUDE.md: PactKit manages a block via markers; user content is preserved
    - CLAUDE.local.md: User-owned, created once and never modified

    STORY-slim-127: Uses managed-block pattern (merge over replace).
    """
    project_root = Path.cwd()

    # R6: Skip if cwd equals home
    if project_root.resolve() == Path.home().resolve():
        return

    claude_dir = project_root / ".claude"
    claude_md_path = claude_dir / "CLAUDE.md"
    claude_local_path = claude_dir / "CLAUDE.local.md"
    project_name = project_root.name

    # STORY-040 R4: Migration heuristic
    if claude_md_path.exists() and not claude_local_path.exists():
        existing_content = claude_md_path.read_text(encoding='utf-8')
        if _is_user_modified_claude_md(existing_content, project_name):
            atomic_write(claude_local_path, existing_content)

    # STORY-040 R3: Create CLAUDE.local.md if missing
    claude_dir.mkdir(parents=True, exist_ok=True)
    _generate_claude_local_md_if_missing(claude_dir)

    # Build managed content and upsert
    managed_content, venv_info = _build_claude_md_managed_content(config, project_root)
    _upsert_claude_md_managed_block(claude_md_path, managed_content, project_name)

    # STORY-064: Persist venv config in CLAUDE.local.md managed block
    _upsert_venv_managed_block(claude_local_path, venv_info)


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
            "devops",
            "pdca",
            "spec-driven",
            "tdd",
            "governance",
            "claude-code",
            "ai-agent",
            "multi-agent",
        ],
    }
    content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    atomic_write(plugin_meta_dir / "plugin.json", content)


def _deploy_claude_md_inline(plugin_root, skills_prefix=CLASSIC_SKILLS_PREFIX):
    """Generate CLAUDE.md with all rules inlined (no @import references)."""
    # Build reverse map: rule_id -> key for ordered iteration
    rule_id_to_key = _build_rule_id_to_key()

    lines = [f"# PactKit Global Constitution (v{__version__} Modular)", ""]

    # Inline all rule modules in sorted order
    for rule_id in sorted(rule_id_to_key.keys()):
        key = rule_id_to_key[rule_id]
        module_content = prompts.RULES_MODULES[key].strip()
        lines.append(module_content)
        lines.append("")  # blank line between modules

    # Add TIP for cross-session context (plugin mode has no context.md by default)
    lines.append("> **TIP**: Run `/project-init` to set up project governance and enable cross-session context.")
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
                "description": "PDCA workflows, role-based agents, and behavioral governance",
            },
        ],
    }
    content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    atomic_write(marketplace_root / "marketplace.json", content)
