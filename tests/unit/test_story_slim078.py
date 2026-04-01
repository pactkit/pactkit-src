"""Tests for STORY-slim-078: Multi-language module resolution for file-mode dependency graph."""
from pathlib import Path
from unittest.mock import MagicMock


# --- R1: build_module_keys ---

class TestPythonBuildModuleKeys:
    """AC7: Python backward compat — keys must match pre-change behavior."""

    def test_simple_module(self, tmp_path):
        from pactkit.skills.analyzers.python_analyzer import PythonAnalyzer
        a = PythonAnalyzer()
        keys = a.build_module_keys(Path('pactkit/config.py'), tmp_path)
        assert 'pactkit.config' in keys

    def test_src_prefix_strip(self, tmp_path):
        from pactkit.skills.analyzers.python_analyzer import PythonAnalyzer
        a = PythonAnalyzer()
        keys = a.build_module_keys(Path('src/pactkit/config.py'), tmp_path)
        assert 'src.pactkit.config' in keys
        assert 'pactkit.config' in keys

    def test_init_py_package_key(self, tmp_path):
        from pactkit.skills.analyzers.python_analyzer import PythonAnalyzer
        a = PythonAnalyzer()
        keys = a.build_module_keys(Path('src/pactkit/__init__.py'), tmp_path)
        assert 'src.pactkit' in keys
        assert 'pactkit' in keys


class TestGoBuildModuleKeys:
    """AC1: Go file edges — keys include slash-separated paths."""

    def _make(self):
        from pactkit.skills.analyzers.go_analyzer import GoAnalyzer
        return GoAnalyzer.__new__(GoAnalyzer)

    def test_slash_separated(self, tmp_path):
        keys = self._make().build_module_keys(Path('backend/internal/ui/auth.go'), tmp_path)
        assert 'backend/internal/ui/auth' in keys

    def test_package_level(self, tmp_path):
        keys = self._make().build_module_keys(Path('backend/internal/ui/auth.go'), tmp_path)
        assert 'backend/internal/ui' in keys

    def test_without_top_dir(self, tmp_path):
        keys = self._make().build_module_keys(Path('backend/internal/ui/auth.go'), tmp_path)
        assert 'internal/ui/auth' in keys


class TestTSBuildModuleKeys:
    """AC2: TS file edges — keys include path variants."""

    def _make(self):
        from pactkit.skills.analyzers.ts_analyzer import TSAnalyzer
        return TSAnalyzer.__new__(TSAnalyzer)

    def test_slash_separated(self, tmp_path):
        keys = self._make().build_module_keys(Path('src/lib/utils.ts'), tmp_path)
        assert 'src/lib/utils' in keys

    def test_src_strip(self, tmp_path):
        keys = self._make().build_module_keys(Path('src/lib/utils.ts'), tmp_path)
        assert 'lib/utils' in keys

    def test_index_file(self, tmp_path):
        keys = self._make().build_module_keys(Path('src/components/index.ts'), tmp_path)
        assert 'src/components' in keys or 'components' in keys


class TestJavaBuildModuleKeys:
    """AC3: Java file edges — keys include qualified class name."""

    def _make(self):
        from pactkit.skills.analyzers.java_analyzer import JavaAnalyzer
        return JavaAnalyzer.__new__(JavaAnalyzer)

    def test_qualified_name(self, tmp_path):
        keys = self._make().build_module_keys(Path('src/main/java/com/example/Foo.java'), tmp_path)
        assert 'com.example.Foo' in keys

    def test_full_path_key(self, tmp_path):
        keys = self._make().build_module_keys(Path('src/main/java/com/example/Foo.java'), tmp_path)
        assert 'src.main.java.com.example.Foo' in keys


# --- R2: normalize_import ---

class TestPythonNormalizeImport:
    def test_returns_as_is(self, tmp_path):
        from pactkit.skills.analyzers.python_analyzer import PythonAnalyzer
        assert PythonAnalyzer().normalize_import('pactkit.config', Path('test.py'), tmp_path) == 'pactkit.config'


class TestGoNormalizeImport:
    def _make(self):
        from pactkit.skills.analyzers.go_analyzer import GoAnalyzer
        return GoAnalyzer.__new__(GoAnalyzer)

    def test_strip_module_prefix(self, tmp_path):
        """AC5: Go module prefix stripping."""
        (tmp_path / 'go.mod').write_text('module github.com/slim/phase-smith\n\ngo 1.22\n')
        result = self._make().normalize_import(
            'github.com/slim/phase-smith/backend/internal/ui',
            tmp_path / 'gateway/main.go', tmp_path,
        )
        assert result == 'backend/internal/ui'

    def test_stdlib_returns_none(self, tmp_path):
        """AC8: External imports ignored."""
        assert self._make().normalize_import('fmt', Path('main.go'), tmp_path) is None

    def test_net_http_returns_none(self, tmp_path):
        """AC8: Go stdlib with slash."""
        assert self._make().normalize_import('net/http', Path('main.go'), tmp_path) is None


