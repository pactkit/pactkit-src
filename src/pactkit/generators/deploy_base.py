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


class DeployerBase:
    """Base class providing shared deployment methods.

    Adapter packages inherit this class and override `deploy()`.
    Shared methods delegate to the existing module-level functions in
    deployer.py to preserve backward compatibility with direct imports.
    """

    profile: FormatProfile = None  # type: ignore[assignment]  # subclass must set

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
    def deploy_rules(claude_root, enabled_rules, rule_scopes=None):
        from pactkit.generators.deployer import _deploy_rules

        return _deploy_rules(claude_root, enabled_rules, rule_scopes=rule_scopes)

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
    def deploy_ci(provider, project_root, config):
        from pactkit.generators.deployer import _deploy_ci

        return _deploy_ci(provider, project_root, config)


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
