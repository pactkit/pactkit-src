"""STORY-slim-065: _PACKAGING_MODES should use canonical _DEPLOYMENT_MODES from profiles.py.

Verifies deployer.py does not maintain a local duplicate of deployment-mode constants.
"""
from pathlib import Path


class TestNoLocalPackagingModes:
    """deployer.py must not define its own _PACKAGING_MODES constant."""

    def test_no_packaging_modes_in_deployer_source(self):
        """The string '_PACKAGING_MODES' should not appear in deployer.py source."""
        deployer_path = Path(__file__).resolve().parent.parent.parent / \
            "src" / "pactkit" / "generators" / "deployer.py"
        source = deployer_path.read_text()
        assert "_PACKAGING_MODES" not in source, (
            "deployer.py still defines _PACKAGING_MODES locally. "
            "Use _DEPLOYMENT_MODES from profiles.py instead."
        )


class TestDeployerImportsDeploymentModes:
    """deployer.py should import _DEPLOYMENT_MODES from profiles."""

    def test_deployment_modes_imported(self):
        """deployer.py must import _DEPLOYMENT_MODES from pactkit.profiles."""
        deployer_path = Path(__file__).resolve().parent.parent.parent / \
            "src" / "pactkit" / "generators" / "deployer.py"
        source = deployer_path.read_text()
        assert "_DEPLOYMENT_MODES" in source, (
            "deployer.py does not reference _DEPLOYMENT_MODES from profiles."
        )


class TestDeploymentModesCanonical:
    """_DEPLOYMENT_MODES in profiles.py is the single source of truth."""

    def test_deployment_modes_contains_plugin(self):
        from pactkit.profiles import _DEPLOYMENT_MODES
        assert "plugin" in _DEPLOYMENT_MODES

    def test_deployment_modes_contains_marketplace(self):
        from pactkit.profiles import _DEPLOYMENT_MODES
        assert "marketplace" in _DEPLOYMENT_MODES

    def test_deployment_modes_not_in_format_profiles(self):
        """Deployment modes should not be registered as environment profiles."""
        from pactkit.profiles import FORMAT_PROFILES, _DEPLOYMENT_MODES
        overlap = set(_DEPLOYMENT_MODES) & set(FORMAT_PROFILES)
        assert overlap == set(), f"Deployment modes overlap with profiles: {overlap}"
