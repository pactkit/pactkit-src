"""STORY-slim-20260903699c84c217e0: deploy-ledger lifecycle closed loop.

Three ledger defects in one day (PM-20260903) each passed unit tests — the
loop between record / rebuild / prove is what broke. These tests make the
loop the tested unit, per format, with the 3-consecutive-rounds discipline
(a single passing round masked the opencode treadmill as byte coincidence).
"""

import json
from pathlib import Path

import pytest

from pactkit.deploy_manifest import (
    load_previous_hashes,
    pactkit_owned_files,
    preserve_or_write,
    record_deployed_file,
    write_deploy_manifest,
)


def _round(root: Path, rel: str, content: str, previous: dict) -> bool:
    """One preserve_or_write round; returns True when written in place."""
    return preserve_or_write(root, root / rel, content, previous, f"test:{rel}")


def _no_candidates(root: Path) -> bool:
    return not list(root.rglob("*.pactkit-new"))


class TestLedgerLifecycle:
    @pytest.mark.parametrize("fmt,rel", [
        ("classic", "skills/project-act/SKILL.md"),
        ("opencode", "commands/project-act.md"),
        ("copilot", "prompts/project-act.prompt.md"),
    ])
    def test_record_rebuild_prove_three_rounds(self, tmp_path, fmt, rel):
        root = tmp_path / "root"
        target = root / rel
        target.parent.mkdir(parents=True)

        # Round 1: fresh write (no ledger) → record → rebuild
        assert _round(root, rel, "V1 content", load_previous_hashes(root))
        record_deployed_file(root, rel)
        write_deploy_manifest(root, fmt, {"skills": [], "commands": ["project-act"], "agents": [], "portable_methods": []})
        manifest = json.loads((root / ".pactkit-deployed.json").read_text())
        assert rel in manifest["files"], "digest lost in rebuild (flavor-3 regression)"

        # Round 2: changed content, ownership proven → in place
        assert _round(root, rel, "V2 content", load_previous_hashes(root))
        assert _no_candidates(root)

        # Round 3: changed again, 3-round stability discipline
        record_deployed_file(root, rel)
        assert _round(root, rel, "V3 content", load_previous_hashes(root))
        assert _no_candidates(root)

    def test_opencode_post_transform_flavor(self, tmp_path):
        """Flavors 2+3 combined: post-pass rewrites bytes, then record, then
        rebuild — the next changed deploy must still be in-place."""
        root = tmp_path / "root"
        rel = "commands/project-act.md"
        target = root / rel
        target.parent.mkdir(parents=True)

        # deploy raw, post-transform in place, record FINAL digest, rebuild
        assert _round(root, rel, "raw v1", load_previous_hashes(root))
        target.write_text("TRANSFORMED v1", encoding="utf-8")
        record_deployed_file(root, rel)
        write_deploy_manifest(root, "opencode", {"skills": [], "commands": ["project-act"], "agents": [], "portable_methods": []})

        # next deploy renders changed raw — ownership via manifest (transformed) vs
        # disk (transformed) proves → overwrite in place, no candidate
        assert _round(root, rel, "raw v2", load_previous_hashes(root))
        assert _no_candidates(root)
        assert target.read_text(encoding="utf-8") == "raw v2"

    def test_codex_merged_reference_view(self, tmp_path):
        """Codex flavor-1: references recorded in the command manifest must
        survive write_deploy_manifest rebuild and still prove ownership via
        the merged view."""
        from pactkit.generators.command_ownership import (
            read_command_references,
            write_command_manifest,
        )

        root = tmp_path / "root"
        rel = "skills/project-act/references/rules/capability-design.md"
        target = root / rel
        target.parent.mkdir(parents=True)

        assert _round(root, rel, "V1", load_previous_hashes(root))
        # adapter records into the command manifest (the wired path)
        write_command_manifest(root / "skills", {}, references={rel: _digest(target)})
        # rebuild the deploy manifest — must not wipe the command-manifest table
        write_deploy_manifest(root, "codex", {"skills": [], "commands": ["project-act"], "agents": [], "portable_methods": []})

        merged = {**load_previous_hashes(root), **read_command_references(root / "skills")}
        assert merged.get(rel) == _digest(target), "reference digest lost across rebuild"

        # changed content proves ownership through the merged view
        assert _round(root, rel, "V2", merged)
        assert _no_candidates(root)

    def test_files_map_survives_rebuild_for_all_formats(self, tmp_path):
        """pactkit_owned_files enumerates each format's real layout."""
        layouts = {
            "classic": "skills/project-act/SKILL.md",
            "opencode": "commands/project-act.md",
            "copilot": "prompts/project-act.prompt.md",
        }
        for fmt, rel in layouts.items():
            root = tmp_path / fmt
            (root / rel).parent.mkdir(parents=True)
            (root / rel).write_text("X", encoding="utf-8")
            owned = pactkit_owned_files(
                root, {"skills": [], "commands": ["project-act"], "agents": [], "portable_methods": []}, fmt,
            )
            assert rel in owned, f"{fmt}: layout not enumerated (flavor-3 regression)"


def _digest(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()
