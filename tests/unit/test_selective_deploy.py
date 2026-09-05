"""
STORY-002: Selective Deployment — Deployer filters by pactkit.yaml config.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from pactkit.config import get_default_config
from pactkit.generators.deployer import deploy
from pactkit.prompts import AGENTS_EXPERT, COMMANDS_CONTENT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_deploy(tmp_path, config=None):
    """Run deploy() with ~/.claude and $CWD redirected to tmp_path (BUG-013)."""
    claude_root = tmp_path / ".claude"
    for d in [claude_root, claude_root / "agents", claude_root / "commands", claude_root / "skills"]:
        d.mkdir(parents=True, exist_ok=True)

    with (
        patch.object(Path, "home", return_value=tmp_path),
        patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_path),
    ):
        deploy(config=config)

    return claude_root


# ===========================================================================
# S1: Full config deploys everything
# ===========================================================================


class TestFullConfigDeploysAll:
    def test_all_agents_deployed(self, tmp_path):
        claude = _run_deploy(tmp_path, config=get_default_config())
        agents_dir = claude / "agents"
        for name in AGENTS_EXPERT:
            assert (agents_dir / f"{name}.md").is_file(), f"Missing agent: {name}"

    def test_all_commands_deployed(self, tmp_path):
        # STORY-slim-063: commands are now deployed as skills/{name}/SKILL.md
        claude = _run_deploy(tmp_path, config=get_default_config())
        skills_dir = claude / "skills"
        for filename in COMMANDS_CONTENT:
            cmd_name = filename.removesuffix(".md")
            assert (skills_dir / cmd_name / "SKILL.md").is_file(), \
                f"Missing command skill: skills/{cmd_name}/SKILL.md"

    def test_all_skills_deployed(self, tmp_path):
        claude = _run_deploy(tmp_path, config=get_default_config())
        skills_dir = claude / "skills"
        for skill_name in ["pactkit-visualize", "pactkit-board", "pactkit-scaffold"]:
            assert (skills_dir / skill_name / "SKILL.md").is_file(), f"Missing skill: {skill_name}"

    def test_all_rules_deployed(self, tmp_path):
        """STORY-slim-112: Global rules in rules/, on-demand rules in skills/_rules/."""
        from pactkit.prompts.rules import RULES_CORE_FILES, RULES_ONDEMAND_FILES, RULES_ONDEMAND_DIR
        claude = _run_deploy(tmp_path, config=get_default_config())
        rules_dir = claude / "rules"
        # Global rules must be in rules/
        for filename in RULES_CORE_FILES.values():
            assert (rules_dir / filename).is_file(), f"Missing global rule: {filename}"
        # On-demand rules must be in skills/_rules/
        ondemand_dir = claude / "skills" / RULES_ONDEMAND_DIR
        for rule_id, filename in RULES_ONDEMAND_FILES.items():
            if rule_id == "pactkit-maintainer":
                continue
            assert (ondemand_dir / filename).is_file(), f"Missing on-demand rule: {filename}"

    def test_no_config_means_full_deploy(self, tmp_path):
        """Backward compat: deploy() with no config deploys everything."""
        claude = _run_deploy(tmp_path, config=None)
        agents_dir = claude / "agents"
        for name in AGENTS_EXPERT:
            assert (agents_dir / f"{name}.md").is_file()

    def test_upgrade_removes_only_unmodified_legacy_portable_methods(self, tmp_path):
        """Old default methods are retired without deleting user customizations."""
        from pactkit.generators.deployer import _render_skill_md
        from pactkit.portable_methods import get_portable_methods
        from pactkit.profiles import get_profile

        claude = tmp_path / ".claude"
        skills = claude / "skills"
        skills.mkdir(parents=True)
        profile = get_profile("classic")
        methods = get_portable_methods()
        old = methods[0]
        old_path = skills / old["name"] / "SKILL.md"
        old_path.parent.mkdir()
        old_path.write_text(
            _render_skill_md(old, profile, profile.skills_path_var), encoding="utf-8",
        )
        user_path = skills / methods[1]["name"] / "SKILL.md"
        user_path.parent.mkdir()
        user_path.write_text("user-owned override\n", encoding="utf-8")

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_path),
        ):
            deploy(config=get_default_config())

        assert not old_path.parent.exists()
        assert user_path.read_text(encoding="utf-8") == "user-owned override\n"

    def test_plugin_upgrade_removes_unmodified_legacy_portable_method(self, tmp_path):
        """Plugin migration compares against the plugin's historical rendering."""
        from pactkit.generators.deployer import (
            PLUGIN_SKILLS_PREFIX,
            _cleanup_legacy_portable_methods,
            _render_skill_md,
        )
        from pactkit.portable_methods import get_portable_methods
        from pactkit.profiles import get_profile

        skills = tmp_path / "skills"
        method = get_portable_methods()[0]
        legacy = skills / method["name"] / "SKILL.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(
            _render_skill_md(method, None, PLUGIN_SKILLS_PREFIX), encoding="utf-8",
        )

        removed = _cleanup_legacy_portable_methods(
            skills, get_profile("classic"), PLUGIN_SKILLS_PREFIX,
        )

        assert removed == {method["name"]}
        assert not legacy.parent.exists()


