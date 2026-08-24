"""Tests for STORY-slim-054: Core library robustness."""
from unittest.mock import patch


# ---------------------------------------------------------------------------
# R1: _rewrite_yaml atomic write
# ---------------------------------------------------------------------------
class TestR1RewriteYamlAtomic:

    def test_rewrite_yaml_preserves_original_on_failure(self, tmp_path):
        """If os.replace fails, original pactkit.yaml must remain intact."""
        yaml_file = tmp_path / "pactkit.yaml"
        original = "stack: python\ndeveloper: slim\n"
        yaml_file.write_text(original, encoding="utf-8")

        from pactkit.config import _rewrite_yaml

        data = {"stack": "go", "developer": "slim"}
        with patch("os.replace", side_effect=OSError("disk full")):
            try:
                _rewrite_yaml(yaml_file, data)
            except OSError:
                pass

        # Original file must be intact
        assert yaml_file.read_text(encoding="utf-8") == original

    def test_rewrite_yaml_no_tmp_residual_on_success(self, tmp_path):
        """After successful _rewrite_yaml, no .tmp file should remain."""
        yaml_file = tmp_path / "pactkit.yaml"
        yaml_file.write_text("stack: python\n", encoding="utf-8")

        from pactkit.config import _rewrite_yaml

        _rewrite_yaml(yaml_file, {"stack": "go", "developer": "slim"})

        tmp_file = yaml_file.with_suffix(".tmp")
        assert not tmp_file.exists(), ".tmp file should not remain after success"
        assert yaml_file.exists()

    def test_rewrite_yaml_no_tmp_residual_on_failure(self, tmp_path):
        """If os.replace fails, .tmp file must be cleaned up."""
        yaml_file = tmp_path / "pactkit.yaml"
        yaml_file.write_text("stack: python\n", encoding="utf-8")

        from pactkit.config import _rewrite_yaml

        with patch("os.replace", side_effect=OSError("disk full")):
            try:
                _rewrite_yaml(yaml_file, {"stack": "go"})
            except OSError:
                pass

        tmp_file = yaml_file.with_suffix(".tmp")
        assert not tmp_file.exists(), ".tmp file should be cleaned up on failure"


# ---------------------------------------------------------------------------
# R2: _deploy_ci dict mutation
# ---------------------------------------------------------------------------
class TestR2DeployCiDictMutation:

    def test_deploy_ci_does_not_consume_ghe_override(self, tmp_path):
        """Calling _deploy_ci must not remove _ghe_override from config dict."""
        from pactkit.generators.deployer import _deploy_ci

        config = {
            "ci": {
                "provider": "github",
                "_ghe_override": True,
            }
        }

        # Call once — should not mutate config["ci"]
        _deploy_ci("github", tmp_path, config)

        assert "_ghe_override" in config["ci"], \
            "_ghe_override was consumed from config dict — should use .get() not .pop()"
        assert config["ci"]["_ghe_override"] is True

    def test_deploy_ci_twice_same_dict(self, tmp_path):
        """Two calls to _deploy_ci with same dict should both see _ghe_override."""
        from pactkit.generators.deployer import _deploy_ci

        config = {
            "ci": {
                "provider": "github",
                "_ghe_override": True,
            }
        }

        _deploy_ci("github", tmp_path, config)
        _deploy_ci("github", tmp_path, config)

        assert "_ghe_override" in config["ci"]


# ---------------------------------------------------------------------------
# R3: atomic_write .tmp cleanup on failure
# ---------------------------------------------------------------------------
class TestR3AtomicWriteTmpCleanup:

    def test_atomic_write_cleans_tmp_on_replace_failure(self, tmp_path):
        """If os.replace fails, .tmp must not remain on disk."""
        from pactkit.utils import atomic_write

        target = tmp_path / "output.md"
        tmp_file = target.with_suffix(".tmp")

        with patch("os.replace", side_effect=OSError("cross-device")):
            try:
                atomic_write(target, "content here")
            except OSError:
                pass

        assert not tmp_file.exists(), ".tmp file should be cleaned up on failure"

    def test_atomic_write_reraises_exception(self, tmp_path):
        """atomic_write must re-raise the exception, not swallow it."""
        from pactkit.utils import atomic_write

        target = tmp_path / "output.md"
        with patch("os.replace", side_effect=OSError("disk error")):
            try:
                atomic_write(target, "content")
                assert False, "Should have raised OSError"
            except OSError as e:
                assert "disk error" in str(e)

    def test_atomic_write_normal_path_unchanged(self, tmp_path):
        """Normal atomic_write should write file and leave no .tmp."""
        from pactkit.utils import atomic_write

        target = tmp_path / "output.md"
        atomic_write(target, "hello world")

        assert target.read_text(encoding="utf-8") == "hello world"
        assert not target.with_suffix(".tmp").exists()

    def test_atomic_write_diagnostic_uses_stderr(self, tmp_path, capsys):
        from pactkit.utils import atomic_write

        atomic_write(tmp_path / "machine.json", "{}\n")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Wrote machine.json" in captured.err
