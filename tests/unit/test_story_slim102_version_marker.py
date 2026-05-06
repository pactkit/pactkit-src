"""Tests for STORY-slim-102: Move version tracking to global deploy marker."""

import sys
from pathlib import Path


def _config():
    import importlib

    import pactkit.config as c
    importlib.reload(c)
    return c


def _guards():
    import importlib

    import pactkit.guards as g
    importlib.reload(g)
    return g


# ---------------------------------------------------------------------------
# AC1: Global marker written on deploy
# ---------------------------------------------------------------------------
class TestAC1GlobalMarkerWritten:
    def test_deploy_classic_writes_version_marker(self, tmp_path):
        """After _deploy_classic, .pactkit-version exists with __version__."""
        from pactkit import __version__
        from pactkit.generators.deployer import _deploy_classic

        _deploy_classic(target=str(tmp_path))
        marker = tmp_path / ".pactkit-version"
        assert marker.exists(), ".pactkit-version not written"
        assert marker.read_text().strip() == __version__


# ---------------------------------------------------------------------------
# AC2: Skip when global marker matches
# ---------------------------------------------------------------------------
class TestAC2SkipOnMatch:
    def test_skip_when_marker_matches(self, tmp_path, monkeypatch):
        """update --if-needed skips when .pactkit-version matches."""
        import subprocess

        from pactkit import __version__

        # Write matching marker to simulate deployed state
        marker = Path.home() / ".claude" / ".pactkit-version"
        marker.write_text(__version__)

        monkeypatch.chdir(tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "pactkit", "update", "--if-needed"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "up-to-date" in result.stdout.lower() or "skipping" in result.stdout.lower()


# ---------------------------------------------------------------------------
# AC4: Default config has no version
# ---------------------------------------------------------------------------
class TestAC4DefaultConfigNoVersion:
    def test_no_version_key(self):
        c = _config()
        cfg = c.get_default_config()
        assert "version" not in cfg


# ---------------------------------------------------------------------------
# AC5: Auto-merge removes stale version
# ---------------------------------------------------------------------------
class TestAC5AutoMergeRemovesVersion:
    def test_removes_version_field(self, tmp_path):
        c = _config()
        yaml_file = tmp_path / "pactkit.yaml"
        yaml_file.write_text('version: "2.10.1"\nstack: python\n')
        c.auto_merge_config_file(yaml_file)

        import yaml
        data = yaml.safe_load(yaml_file.read_text())
        assert "version" not in data, "version field should be removed"


# ---------------------------------------------------------------------------
# AC6: Guard uses global marker
# ---------------------------------------------------------------------------
class TestAC6GuardUsesGlobalMarker:
    def test_no_warning_when_marker_matches(self, tmp_path, monkeypatch):
        """No mismatch warning when global marker matches, regardless of yaml."""
        from pactkit import __version__

        g = _guards()

        # Write matching global marker
        marker_dir = tmp_path / "claude_home"
        marker_dir.mkdir()
        marker = marker_dir / ".pactkit-version"
        marker.write_text(__version__)

        monkeypatch.setattr(g, "_get_global_version_marker", lambda: marker)

        result = g.check_version_mismatch(tmp_path)
        assert result is None

    def test_warning_when_marker_mismatches(self, tmp_path, monkeypatch):
        """Warning when global marker has old version."""
        g = _guards()

        marker_dir = tmp_path / "claude_home"
        marker_dir.mkdir()
        marker = marker_dir / ".pactkit-version"
        marker.write_text("2.0.0")

        monkeypatch.setattr(g, "_get_global_version_marker", lambda: marker)

        result = g.check_version_mismatch(tmp_path)
        assert result is not None
        assert "mismatch" in result.lower() or "2.0.0" in result


# ---------------------------------------------------------------------------
# AC7: Old yaml with version still loads
# ---------------------------------------------------------------------------
class TestAC7OldYamlStillLoads:
    def test_loads_without_error(self, tmp_path):
        c = _config()
        yaml_file = tmp_path / "pactkit.yaml"
        yaml_file.write_text('version: "2.10.1"\nstack: python\n')
        cfg = c.load_config(yaml_file)
        assert isinstance(cfg, dict)
        assert cfg.get("stack") == "python"


# ---------------------------------------------------------------------------
# AC: _rewrite_yaml does NOT write version
# ---------------------------------------------------------------------------
class TestRewriteYamlNoVersion:
    def test_no_version_field_in_output(self, tmp_path):
        c = _config()
        yaml_file = tmp_path / "pactkit.yaml"
        data = {"stack": "python", "root": "."}
        c._rewrite_yaml(yaml_file, data)
        import yaml
        parsed = yaml.safe_load(yaml_file.read_text())
        assert "version" not in parsed, "version field should not be in rewritten yaml"
