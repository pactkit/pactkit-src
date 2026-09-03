"""Tests for STORY-slim-20260903a24e1ece0d7f: accept-candidates command.

R2: `pactkit accept-candidates --root <path>` moves every .pactkit-new
candidate over its original and records the new digest in BOTH ownership
ledgers (command manifest references table for skills/*/references/**,
.pactkit-deployed.json files map otherwise). R3: idempotent.
"""

import json
from pathlib import Path

import pytest


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / "deploy-root"
    (root / "skills" / "project-act" / "references" / "rules").mkdir(parents=True)
    (root / "skills" / "project-plan").mkdir(parents=True)
    return root


def _make_candidate(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("OLD USER CONTENT\n", encoding="utf-8")
    path.with_suffix(path.suffix + ".pactkit-new").write_text(content, encoding="utf-8")


def _cmd_manifest(root: Path) -> dict:
    return json.loads((root / "skills" / ".pactkit-command-manifest.json").read_text())


def _deploy_manifest(root: Path) -> dict:
    return json.loads((root / ".pactkit-deployed.json").read_text())


class TestAcceptCandidates:
    def test_accepts_and_updates_both_ledgers(self, tmp_path):
        from pactkit.accept_candidates import accept_candidates

        root = _make_root(tmp_path)
        ref = root / "skills" / "project-act" / "references" / "rules" / "capability-design.md"
        skill_md = root / "skills" / "project-plan" / "SKILL.md"
        _make_candidate(ref, "NEW RULE CONTENT v2\n")
        _make_candidate(skill_md, "NEW SKILL CONTENT v2\n")

        accepted = accept_candidates(root)

        assert accepted == 2
        # 候选消失,原文件被覆盖
        assert ref.read_text(encoding="utf-8") == "NEW RULE CONTENT v2\n"
        assert skill_md.read_text(encoding="utf-8") == "NEW SKILL CONTENT v2\n"
        assert not ref.with_suffix(ref.suffix + ".pactkit-new").exists()
        # references 路径进 command manifest references 表
        cmd = _cmd_manifest(root)
        rel = "skills/project-act/references/rules/capability-design.md"
        assert rel in cmd["references"]
        import hashlib
        assert cmd["references"][rel] == hashlib.sha256(ref.read_bytes()).hexdigest()
        # 普通路径进 .pactkit-deployed.json files 映射
        dep = _deploy_manifest(root)
        rel2 = "skills/project-plan/SKILL.md"
        assert rel2 in dep["files"]
        assert dep["files"][rel2] == hashlib.sha256(skill_md.read_bytes()).hexdigest()

    def test_idempotent_when_no_candidates(self, tmp_path):
        from pactkit.accept_candidates import accept_candidates

        root = _make_root(tmp_path)
        assert accept_candidates(root) == 0

    def test_preserves_existing_ledger_entries(self, tmp_path):
        """Accepting one candidate must not wipe the other ledger rows."""
        from pactkit.accept_candidates import accept_candidates

        root = _make_root(tmp_path)
        # 预置两本账的既有条目
        cmd_path = root / "skills" / ".pactkit-command-manifest.json"
        cmd_path.write_text(json.dumps({
            "version": 2, "commands": {"project-act": "a" * 64},
            "references": {"skills/project-act/references/rules/old-rule.md": "b" * 64},
        }), encoding="utf-8")
        dep_path = root / ".pactkit-deployed.json"
        dep_path.write_text(json.dumps({
            "files": {"skills/pactkit-board/SKILL.md": "c" * 64},
        }), encoding="utf-8")

        ref = root / "skills" / "project-act" / "references" / "rules" / "capability-design.md"
        _make_candidate(ref, "v3\n")
        assert accept_candidates(root) == 1

        cmd = _cmd_manifest(root)
        assert cmd["references"]["skills/project-act/references/rules/old-rule.md"] == "b" * 64
        assert "project-act" in cmd["commands"]
        dep = _deploy_manifest(root)
        assert dep["files"]["skills/pactkit-board/SKILL.md"] == "c" * 64


@pytest.mark.parametrize("sub", ["accept-candidates"])
def test_cli_registers_accept_candidates(sub):
    """The subcommand exists on the CLI surface (dead-subcommand guard)."""
    from pactkit.prompts.commands import COMMANDS_CONTENT

    referenced = any(
        "accept-candidates" in content for content in COMMANDS_CONTENT.values()
    )
    # 命令必须可被 prompt 引用或至少可被发现——死子命令检测的锚
    import subprocess
    import sys
    proc = subprocess.run(
        [sys.executable, "-m", "pactkit", sub, "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
