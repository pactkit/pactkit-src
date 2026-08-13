"""STORY-slim-135: Schema-driven pactkit.yaml governance.

R1: CONFIG_SCHEMA single source of truth
R2: minimal init yaml (stack + developer only)
R3: single schema-driven renderer, no re-inflation of absent sections
R4: multi-copy sync + doctor drift detection
R5: pactkit schema config discoverability
R6: load_config merge equivalence (golden fixtures)
"""

import json
import warnings
from pathlib import Path

import pytest
import yaml

from pactkit.config import (
    CONFIG_SCHEMA,
    _rewrite_yaml,
    check_config_copy_drift,
    generate_default_yaml,
    get_default_config,
    load_config,
    schema_config_report,
    sync_config_copies,
)

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "config_golden"


# ---------------------------------------------------------------------------
# R6: golden merge equivalence — refactor must not change load_config results
# ---------------------------------------------------------------------------


class TestGoldenMergeEquivalence:
    @pytest.mark.parametrize(
        "fixture",
        sorted(f.name for f in FIXTURE_DIR.glob("*.yaml")),
    )
    def test_merge_matches_golden(self, fixture, tmp_path):
        src = FIXTURE_DIR / fixture
        target = tmp_path / fixture
        target.write_bytes(src.read_bytes())  # load_config may not mutate, but be safe
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            merged = load_config(target)
        golden = json.loads((FIXTURE_DIR / (src.stem + ".json")).read_text())
        assert json.dumps(merged, sort_keys=True, default=str) == json.dumps(
            golden, sort_keys=True
        )


# ---------------------------------------------------------------------------
# R1: CONFIG_SCHEMA registry
# ---------------------------------------------------------------------------


class TestConfigSchema:
    def test_schema_covers_all_default_keys(self):
        non_optional = {k for k, v in CONFIG_SCHEMA.items() if not v.get("optional")}
        assert set(get_default_config().keys()) == non_optional

    def test_schema_entries_have_required_metadata(self):
        for key, entry in CONFIG_SCHEMA.items():
            assert "default" in entry, f"{key} missing default"
            assert "deep_merge" in entry, f"{key} missing deep_merge"
            assert "kind" in entry, f"{key} missing kind"
            assert entry["kind"] in ("scalar", "list", "mapping"), f"{key} bad kind"

    def test_defaults_match_schema(self):
        defaults = get_default_config()
        for key, entry in CONFIG_SCHEMA.items():
            if entry.get("optional"):
                continue
            assert defaults[key] == entry["default"], f"{key} default drifted"


# ---------------------------------------------------------------------------
# R2: minimal init yaml
# ---------------------------------------------------------------------------


class TestMinimalInitYaml:
    FORBIDDEN_SECTIONS = (
        "ci:", "issue_tracker:", "lint_blocking", "auto_fix", "venv:",
        "release:", "regression:", "check:", "done:", "e2e:",
        "visualize:", "command_models:",
    )

    def test_only_stack_and_developer(self):
        content = generate_default_yaml("python")
        assert "stack: python" in content
        assert 'developer: ""' in content
        for section in self.FORBIDDEN_SECTIONS:
            assert section not in content, f"minimal yaml must not contain {section!r}"

    def test_line_count_bounded(self):
        content = generate_default_yaml("python")
        lines = [ln for ln in content.splitlines() if ln.strip()]
        assert len(lines) <= 12

    def test_points_to_schema_config(self):
        content = generate_default_yaml("python")
        assert "pactkit schema config" in content

    def test_roundtrip_parseable(self):
        data = yaml.safe_load(generate_default_yaml(["go", "python"]))
        assert data["stack"] == ["go", "python"]
        assert "developer" in data


# ---------------------------------------------------------------------------
# R3: single renderer — preserves explicit keys, skips absent sections
# ---------------------------------------------------------------------------


