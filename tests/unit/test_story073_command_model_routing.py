"""
STORY-073: OpenCode Format Final Mile — Command Model Routing and Claude Code Residuals
Tests for command model routing, project-init conditional, YAML comments, doc strings.
"""


from pactkit.config import get_default_config
from pactkit.generators.deployer import deploy

try:
    from pactkit.generators.deployer import _resolve_opencode_model_id
except ImportError:
    _resolve_opencode_model_id = None


# ===========================================================================
# AC1: OpenCode command contains model
# ===========================================================================


class TestAC1CommandModel:
    """AC1: OpenCode commands with sonnet role have model: field."""

    def test_act_has_model(self, tmp_path):
        """project-act.md has model: in frontmatter."""
        out = tmp_path / "oc"
        deploy(format="opencode", target=str(out))
        content = (out / "commands" / "project-act.md").read_text()
        parts = content.split("---", 2)
        frontmatter = parts[1]
        assert "model:" in frontmatter

    def test_done_has_model(self, tmp_path):
        """project-done.md has model: in frontmatter."""
        out = tmp_path / "oc"
        deploy(format="opencode", target=str(out))
        content = (out / "commands" / "project-done.md").read_text()
        parts = content.split("---", 2)
        frontmatter = parts[1]
        assert "model:" in frontmatter

    def test_check_has_model(self, tmp_path):
        """project-check.md has model: in frontmatter."""
        out = tmp_path / "oc"
        deploy(format="opencode", target=str(out))
        content = (out / "commands" / "project-check.md").read_text()
        parts = content.split("---", 2)
        frontmatter = parts[1]
        assert "model:" in frontmatter


# ===========================================================================
# AC2: Plan command does NOT have model
# ===========================================================================


class TestAC2PlanNoModel:
    """AC2: Commands that inherit main model don't have model: field."""

    def test_plan_no_model(self, tmp_path):
        """project-plan.md does NOT have model: in frontmatter."""
        out = tmp_path / "oc"
        deploy(format="opencode", target=str(out))
        content = (out / "commands" / "project-plan.md").read_text()
        parts = content.split("---", 2)
        frontmatter = parts[1]
        for line in frontmatter.strip().split("\n"):
            assert not line.strip().startswith("model:"), f"Unexpected model: {line}"

    def test_clarify_no_model(self, tmp_path):
        """project-clarify.md does NOT have model: in frontmatter."""
        out = tmp_path / "oc"
        deploy(format="opencode", target=str(out))
        content = (out / "commands" / "project-clarify.md").read_text()
        parts = content.split("---", 2)
        frontmatter = parts[1]
        for line in frontmatter.strip().split("\n"):
            assert not line.strip().startswith("model:"), f"Unexpected model: {line}"


# ===========================================================================
# AC3: Classic format has no model field
# ===========================================================================


class TestAC3ClassicNoModel:
    """AC3: Classic format commands never have model: field."""

    def test_classic_no_model(self, tmp_path):
        """Classic project-act.md has no model: field."""
        out = tmp_path / "classic"
        deploy(format="classic", target=str(out))
        content = (out / "commands" / "project-act.md").read_text()
        parts = content.split("---", 2)
        frontmatter = parts[1]
        for line in frontmatter.strip().split("\n"):
            assert not line.strip().startswith("model:"), f"Unexpected model: {line}"


# ===========================================================================
# AC4: project-init conditional (playbook text check)
# ===========================================================================


class TestAC4InitConditional:
    """AC4: project-init has conditional CLAUDE.md vs AGENTS.md."""

    def test_init_has_conditional(self):
        """project-init playbook has OpenCode conditional for CLAUDE.md."""
        from pactkit.prompts import COMMANDS_CONTENT

        init_content = COMMANDS_CONTENT["project-init.md"]
        # Should mention skipping CLAUDE.md for OpenCode
        assert "OpenCode" in init_content
        assert "AGENTS.md" in init_content
        # Should NOT unconditionally say "Create CLAUDE.md"
        # It should be conditional on environment
        assert "Claude Code" in init_content or ".claude/" in init_content


# ===========================================================================
# AC5: YAML comments have no ~/.claude/
# ===========================================================================


class TestAC5YamlComments:
    """AC5: Generated pactkit.yaml comments don't reference ~/.claude/."""

    def test_default_yaml_no_claude_path(self):
        """generate_default_yaml() output has no ~/.claude/ in comments."""
        from pactkit.config import generate_default_yaml

        yaml_text = generate_default_yaml()
        for line in yaml_text.split("\n"):
            if line.strip().startswith("#"):
                assert "~/.claude/" not in line, f"Comment references ~/.claude/: {line}"

    def test_rewrite_yaml_no_claude_path(self, tmp_path, monkeypatch):
        """_rewrite_yaml() output has no ~/.claude/ in comments."""
        from pactkit.config import _rewrite_yaml, get_default_config

        monkeypatch.chdir(tmp_path)
        yaml_path = tmp_path / "test.yaml"
        _rewrite_yaml(yaml_path, get_default_config())
        content = yaml_path.read_text()
        for line in content.split("\n"):
            if line.strip().startswith("#"):
                assert "~/.claude/" not in line, f"Comment references ~/.claude/: {line}"


# ===========================================================================
# AC6: User can override command model
# ===========================================================================


class TestAC6CommandModelOverride:
    """AC6: command_models in config overrides defaults."""

    def test_default_config_has_command_models(self):
        """Default config includes command_models."""
        defaults = get_default_config()
        assert "command_models" in defaults
        assert isinstance(defaults["command_models"], dict)

    def test_resolve_model_id_sonnet(self):
        """_resolve_opencode_model_id resolves 'sonnet' to provider model ID."""
        # Mock provider config
        providers = {
            "my-provider": {
                "models": {
                    "claude-sonnet-4.6": {"name": "Sonnet"},
                    "claude-opus-4.6": {"name": "Opus"},
                }
            }
        }
        result = _resolve_opencode_model_id("sonnet", providers)
        assert result == "my-provider/claude-sonnet-4.6"

    def test_resolve_model_id_haiku(self):
        """_resolve_opencode_model_id resolves 'haiku' to provider model ID."""
        providers = {
            "my-provider": {
                "models": {
                    "claude-haiku-4.5": {"name": "Haiku"},
                }
            }
        }
        result = _resolve_opencode_model_id("haiku", providers)
        assert result == "my-provider/claude-haiku-4.5"

    def test_resolve_model_id_not_found(self):
        """_resolve_opencode_model_id returns None when model not found."""
        providers = {"my-provider": {"models": {"gpt-4": {"name": "GPT"}}}}
        result = _resolve_opencode_model_id("sonnet", providers)
        assert result is None

    def test_resolve_model_id_empty_providers(self):
        """_resolve_opencode_model_id returns None with empty providers."""
        result = _resolve_opencode_model_id("sonnet", {})
        assert result is None


# ===========================================================================
# Skills.py doc string update
# ===========================================================================


class TestR4DocStrings:
    """R4: skills.py doc strings mention both paths."""

    def test_skills_mention_opencode_path(self):
        """Skill doc strings mention OpenCode path."""
        from pactkit.prompts import skills as skills_mod

        # Check SKILL_VISUALIZE_MD or similar
        full_text = ""
        for attr_name in dir(skills_mod):
            val = getattr(skills_mod, attr_name)
            if isinstance(val, str) and "Script location" in val:
                full_text += val
        if full_text:
            assert "opencode" in full_text.lower() or "~/.config/opencode" in full_text
