"""STORY-slim-139: skill manifest single source + adapter parity check."""

import json
from pathlib import Path


from pactkit.config import VALID_COMMANDS, VALID_SKILLS

PACTKIT_SKILLS = sorted(s for s in VALID_SKILLS if s.startswith("pactkit-"))


# ---------------------------------------------------------------------------
# R1: SKILL_MANIFEST single source
# ---------------------------------------------------------------------------


class TestSkillManifest:
    def test_manifest_covers_all_pactkit_skills(self):
        from pactkit.prompts.skills import SKILL_MANIFEST

        names = sorted(e["name"] for e in SKILL_MANIFEST)
        assert names == PACTKIT_SKILLS

    def test_manifest_entries_complete(self):
        from pactkit.prompts.skills import SKILL_MANIFEST

        for entry in SKILL_MANIFEST:
            assert entry["name"].startswith("pactkit-")
            assert entry["skill_md"].strip().startswith("---"), entry["name"]
            assert "script_name" in entry  # may be None for prompt-only

    def test_get_skill_manifest_resolves_scripts(self):
        from pactkit.prompts.skills import get_skill_manifest

        manifest = get_skill_manifest()
        scripted = [e for e in manifest if e["script_name"]]
        assert len(scripted) >= 4  # visualize/board/scaffold/report
        for entry in scripted:
            assert entry["script_source"].strip(), entry["name"]
        prompt_only = [e for e in manifest if not e["script_name"]]
        assert all("script_source" not in e for e in prompt_only)

    def test_deploy_skills_has_no_hardcoded_list(self):
        """AC1: _deploy_skills must iterate the manifest, not a local list."""
        import inspect

        from pactkit.generators import deployer

        src = inspect.getsource(deployer._deploy_skills)
        assert "scripted_skill_defs" not in src
        assert "prompt_only_skill_defs" not in src
        assert "get_skill_manifest" in src

    def test_deploy_skills_via_manifest(self, tmp_path):
        from pactkit.generators.deployer import _deploy_skills

        skills_dir = tmp_path / "skills"
        n = _deploy_skills(skills_dir, PACTKIT_SKILLS)
        assert n == len(PACTKIT_SKILLS)
        for name in PACTKIT_SKILLS:
            assert (skills_dir / name / "SKILL.md").exists(), name
        assert (skills_dir / "pactkit-board" / "scripts" / "board.py").exists()
        assert not (skills_dir / "pactkit-trace" / "scripts").exists()

    def test_enabled_filtering_still_works(self, tmp_path):
        from pactkit.generators.deployer import _deploy_skills

        enabled = [s for s in PACTKIT_SKILLS if s != "pactkit-garden"]
        n = _deploy_skills(tmp_path / "skills", enabled)
        assert n == len(PACTKIT_SKILLS) - 1
        assert not (tmp_path / "skills" / "pactkit-garden").exists()


# ---------------------------------------------------------------------------
# R2: deployment manifest on disk
# ---------------------------------------------------------------------------


class TestDeployManifest:
    def test_write_and_shape(self, tmp_path):
        from pactkit.deploy_manifest import write_deploy_manifest

        config = {"skills": PACTKIT_SKILLS, "commands": sorted(VALID_COMMANDS)}
        path = write_deploy_manifest(tmp_path, "classic", config)
        data = json.loads(path.read_text())
        assert data["format"] == "classic"
        assert data["pactkit_version"]
        assert sorted(data["skills"]) == PACTKIT_SKILLS
        assert "project-sprint" in data["commands"]  # classic has no exclusions

    def test_commands_respect_profile_exclusions(self, tmp_path):
        from pactkit.deploy_manifest import write_deploy_manifest

        config = {"skills": PACTKIT_SKILLS, "commands": sorted(VALID_COMMANDS)}
        path = write_deploy_manifest(tmp_path, "codex", config)
        data = json.loads(path.read_text())
        assert "project-sprint" not in data["commands"]


# ---------------------------------------------------------------------------
# R3: doctor parity check
# ---------------------------------------------------------------------------


def _write_manifest(root: Path, fmt: str, skills: list[str], commands: list[str]):
    from pactkit.config import VALID_AGENTS

    (root / ".pactkit-deployed.json").write_text(json.dumps({
        "format": fmt, "pactkit_version": "2.17.0",
        "skills": skills, "commands": commands, "agents": sorted(VALID_AGENTS),
    }))


class TestDeployParity:
    def test_drift_detected(self, tmp_path, monkeypatch):
        """AC3: codex manifest missing garden -> explicit drift report."""
        from pactkit.doctor import check_deploy_parity

        fake_home = tmp_path / "home"
        codex_dir = fake_home / ".codex"
        codex_dir.mkdir(parents=True)
        codex_cmds = sorted(set(VALID_COMMANDS) - {"project-sprint"})
        _write_manifest(codex_dir, "codex", [s for s in PACTKIT_SKILLS if s != "pactkit-garden"], codex_cmds)
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        project = tmp_path / "project"
        project.mkdir()
        result = check_deploy_parity(project)
        assert result["drift"] is True
        assert any("codex" in d and "pactkit-garden" in d for d in result["details"])

    def test_capability_matrix_no_false_positive(self, tmp_path, monkeypatch):
        """AC4: codex without project-sprint is legal — no drift."""
        from pactkit.doctor import check_deploy_parity

        fake_home = tmp_path / "home"
        codex_dir = fake_home / ".codex"
        codex_dir.mkdir(parents=True)
        codex_cmds = sorted(set(VALID_COMMANDS) - {"project-sprint"})
        _write_manifest(codex_dir, "codex", PACTKIT_SKILLS, codex_cmds)
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        project = tmp_path / "project"
        project.mkdir()
        result = check_deploy_parity(project)
        assert result["drift"] is False, result["details"]

    def test_missing_manifest_warns_not_fails(self, tmp_path, monkeypatch):
        """Pre-manifest deployments degrade to a re-deploy hint, not drift."""
        from pactkit.doctor import check_deploy_parity

        fake_home = tmp_path / "home"
        (fake_home / ".codex" / "skills").mkdir(parents=True)  # deployed but no manifest
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        project = tmp_path / "project"
        project.mkdir()
        result = check_deploy_parity(project)
        assert result["drift"] is False
        assert any("no deployment manifest" in w for w in result["warnings"])

    def test_corrupt_manifest_tolerated(self, tmp_path, monkeypatch):
        """SEC-2/SEC-7: corrupt JSON degrades to warning."""
        from pactkit.doctor import check_deploy_parity

        fake_home = tmp_path / "home"
        codex_dir = fake_home / ".codex"
        codex_dir.mkdir(parents=True)
        (codex_dir / ".pactkit-deployed.json").write_text("{oops")
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        project = tmp_path / "project"
        project.mkdir()
        result = check_deploy_parity(project)
        assert result["drift"] is False
        assert result["warnings"]
