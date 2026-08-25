"""DeployerProtocol, DeployerBase, and deployer registry.

STORY-slim-057: Provides the extension point for adapter packages
(pactkit-opencode, pactkit-trae) to register their own deployers.

Usage:
    from pactkit.generators.deploy_base import DeployerBase, register_deployer

    class OpenCodeDeployer(DeployerBase):
        profile = get_profile("opencode")
        def deploy(self, config=None, target=None): ...

    register_deployer("opencode", OpenCodeDeployer)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pactkit.profiles import FormatProfile


@runtime_checkable
class DeployerProtocol(Protocol):
    """Interface that all deployers must satisfy.

    Concrete deployers (ClassicDeployer, OpenCodeDeployer, etc.) must provide:
    - profile: FormatProfile — the format this deployer handles
    - deploy(config, target) -> None — the deployment entry point
    """

    profile: FormatProfile

    def deploy(self, config=None, target=None) -> None: ...


# ---------------------------------------------------------------------------
# Forbidden patterns for deploy-output validation (STORY-slim-084)
# ---------------------------------------------------------------------------

# Path patterns: each tuple is (pattern_substring, owning_global_config_dir_prefix)
_FORBIDDEN_PATH_PATTERNS: list[tuple[str, str]] = [
    ("~/.claude/skills/", "~/.claude"),
    ("~/.claude/rules/", "~/.claude"),
    ("~/.claude/commands/", "~/.claude"),
    ("~/.config/opencode/skills/", "~/.config/opencode"),
    ("~/.config/opencode/commands/", "~/.config/opencode"),
    ("~/.codex/skills/", "~/.codex"),
    ("~/.codex/rules/", "~/.codex"),
]

# CLI command patterns (checked only when has_pactkit_cli is False)
_FORBIDDEN_CLI_PATTERNS: list[str] = [
    "`pactkit visualize",
    "`pactkit clean",
    "`pactkit guard",
    "`pactkit lint",
    "`pactkit regression",
    "`pactkit context",
    "`pactkit doctor",
    "`pactkit update",
    "`pactkit continuation",
]
# --- Prompt integrity validators (STORY-slim-145 R4) ---
_DOUBLE_IMPERATIVE = re.compile(r"\bRun\s+run\b", re.IGNORECASE)
_STRANDED_OPTION = re.compile(r"\b(?:manually|directly|now|here)\s+--[\w-]+")
_UNRESOLVED_VAR = re.compile(r"\{PACTKIT_OP_\w+\}")
_PROJECT_ACT_MARKER = re.compile(r"project-act", re.IGNORECASE)
_PROJECT_ACT_PLAYBOOK = re.compile(r"#\s*Command:\s*Act\b", re.IGNORECASE)
# HTML comments survive all supported Markdown deployments but do not pollute
# the host UI.  They identify required workflow capabilities by operation,
# rather than treating a glossary containing the right English words as a
# usable Act playbook.
_REQUIRED_ACT_MARKERS = (
    "spec_lint",
    "tdd_red_green",
    "regression_classification",
    "lint",
    "continuation_update",
    "graph_sync",
    "board_update",
    "requirement_coverage",
)


def _check_lexical_integrity(content: str) -> list[str]:
    """Detect malformed Markdown introduced by deployment (R4 lexical layer)."""
    v: list[str] = []
    if _DOUBLE_IMPERATIVE.search(content):
        v.append("Duplicated imperative fragment: 'Run run'")
    # Count inline backticks only — strip paired fences, then any lone ```
    # fence delimiters, so only stray inline backticks (the Codex corruption
    # signature, e.g. a stranded closing backtick) trip the check. Pre-existing
    # source fence imbalance (odd ``{M}`` tokens) is not a deployment defect.
    _no_fences = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    _no_fences = re.sub(r"```", "", _no_fences)
    if _no_fences.count("`") % 2 != 0:
        v.append("Unbalanced Markdown backticks")
    if _STRANDED_OPTION.search(content):
        v.append("CLI option stranded in prose fallback (e.g. 'manually --continuation')")
    if _UNRESOLVED_VAR.search(content):
        v.append("Unresolved template variable: {PACTKIT_OP_*}")
    return v


def _check_semantic_integrity(content: str) -> list[str]:
    """Verify required project-act workflow operations are present (R4 semantic layer)."""
    v: list[str] = []
    if not (_PROJECT_ACT_MARKER.search(content) and _PROJECT_ACT_PLAYBOOK.search(content)):
        return v
    markers = set(re.findall(r"<!--\s*PACTKIT_ACT_OP:([a-z_]+)\s*-->", content))
    for operation in _REQUIRED_ACT_MARKERS:
        if operation not in markers:
            v.append(f"Missing required Act operation: {operation}")
    return v


class DeployerBase:
    """Base class providing shared deployment methods.

    Adapter packages inherit this class and override `deploy()`.
    Shared methods delegate to the existing module-level functions in
    deployer.py to preserve backward compatibility with direct imports.
    """

    profile: FormatProfile = None  # type: ignore[assignment]  # subclass must set

    # --- Deploy-output validation (STORY-slim-084) ---

    @staticmethod
    def validate_deployed_content(content: str, profile: FormatProfile) -> list[str]:
        """Check deployed content for patterns that should not appear in this profile.

        Returns a list of violation descriptions (empty = clean).
        Pure function — no side effects, safe for testing.
        """
        violations: list[str] = []

        # 1. Path patterns — skip if the pattern belongs to this profile's own config dir
        for pattern, owner_prefix in _FORBIDDEN_PATH_PATTERNS:
            if profile.global_config_dir.rstrip("/").startswith(owner_prefix):
                continue
            if pattern in content:
                violations.append(f"Foreign path reference: {pattern}")

        # 2. CLI command patterns — only check when profile lacks pactkit CLI
        if not profile.has_pactkit_cli:
            for line in content.splitlines():
                # Skip install instructions (pactkit init --format is guidance)
                if "pactkit init --format" in line:
                    continue
                # Skip lines already annotated as terminal-only guidance:
                # adapters convert unreachable CLI refs to "run from terminal" notes.
                if "from the terminal" in line or "(run from terminal)" in line or "(terminal only)" in line:
                    continue
                for cli_pat in _FORBIDDEN_CLI_PATTERNS:
                    # Use word-boundary check: the pattern must not be followed by a
                    # hyphen or alphanumeric character (which would indicate a different
                    # hyphenated subcommand, e.g. `pactkit lint-context` ≠ `pactkit lint`).
                    if re.search(re.escape(cli_pat) + r"(?![-\w])", line):
                        violations.append(f"CLI reference in CLI-less profile: {cli_pat}")

        # 3. Lexical + semantic prompt integrity (STORY-slim-145 R4) — all profiles.
        violations.extend(_check_lexical_integrity(content))
        violations.extend(_check_semantic_integrity(content))

        return violations

    def deploy(self, config=None, target=None) -> None:
        """Override in subclass."""
        raise NotImplementedError

    # --- Shared methods (thin wrappers around module-level functions) ---

    @staticmethod
    def render_prompt(template: str, profile: FormatProfile) -> str:
        from pactkit.generators.deployer import _render_prompt

        return _render_prompt(template, profile)

    @staticmethod
    def deploy_skills(skills_dir, enabled_skills, profile=None, _legacy_prefix=None):
        from pactkit.generators.deployer import _deploy_skills

        return _deploy_skills(skills_dir, enabled_skills, profile=profile, _legacy_prefix=_legacy_prefix)

    @staticmethod
    def deploy_rules(claude_root, enabled_rules, rule_scopes=None, profile=None):
        from pactkit.generators.deployer import _deploy_rules

        return _deploy_rules(claude_root, enabled_rules, rule_scopes=rule_scopes, profile=profile)

    @staticmethod
    def deploy_agents(agents_dir, enabled_agents, profile=None, agent_models=None, _legacy_prefix=None):
        from pactkit.generators.deployer import _deploy_agents

        return _deploy_agents(
            agents_dir, enabled_agents, profile=profile,
            agent_models=agent_models, _legacy_prefix=_legacy_prefix,
        )

    @staticmethod
    def deploy_commands(commands_dir, enabled_commands, profile=None, config=None, _legacy_prefix=None):
        from pactkit.generators.deployer import _deploy_commands

        return _deploy_commands(
            commands_dir, enabled_commands, profile=profile,
            config=config, _legacy_prefix=_legacy_prefix,
        )

    @staticmethod
    def deploy_guides(claude_root, profile=None):
        from pactkit.generators.deployer import _deploy_guides

        return _deploy_guides(claude_root, profile=profile)

    @staticmethod
    def deploy_ci(provider, project_root, config):
        from pactkit.generators.deployer import _deploy_ci

        return _deploy_ci(provider, project_root, config)

    @staticmethod
    def strip_excluded_command_references(content: str, profile: FormatProfile) -> str:
        """Remove references to excluded commands from deployed content.

        Currently handles project-sprint (the only excluded command).
        Called by adapter deployers after rendering prompts.
        """
        if "project-sprint" not in profile.excluded_commands:
            return content
        # Remove routing table Sprint section (### Sprint ... until next ###)
        content = re.sub(
            r'### Sprint \(`/project-sprint`\)\n(?:.*\n)*?(?=### |\n##|\Z)',
            '',
            content,
        )
        # Remove PDCA routing table Sprint row
        content = re.sub(r'\|.*`/project-sprint`.*\n', '', content)
        # Replace inline references with /project-act (single-story fallback)
        content = content.replace("Ready for /project-sprint", "Ready for /project-act")
        content = content.replace("ready for `/project-sprint`", "ready for `/project-act`")
        content = content.replace('"/project-sprint"', '"/project-act"')
        content = content.replace("'/project-sprint'", "'/project-act'")
        content = content.replace("`/project-sprint`", "`/project-act`")
        return content


# ---------------------------------------------------------------------------
# Deployer Registry
# ---------------------------------------------------------------------------

_DEPLOYER_REGISTRY: dict[str, type] = {}


def register_deployer(format_name: str, deployer_cls: type, *, force: bool = False) -> None:
    """Register a deployer class for a format name.

    Args:
        format_name: Format identifier (e.g., "opencode", "trae").
        deployer_cls: Class that inherits DeployerBase.
        force: If True, allow overwriting an existing registration.

    Raises:
        ValueError: If format_name is already registered and force is False.
    """
    if format_name in _DEPLOYER_REGISTRY and not force:
        raise ValueError(
            f"Deployer for '{format_name}' is already registered. "
            f"Use force=True to overwrite."
        )
    _DEPLOYER_REGISTRY[format_name] = deployer_cls


def get_deployer(format_name: str) -> type:
    """Look up a registered deployer class by format name.

    Raises:
        ValueError: If no deployer is registered, with a helpful install hint.
    """
    if format_name not in _DEPLOYER_REGISTRY:
        raise ValueError(
            f"No deployer registered for format '{format_name}'. "
            f"Install the adapter package: pip install pactkit-{format_name}"
        )
    return _DEPLOYER_REGISTRY[format_name]
