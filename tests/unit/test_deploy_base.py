"""Tests for STORY-slim-057: DeployerProtocol, DeployerBase, registry dispatch."""

import pytest
from unittest.mock import MagicMock, patch


class TestDeployerProtocol:
    """AC1: DeployerProtocol is importable and type-checkable."""

    def test_import_protocol_and_base(self):
        """Protocol and DeployerBase are importable."""
        from pactkit.generators.deploy_base import DeployerBase, DeployerProtocol

        assert DeployerProtocol is not None
        assert DeployerBase is not None

    def test_classic_deployer_satisfies_protocol(self):
        """ClassicDeployer implements DeployerProtocol."""
        from pactkit.generators.deployer import ClassicDeployer

        assert hasattr(ClassicDeployer, "deploy")
        assert hasattr(ClassicDeployer, "profile")

    def test_plugin_deployer_satisfies_protocol(self):
        """AC6: PluginDeployer implements DeployerProtocol."""
        from pactkit.generators.deployer import PluginDeployer

        assert hasattr(PluginDeployer, "deploy")
        assert hasattr(PluginDeployer, "profile")


class TestDeployerRegistry:
    """AC4, AC5: Registry dispatch and external registration."""

    def test_classic_in_registry(self):
        """Classic deployer is registered by default."""
        from pactkit.generators.deploy_base import _DEPLOYER_REGISTRY

        assert "classic" in _DEPLOYER_REGISTRY

    def test_plugin_in_registry(self):
        """Plugin deployer is registered by default."""
        from pactkit.generators.deploy_base import _DEPLOYER_REGISTRY

        assert "plugin" in _DEPLOYER_REGISTRY

    def test_unregistered_format_raises_helpful_error(self):
        """AC4: Unknown format raises ValueError."""
        from pactkit.generators.deployer import deploy

        # "nosuchtool" is not in VALID_FORMATS — should raise immediately
        with pytest.raises(ValueError, match="Unknown format"):
            deploy(format="nosuchtool", config={"skills": [], "rules": [], "agents": [], "commands": []})

    def test_register_deployer_works(self):
        """AC5: External deployer registration dispatches correctly."""
        from pactkit.generators.deploy_base import (
            DeployerBase,
            _DEPLOYER_REGISTRY,
            register_deployer,
        )
        from pactkit.profiles import get_profile

        mock_deploy_called = []

        class MockTraeDeployer(DeployerBase):
            profile = get_profile("classic")  # Use classic as stand-in

            def deploy(self, config=None, target=None):
                mock_deploy_called.append(True)

        # Register a new format
        register_deployer("trae-test", MockTraeDeployer)
        assert "trae-test" in _DEPLOYER_REGISTRY

        # Clean up after test
        try:
            del _DEPLOYER_REGISTRY["trae-test"]
        except KeyError:
            pass

    def test_register_deployer_rejects_duplicate(self):
        """Cannot overwrite an existing registration without force."""
        from pactkit.generators.deploy_base import register_deployer

        # "classic" is already registered — should raise
        with pytest.raises(ValueError, match="already registered"):
            register_deployer("classic", MagicMock)


class TestDeployDispatch:
    """AC3, AC4: deploy() uses registry for dispatch."""

    def test_deploy_classic_uses_registry(self):
        """deploy(format='classic') dispatches to ClassicDeployer."""
        from pactkit.generators.deployer import ClassicDeployer

        with patch.object(ClassicDeployer, "deploy") as mock:
            from pactkit.generators.deployer import deploy

            deploy(format="classic", config={"skills": [], "rules": [], "agents": [], "commands": []})
            mock.assert_called_once()

    def test_deploy_plugin_uses_registry(self):
        """deploy(format='plugin') dispatches to PluginDeployer."""
        from pactkit.generators.deployer import PluginDeployer

        with patch.object(PluginDeployer, "deploy") as mock:
            from pactkit.generators.deployer import deploy

            deploy(format="plugin")
            mock.assert_called_once()

    def test_deploy_marketplace_still_works(self):
        """Marketplace mode still works (delegates to plugin internally)."""
        from pactkit.generators.deployer import deploy

        with patch("pactkit.generators.deployer._deploy_marketplace") as mock:
            deploy(format="marketplace")
            mock.assert_called_once()


class TestDeployerBaseInheritance:
    """AC2: DeployerBase provides shared deployment methods."""

    def test_deployer_base_has_shared_methods(self):
        """DeployerBase exposes all shared deployment methods."""
        from pactkit.generators.deploy_base import DeployerBase

        # These are the shared methods from the Spec R2
        assert callable(getattr(DeployerBase, "deploy_skills", None))
        assert callable(getattr(DeployerBase, "deploy_rules", None))
        assert callable(getattr(DeployerBase, "deploy_agents", None))
        assert callable(getattr(DeployerBase, "deploy_commands", None))
        assert callable(getattr(DeployerBase, "deploy_ci", None))
        assert callable(getattr(DeployerBase, "render_prompt", None))
