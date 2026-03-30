"""Tests for monorepo subdirectory marker detection (HOTFIX-slim-067)."""
import pytest


class TestMonorepoDetect:
    """TopologyParser.detect() should find markers in immediate subdirectories."""

    def test_detect_marker_in_root(self, tmp_path):
        """Standard case: marker at root level."""
        from pactkit.skills.visualize import FrontendParser
        (tmp_path / "next.config.ts").touch()
        assert FrontendParser().detect(tmp_path) is True

    def test_detect_marker_in_subdirectory(self, tmp_path):
        """Monorepo case: marker in web/ subdirectory."""
        from pactkit.skills.visualize import FrontendParser
        web = tmp_path / "web"
        web.mkdir()
        (web / "next.config.ts").touch()
        assert FrontendParser().detect(tmp_path) is True

    def test_detect_marker_in_frontend_subdirectory(self, tmp_path):
        """Monorepo case: marker in frontend/ subdirectory."""
        from pactkit.skills.visualize import FrontendParser
        fe = tmp_path / "frontend"
        fe.mkdir()
        (fe / "vite.config.ts").touch()
        assert FrontendParser().detect(tmp_path) is True

    def test_detect_ignores_dotdirs(self, tmp_path):
        """Should NOT search .hidden directories."""
        from pactkit.skills.visualize import FrontendParser
        hidden = tmp_path / ".cache"
        hidden.mkdir()
        (hidden / "next.config.ts").touch()
        assert FrontendParser().detect(tmp_path) is False

    def test_detect_ignores_node_modules(self, tmp_path):
        """Should NOT search node_modules."""
        from pactkit.skills.visualize import FrontendParser
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "next.config.ts").touch()
        assert FrontendParser().detect(tmp_path) is False

    def test_detect_no_markers_anywhere(self, tmp_path):
        """No markers at root or subdirs."""
        from pactkit.skills.visualize import FrontendParser
        (tmp_path / "README.md").touch()
        (tmp_path / "src").mkdir()
        assert FrontendParser().detect(tmp_path) is False

    def test_detect_nested_marker_path(self, tmp_path):
        """Monorepo with nested marker like app/layout.tsx in web/."""
        from pactkit.skills.visualize import FrontendParser
        web = tmp_path / "web"
        app = web / "app"
        app.mkdir(parents=True)
        (app / "layout.tsx").touch()
        assert FrontendParser().detect(tmp_path) is True

    def test_detect_topology_monorepo(self, tmp_path):
        """detect_topology() also finds markers in subdirs."""
        from pactkit.skills.visualize import detect_topology
        web = tmp_path / "web"
        web.mkdir()
        (web / "next.config.ts").touch()
        result = detect_topology(tmp_path)
        assert "frontend" in result


class TestApiCallParserMonorepo:
    """ApiCallParser should detect and parse monorepo projects."""

    @pytest.fixture(autouse=True)
    def _skip_no_treesitter(self):
        try:
            from pactkit.skills.visualize import ApiCallParser, _HAS_TREE_SITTER  # noqa: F401
            if not _HAS_TREE_SITTER:
                pytest.skip("tree-sitter not installed")
        except ImportError:
            pytest.skip("ApiCallParser not yet implemented")

    def test_detect_in_web_subdirectory(self, tmp_path):
        """ApiCallParser detects Next.js project in web/ subdirectory."""
        from pactkit.skills.visualize import ApiCallParser
        web = tmp_path / "web"
        web.mkdir()
        (web / "next.config.ts").touch()
        src = web / "src" / "app"
        src.mkdir(parents=True)
        page = src / "page.tsx"
        page.write_text('const data = await apiFetch("/api/v1/items");\n')
        assert ApiCallParser().detect(tmp_path) is True
