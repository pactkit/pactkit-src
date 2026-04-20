"""Tests for pactkit clean (STORY-slim-014 R1)."""
from pactkit.cleaners import clean_artifacts, detect_stack


class TestDetectStack:
    """Auto-detect project stack from marker files."""

    def test_detect_python(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        assert detect_stack(tmp_path) == "python"

    def test_detect_node(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        assert detect_stack(tmp_path) == "node"

    def test_detect_go(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example")
        assert detect_stack(tmp_path) == "go"

    def test_detect_java(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        assert detect_stack(tmp_path) == "java"

    def test_detect_default_python(self, tmp_path):
        """No marker files → default to python."""
        assert detect_stack(tmp_path) == "python"

    def test_detect_python_setup_py(self, tmp_path):
        """setup.py also indicates Python."""
        (tmp_path / "setup.py").write_text("from setuptools import setup")
        assert detect_stack(tmp_path) == "python"


class TestCleanArtifacts:
    """Clean language-specific artifacts."""

    def test_clean_python_pycache(self, tmp_path):
        """Remove __pycache__ directories."""
        cache = tmp_path / "src" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "module.cpython-311.pyc").write_text("")

        removed = clean_artifacts(tmp_path, stack="python")
        assert any("__pycache__" in str(p) for p in removed)
        assert not cache.exists()

    def test_clean_python_pytest_cache(self, tmp_path):
        """Remove .pytest_cache directories."""
        cache = tmp_path / ".pytest_cache"
        cache.mkdir()
        (cache / "README.md").write_text("")

        removed = clean_artifacts(tmp_path, stack="python")
        assert any(".pytest_cache" in str(p) for p in removed)

    def test_clean_python_pyc_files(self, tmp_path):
        """Remove *.pyc files."""
        (tmp_path / "old.pyc").write_text("")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "other.pyc").write_text("")

        removed = clean_artifacts(tmp_path, stack="python")
        assert len(removed) >= 2

    def test_clean_dry_run(self, tmp_path):
        """Dry run lists files but doesn't delete."""
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "module.cpython-311.pyc").write_text("")

        removed = clean_artifacts(tmp_path, stack="python", dry_run=True)
        assert len(removed) >= 1
        assert cache.exists()  # Not deleted

    def test_clean_nothing_to_remove(self, tmp_path):
        """No artifacts → empty list."""
        removed = clean_artifacts(tmp_path, stack="python")
        assert removed == []

    def test_clean_auto_stack(self, tmp_path):
        """Stack auto-detection works."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "m.pyc").write_text("")

        removed = clean_artifacts(tmp_path, stack="auto")
        assert len(removed) >= 1

    def test_clean_node_skips_dist_inside_node_modules(self, tmp_path):
        """dist inside node_modules must NOT be deleted."""
        (tmp_path / "package.json").write_text("{}")
        # Create a dependency with dist/
        dep_dist = tmp_path / "node_modules" / "some-pkg" / "dist"
        dep_dist.mkdir(parents=True)
        (dep_dist / "index.js").write_text("module.exports = {}")
        # Create a project-level dist/ that SHOULD be cleaned
        proj_dist = tmp_path / "dist"
        proj_dist.mkdir()
        (proj_dist / "bundle.js").write_text("")

        removed = clean_artifacts(tmp_path, stack="node")
        assert proj_dist not in list(tmp_path.iterdir())
        assert dep_dist.exists(), "node_modules/*/dist must survive clean"

    def test_clean_node_modules_cache_still_cleaned(self, tmp_path):
        """node_modules/.cache is explicitly targeted and should be cleaned."""
        (tmp_path / "package.json").write_text("{}")
        nm_cache = tmp_path / "node_modules" / ".cache"
        nm_cache.mkdir(parents=True)
        (nm_cache / "babel").mkdir()
        (nm_cache / "babel" / "data.json").write_text("{}")

        removed = clean_artifacts(tmp_path, stack="node")
        assert any("node_modules/.cache" in str(p) for p in removed)
        assert not nm_cache.exists()

    def test_clean_skips_pyc_inside_node_modules(self, tmp_path):
        """Glob patterns (*.pyc) must not match inside node_modules."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        # A .pyc in node_modules (unlikely but possible in hybrid projects)
        nm_pyc = tmp_path / "node_modules" / "weird" / "file.pyc"
        nm_pyc.parent.mkdir(parents=True)
        nm_pyc.write_text("")
        # A normal .pyc that should be cleaned
        normal_pyc = tmp_path / "src" / "mod.pyc"
        normal_pyc.parent.mkdir(parents=True)
        normal_pyc.write_text("")

        removed = clean_artifacts(tmp_path, stack="python")
        assert not normal_pyc.exists(), "src/*.pyc should be cleaned"
        assert nm_pyc.exists(), "node_modules/**/*.pyc must survive clean"
