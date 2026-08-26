"""
STORY-slim-202608264cf429c75e22: Unify deployment ownership safety.

Skills, agents, CLAUDE.md and the rollback boundary must reach the same
manifest-hash ownership protection that rules and guides already have.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pactkit import __version__
from pactkit.deployment_transaction import rollback_paths
from pactkit.generators.deployer import (
    _deploy_agents,
    _deploy_claude_md,
    _deploy_guides,
    _deploy_rules,
    _deploy_skills,
)
from pactkit.profiles import get_profile

PROFILE = get_profile("classic")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_manifest(root: Path, files: dict, components: dict | None = None) -> None:
    payload: dict = {"files": files}
    if components:
        payload.update(components)
    (Path(root) / ".pactkit-deployed.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


# ===========================================================================
# AC1: user-modified skill preserved (R2)
# ===========================================================================

class TestSkillOwnership:
    def test_user_modified_skill_md_preserved_with_candidate(self, tmp_path):
        skills = tmp_path / "skills"
        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)
        skill_md = skills / "pactkit-visualize" / "SKILL.md"
        skill_md.write_text("user customized\n", encoding="utf-8")

        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)

        assert skill_md.read_text(encoding="utf-8") == "user customized\n"
        candidate = skills / "pactkit-visualize" / "SKILL.md.pactkit-new"
        assert candidate.is_file()

    def test_user_modified_skill_script_preserved_with_candidate(self, tmp_path):
        skills = tmp_path / "skills"
        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)
        script = skills / "pactkit-visualize" / "scripts" / "visualize.py"
        script.write_text("# user tweak\n", encoding="utf-8")

        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)

        assert script.read_text(encoding="utf-8") == "# user tweak\n"
        candidate = skills / "pactkit-visualize" / "scripts" / "visualize.py.pactkit-new"
        assert candidate.is_file()

    def test_manifest_proven_skill_updates_in_place(self, tmp_path):
        """AC2: bytes match the recorded hash -> overwrite, no candidate."""
        skills = tmp_path / "skills"
        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)
        skill_md = skills / "pactkit-visualize" / "SKILL.md"
        rendered = skill_md.read_text(encoding="utf-8")
        stale = "previous version content\n"
        skill_md.write_text(stale, encoding="utf-8")
        _write_manifest(
            tmp_path,
            {"skills/pactkit-visualize/SKILL.md": _sha(stale.encode("utf-8"))},
        )

        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)

        assert skill_md.read_text(encoding="utf-8") == rendered
        assert not (skills / "pactkit-visualize" / "SKILL.md.pactkit-new").exists()


# ===========================================================================
# AC3: agent deletion/overwrite requires ownership proof (R3)
# ===========================================================================

class TestAgentOwnership:
    @pytest.fixture
    def agents_dir(self, tmp_path):
        agents = tmp_path / "agents"
        agents.mkdir()
        return agents

    def test_retirement_without_manifest_proof_preserves_user_file(self, agents_dir):
        (agents_dir / "system-architect.md").write_text(
            "# user's own architect\n", encoding="utf-8"
        )

        _deploy_agents(agents_dir, ["qa-engineer"], profile=PROFILE)

        assert (agents_dir / "system-architect.md").read_text(
            encoding="utf-8"
        ) == "# user's own architect\n"

    def test_retirement_with_manifest_proof_deletes(self, agents_dir, tmp_path):
        content = "# rendered by pactkit\n"
        (agents_dir / "system-architect.md").write_text(content, encoding="utf-8")
        _write_manifest(
            tmp_path, {"agents/system-architect.md": _sha(content.encode("utf-8"))}
        )

        _deploy_agents(agents_dir, ["qa-engineer"], profile=PROFILE)

        assert not (agents_dir / "system-architect.md").exists()

    def test_user_modified_enabled_agent_preserved(self, agents_dir):
        (agents_dir / "qa-engineer.md").write_text("user edited\n", encoding="utf-8")

        _deploy_agents(agents_dir, ["qa-engineer"], profile=PROFILE)

        assert (agents_dir / "qa-engineer.md").read_text(encoding="utf-8") == "user edited\n"
        assert (agents_dir / "qa-engineer.md.pactkit-new").is_file()

    def test_manifest_proven_agent_updates_in_place(self, agents_dir, tmp_path):
        (agents_dir / "qa-engineer.md").write_text("old rendered\n", encoding="utf-8")
        _write_manifest(
            tmp_path, {"agents/qa-engineer.md": _sha(b"old rendered\n")}
        )

        _deploy_agents(agents_dir, ["qa-engineer"], profile=PROFILE)

        assert (agents_dir / "qa-engineer.md").read_text(encoding="utf-8") != "old rendered\n"
        assert not (agents_dir / "qa-engineer.md.pactkit-new").exists()


# ===========================================================================
# AC4: manifest must not over-claim skill directory contents (R4)
# ===========================================================================

class TestManifestOwnershipScope:
    def test_user_file_in_skill_dir_not_claimed(self, tmp_path):
        skills = tmp_path / "skills"
        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)
        notes = skills / "pactkit-visualize" / "references" / "my-notes.md"
        notes.parent.mkdir(parents=True)
        notes.write_text("user notes\n", encoding="utf-8")

        from pactkit.deploy_manifest import expected_components, pactkit_owned_files

        components = expected_components(
            "classic", {"skills": ["pactkit-visualize"], "commands": [], "agents": []}
        )
        owned = pactkit_owned_files(tmp_path, components, "classic")

        assert "skills/pactkit-visualize/references/my-notes.md" not in owned
        assert "skills/pactkit-visualize/SKILL.md" in owned
        assert "skills/pactkit-visualize/scripts/visualize.py" in owned


# ===========================================================================
# AC5/AC6: CLAUDE.md preservation (R5)
# ===========================================================================

class TestClaudeMdSafety:
    def test_unreadable_claude_md_preserved_with_candidate(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_bytes(b"\xff\xfe\x00 not utf8")

        _deploy_claude_md(tmp_path, [])

        assert claude_md.read_bytes() == b"\xff\xfe\x00 not utf8"
        assert (tmp_path / "CLAUDE.md.pactkit-new").is_file()

    def test_appended_claude_md_user_content_preserved(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            "# PactKit Runtime Contract (v0.0.1)\n\n"
            "@~/.claude/rules/pactkit-runtime.md\n\n"
            "# My personal rules\nDo things.\n",
            encoding="utf-8",
        )

        _deploy_claude_md(tmp_path, [])

        content = claude_md.read_text(encoding="utf-8")
        assert f"# PactKit Runtime Contract (v{__version__})" in content
        assert "@~/.claude/rules/pactkit-runtime.md" in content
        assert "# My personal rules" in content
        assert "Do things." in content

    def test_non_managed_claude_md_untouched(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        original = "# My totally custom file\n"
        claude_md.write_text(original, encoding="utf-8")

        _deploy_claude_md(tmp_path, [])

        assert claude_md.read_text(encoding="utf-8") == original
        assert not (tmp_path / "CLAUDE.md.pactkit-new").exists()


# ===========================================================================
# AC7/AC10: rollback covers interrupts and restore isolation (R6/R7)
# ===========================================================================

class TestRollbackBoundary:
    def test_keyboard_interrupt_rolls_back(self, tmp_path):
        target = tmp_path / "config.toml"
        target.write_text("before", encoding="utf-8")

        with pytest.raises(KeyboardInterrupt):
            with rollback_paths((target,)):
                target.write_text("partial", encoding="utf-8")
                raise KeyboardInterrupt()

        assert target.read_text(encoding="utf-8") == "before"

    def test_restore_failure_does_not_abort_remaining_restores(self, tmp_path, monkeypatch):
        import pactkit.deployment_transaction as dt

        a = tmp_path / "a.txt"
        a.write_text("a-before", encoding="utf-8")
        b = tmp_path / "b.txt"
        b.write_text("b-before", encoding="utf-8")
        real_copy2 = dt.shutil.copy2

        def flaky_copy2(src, dst, **kwargs):
            if Path(dst) == a:
                raise OSError("forced restore failure")
            return real_copy2(src, dst, **kwargs)

        monkeypatch.setattr(dt.shutil, "copy2", flaky_copy2)

        with pytest.raises(RuntimeError, match="deploy failed"):
            with rollback_paths((a, b)):
                a.write_text("a-after", encoding="utf-8")
                b.write_text("b-after", encoding="utf-8")
                raise RuntimeError("deploy failed")

        assert b.read_text(encoding="utf-8") == "b-before"


# ===========================================================================
# AC8: disabled skill retirement by proof (R8)
# ===========================================================================

class TestSkillRetirement:
    def test_disabled_skill_retired_when_proven(self, tmp_path):
        skills = tmp_path / "skills"
        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)
        skill_md = skills / "pactkit-visualize" / "SKILL.md"
        script = skills / "pactkit-visualize" / "scripts" / "visualize.py"
        _write_manifest(
            tmp_path,
            {
                "skills/pactkit-visualize/SKILL.md": _sha(skill_md.read_bytes()),
                "skills/pactkit-visualize/scripts/visualize.py": _sha(script.read_bytes()),
            },
            components={"skills": ["pactkit-visualize"]},
        )

        _deploy_skills(skills, ["pactkit-board"], profile=PROFILE)

        assert not (skills / "pactkit-visualize").exists()
        assert (skills / "pactkit-board" / "SKILL.md").is_file()

    def test_drifted_disabled_skill_preserved(self, tmp_path):
        skills = tmp_path / "skills"
        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)
        skill_md = skills / "pactkit-visualize" / "SKILL.md"
        drifted = "user customized\n"
        skill_md.write_text(drifted, encoding="utf-8")
        script = skills / "pactkit-visualize" / "scripts" / "visualize.py"
        _write_manifest(
            tmp_path,
            {
                "skills/pactkit-visualize/SKILL.md": _sha(b"other bytes"),
                "skills/pactkit-visualize/scripts/visualize.py": _sha(script.read_bytes()),
            },
            components={"skills": ["pactkit-visualize"]},
        )

        _deploy_skills(skills, ["pactkit-board"], profile=PROFILE)

        assert skill_md.read_text(encoding="utf-8") == drifted


# ===========================================================================
# AC9: rules/guides preservation semantics unchanged after refactor (R1)
# ===========================================================================

class TestRulesGuidesRegression:
    def test_rules_preservation_semantics_unchanged(self, tmp_path):
        _deploy_rules(tmp_path, enabled_rules=["git-workflow"], profile=PROFILE)
        rule_files = [
            path for path in tmp_path.rglob("*.md")
            if ".pactkit-new" not in path.name and "guides" not in path.parts
        ]
        assert rule_files, "expected at least one deployed rule file"
        rule = rule_files[0]
        rule.write_text("user override\n", encoding="utf-8")

        _deploy_rules(tmp_path, enabled_rules=["git-workflow"], profile=PROFILE)

        assert rule.read_text(encoding="utf-8") == "user override\n"
        assert rule.with_suffix(rule.suffix + ".pactkit-new").is_file()

    def test_guides_preservation_semantics_unchanged(self, tmp_path):
        _deploy_guides(tmp_path, profile=PROFILE)
        guides_dir = next(
            path for path in tmp_path.rglob("guides") if path.is_dir()
        )
        guide = next(guides_dir.glob("*.md"))
        guide.write_text("user override\n", encoding="utf-8")

        _deploy_guides(tmp_path, profile=PROFILE)

        assert guide.read_text(encoding="utf-8") == "user override\n"
        assert guide.with_suffix(guide.suffix + ".pactkit-new").is_file()


# ===========================================================================
# Plugin/marketplace regeneration must keep overwriting (generation mode)
# ===========================================================================

class TestPluginGenerationMode:
    def test_plugin_regeneration_overwrites_modified_skill(self, tmp_path):
        from pactkit.generators.deployer import deploy

        out = tmp_path / "pactkit-plugin"
        deploy(format="plugin", target=str(out))
        skill_dirs = [
            path for path in (out / "skills").iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        ]
        assert skill_dirs
        skill_md = skill_dirs[0] / "SKILL.md"
        skill_md.write_text("stale generated content\n", encoding="utf-8")

        deploy(format="plugin", target=str(out))

        assert skill_md.read_text(encoding="utf-8") != "stale generated content\n"
        assert not list(out.rglob("*.pactkit-new"))


# ===========================================================================
# QA fix iteration (2026-08-26): command-skill bypass + CLAUDE.md boundaries
# ===========================================================================

class TestCommandSkillOwnership:
    """QA P1: _deploy_commands must not overwrite drifted command SKILL.md."""

    def test_user_modified_command_skill_preserved(self, tmp_path):
        from unittest.mock import patch

        from pactkit.config import get_default_config
        from pactkit.generators.deployer import deploy

        claude = tmp_path / ".claude"
        cfg = get_default_config()
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_path),
        ):
            deploy(config=cfg)

        skill_md = claude / "skills" / "project-act" / "SKILL.md"
        assert skill_md.is_file(), "expected command skill deployed"
        drifted = "USER CUSTOMIZED COMMAND PLAYBOOK\n"
        skill_md.write_text(drifted, encoding="utf-8")

        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_path),
        ):
            deploy(config=cfg)

        assert skill_md.read_text(encoding="utf-8") == drifted
        assert (skill_md.parent / "SKILL.md.pactkit-new").is_file()


class TestClaudeMdBoundaryTightening:
    """QA P2: interleaved or quoted import lines must fail safe."""

    def test_user_content_between_header_and_import_preserved(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        original = (
            "# PactKit Runtime Contract (v0.0.1)\n\n"
            "MY IMPORTANT USER NOTE\n\n"
            "@~/.claude/rules/pactkit-runtime.md\n\n"
            "trailing\n"
        )
        claude_md.write_text(original, encoding="utf-8")

        _deploy_claude_md(tmp_path, [])

        assert claude_md.read_text(encoding="utf-8") == original
        assert (tmp_path / "CLAUDE.md.pactkit-new").is_file()

    def test_user_quoted_import_line_preserved(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        original = (
            "# PactKit Runtime Contract (v0.0.1)\n"
            "User docs:\n"
            "@~/.claude/rules/pactkit-runtime.md\n"
            "more notes\n"
        )
        claude_md.write_text(original, encoding="utf-8")

        _deploy_claude_md(tmp_path, [])

        assert claude_md.read_text(encoding="utf-8") == original
        assert (tmp_path / "CLAUDE.md.pactkit-new").is_file()


class TestGateUnification:
    """QA P2: a bare deploy_skills call must fail safe (enforce ownership)."""

    def test_bare_deploy_skills_call_enforces_ownership(self, tmp_path):
        skills = tmp_path / "skills"
        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)
        skill_md = skills / "pactkit-visualize" / "SKILL.md"
        skill_md.write_text("user customized\n", encoding="utf-8")

        # Neither profile nor _legacy_prefix: must not silently degrade to
        # unconditional overwrite.
        _deploy_skills(skills, ["pactkit-visualize"])

        assert skill_md.read_text(encoding="utf-8") == "user customized\n"
        assert (skills / "pactkit-visualize" / "SKILL.md.pactkit-new").is_file()


class TestRetirementProofHardening:
    """QA P3: a user-created empty subdirectory must block retirement."""

    def test_empty_user_subdir_prevents_retirement(self, tmp_path):
        skills = tmp_path / "skills"
        _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE)
        skill_md = skills / "pactkit-visualize" / "SKILL.md"
        script = skills / "pactkit-visualize" / "scripts" / "visualize.py"
        (skills / "pactkit-visualize" / "references").mkdir()
        _write_manifest(
            tmp_path,
            {
                "skills/pactkit-visualize/SKILL.md": _sha(skill_md.read_bytes()),
                "skills/pactkit-visualize/scripts/visualize.py": _sha(script.read_bytes()),
            },
            components={"skills": ["pactkit-visualize"]},
        )

        _deploy_skills(skills, ["pactkit-board"], profile=PROFILE)

        assert (skills / "pactkit-visualize").is_dir()


class TestDeployedCountHonesty:
    """QA P3: preserved (skipped) skills must not inflate the deployed count."""

    def test_preserved_skill_not_counted(self, tmp_path):
        skills = tmp_path / "skills"
        assert _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE) == 1
        (skills / "pactkit-visualize" / "SKILL.md").write_text(
            "user customized\n", encoding="utf-8"
        )

        assert _deploy_skills(skills, ["pactkit-visualize"], profile=PROFILE) == 0