class TestTSNormalizeImport:
    def _make(self):
        from pactkit.skills.analyzers.ts_analyzer import TSAnalyzer
        return TSAnalyzer.__new__(TSAnalyzer)

    def test_resolve_relative(self, tmp_path):
        consumer = tmp_path / 'src/app/page.ts'
        assert self._make().normalize_import('../lib/utils', consumer, tmp_path) == 'src/lib/utils'

    def test_bare_module_returns_none(self, tmp_path):
        """AC8: External imports ignored."""
        assert self._make().normalize_import('react', tmp_path / 'src/app.ts', tmp_path) is None

    def test_scoped_package_returns_none(self, tmp_path):
        """AC8: @scope/pkg ignored."""
        assert self._make().normalize_import('@supabase/ssr', tmp_path / 'src/app.ts', tmp_path) is None


class TestJavaNormalizeImport:
    def _make(self):
        from pactkit.skills.analyzers.java_analyzer import JavaAnalyzer
        return JavaAnalyzer.__new__(JavaAnalyzer)

    def test_returns_as_is(self, tmp_path):
        assert self._make().normalize_import('com.example.Service', Path('App.java'), tmp_path) == 'com.example.Service'

    def test_stdlib_returns_none(self, tmp_path):
        """AC8: java.util.List ignored."""
        assert self._make().normalize_import('java.util.List', Path('App.java'), tmp_path) is None


# --- R3: Multi-analyzer dispatch (AC4) ---

class TestMultiAnalyzerDispatch:
    def test_uses_correct_analyzer_per_stack(self, tmp_path):
        from pactkit.skills.visualize import _build_file_graph

        py_file = tmp_path / 'app.py'
        py_file.touch()
        go_file = tmp_path / 'main.go'
        go_file.touch()

        py_a = MagicMock()
        py_a.extract_imports.return_value = []
        py_a.normalize_import.return_value = None
        go_a = MagicMock()
        go_a.extract_imports.return_value = []
        go_a.normalize_import.return_value = None

        file_to_node = {py_file: 'app_py', go_file: 'main_go'}
        _build_file_graph(
            tmp_path, [py_file, go_file], {}, file_to_node, None,
            analyzer_file_groups=[('python', py_a, [py_file]), ('go', go_a, [go_file])],
        )
        py_a.extract_imports.assert_called_once_with(py_file)
        go_a.extract_imports.assert_called_once_with(go_file)


# --- R4: src-strip fix (AC6) ---

class TestSrcStripFix:
    def test_ts_no_extension_in_key(self, tmp_path):
        """AC6: src/lib/utils.ts → secondary key lib.utils, not lib.utils.ts."""
        from pactkit.skills.analyzers.ts_analyzer import TSAnalyzer
        keys = TSAnalyzer.__new__(TSAnalyzer).build_module_keys(Path('src/lib/utils.ts'), tmp_path)
        for key in keys:
            assert not key.endswith('.ts'), f"Key '{key}' still has .ts extension"

    def test_go_no_extension_in_key(self, tmp_path):
        from pactkit.skills.analyzers.go_analyzer import GoAnalyzer
        keys = GoAnalyzer.__new__(GoAnalyzer).build_module_keys(Path('src/internal/handler.go'), tmp_path)
        for key in keys:
            assert not key.endswith('.go'), f"Key '{key}' still has .go extension"


# --- R4: _scan_files with analyzer ---

class TestScanFilesAnalyzer:
    def test_uses_analyzer_build_module_keys(self, tmp_path):
        from pactkit.skills.visualize import _scan_files
        (tmp_path / 'src' / 'lib').mkdir(parents=True)
        (tmp_path / 'src' / 'lib' / 'utils.ts').write_text('export const foo = 1;')

        mock_a = MagicMock()
        mock_a.build_module_keys.return_value = ['src/lib/utils', 'lib/utils']

        files, mi, ftn = _scan_files(tmp_path, file_ext='.ts', analyzer=mock_a)
        assert len(files) == 1
        assert 'src/lib/utils' in mi
        assert 'lib/utils' in mi
        mock_a.build_module_keys.assert_called_once()


# --- R5: Go module prefix detection (AC5, STORY-slim-080: nearest-ancestor) ---

