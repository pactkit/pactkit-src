"""STORY-slim-141: deployment manifest content hash + doctor content-level parity.

The manifest gains a per-file sha256 ``files`` field (R1); ``doctor``'s parity
check drops from component-name-list comparison to per-file content comparison
(R2), with backward-compat downgrade for pre-2.18 manifests (R3) and zero
false-positives for merge-semantics files (R4).
"""

import hashlib
import json
from pathlib import Path

from pactkit.config import VALID_AGENTS, VALID_COMMANDS, VALID_SKILLS

PACTKIT_SKILLS = sorted(s for s in VALID_SKILLS if s.startswith("pactkit-"))

EXCLUDED = {
    ".pactkit-deployed.json",
    ".pactkit-version",
    "CLAUDE.md",
}


def _deploy_fake_tree(root: Path) -> dict:
    """Create a minimal pactkit-owned file tree and return expected rel->hash."""
    (root / "skills" / "pactkit-board" / "SKILL.md").parent.mkdir(parents=True, exist_ok=True)
    board = (root / "skills" / "pactkit-board" / "SKILL.md")
    board.write_text("---\nname: pactkit-board\n---\n", encoding="utf-8")

    (root / "agents" / "qa-engineer.md").parent.mkdir(parents=True, exist_ok=True)
    agent = (root / "agents" / "qa-engineer.md")
    agent.write_text("---\nname: qa-engineer\n---\n", encoding="utf-8")

    (root / "rules").mkdir(parents=True, exist_ok=True)
    rule = (root / "rules" / "pactkit.md")
    rule.write_text("# pactkit rule\n", encoding="utf-8")

    # Merge-semantics / meta files — MUST be excluded from hashing (R1/R4).
    (root / "CLAUDE.md").write_text("# constitution\n", encoding="utf-8")
    (root / ".pactkit-version").write_text("2.17.0\n", encoding="utf-8")

    return {
        "skills/pactkit-board/SKILL.md": _sha256(board),
        "agents/qa-engineer.md": _sha256(agent),
        "rules/pactkit.md": _sha256(rule),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _full_config() -> dict:
    return {"skills": PACTKIT_SKILLS, "commands": sorted(VALID_COMMANDS)}


# ---------------------------------------------------------------------------
# R1: manifest carries per-file hashes
# ---------------------------------------------------------------------------


class TestManifestFiles:
    def test_write_includes_files_hash(self, tmp_path):
        from pactkit.deploy_manifest import write_deploy_manifest

        expected = _deploy_fake_tree(tmp_path)
        write_deploy_manifest(tmp_path, "classic", _full_config())
        data = json.loads((tmp_path / ".pactkit-deployed.json").read_text())

        assert "files" in data
        for rel, digest in expected.items():
            assert data["files"][rel] == digest
        # Exclusions absent (R4).
        assert not any(e in data["files"] for e in EXCLUDED)

    def test_hash_is_sha256_hex(self, tmp_path):
        from pactkit.deploy_manifest import write_deploy_manifest

        _deploy_fake_tree(tmp_path)
        write_deploy_manifest(tmp_path, "classic", _full_config())
        data = json.loads((tmp_path / ".pactkit-deployed.json").read_text())

        for rel, digest in data["files"].items():
            assert len(digest) == 64, rel
            assert all(c in "0123456789abcdef" for c in digest), rel

    def test_signature_unchanged(self, tmp_path):
        """AC6: existing (deploy_root, format_name, config) callers still work."""
        from pactkit.deploy_manifest import write_deploy_manifest

        _deploy_fake_tree(tmp_path)
        path = write_deploy_manifest(tmp_path, "codex", _full_config())  # positional args
        assert isinstance(path, Path)
        assert "files" in json.loads(path.read_text())


# ---------------------------------------------------------------------------
# R2/R3/R4/R5: doctor content-level parity
# ---------------------------------------------------------------------------


def _write_manifest_with_files(root: Path, fmt: str, config: dict):
    from pactkit.deploy_manifest import write_deploy_manifest

    return write_deploy_manifest(root, fmt, config)


class TestContentParity:
    def _probe(self, tmp_path, monkeypatch):
        fake_home = tmp_path / "home"
        codex_dir = fake_home / ".codex"
        codex_dir.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        project = tmp_path / "project"
        project.mkdir()
        return codex_dir, project

    def test_content_drift_detected(self, tmp_path, monkeypatch):
        from pactkit.doctor import check_deploy_parity

        codex_dir, project = self._probe(tmp_path, monkeypatch)
        codex_cmds = sorted(VALID_COMMANDS)
        _deploy_fake_tree(codex_dir)
        _write_manifest_with_files(codex_dir, "codex", {"skills": PACTKIT_SKILLS, "commands": codex_cmds})

        # Tamper a pactkit-owned file after manifest was written.
        (codex_dir / "rules" / "pactkit.md").write_text("# tampered\n", encoding="utf-8")

        result = check_deploy_parity(project)
        assert result["drift"] is True
        assert any("rules/pactkit.md" in d for d in result["details"])

    def test_no_false_positive_on_excluded_append(self, tmp_path, monkeypatch):
        from pactkit.doctor import check_deploy_parity

        codex_dir, project = self._probe(tmp_path, monkeypatch)
        codex_cmds = sorted(VALID_COMMANDS)
        _deploy_fake_tree(codex_dir)
        _write_manifest_with_files(codex_dir, "codex", {"skills": PACTKIT_SKILLS, "commands": codex_cmds})

        # User appends to a merge-semantics file (excluded from hash) — no drift.
        with (codex_dir / "CLAUDE.md").open("a", encoding="utf-8") as f:
            f.write("\n# user section\n")

        result = check_deploy_parity(project)
        assert result["drift"] is False, result["details"]

    def test_old_manifest_without_files_warns(self, tmp_path, monkeypatch):
        from pactkit.doctor import check_deploy_parity

        codex_dir, project = self._probe(tmp_path, monkeypatch)
        (codex_dir / "skills").mkdir(parents=True)
        codex_cmds = sorted(VALID_COMMANDS)
        (codex_dir / ".pactkit-deployed.json").write_text(json.dumps({
            "format": "codex", "pactkit_version": "2.17.0",
            "skills": PACTKIT_SKILLS, "commands": codex_cmds, "agents": sorted(VALID_AGENTS),
        }))

        result = check_deploy_parity(project)
        assert result["drift"] is False
        assert any("content verification" in w for w in result["warnings"])

    def test_missing_declared_file_detected(self, tmp_path, monkeypatch):
        from pactkit.doctor import check_deploy_parity

        codex_dir, project = self._probe(tmp_path, monkeypatch)
        codex_cmds = sorted(VALID_COMMANDS)
        _deploy_fake_tree(codex_dir)
        _write_manifest_with_files(codex_dir, "codex", {"skills": PACTKIT_SKILLS, "commands": codex_cmds})

        (codex_dir / "skills" / "pactkit-board" / "SKILL.md").unlink()

        result = check_deploy_parity(project)
        assert result["drift"] is True
        assert any("skills/pactkit-board/SKILL.md" in d for d in result["details"])

    def test_unreadable_file_warns_not_crashes(self, tmp_path, monkeypatch):
        """SEC-7: permission error on a listed file degrades to warning."""
        from pactkit.doctor import check_deploy_parity

        codex_dir, project = self._probe(tmp_path, monkeypatch)
        codex_cmds = sorted(VALID_COMMANDS)
        _deploy_fake_tree(codex_dir)
        _write_manifest_with_files(codex_dir, "codex", {"skills": PACTKIT_SKILLS, "commands": codex_cmds})

        (codex_dir / "rules" / "pactkit.md").chmod(0)
        try:
            result = check_deploy_parity(project)
        finally:
            (codex_dir / "rules" / "pactkit.md").chmod(0o644)

        assert result["drift"] is False
        assert any("unreadable" in w for w in result["warnings"])

    def test_corrupt_files_field_warns_not_crashes(self, tmp_path, monkeypatch):
        """SEC-7: 'files' present but not a dict degrades to warning."""
        from pactkit.doctor import check_deploy_parity

        codex_dir, project = self._probe(tmp_path, monkeypatch)
        codex_cmds = sorted(VALID_COMMANDS)
        _deploy_fake_tree(codex_dir)
        _write_manifest_with_files(codex_dir, "codex", {"skills": PACTKIT_SKILLS, "commands": codex_cmds})

        manifest = json.loads((codex_dir / ".pactkit-deployed.json").read_text())
        manifest["files"] = ["rules/pactkit.md"]  # corrupted type
        (codex_dir / ".pactkit-deployed.json").write_text(json.dumps(manifest))

        result = check_deploy_parity(project)
        assert result["drift"] is False
        assert any("corrupt" in w for w in result["warnings"])

    def test_multi_drift_no_short_circuit(self, tmp_path, monkeypatch):
        """R2: all drifted files reported in one run, no early exit."""
        from pactkit.doctor import check_deploy_parity

        codex_dir, project = self._probe(tmp_path, monkeypatch)
        codex_cmds = sorted(set(VALID_COMMANDS) - {"project-sprint"})
        _deploy_fake_tree(codex_dir)
        _write_manifest_with_files(codex_dir, "codex", {"skills": PACTKIT_SKILLS, "commands": codex_cmds})

        (codex_dir / "rules" / "pactkit.md").write_text("# tampered\n", encoding="utf-8")
        (codex_dir / "agents" / "qa-engineer.md").write_text("# tampered\n", encoding="utf-8")

        result = check_deploy_parity(project)
        assert result["drift"] is True
        assert any("rules/pactkit.md" in d for d in result["details"])
        assert any("agents/qa-engineer.md" in d for d in result["details"])

    def test_manifest_keys_are_posix(self, tmp_path):
        """Manifest rel-path keys use forward slashes on every platform."""
        from pactkit.deploy_manifest import write_deploy_manifest

        _deploy_fake_tree(tmp_path)
        write_deploy_manifest(tmp_path, "classic", _full_config())
        data = json.loads((tmp_path / ".pactkit-deployed.json").read_text())

        assert data["files"]
        assert all("\\" not in rel for rel in data["files"])
