import json
import re
import sys
from pathlib import Path

import yaml


class DeployIntegrityError(Exception):
    """Raised when deployed prompt content fails lexical/semantic integrity (STORY-slim-145 R4).

    Carries (label, violations) so callers can report which artifact set was
    refused before atomic_write. Replaces the prior warn-and-write behavior.
    """

    def __init__(self, label: str, violations: list[str]):
        self.label = label
        self.violations = violations
        super().__init__(f"[{label}] {len(violations)} integrity violation(s): {violations}")

# 确保能 import pactkit.prompts
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pactkit import __version__, prompts
from pactkit.config import (
    CURRENT_RULE_IDS,
    VALID_AGENTS,
    VALID_COMMANDS,
    VALID_SKILLS,
    activate_pactkit_maintainer_overlay,
    auto_merge_config_file,
    detect_venv,
    generate_default_yaml,
    load_config,
    validate_config,
)
from pactkit.generators.command_ownership import (
    cleanup_disabled_command_skills,
    cleanup_unmodified_legacy_skills,
    record_deployed_command,
    write_command_manifest,
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
from pactkit.utils import atomic_write

# Path prefix constants — kept for plugin/marketplace modes only
# For classic/opencode: use profile.skills_path_var instead
CLASSIC_SKILLS_PREFIX = "~/.claude/skills"
PLUGIN_SKILLS_PREFIX = "${CLAUDE_PLUGIN_ROOT}/skills"


def _enforce_deploy_integrity(content: str, profile: FormatProfile, label: str) -> None:
    """Validate deployed content; raise DeployIntegrityError on any violation
    (STORY-slim-145 R4: fail before atomic_write, never warn-and-write)."""
    violations = DeployerBase.validate_deployed_content(content, profile)
    if violations:
        raise DeployIntegrityError(label, violations)


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

    # Operation tokens (STORY-slim-145 R2): structured operation contract.
    # Adapters consume these tokens instead of matching natural-language CLI
    # prefixes. Value resolves via the profile CLI policy:
    #   required/preferred (has_pactkit_cli True) -> canonical `pactkit` invocation
    #   unavailable (has_pactkit_cli False)       -> complete fallback operation.
    # Fallbacks are object-form (not verb-led) so a "Run {TOKEN}" prefix never
    # produces "Run run", and no CLI option strays into prose.
    _viz_cmd = var_map["VISUALIZE_CMD"]
    _op_canonical = {
        "REGRESSION": "`pactkit regression`",
        "LINT": "`pactkit lint`",
        "CONTEXT_CONTINUATION": "`pactkit context --continuation`",
        "CLEANUP": "`pactkit clean`",
        "LAZY_VISUALIZE": "`pactkit visualize --lazy`",
        "INSTALL_UPDATE": "`pactkit update`",
        "GUARD": "`pactkit guard`",
        "DOCTOR": "`pactkit doctor`",
        "CONTINUATION": "`pactkit continuation resume`",
    }
    _op_fallback = {
        "REGRESSION": (
            "the test suite with impact classification "
            "(SKIP/IMPACT/FULL; e.g., `python3 -m pytest tests/ -v`)"
        ),
        "LINT": "the project linter (e.g., `ruff check src/ tests/`)",
        "CONTEXT_CONTINUATION": (
            "the context continuation update in ignored `.pactkit/context.md` "
            "— set `last-command` to the last PDCA command and `phase` to "
            "the current phase in the continuation section, for session handoff"
        ),
        "CLEANUP": "language-specific cleanup (e.g., `find . -name '__pycache__' -exec rm -rf {} +`)",
        "LAZY_VISUALIZE": f"`{_viz_cmd} --lazy` (file, `--mode class`, `--mode call` if source changed)",
        "INSTALL_UPDATE": f"`pactkit init --format {profile.name}` from the terminal to reinstall",
        "GUARD": "the init-marker and lint/test checks manually",
        "DOCTOR": "the project file and structure checks manually",
        "CONTINUATION": (
            "optional local handover notes; inspect the Story checkpoint, Spec, Board, "
            "and worktree only when useful, then continue from the current session"
        ),
    }
    _cli_preserving = profile.has_pactkit_cli
    for _op in _op_canonical:
        var_map["PACTKIT_OP_" + _op] = (
            _op_canonical[_op]
            if _cli_preserving
            else _op_fallback[_op]
        )

    # Replace only known variables via sequential string replacement.
    # This avoids str.format_map() issues with complex keys like {R1, R2, ...}
    # or {some description with commas} that appear in user-facing prompt text.
    result = template
    for key, value in var_map.items():
        result = result.replace("{" + key + "}", value)

    # Core CLI→fallback replacement (STORY-slim-145 R2 equivalent): for
    # CLI-unavailable profiles, replace canonical `pactkit <cmd>` code spans
    # with complete fallback operations. Safe complete-span matching (never
    # prefix), so no "Run run" or stranded args. Hyphenated subcommands
    # (e.g. `pactkit lint-testcase`) are NOT matched — they stay as-is.
    if not _cli_preserving:
        _sub_fallback = {
            "regression": _op_fallback["REGRESSION"],
            "lint": _op_fallback["LINT"],
            "clean": _op_fallback["CLEANUP"],
            "visualize": _op_fallback["LAZY_VISUALIZE"],
            "guard": _op_fallback["GUARD"],
            "doctor": _op_fallback["DOCTOR"],
            "update": _op_fallback["INSTALL_UPDATE"],
            "context": _op_fallback["CONTEXT_CONTINUATION"],
            "continuation": _op_fallback["CONTINUATION"],
        }
        _span_re = re.compile(r"`pactkit (" + "|".join(_sub_fallback) + r")(?=\s|`)[^`]*`")

        def _core_cli_repl(m):
            sub = m.group(1)
            if sub is not None and sub in _sub_fallback:
                return _sub_fallback[sub]
            full = m.group(0)
            return full if full is not None else ""

        result = _span_re.sub(_core_cli_repl, result)

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
    from pactkit.prompts.rules import RULE_DEFINITIONS, normalize_rule_id

    result = {filename.removesuffix(".md"): key for key, filename in prompts.RULES_FILES.items()}
    for rule_id, definition in RULE_DEFINITIONS.items():
        result[rule_id] = rule_id
        for legacy_id in definition.legacy_ids:
            result[legacy_id] = normalize_rule_id(legacy_id) or rule_id
    return result


def _build_rule_id_to_filename() -> dict:
    """Build reverse map: rule_id -> filename.

    Example: 'pactkit' -> 'pactkit.md', '01-workflow-conventions' -> '01-workflow-conventions.md'

    Used by _deploy_claude_md().
    """
    from pactkit.prompts.rules import RULE_DEFINITIONS

    result = {filename.removesuffix(".md"): filename for filename in prompts.RULES_FILES.values()}
    for rule_id, definition in RULE_DEFINITIONS.items():
        result[rule_id] = definition.filename
        for legacy_id in definition.legacy_ids:
            result[legacy_id] = definition.filename
    return result


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

    def deploy(self, config=None, target=None, project_root=None):
        _deploy_classic(config, target, project_root=project_root)


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
    no_git=False, no_external=False, non_interactive=False, mode=None,
    allow_skew: bool = False, project_root: Path | str | None = None,
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
        skipped: list[str] = []
        compat_skipped: list[str] = []
        for fmt_name in sorted(_DEPLOYER_REGISTRY):
            if fmt_name in _DEPLOYMENT_MODES:
                continue
            # STORY-slim-142 R1: adapters cannot honor -t (they always deploy
            # to their own home dirs); with an explicit target the call is a
            # preview/test — deploying into real homes would pollute them.
            if target is not None and fmt_name != "classic":
                skipped.append(fmt_name)
                continue
            # STORY-slim-145 R6: per-adapter compat gate. For format=all an
            # incompatible adapter is SKIPPED (skip-only) — other formats still
            # deploy and existing deployments are not destroyed. --allow-adapter-skew
            # overrides (warns, deploys anyway).
            if fmt_name != "classic":
                from pactkit.doctor import check_adapter_compat
                errors = check_adapter_compat(fmt_name, allow_skew=allow_skew)
                if errors:
                    compat_skipped.append(fmt_name)
                    for e in errors:
                        print(f"  ✗ {e}")
                    continue
            deployer_cls = _DEPLOYER_REGISTRY[fmt_name]
            deployer_instance = deployer_cls()
            # Classic respects -t target; adapters always deploy to their own default
            fmt_target = target if fmt_name == "classic" else None
            if isinstance(deployer_instance, ClassicDeployer):
                deployer_instance.deploy(
                    config=config, target=fmt_target, project_root=project_root,
                )
            else:
                deployer_instance.deploy(config=config, target=fmt_target)
        if skipped:
            print(f"Skipping adapter formats ({', '.join(skipped)}): -t target only applies to classic")
        if compat_skipped:
            print(f"Skipped incompatible adapters ({', '.join(compat_skipped)}) — upgrade or pass --allow-adapter-skew")
        return

    if format not in VALID_FORMATS:
        raise ValueError(f"Unknown format: {format!r}. Valid: {', '.join(VALID_FORMATS)}")

    # Marketplace is a meta-mode that wraps plugin
    if format == "marketplace":
        _deploy_marketplace(target)
        return

    # STORY-slim-057: Registry-based dispatch for environment formats
    if format in _DEPLOYER_REGISTRY:
        # Public Python callers must not bypass the CLI compatibility preflight.
        if format != "classic":
            from pactkit.doctor import check_adapter_compat

            errors = check_adapter_compat(format, allow_skew=allow_skew)
            if errors:
                raise ValueError("; ".join(errors))
        deployer_cls = _DEPLOYER_REGISTRY[format]
        deployer_instance = deployer_cls()
        if isinstance(deployer_instance, ClassicDeployer):
            deployer_instance.deploy(
                config=config, target=target, project_root=project_root,
            )
        else:
            deployer_instance.deploy(config=config, target=target)
        return

    # Fallback: format is in VALID_FORMATS but no deployer registered
    # (e.g., "opencode" without pactkit-opencode installed)
    raise ValueError(
        f"No deployer registered for format '{format}'. "
        f"Install the adapter package: pip install pactkit-{format}"
    )


def _deploy_classic(config=None, target=None, *, project_root=None):
    """Classic deployment — write files to ~/.claude/ (original behavior)."""
    project_root = Path(project_root or Path.cwd()).resolve()
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

        project_yaml = find_pactkit_yaml(project_root)
        if project_yaml is None:
            project_yaml = project_root / ".claude" / "pactkit.yaml"
        # Auto-merge new components before loading (STORY-009)
        auto_added = auto_merge_config_file(project_yaml)
        for item in auto_added:
            print(f"  -> Auto-added: {item}")
        # STORY-slim-077: Re-detect stacks for monorepo support
        if project_yaml.exists() and _update_stack_if_stale(project_yaml, project_root):
            print("  -> Stack re-detected from project markers")
        config = load_config(project_yaml)

    validate_config(config)
    config = activate_pactkit_maintainer_overlay(config, project_root)

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
    enabled_rules = config.get("rules", sorted(CURRENT_RULE_IDS - {"pactkit-maintainer"}))
    enabled_agents = config.get("agents", sorted(VALID_AGENTS))
    enabled_commands = config.get("commands", sorted(VALID_COMMANDS))

    classic_profile = get_profile("classic")
    _cleanup_legacy_portable_methods(skills_dir, classic_profile)
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
    _deploy_ci(ci_provider, project_root, config)

    # Generate pactkit.yaml at project-level if it doesn't exist (BUG-013)
    _generate_config_if_missing(project_root=project_root)

    # Generate project-level CLAUDE.md (always regenerate) and CLAUDE.local.md (if missing) (STORY-040)
    # Skip when target is specified (preview mode) to avoid modifying real project
    if target is None:
        _generate_project_claude_md(config, project_root=project_root)

    # Summary — STORY-slim-063: commands are now deployed as skills
    total_agents = len(VALID_AGENTS)
    from pactkit.prompts.skills import SKILL_MANIFEST

    total_skills = len(SKILL_MANIFEST) + len(VALID_COMMANDS)
    # VALID_RULES includes legacy aliases accepted only for migration.  They
    # are not separately deployed rules and must not inflate the user-facing
    # deployment summary. The optional maintainer overlay counts only when it
    # is active for PactKit self-development.
    total_rules = len(CURRENT_RULE_IDS - {"pactkit-maintainer"})
    if "pactkit-maintainer" in enabled_rules:
        total_rules += 1

    print(
        f"\n✅ Deployed: {n_agents}/{total_agents} Agents, "
        f"{n_skills + n_commands}/{total_skills} Skills "
        f"({n_skills} embedded + {n_commands} commands), "
        f"{n_rules}/{total_rules} Rules"
    )

    # STORY-slim-102: Write global version marker
    atomic_write(claude_root / ".pactkit-version", f"{__version__}\n")

    # STORY-slim-139 R2: machine-readable deployment manifest for parity checks
    from pactkit.deploy_manifest import write_deploy_manifest

    write_deploy_manifest(claude_root, "classic", config)

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
    _cleanup_legacy_portable_methods(skills_dir, get_profile("classic"), prefix)
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



def _deploy_skills(
    skills_dir,
    enabled_skills,
    profile=None,
    _legacy_prefix=None,
    include_portable_methods=False,
):
    """Deploy skill directories filtered by config.

    Iterates the single-source SKILL_MANIFEST (STORY-slim-139 R1) — no local
    hardcoded skill lists here or in adapters.

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

    from pactkit.prompts.skills import get_skill_manifest

    enabled_set = set(enabled_skills)
    deployed = 0

    for sd in get_skill_manifest(include_portable_methods=include_portable_methods):
        is_method = sd["name"].startswith("pactkit-method-")
        if not is_method and sd["name"] not in enabled_set:
            continue
        skill_dir = skills_dir / sd["name"]
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = _render_skill_md(sd, profile, _prefix)
        if profile is not None:
            _enforce_deploy_integrity(skill_md, profile, f"skill:{sd['name']}")
        atomic_write(skill_dir / "SKILL.md", skill_md)
        if sd["script_name"]:
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            atomic_write(scripts_dir / sd["script_name"], sd["script_source"])
        deployed += 1

    return deployed


def _cleanup_legacy_portable_methods(skills_dir, profile, _legacy_prefix=None):
    """Safely retire portable-method skills from a default deployment.

    The methods remain an explicit Core API, but they must not remain in an
    agent's default skill discovery after an upgrade.
    """
    from pactkit.portable_methods import get_portable_methods

    prefix = profile.skills_path_var if _legacy_prefix is None else _legacy_prefix
    # Plugin/marketplace historically rendered through the legacy prefix path
    # (with no FormatProfile).  Reconstruct exactly that form before deciding
    # a stale directory is safe to remove.
    render_profile = profile if _legacy_prefix is None else None
    expected = {
        item["name"]: _render_skill_md(item, render_profile, prefix)
        for item in get_portable_methods()
    }
    return cleanup_unmodified_legacy_skills(skills_dir, expected)


def _cleanup_legacy(skills_dir):
    """Clean up legacy pactkit_tools.py."""
    legacy = skills_dir / "pactkit_tools.py"
    if legacy.exists():
        legacy.unlink()


def _cleanup_legacy_commands(commands_dir):
    """Preserve legacy flat commands without a verifiable ownership record.

    File names alone do not prove PactKit created a file.  A deployment must
    never delete a user command simply because it is named ``project-*.md``.
    The legacy format predates the manifest, so its filename alone cannot
    safely distinguish a prior PactKit deployment from a user command.
    Managed skill directories are cleaned through the manifest maintained by
    :func:`_deploy_commands`; unproven legacy files stay available for manual
    review.
    """
    del commands_dir


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

    from pactkit.prompts.rules import (
        LEGACY_RULE_CONTENTS,
        RULE_DEFINITIONS,
        normalize_rule_id,
    )

    # A legacy filename is deleted only when its bytes still equal the exact
    # 2.23 managed content.  A matching name alone is never ownership proof.
    # This protects files the user edited in place before this registry existed.
    legacy_paths = {
        filename for filename in LEGACY_RULE_CONTENTS
    } | {
        "01-core-protocol.md", "02-hierarchy-of-truth.md",
        "03-file-atlas.md", "04-routing-table.md",
        "05-principles.md", "11-pdca-nudge.md",
        "05-workflow-conventions.md", "06-mcp-integration.md",
        "07-shared-protocols.md", "08-architecture-principles.md",
        "09-sectional-write.md", "12-solution-design.md",
    }
    for directory in (rules_dir, ondemand_dir):
        for path in directory.rglob("*.md"):
            if path.name not in legacy_paths:
                continue
            expected = LEGACY_RULE_CONTENTS.get(path.name)
            if expected is not None and path.read_text(encoding="utf-8") == expected:
                path.unlink()
            elif expected is not None:
                print(f"  ⚠️  preserved user-modified legacy rule: {path}")

    # The previous manifest is the only reliable ownership proof for a
    # current-format file.  A path can exist for many legitimate user reasons,
    # so never infer ownership from its name alone.
    previous_hashes = {}
    manifest_path = claude_root / ".pactkit-deployed.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = manifest.get("files", {})
            if isinstance(files, dict):
                previous_hashes = files
        except (OSError, ValueError, TypeError):
            # A corrupt advisory manifest must not make deployment unsafe or
            # unavailable.  It merely means we cannot prove old ownership.
            pass

    # Resolve current and legacy config identifiers to deduplicated logical IDs.
    enabled_ids = []
    for configured_id in enabled_rules:
        rule_id = normalize_rule_id(configured_id)
        if rule_id and rule_id not in enabled_ids:
            enabled_ids.append(rule_id)

    # A selective deployment is a projection of the configured registry, not
    # an additive install. Retire a disabled rule only when the previous
    # manifest proves ownership and the bytes are still unchanged. Modified
    # files remain user-owned and are omitted from the replacement manifest.
    enabled_paths = set()
    for rule_id in enabled_ids:
        definition = RULE_DEFINITIONS[rule_id]
        base = rules_dir if definition.load_policy == "global" else ondemand_dir
        enabled_paths.add((base / definition.filename).relative_to(claude_root).as_posix())
    for definition in RULE_DEFINITIONS.values():
        for base in (rules_dir, ondemand_dir):
            path = base / definition.filename
            relative = path.relative_to(claude_root).as_posix()
            expected_hash = previous_hashes.get(relative)
            if relative in enabled_paths or not path.is_file() or not expected_hash:
                continue
            import hashlib

            if hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash:
                path.unlink()
                parent = path.parent
                while parent not in (rules_dir, ondemand_dir, claude_root):
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent

    # Write only enabled rules to their registry-defined paths.
    deployed = 0
    for rule_id in enabled_ids:
        definition = RULE_DEFINITIONS[rule_id]
        filename = definition.filename
        content = definition.content

        # Render template variables if profile provided
        if profile is not None:
            content = _render_prompt(content, profile)

        # Add includeFiles frontmatter if scope is defined (STORY-028)
        scope = rule_scopes.get(rule_id)
        if scope is None:
            scope = next((rule_scopes[legacy] for legacy in definition.legacy_ids if legacy in rule_scopes), None)
        if scope:
            if isinstance(scope, list):
                include_lines = "\n".join(f'  - "{p}"' for p in scope)
                frontmatter = f"---\nincludeFiles:\n{include_lines}\n---\n\n"
            else:
                frontmatter = f'---\nincludeFiles: ["{scope}"]\n---\n\n'
            content = frontmatter + content

        # Runtime is the only always-loaded PactKit rule.  All others are
        # private to skills and are imported or inlined by the active command.
        dest_dir = rules_dir if definition.load_policy == "global" else ondemand_dir
        destination = dest_dir / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        relative_path = destination.relative_to(claude_root).as_posix()

        # Preserve a user-modified managed file.  Write the newly rendered
        # PactKit proposal alongside it so upgrade remains both non-destructive
        # and actionable.  The candidate deliberately stays outside the
        # manifest's owned set.
        expected_hash = previous_hashes.get(relative_path)
        if destination.is_file():
            import hashlib

            actual_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            # A same-named file without a prior manifest record is user-owned
            # until proven otherwise.  For a known managed file, a hash drift
            # has the same preservation behavior.
            if actual_hash != content_hash and (not expected_hash or actual_hash != expected_hash):
                candidate = destination.with_suffix(destination.suffix + ".pactkit-new")
                atomic_write(candidate, content)
                print(
                    f"  ⚠️  preserved user-modified PactKit rule: {destination}; "
                    f"wrote candidate {candidate.name}"
                )
                continue

        if profile is not None:
            _enforce_deploy_integrity(content, profile, f"rule:{rule_id}")
        atomic_write(destination, content)
        deployed += 1

    return deployed


def _deploy_guides(claude_root, profile=None, relative_dir=None):
    """Deploy engineering guide files to skills/_rules/guides/ (STORY-slim-128).

    Guides are on-demand reference files loaded by Act Phase 1.5 based on
    Spec's engineering concerns. Not loaded into context unless explicitly read.
    """
    from pactkit.prompts.guides import GUIDES_DIR, GUIDES_FILES

    guides_dir = (
        claude_root / relative_dir
        if relative_dir is not None
        else claude_root / "skills" / prompts.RULES_ONDEMAND_DIR / GUIDES_DIR
    )
    guides_dir.mkdir(parents=True, exist_ok=True)

    # The deployment manifest is the ownership proof for current-format
    # guides.  A matching filename alone is not authority to delete or
    # overwrite a user's local adaptation.
    previous_hashes = {}
    manifest_path = claude_root / ".pactkit-deployed.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = manifest.get("files", {})
            if isinstance(files, dict):
                previous_hashes = files
        except (OSError, ValueError, TypeError):
            # A corrupt advisory manifest must not make upgrades destructive.
            pass

    deployed = 0
    for filename, content in GUIDES_FILES.items():
        if profile is not None:
            content = _render_prompt(content, profile)
        destination = guides_dir / filename
        relative_path = destination.relative_to(claude_root).as_posix()
        expected_hash = previous_hashes.get(relative_path)
        if destination.is_file():
            import hashlib

            actual_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            # A same-named guide without a manifest record is user-owned
            # until PactKit can prove otherwise.  For a recorded guide, hash
            # drift gets the same non-destructive treatment.
            if actual_hash != content_hash and (not expected_hash or actual_hash != expected_hash):
                candidate = destination.with_suffix(destination.suffix + ".pactkit-new")
                atomic_write(candidate, content)
                print(
                    f"  ⚠️  preserved user-modified PactKit guide: {destination}; "
                    f"wrote candidate {candidate.name}"
                )
                continue
        atomic_write(destination, content)
        deployed += 1

    return deployed


def _is_pactkit_managed_global_md(content):
    """Detect if CLAUDE.md content is a PactKit-managed template (BUG-slim-089).

    Returns True if the first line starts with a PactKit generated heading.
    """
    first_line = content.split("\n", 1)[0] if content else ""
    return first_line.startswith(("# PactKit Global Constitution", "# PactKit Runtime Contract"))


def _deploy_claude_md(claude_root, enabled_rules):
    """Generate the small global Claude entrypoint.

    Only the Runtime Kernel is always loaded.  Phase and concern rules remain
    private to the active skill, preventing ordinary conversations from being
    captured by PDCA governance.

    BUG-slim-089: Read-before-write guard to preserve user-modified content.
    """
    claude_md_path = claude_root / "CLAUDE.md"
    new_header = f"# PactKit Runtime Contract (v{__version__})"
    new_content = f"{new_header}\n\n@~/.claude/rules/pactkit-runtime.md\n"

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

    # PactKit-managed — replace the tiny generated entrypoint as a whole. A
    # title-only rewrite would leave a 2.23 file without the new Runtime
    # import, while user-owned content has already returned above untouched.
    if existing != new_content:
        atomic_write(claude_md_path, new_content)
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
        _enforce_deploy_integrity(rendered, profile, f"agent:{name}")
        atomic_write(agent_path, rendered)
        deployed += 1

    return deployed


def _get_command_rules(cmd_name, config=None):
    """Resolve the rule list for a command (STORY-slim-011).

    Priority: config['command_rules'][cmd] > COMMAND_RULES_MAP default.
    Credential safety is part of the global Runtime Kernel and is therefore
    not duplicated into every command.

    Args:
        cmd_name: Command name (e.g. 'project-act').
        config: Optional config dict with 'command_rules' override.

    Returns:
        List of active rule IDs.
    """
    from pactkit.prompts.rules import normalize_rule_id

    if config and "command_rules" in config and cmd_name in config["command_rules"]:
        rules = list(config["command_rules"][cmd_name])
    else:
        rules = list(prompts.COMMAND_RULES_MAP.get(cmd_name, []))

    # Normalize legacy configuration values. The old virtual credential rule
    # maps to Runtime because credential safety is now self-contained there.
    # Unknown values are ignored here because
    # config validation reports them before deployment.
    normalized = []
    for rule in rules:
        current = "runtime" if rule == "credential" else normalize_rule_id(rule) or rule
        if current not in normalized:
            normalized.append(current)
    rules = normalized

    if config and config.get("_pactkit_self_development") and "pactkit-maintainer" not in rules:
        rules.append("pactkit-maintainer")

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
        from pactkit.prompts.rules import RULE_DEFINITIONS
        rule_id_to_filename = _build_rule_id_to_filename()
        ondemand_dir = prompts.RULES_ONDEMAND_DIR
        skills_prefix = profile.skills_dir  # e.g. "~/.claude/skills"
        lines = []
        for key in sorted(rules):
            filename = rule_id_to_filename.get(key)
            if filename:
                definition = RULE_DEFINITIONS.get(key)
                if definition and definition.load_policy == "global":
                    pass
                else:
                    lines.append(f"@{skills_prefix}/{ondemand_dir}/{filename}")
        lines.append("")  # blank line before command content
        return "\n".join(lines) + "\n"

    elif style == "inline":
        # Inline content embedding. Runtime is already global; every
        # phase/shared module is embedded
        # only for the active command.
        from pactkit.prompts.rules import RULE_DEFINITIONS
        parts = []
        for key in sorted(rules):
            definition = RULE_DEFINITIONS.get(key)
            if definition and definition.load_policy == "global":
                continue
            content = definition.content if definition else None
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
    _deploy_as_skill = profile.name == "classic" and _legacy_prefix is None
    manifest = {}
    if _deploy_as_skill:
        manifest = cleanup_disabled_command_skills(
            commands_dir, enabled_set, VALID_COMMANDS,
        )

    # Deploy enabled commands
    deployed = 0
    from pactkit.prompts.commands import get_deployable_commands

    for filename, content in get_deployable_commands().items():
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
        _enforce_deploy_integrity(rendered, profile, f"command:{cmd_name}")

        if _deploy_as_skill:
            # STORY-slim-063: Write as skills_dir/{name}/SKILL.md
            target = commands_dir / cmd_name / "SKILL.md"
            atomic_write(target, rendered)
            record_deployed_command(manifest, cmd_name, target)
        else:
            atomic_write(commands_dir / filename, rendered)
        deployed += 1

    if _deploy_as_skill:
        write_command_manifest(commands_dir, manifest)

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

    # Apply actions_ref prefix: "my-org/" -> "my-org/actions/checkout@v7"
    checkout_action = f"{actions_ref}actions/checkout@v7"
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


def _generate_config_if_missing(format: str | None = None, *, project_root=None):
    """Generate a missing pactkit.yaml in the format-aware project directory."""
    from pactkit.config import find_pactkit_yaml, resolve_pactkit_yaml_dir

    project_root = Path(project_root or Path.cwd()).resolve()
    # If already exists anywhere, skip
    if find_pactkit_yaml(project_root) is not None:
        return

    # STORY-slim-076: Auto-detect stacks for new projects
    from pactkit.cleaners import detect_stacks
    stacks = detect_stacks(project_root)

    yaml_path = resolve_pactkit_yaml_dir(cwd=project_root, format=format)
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
                "This project has codegraph enabled. Prefer codegraph over grep/find for code navigation.",
                "Run `codegraph --help` for available commands.",
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
    at_imports = "\n@./.claude/CLAUDE.local.md\n"
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
        if "@./.claude/CLAUDE.local.md" not in new_content:
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


def _generate_project_claude_md(config, *, project_root=None):
    """Merge managed CLAUDE.md content while preserving user-owned content."""
    project_root = Path(project_root or Path.cwd()).resolve()

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
    """Generate plugin CLAUDE.md with only the Runtime Kernel inlined."""
    from pactkit.prompts.rules import RULE_DEFINITIONS

    lines = [
        f"# PactKit Runtime Contract (v{__version__})", "",
        RULE_DEFINITIONS["runtime"].content.strip(), "",
        "Phase contracts and shared capabilities are supplied by the active command only.",
        "",
    ]

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
