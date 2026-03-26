"""Tests for STORY-slim-058: Extract pactkit-opencode as independent adapter package.

Tests the core-side changes: entry_point loading, OpenCode code removal,
and friendly error messages when pactkit-opencode is not installed.
"""

import pytest


class TestEntryPointLoading:
    """R3: entry_point auto-registration."""

    def test_load_entry_point_deployers_function_exists(self):
        """_load_entry_point_deployers is callable."""
        from pactkit.generators.deployer import _load_entry_point_deployers

        assert callable(_load_entry_point_deployers)

    def test_load_entry_point_deployers_populates_registry(self):
        """Entry points are scanned and registered."""
        from pactkit.generators.deploy_base import _DEPLOYER_REGISTRY

        # If pactkit-opencode is installed (pip install -e), opencode should be in registry
        # This test verifies the mechanism works, not a specific adapter
        assert isinstance(_DEPLOYER_REGISTRY, dict)
        # At minimum, classic and plugin are always registered
        assert "classic" in _DEPLOYER_REGISTRY
        assert "plugin" in _DEPLOYER_REGISTRY


class TestOpenCodeRemoval:
    """R4: OpenCode-specific functions removed from core deployer.py."""

    def test_no_deploy_opencode_function(self):
        """_deploy_opencode is NOT in deployer.py module namespace."""
        import pactkit.generators.deployer as mod

        assert not hasattr(mod, "_deploy_opencode"), \
            "_deploy_opencode should be moved to pactkit-opencode"

    def test_no_opencode_deployer_class_in_core(self):
        """OpenCodeDeployer is NOT in deployer.py module namespace."""
        import pactkit.generators.deployer as mod

        assert not hasattr(mod, "OpenCodeDeployer"), \
            "OpenCodeDeployer should be in pactkit-opencode, not core"

    def test_no_update_global_opencode_json(self):
        """_update_global_opencode_json is NOT in deployer.py."""
        import pactkit.generators.deployer as mod

        assert not hasattr(mod, "_update_global_opencode_json")

    def test_no_deploy_agents_md_inline(self):
        """_deploy_agents_md_inline is NOT in deployer.py."""
        import pactkit.generators.deployer as mod

        assert not hasattr(mod, "_deploy_agents_md_inline")

    def test_no_deploy_opencode_json(self):
        """_deploy_opencode_json is NOT in deployer.py."""
        import pactkit.generators.deployer as mod

        assert not hasattr(mod, "_deploy_opencode_json")

    def test_no_resolve_opencode_model_id(self):
        """_resolve_opencode_model_id is NOT in deployer.py."""
        import pactkit.generators.deployer as mod

        assert not hasattr(mod, "_resolve_opencode_model_id")

    def test_no_print_mcp_recommendations_opencode(self):
        """_print_mcp_recommendations_opencode is NOT in deployer.py."""
        import pactkit.generators.deployer as mod

        assert not hasattr(mod, "_print_mcp_recommendations_opencode")

    def test_no_generate_project_agents_md(self):
        """_generate_project_agents_md is NOT in deployer.py."""
        import pactkit.generators.deployer as mod

        assert not hasattr(mod, "_generate_project_agents_md")

    def test_no_load_opencode_providers(self):
        """_load_opencode_providers is NOT in deployer.py."""
        import pactkit.generators.deployer as mod

        assert not hasattr(mod, "_load_opencode_providers")


class TestFriendlyError:
    """R5: Friendly error message when pactkit-opencode is not installed."""

    def test_unregistered_opencode_gives_install_hint(self):
        """AC4: deploy(format='opencode') without adapter gives helpful message."""
        from pactkit.generators.deploy_base import _DEPLOYER_REGISTRY

        # Temporarily remove opencode registration if it exists
        saved = _DEPLOYER_REGISTRY.pop("opencode", None)
        try:
            from pactkit.generators.deployer import deploy

            with pytest.raises(ValueError, match="pactkit-opencode"):
                deploy(format="opencode")
        finally:
            if saved is not None:
                _DEPLOYER_REGISTRY["opencode"] = saved


class TestSharedFunctionsStillAccessible:
    """Verify shared functions used by both Classic and OpenCode remain in deployer.py."""

    def test_deploy_skills_exists(self):
        from pactkit.generators.deployer import _deploy_skills
        assert callable(_deploy_skills)

    def test_deploy_rules_exists(self):
        from pactkit.generators.deployer import _deploy_rules
        assert callable(_deploy_rules)

    def test_deploy_agents_exists(self):
        from pactkit.generators.deployer import _deploy_agents
        assert callable(_deploy_agents)

    def test_deploy_commands_exists(self):
        from pactkit.generators.deployer import _deploy_commands
        assert callable(_deploy_commands)

    def test_deploy_ci_exists(self):
        from pactkit.generators.deployer import _deploy_ci
        assert callable(_deploy_ci)

    def test_render_prompt_exists(self):
        from pactkit.generators.deployer import _render_prompt
        assert callable(_render_prompt)

    def test_convert_command_frontmatter_opencode_exists(self):
        """This shared function is used by _deploy_commands for OpenCode format — stays in core."""
        from pactkit.generators.deployer import _convert_command_frontmatter_opencode
        assert callable(_convert_command_frontmatter_opencode)

    def test_build_command_rules_header_exists(self):
        from pactkit.generators.deployer import _build_command_rules_header
        assert callable(_build_command_rules_header)
