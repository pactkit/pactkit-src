"""Tests for STORY-slim-063: Migrate Claude Code commands to skills deployment."""


class TestAC1CommandsDeployedToSkillsDir:
    """AC1: Commands deployed to skills directory."""

    def test_commands_written_as_skill_md(self, tmp_path):
        """Commands should be written to skills_dir/{name}/SKILL.md."""
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        profile = get_profile("classic")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        enabled = ["project-plan", "project-act", "project-done"]
        n = _deploy_commands(skills_dir, enabled, profile=profile, config={})

        assert n == 3
        for cmd in enabled:
            skill_file = skills_dir / cmd / "SKILL.md"
            assert skill_file.exists(), f"{cmd}/SKILL.md not found"
            content = skill_file.read_text()
            assert "---" in content  # frontmatter present
            assert "description:" in content

    def test_no_flat_md_files_created(self, tmp_path):
        """No flat .md files should be created in the target dir."""
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        profile = get_profile("classic")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        _deploy_commands(skills_dir, ["project-plan"], profile=profile, config={})

        # No flat .md files in skills_dir root
        flat_files = list(skills_dir.glob("*.md"))
        assert flat_files == [], f"Unexpected flat files: {flat_files}"

    def test_rule_imports_present_in_skill_md(self, tmp_path):
        """@ rule imports should be prepended in the SKILL.md content."""
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        profile = get_profile("classic")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        _deploy_commands(skills_dir, ["project-plan"], profile=profile, config={})

        content = (skills_dir / "project-plan" / "SKILL.md").read_text()
        assert "@~/.claude/rules/" in content


class TestAC2ValidSkillsContainsAll:
    """AC2: VALID_SKILLS contains all 24 entries (+pactkit-audit, +pactkit-report)."""

    def test_valid_skills_count(self):
        from pactkit.config import VALID_SKILLS

        assert len(VALID_SKILLS) == 25

    def test_commands_in_valid_skills(self):
        from pactkit.config import VALID_COMMANDS, VALID_SKILLS

        for cmd in VALID_COMMANDS:
            assert cmd in VALID_SKILLS, f"{cmd} not in VALID_SKILLS"

    def test_original_skills_in_valid_skills(self):
        from pactkit.config import VALID_SKILLS

        original_skills = {
            "pactkit-visualize", "pactkit-board", "pactkit-scaffold",
            "pactkit-trace", "pactkit-draw", "pactkit-status",
            "pactkit-doctor", "pactkit-review", "pactkit-release",
            "pactkit-analyze",
        }
        for skill in original_skills:
            assert skill in VALID_SKILLS, f"{skill} not in VALID_SKILLS"


class TestAC3LegacyCommandFilesPreserved:
    """Legacy names alone must never authorize deletion."""

    def test_cleanup_preserves_project_md_files_without_ownership(self, tmp_path):
        """A user command named project-*.md is retained."""
        from pactkit.generators.deployer import _cleanup_legacy_commands

        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        # These may be user-authored; filename matching is not ownership.
        (commands_dir / "project-plan.md").write_text("old")
        (commands_dir / "project-act.md").write_text("old")
        # Non-PactKit file should be preserved
        (commands_dir / "ultra-think.md").write_text("keep")

        _cleanup_legacy_commands(commands_dir)

        assert (commands_dir / "project-plan.md").exists()
        assert (commands_dir / "project-act.md").exists()
        assert (commands_dir / "ultra-think.md").exists()


class TestAC4YamlCommandsSectionWorks:
    """AC4: pactkit.yaml commands section still works."""

    def test_selective_deployment(self, tmp_path):
        """Only enabled commands should be deployed."""
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        profile = get_profile("classic")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Only enable 2 of 11 commands
        enabled = ["project-plan", "project-act"]
        n = _deploy_commands(skills_dir, enabled, profile=profile, config={})

        assert n == 2
        assert (skills_dir / "project-plan" / "SKILL.md").exists()
        assert (skills_dir / "project-act" / "SKILL.md").exists()
        assert not (skills_dir / "project-done" / "SKILL.md").exists()

    def test_selective_redeploy_removes_only_manifest_owned_command(self, tmp_path):
        """A disabled command is removed only after PactKit deployed it."""
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        profile = get_profile("classic")
        _deploy_commands(skills_dir, ["project-plan", "project-act"], profile=profile, config={})
        _deploy_commands(skills_dir, ["project-plan"], profile=profile, config={})

        assert (skills_dir / "project-plan" / "SKILL.md").is_file()
        assert not (skills_dir / "project-act").exists()

    def test_selective_redeploy_preserves_modified_managed_command(self, tmp_path):
        """A user-edited command loses managed ownership instead of being deleted."""
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        profile = get_profile("classic")
        _deploy_commands(skills_dir, ["project-plan", "project-act"], profile=profile, config={})
        edited = skills_dir / "project-act" / "SKILL.md"
        edited.write_text("user-authored command\n", encoding="utf-8")
        _deploy_commands(skills_dir, ["project-plan"], profile=profile, config={})

        assert edited.read_text(encoding="utf-8") == "user-authored command\n"

    def test_selective_redeploy_preserves_extra_files_in_managed_command(self, tmp_path):
        """An unchanged SKILL.md does not own user files beside it."""
        from pactkit.generators.deployer import _deploy_commands
        from pactkit.profiles import get_profile

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        profile = get_profile("classic")
        _deploy_commands(skills_dir, ["project-plan", "project-act"], profile=profile, config={})
        extra = skills_dir / "project-act" / "scripts" / "local_helper.py"
        extra.parent.mkdir()
        extra.write_text("# user-owned\n", encoding="utf-8")

        _deploy_commands(skills_dir, ["project-plan"], profile=profile, config={})

        assert extra.read_text(encoding="utf-8") == "# user-owned\n"
        assert not (skills_dir / "project-act" / "SKILL.md").exists()


class TestAC5CrossFormatIsolation:
    """AC5: Codex and OpenCode unaffected."""

    def test_opencode_profile_unchanged(self):
        """OpenCode profile should not be affected — still deploys to its own commands_dir."""
        from pactkit.profiles import get_profile

        profile = get_profile("opencode")
        assert profile.commands_dir == "~/.config/opencode/commands"

    def test_codex_profile_unchanged(self):
        """Codex profile should not be affected."""
        from pactkit.profiles import get_profile

        profile = get_profile("codex")
        # Codex has its own commands_dir
        assert profile.commands_dir == "~/.codex/prompts"


class TestAC6SkillsCoexist:
    """AC6: Existing 10 skills coexist with 11 commands."""

    def test_no_name_collisions(self):
        """Command names and skill names should not overlap."""
        from pactkit.config import VALID_COMMANDS

        original_skills = {
            "pactkit-visualize", "pactkit-board", "pactkit-scaffold",
            "pactkit-trace", "pactkit-draw", "pactkit-status",
            "pactkit-doctor", "pactkit-review", "pactkit-release",
            "pactkit-analyze",
        }
        overlap = VALID_COMMANDS & original_skills
        assert overlap == set(), f"Name collision: {overlap}"
