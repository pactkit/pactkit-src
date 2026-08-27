"""STORY-slim-20260827fc9de5542ad7: command manifest v2 reference ledger.

R1 v2 schema + v1 compatibility, R4 corrupt-manifest degradation (core side).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


from pactkit.generators.command_ownership import (
    _MANIFEST_FILE,
    cleanup_disabled_command_skills,
    read_command_references,
    record_deployed_command,
    record_deployed_reference,
    write_command_manifest,
)


def _write_skill(skills_dir: Path, name: str, content: str = "skill body\n") -> Path:
    skill = skills_dir / name / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(content, encoding="utf-8")
    return skill


class TestV2Schema:
    def test_write_and_read_references_roundtrip(self, tmp_path):
        reference = _write_skill(tmp_path / "skills", "project-act")
        ref_dir = tmp_path / "skills" / "project-act" / "references" / "guides"
        ref_dir.mkdir(parents=True)
        ref_file = ref_dir / "caching.md"
        ref_file.write_text("guide body\n", encoding="utf-8")

        entries: dict[str, str] = {}
        record_deployed_command(entries, "project-act", reference)
        references: dict[str, str] = {}
        record_deployed_reference(
            references,
            "skills/project-act/references/guides/caching.md",
            ref_file,
        )
        write_command_manifest(tmp_path / "skills", entries, references=references)

        payload = json.loads(
            (tmp_path / "skills" / _MANIFEST_FILE).read_text(encoding="utf-8")
        )
        assert payload["version"] == 2
        assert set(payload["commands"]) == {"project-act"}
        assert set(payload["references"]) == {
            "skills/project-act/references/guides/caching.md"
        }
        assert read_command_references(tmp_path / "skills") == payload["references"]

    def test_write_without_references_emits_empty_section(self, tmp_path):
        write_command_manifest(tmp_path, {"project-act": "a" * 64})
        payload = json.loads(
            (tmp_path / _MANIFEST_FILE).read_text(encoding="utf-8")
        )
        assert payload["version"] == 2
        assert payload["references"] == {}
        assert read_command_references(tmp_path) == {}

    def test_deterministic_output_is_stable(self, tmp_path):
        write_command_manifest(tmp_path, {"b": "b" * 64, "a": "a" * 64}, references={
            "skills/b/references/rules/x.md": "c" * 64,
        })
        first = (tmp_path / _MANIFEST_FILE).read_text(encoding="utf-8")
        write_command_manifest(tmp_path, {"a": "a" * 64, "b": "b" * 64}, references={
            "skills/b/references/rules/x.md": "c" * 64,
        })
        assert first == (tmp_path / _MANIFEST_FILE).read_text(encoding="utf-8")


class TestV1Compatibility:
    def test_v1_manifest_commands_remain_readable(self, tmp_path):
        skill = _write_skill(tmp_path, "project-act")
        (tmp_path / _MANIFEST_FILE).write_text(
            json.dumps({
                "version": 1,
                "commands": {
                    "project-act": hashlib.sha256(skill.read_bytes()).hexdigest(),
                },
            }),
            encoding="utf-8",
        )
        # v1 has no references section — degrade to an empty proof table
        assert read_command_references(tmp_path) == {}
        # ...but the commands table must keep working for retirement
        _write_skill(tmp_path, "project-act")
        retained = cleanup_disabled_command_skills(
            tmp_path, enabled_commands=set(), known_commands={"project-act", "project-plan"},
        )
        assert retained == {}
        assert not (tmp_path / "project-act").exists()

    def test_upgrade_rewrites_v1_as_v2(self, tmp_path):
        (tmp_path / _MANIFEST_FILE).write_text(
            json.dumps({"version": 1, "commands": {"project-act": "a" * 64}}),
            encoding="utf-8",
        )
        skill = _write_skill(tmp_path, "project-act")
        entries = {"project-act": "b" * 64}
        record_deployed_command(entries, "project-act", skill)
        write_command_manifest(tmp_path, entries)
        payload = json.loads(
            (tmp_path / _MANIFEST_FILE).read_text(encoding="utf-8")
        )
        assert payload["version"] == 2


class TestCorruptManifestDegradation:
    def test_corrupt_json_yields_empty_proofs(self, tmp_path):
        (tmp_path / _MANIFEST_FILE).write_text("{not json", encoding="utf-8")
        assert read_command_references(tmp_path) == {}

    def test_wrong_shape_yields_empty_proofs(self, tmp_path):
        (tmp_path / _MANIFEST_FILE).write_text(
            json.dumps({"version": 2, "references": ["not", "a", "dict"]}),
            encoding="utf-8",
        )
        assert read_command_references(tmp_path) == {}

    def test_invalid_digests_are_dropped(self, tmp_path):
        (tmp_path / _MANIFEST_FILE).write_text(
            json.dumps({
                "version": 2,
                "commands": {},
                "references": {
                    "skills/a/references/rules/x.md": "nothex",
                    "skills/a/references/rules/y.md": 42,
                    "skills/a/references/rules/z.md": "d" * 64,
                },
            }),
            encoding="utf-8",
        )
        assert read_command_references(tmp_path) == {
            "skills/a/references/rules/z.md": "d" * 64,
        }
