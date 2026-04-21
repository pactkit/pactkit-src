"""
BUG-026 / STORY-slim-102: Version tracking moved off project yaml.

New behavior (STORY-slim-102):
- version is NOT in get_default_config()
- _rewrite_yaml() does NOT write a version: line
- auto_merge_config_file() REMOVES the version field when present
- generate_default_yaml() does NOT contain version:
- Global deploy marker: ~/.claude/.pactkit-version tracks the deployed version
"""
from pathlib import Path

import yaml

from pactkit import __version__
from pactkit.config import (
    _rewrite_yaml,
    auto_merge_config_file,
    generate_default_yaml,
    get_default_config,
)

_STALE_V1 = "0.0.1"
_STALE_V2 = "1.4.0"


def _write_minimal(tmp_path: Path, version: str) -> Path:
    """Write a minimal pactkit.yaml with given version (legacy format)."""
    p = tmp_path / "pactkit.yaml"
    p.write_text(
        f'version: "{version}"\nstack: auto\nroot: .\n',
        encoding="utf-8",
    )
    return p


def _write_complete(tmp_path: Path, version: str) -> Path:
    """Write a complete pactkit.yaml (all sections) with given version (legacy format)."""
    from pactkit.config import VALID_AGENTS, VALID_COMMANDS, VALID_RULES, VALID_SKILLS
    cfg = {
        "version": version,
        "stack": "auto",
        "root": ".",
        "agents": sorted(VALID_AGENTS),
        "commands": sorted(VALID_COMMANDS),
        "skills": sorted(VALID_SKILLS),
        "rules": sorted(VALID_RULES),
        "ci": {"provider": "none"},
        "issue_tracker": {"provider": "none"},
        "hooks": {"pre_commit_lint": False, "post_test_coverage": False, "pre_push_check": False},
        "lint_blocking": False,
        "auto_fix": False,
        "e2e": {"type": "none", "blocking": False, "test_dir": "tests/e2e",
                "env_file": ".env.test", "api_spec": "", "compose_file": "docker-compose.test.yml"},
        "venv": {"auto_detect": True},
        "release": {"github_release": False},
        "regression": {"strategy": "impact", "max_impact_tests": 50},
        "check": {"security_checklist": True},
        "done": {"lesson_quality_threshold": 15},
        "visualize": {"scan_excludes": ["venv", ".venv"]},
    }
    p = tmp_path / "pactkit.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# R1: get_default_config no longer includes version
# ---------------------------------------------------------------------------

class TestGetDefaultConfigVersion:
    """STORY-slim-102: get_default_config() must NOT include a version key."""

    def test_version_not_in_default_config(self):
        """version is no longer tracked in project yaml."""
        cfg = get_default_config()
        assert "version" not in cfg, (
            f"get_default_config() should not include 'version'; got keys: {list(cfg.keys())}"
        )


# ---------------------------------------------------------------------------
# R2: _rewrite_yaml does NOT write a version: line
# ---------------------------------------------------------------------------

class TestRewriteYamlVersion:
    """R2: _rewrite_yaml must NOT write a version line (STORY-slim-102)."""

    def test_no_version_line_in_output(self, tmp_path):
        """_rewrite_yaml output must not contain version: line."""
        p = tmp_path / "pactkit.yaml"
        p.write_text("stack: auto\nroot: .\n", encoding="utf-8")
        data = yaml.safe_load(p.read_text())
        _rewrite_yaml(p, data)
        result_text = p.read_text()
        # No version: line should appear in output
        for line in result_text.splitlines():
            stripped = line.strip()
            assert not stripped.startswith("version:"), (
                f"_rewrite_yaml should not write a version line; got: {line!r}"
            )

    def test_existing_version_in_data_not_written(self, tmp_path):
        """_rewrite_yaml must ignore version in data dict and not write it."""
        p = _write_minimal(tmp_path, _STALE_V1)
        data = yaml.safe_load(p.read_text())
        assert data.get("version") == _STALE_V1  # pre-condition: data has version
        _rewrite_yaml(p, data)
        result_text = p.read_text()
        for line in result_text.splitlines():
            stripped = line.strip()
            assert not stripped.startswith("version:"), (
                "_rewrite_yaml should not emit version line even when data contains version"
            )


# ---------------------------------------------------------------------------
# R3: auto_merge_config_file REMOVES version field
# ---------------------------------------------------------------------------

class TestAutoMergeVersionSync:
    """R3: auto_merge_config_file must REMOVE the version field (STORY-slim-102)."""

    def test_stale_version_removed_from_file(self, tmp_path):
        """AC1: after auto_merge, version field must be absent from file."""
        p = _write_minimal(tmp_path, _STALE_V1)
        auto_merge_config_file(p)
        result = yaml.safe_load(p.read_text())
        assert "version" not in result, (
            f"auto_merge should remove version; got: {result}"
        )

    def test_older_stale_version_removed(self, tmp_path):
        """AC2: version '1.4.0' is removed after auto_merge."""
        p = _write_minimal(tmp_path, _STALE_V2)
        auto_merge_config_file(p)
        result = yaml.safe_load(p.read_text())
        assert "version" not in result

    def test_version_removal_reported_in_added(self, tmp_path):
        """auto_merge must report version removal in the returned list."""
        p = _write_minimal(tmp_path, _STALE_V1)
        added = auto_merge_config_file(p)
        assert any("version" in item for item in added), (
            f"Expected version removal in added list, got: {added}"
        )

    def test_current_version_also_removed(self, tmp_path):
        """Even current __version__ is removed from project yaml (tracked globally)."""
        p = _write_complete(tmp_path, __version__)
        added = auto_merge_config_file(p)
        result = yaml.safe_load(p.read_text())
        assert "version" not in result, (
            f"version should be removed regardless of its value; got: {result}"
        )
        assert any("version" in item for item in added), (
            f"Version removal should be reported in added list: {added}"
        )

    def test_complete_config_version_removed(self, tmp_path):
        """R3: version removal fires even when all sections are present."""
        p = _write_complete(tmp_path, _STALE_V1)
        added = auto_merge_config_file(p)
        result = yaml.safe_load(p.read_text())
        assert "version" not in result, (
            f"Version not removed from complete config; got {result}"
        )
        assert any("version" in item for item in added), (
            f"Version removal not reported in added list: {added}"
        )


# ---------------------------------------------------------------------------
# AC3: generate_default_yaml does NOT include version
# ---------------------------------------------------------------------------

class TestGenerateDefaultYamlVersion:
    """AC3: generate_default_yaml() must NOT output a version field."""

    def test_yaml_string_has_no_version(self):
        """generate_default_yaml() must not contain version: line."""
        yaml_str = generate_default_yaml()
        data = yaml.safe_load(yaml_str)
        assert "version" not in data, (
            f"generate_default_yaml() should not write version; got keys: {list(data.keys())}"
        )