# ===========================================================================
# S2: Partial agent config
# ===========================================================================


class TestPartialAgentConfig:
    def test_only_selected_agents_deployed(self, tmp_path):
        cfg = get_default_config()
        cfg["agents"] = ["system-architect", "senior-developer"]

        claude = _run_deploy(tmp_path, config=cfg)
        agents_dir = claude / "agents"

        assert (agents_dir / "system-architect.md").is_file()
        assert (agents_dir / "senior-developer.md").is_file()

        # Others should NOT exist
        assert not (agents_dir / "qa-engineer.md").exists()
        assert not (agents_dir / "repo-maintainer.md").exists()
        assert not (agents_dir / "security-auditor.md").exists()

    def test_stale_agents_cleaned_on_partial(self, tmp_path):
        """Pre-existing managed agents not in config should be removed.

        STORY-slim-202608264cf429c75e22 R3: deletion requires the previous
        manifest to prove ownership, so the seeded agent is recorded the way
        a real prior deployment would have recorded it.
        """
        import hashlib
        import json

        claude = tmp_path / ".claude"
        agents_dir = claude / "agents"
        agents_dir.mkdir(parents=True)
        # Seed a managed agent that won't be in partial config
        (agents_dir / "qa-engineer.md").write_text("stale")
        (claude / ".pactkit-deployed.json").write_text(json.dumps({
            "files": {
                "agents/qa-engineer.md": hashlib.sha256(b"stale").hexdigest(),
            },
        }))

        cfg = get_default_config()
        cfg["agents"] = ["system-architect"]
        _run_deploy(tmp_path, config=cfg)

        assert not (agents_dir / "qa-engineer.md").exists()

    def test_unproven_stale_agent_preserved_on_partial(self, tmp_path):
        """A same-named agent file without manifest proof is user-owned (R3)."""
        claude = tmp_path / ".claude"
        agents_dir = claude / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "qa-engineer.md").write_text("possibly user content")

        cfg = get_default_config()
        cfg["agents"] = ["system-architect"]
        _run_deploy(tmp_path, config=cfg)

        assert (agents_dir / "qa-engineer.md").read_text() == "possibly user content"

    def test_user_custom_agent_preserved(self, tmp_path):
        claude = tmp_path / ".claude"
        agents_dir = claude / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "my-custom-agent.md").write_text("user content")

        cfg = get_default_config()
        cfg["agents"] = ["system-architect"]
        _run_deploy(tmp_path, config=cfg)

        assert (agents_dir / "my-custom-agent.md").is_file()
        assert (agents_dir / "my-custom-agent.md").read_text() == "user content"


# ===========================================================================
# S3: Partial command config
# ===========================================================================