class TestSingleRenderer:
    def test_rewrite_does_not_reinflate_absent_sections(self, tmp_path):
        path = tmp_path / "pactkit.yaml"
        path.write_text('stack: python\ndeveloper: "slim"\n')
        _rewrite_yaml(path, {"stack": "python", "developer": "slim"})
        content = path.read_text()
        for section in ("ci:", "check:", "e2e:", "visualize:", "regression:"):
            assert f"\n{section}" not in content, f"re-inflated absent section {section!r}"

    def test_rewrite_preserves_explicit_sections(self, tmp_path):
        path = tmp_path / "pactkit.yaml"
        data = {
            "stack": "python",
            "developer": "slim",
            "ci": {"provider": "github"},
            "regression": {"strategy": "full", "max_impact_tests": 30},
        }
        _rewrite_yaml(path, data)
        content = path.read_text()
        assert "provider: github" in content
        assert "strategy: full" in content
        assert "max_impact_tests: 30" in content

    def test_rewrite_preserves_unknown_keys(self, tmp_path):
        """BUG-023 regression guard: user-defined keys survive rewrite."""
        path = tmp_path / "pactkit.yaml"
        data = {"stack": "python", "developer": "", "my_custom": {"nested": True}}
        _rewrite_yaml(path, data)
        content = path.read_text()
        assert "my_custom" in content
        assert "nested" in content

    def test_rewrite_preserves_nested_explicit_values(self, tmp_path):
        """check.pactguard/observe sub-sections render when explicitly present."""
        path = tmp_path / "pactkit.yaml"
        data = {
            "stack": "python",
            "developer": "",
            "check": {"pactguard": {"enabled": True, "mode": "pattern"}},
        }
        _rewrite_yaml(path, data)
        content = path.read_text()
        assert "pactguard:" in content
        assert "enabled: true" in content
        assert "mode: pattern" in content


# ---------------------------------------------------------------------------
# R4: multi-copy sync + drift detection
# ---------------------------------------------------------------------------


def _make_copies(root: Path, claude_dev: str, codex_dev: str) -> tuple[Path, Path]:
    c1 = root / ".claude" / "pactkit.yaml"
    c2 = root / ".codex" / "pactkit.yaml"
    c1.parent.mkdir(parents=True)
    c2.parent.mkdir(parents=True)
    c1.write_text(f'stack: python\ndeveloper: "{claude_dev}"\nagent_models:\n  code-explorer: haiku\n')
    c2.write_text(f'stack: python\ndeveloper: "{codex_dev}"\n')
    return c1, c2


class TestCopyDrift:
    def test_drift_detected(self, tmp_path):
        _make_copies(tmp_path, "slim", "")
        drift = check_config_copy_drift(tmp_path)
        assert drift["drift"] is True
        assert any("developer" in d for d in drift["details"])

    def test_no_drift_when_consistent(self, tmp_path):
        _make_copies(tmp_path, "slim", "slim")
        # make content identical to rule out formatting-only diffs
        c2 = tmp_path / ".codex" / "pactkit.yaml"
        c2.write_text((tmp_path / ".claude" / "pactkit.yaml").read_text())
        drift = check_config_copy_drift(tmp_path)
        assert drift["drift"] is False

    def test_single_copy_no_drift(self, tmp_path):
        c1 = tmp_path / ".claude" / "pactkit.yaml"
        c1.parent.mkdir(parents=True)
        c1.write_text('developer: "slim"\n')
        assert check_config_copy_drift(tmp_path)["drift"] is False

    def test_sync_makes_copies_identical(self, tmp_path):
        c1, c2 = _make_copies(tmp_path, "slim", "")
        synced = sync_config_copies(tmp_path)
        assert c2 in synced
        assert c1.read_text() == c2.read_text()

    def test_sync_prefers_claude_copy_as_canonical(self, tmp_path):
        """Canonical = first existing in CANONICAL_PREFERENCE (.claude first),
        regardless of key count — an inflated default-wall copy must NOT win."""
        c1, c2 = _make_copies(tmp_path, "slim", "")
        sync_config_copies(tmp_path)
        assert 'developer: "slim"' in c2.read_text()
        assert "agent_models" in c2.read_text()


# ---------------------------------------------------------------------------
# R5: pactkit schema config
# ---------------------------------------------------------------------------


class TestSchemaConfigReport:
    def test_report_covers_all_keys(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        report = schema_config_report(tmp_path)
        for key in CONFIG_SCHEMA:
            assert key in report

    def test_report_shows_source(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "pactkit.yaml").write_text('developer: "slim"\n')
        report = schema_config_report(tmp_path)
        assert ".claude/pactkit.yaml" in report  # explicit source for developer
        assert "default" in report  # unresolved keys marked as default

    def test_report_shows_effective_values(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "pactkit.yaml").write_text('developer: "slim"\n')
        report = schema_config_report(tmp_path)
        assert "slim" in report