class TestGoModulePrefix:
    def _make(self):
        from pactkit.skills.analyzers.go_analyzer import GoAnalyzer
        go = GoAnalyzer.__new__(GoAnalyzer)
        go._go_mod_cache = {}
        return go

    def test_read_prefix(self, tmp_path):
        (tmp_path / 'go.mod').write_text('module github.com/slim/phase-smith\n\ngo 1.22\n')
        prefix, _ = self._make()._find_nearest_go_mod(tmp_path / 'cmd/main.go', tmp_path)
        assert prefix == 'github.com/slim/phase-smith'

    def test_no_go_mod(self, tmp_path):
        prefix, _ = self._make()._find_nearest_go_mod(tmp_path / 'main.go', tmp_path)
        assert prefix is None

    def test_subdir_go_mod(self, tmp_path):
        sub = tmp_path / 'backend'
        sub.mkdir()
        (sub / 'go.mod').write_text('module github.com/slim/phase-smith/backend\n')
        prefix, _ = self._make()._find_nearest_go_mod(tmp_path / 'backend/cmd/main.go', tmp_path)
        assert prefix == 'github.com/slim/phase-smith/backend'


# --- R0: load_script merge ---

class TestLoadScriptMerge:
    def test_merged_contains_analyzer_code(self):
        from pactkit.skills import load_script
        content = load_script('visualize.py')
        assert 'class PythonAnalyzer' in content
        assert 'class LanguageAnalyzer' in content
        assert 'def build_module_keys' in content
        assert 'def normalize_import' in content

    def test_merged_no_analyzer_imports(self):
        from pactkit.skills import load_script
        content = load_script('visualize.py')
        assert 'from pactkit.skills.analyzers' not in content
        assert 'from .analyzers' not in content


# --- Integration: Go edges (AC1) ---

class TestGoEdgesIntegration:
    def test_go_file_produces_edge(self, tmp_path):
        from pactkit.skills.visualize import _build_file_graph
        handler = tmp_path / 'internal/api/handler.go'
        store = tmp_path / 'internal/db/store.go'
        handler.parent.mkdir(parents=True)
        store.parent.mkdir(parents=True)
        handler.touch()
        store.touch()

        file_to_node = {handler: 'internal_api_handler_go', store: 'internal_db_store_go'}
        module_index = {
            'internal/api/handler': [handler], 'internal/api': [handler],
            'internal/db/store': [store], 'internal/db': [store],
        }
        mock = MagicMock()
        mock.extract_imports.side_effect = lambda f: ['internal/db'] if f == handler else []
        mock.normalize_import.side_effect = lambda imp, p, r: imp

        dest, content = _build_file_graph(
            tmp_path, [handler, store], module_index, file_to_node, None,
            analyzer_file_groups=[('go', mock, [handler, store])],
        )
        assert 'internal_api_handler_go --> internal_db_store_go' in content


# --- Integration: TS edges (AC2) ---

class TestTSEdgesIntegration:
    def test_ts_relative_import_edge(self, tmp_path):
        from pactkit.skills.visualize import _build_file_graph
        page = tmp_path / 'src/app/page.ts'
        utils = tmp_path / 'src/lib/utils.ts'
        page.parent.mkdir(parents=True)
        utils.parent.mkdir(parents=True)
        page.touch()
        utils.touch()

        file_to_node = {page: 'src_app_page_ts', utils: 'src_lib_utils_ts'}
        module_index = {'src/lib/utils': [utils], 'lib/utils': [utils], 'src/app/page': [page]}
        mock = MagicMock()
        mock.extract_imports.side_effect = lambda f: ['../lib/utils'] if f == page else []
        mock.normalize_import.side_effect = lambda imp, p, r: 'src/lib/utils' if imp == '../lib/utils' else None

        dest, content = _build_file_graph(
            tmp_path, [page, utils], module_index, file_to_node, None,
            analyzer_file_groups=[('node', mock, [page, utils])],
        )
        assert 'src_app_page_ts --> src_lib_utils_ts' in content


# --- Integration: Java edges (AC3) ---

class TestJavaEdgesIntegration:
    def test_java_package_import_edge(self, tmp_path):
        from pactkit.skills.visualize import _build_file_graph
        app = tmp_path / 'src/main/java/com/example/App.java'
        svc = tmp_path / 'src/main/java/com/example/Service.java'
        app.parent.mkdir(parents=True)
        app.touch()
        svc.touch()

        file_to_node = {
            app: 'src_main_java_com_example_App_java',
            svc: 'src_main_java_com_example_Service_java',
        }
        module_index = {'com.example.App': [app], 'com.example.Service': [svc]}
        mock = MagicMock()
        mock.extract_imports.side_effect = lambda f: ['com.example.Service'] if f == app else []
        mock.normalize_import.side_effect = lambda imp, p, r: imp

        dest, content = _build_file_graph(
            tmp_path, [app, svc], module_index, file_to_node, None,
            analyzer_file_groups=[('java', mock, [app, svc])],
        )
        assert 'src_main_java_com_example_App_java --> src_main_java_com_example_Service_java' in content