class TestPartialCommandConfig:
    def test_only_selected_commands_deployed(self, tmp_path):
        # STORY-slim-063: commands are now deployed as skills/{name}/SKILL.md
        cfg = get_default_config()
        cfg["commands"] = ["project-plan", "project-act", "project-done"]

        claude = _run_deploy(tmp_path, config=cfg)
        skills_dir = claude / "skills"

        assert (skills_dir / "project-plan" / "SKILL.md").is_file()
        assert (skills_dir / "project-act" / "SKILL.md").is_file()
        assert (skills_dir / "project-done" / "SKILL.md").is_file()

        # Others should NOT exist
        assert not (skills_dir / "project-check" / "SKILL.md").exists()
        assert not (skills_dir / "project-sprint" / "SKILL.md").exists()

    def test_user_custom_command_preserved(self, tmp_path):
        claude = tmp_path / ".claude"
        cmds_dir = claude / "commands"
        cmds_dir.mkdir(parents=True)
        (cmds_dir / "ultra-think.md").write_text("user command")

        cfg = get_default_config()
        cfg["commands"] = ["project-plan"]
        _run_deploy(tmp_path, config=cfg)

        assert (cmds_dir / "ultra-think.md").is_file()


# ===========================================================================
# S4: CLAUDE.md reflects enabled rules only
# ===========================================================================


class TestSelectiveRules:
    def test_claude_md_loads_runtime_not_legacy_or_phase_rules(self, tmp_path):
        cfg = get_default_config()
        cfg["rules"] = ["pactkit", "01-workflow-conventions"]

        claude = _run_deploy(tmp_path, config=cfg)
        content = (claude / "CLAUDE.md").read_text()

        # STORY-slim-011: CLAUDE.md should not have old rule filenames
        assert "01-core-protocol.md" not in content
        assert "01-workflow-conventions.md" not in content
        assert "# PactKit Runtime Contract" in content
        assert "@~/.claude/rules/pactkit-runtime.md" in content
        assert "skills/_rules" not in content

    def test_only_enabled_rule_files_exist(self, tmp_path):
        cfg = get_default_config()
        cfg["rules"] = ["pactkit"]

        claude = _run_deploy(tmp_path, config=cfg)
        rules_dir = claude / "rules"

        assert (rules_dir / "pactkit-runtime.md").is_file()
        assert not (rules_dir / "01-core-protocol.md").exists()
        assert not (rules_dir / "02-mcp-integration.md").exists()

    def test_full_rules_deploys_all(self, tmp_path):
        """STORY-slim-112: Full deploy puts global rules in rules/, on-demand in skills/_rules/."""
        from pactkit.prompts.rules import RULES_CORE_FILES, RULES_ONDEMAND_FILES, RULES_ONDEMAND_DIR
        cfg = get_default_config()
        claude = _run_deploy(tmp_path, config=cfg)
        rules_dir = claude / "rules"
        ondemand_dir = claude / "skills" / RULES_ONDEMAND_DIR

        # Global rules in rules/
        for filename in RULES_CORE_FILES.values():
            assert (rules_dir / filename).is_file(), f"Missing global rule: {filename}"
        # On-demand rules in skills/_rules/
        for rule_id, filename in RULES_ONDEMAND_FILES.items():
            if rule_id == "pactkit-maintainer":
                continue
            assert (ondemand_dir / filename).is_file(), f"Missing on-demand rule: {filename}"


# ===========================================================================
# S5: Idempotent re-deploy preserves user config
# ===========================================================================


class TestIdempotentDeploy:
    def test_existing_yaml_not_overwritten(self, tmp_path):
        claude = tmp_path / ".claude"
        claude.mkdir(parents=True)
        yaml_path = claude / "pactkit.yaml"
        original_content = 'agents:\n  - system-architect\nversion: "9.9.9"\n'
        yaml_path.write_text(original_content)

        _run_deploy(tmp_path, config=get_default_config())

        assert yaml_path.read_text() == original_content


# ===========================================================================
# S6: Config file auto-generated on first init
# ===========================================================================


class TestConfigAutoGeneration:
    def test_yaml_created_when_missing(self, tmp_path):
        claude = _run_deploy(tmp_path, config=get_default_config())
        yaml_path = claude / "pactkit.yaml"
        assert yaml_path.is_file()

    def test_generated_yaml_is_valid(self, tmp_path):
        import yaml

        claude = _run_deploy(tmp_path, config=get_default_config())
        yaml_path = claude / "pactkit.yaml"
        parsed = yaml.safe_load(yaml_path.read_text())
        assert parsed is not None
        assert "stack" in parsed


