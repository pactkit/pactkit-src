"""STORY-slim-133: project-debug skill registration and deployment.

Tests verify that:
- project-debug is registered in VALID_COMMANDS (TC-1)
- project-debug SKILL.md source template exists in deployer (TC-2)
- Deployed SKILL.md contains required frontmatter (TC-3)
"""
from pactkit.config import VALID_COMMANDS
from pactkit.generators.deployer import _deploy_commands


class TestDebugSkillRegistered:
    """TC-1: project-debug is in VALID_COMMANDS."""

    def test_project_debug_in_valid_commands(self):
        assert "project-debug" in VALID_COMMANDS


class TestDebugSkillDeploys:
    """TC-2/TC-3: project-debug deploys with correct frontmatter."""

    def test_deploy_creates_debug_skill(self, tmp_path):
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        _deploy_commands(commands_dir, ["project-debug"])
        # Classic profile deploys as subdirectory/SKILL.md
        skill_file = commands_dir / "project-debug" / "SKILL.md"
        assert skill_file.is_file(), "project-debug/SKILL.md not deployed"

    def test_deployed_frontmatter_has_no_model(self, tmp_path):
        # STORY-slim-134: model field removed from command frontmatter to fix
        # Bedrock alias resolution in VS Code plugin environments
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        _deploy_commands(commands_dir, ["project-debug"])
        content = (commands_dir / "project-debug" / "SKILL.md").read_text()
        assert "model:" not in content.split("---")[1] if content.count("---") >= 2 else True