# ===========================================================================
# S7: Deployment summary is printed
# ===========================================================================


class TestDeploymentSummary:
    def test_summary_printed_full(self, tmp_path, capsys):
        # 13 embedded skills + 12 commands.
        # Scenario registry: 1 Runtime Kernel + 20 command/shared modules.
        # STORY-slim-20260905efced66ebc9c R6: +4 phase capsules (init/clarify/design/debug).
        _run_deploy(tmp_path, config=get_default_config())
        output = capsys.readouterr().out
        assert "9/9 Agents" in output
        assert "25/25 Skills" in output
        assert "13 embedded" in output
        assert "12 commands" in output
        assert "21/21 Rules" in output

    def test_summary_printed_partial(self, tmp_path, capsys):
        # STORY-slim-133: 25 total (13 embedded + 12 commands)
        cfg = get_default_config()
        cfg["agents"] = ["system-architect", "senior-developer"]
        cfg["commands"] = ["project-plan", "project-act", "project-done"]

        _run_deploy(tmp_path, config=cfg)
        output = capsys.readouterr().out
        assert "2/9 Agents" in output
        # 13 embedded skills + 3 commands = 16 total skills deployed out of 25.
        assert "16/25 Skills" in output

    def test_self_development_summary_counts_the_maintainer_overlay(self, tmp_path, capsys):
        cfg = get_default_config()
        cfg["rules"].append("pactkit-maintainer")

        _run_deploy(tmp_path, config=cfg)
        assert "22/22 Rules" in capsys.readouterr().out


# ===========================================================================
# S8: Custom target directory works (via deploy with target param)
# ===========================================================================


class TestCustomTarget:
    def test_deploy_with_target(self, tmp_path):
        target = tmp_path / "custom-target"
        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_path):
            deploy(config=get_default_config(), target=str(target))

        assert (target / "agents").is_dir()
        assert (target / "commands").is_dir()
        assert (target / "skills").is_dir()
        assert (target / "CLAUDE.md").is_file()
        # Config is generated at $CWD/.claude/, not at target (BUG-013)
        assert (tmp_path / ".claude" / "pactkit.yaml").is_file()

    def test_target_agents_deployed(self, tmp_path):
        target = tmp_path / "custom-target"
        deploy(config=get_default_config(), target=str(target))

        for name in AGENTS_EXPERT:
            assert (target / "agents" / f"{name}.md").is_file()


# ===========================================================================
# Selective skill deployment
# ===========================================================================


class TestSelectiveSkills:
    def test_only_selected_skills_deployed(self, tmp_path):
        cfg = get_default_config()
        cfg["skills"] = ["pactkit-visualize"]

        claude = _run_deploy(tmp_path, config=cfg)
        skills_dir = claude / "skills"

        assert (skills_dir / "pactkit-visualize" / "SKILL.md").is_file()
        assert not (skills_dir / "pactkit-board" / "SKILL.md").exists()
        assert not (skills_dir / "pactkit-scaffold" / "SKILL.md").exists()

    def test_empty_skills_deploys_none(self, tmp_path):
        cfg = get_default_config()
        cfg["skills"] = []

        claude = _run_deploy(tmp_path, config=cfg)
        skills_dir = claude / "skills"

        for name in ["pactkit-visualize", "pactkit-board", "pactkit-scaffold"]:
            assert not (skills_dir / name / "SKILL.md").exists()


@pytest.mark.parametrize("payload", ["[]", "null", '"manifest"', "1"])
def test_non_object_command_ownership_manifest_does_not_half_deploy(tmp_path, payload):
    """Valid but non-object JSON is untrusted input, never a deploy blocker."""
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    manifest = skills_dir / ".pactkit-command-manifest.json"
    manifest.write_text(payload, encoding="utf-8")

    claude = _run_deploy(tmp_path, config=get_default_config())

    assert (claude / ".pactkit-version").is_file()
    assert (claude / ".pactkit-deployed.json").is_file()
    replacement = manifest.read_text(encoding="utf-8")
    assert '"version": 2' in replacement  # v2 schema (STORY-slim-20260827fc9de5542ad7)
