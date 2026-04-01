"""Tests for STORY-slim-076: Multi-stack visualize — class mode + multi-language file scanning."""
import textwrap

import pytest

from pactkit.skills.visualize import (
    _build_class_graph,
    _detect_stack,
    _scan_files,
    PythonAnalyzer,
)

# Tree-sitter is optional — skip analyzer tests if unavailable
_has_tree_sitter = False
try:
    import tree_sitter  # noqa: F401
    _has_tree_sitter = True
except ImportError:
    pass


# ── Helpers ─────────────────────────────────────────────────────────────

def _make_pactkit_yaml(root, stack_value):
    """Write a pactkit.yaml with a given stack field."""
    config_dir = root / '.claude'
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'pactkit.yaml').write_text(f'stack: {stack_value}\n')


def _make_marker(root, filename):
    """Create a marker file (e.g. go.mod, package.json)."""
    (root / filename).write_text('')


# ── AC1: Multi-stack detection returns all stacks ───────────────────────

class TestAC1MultiStackDetection:
    def test_go_and_node_detected(self, tmp_path):
        from pactkit.skills.visualize import _detect_stacks
        _make_marker(tmp_path, 'go.mod')
        _make_marker(tmp_path, 'package.json')
        stacks = _detect_stacks(tmp_path)
        assert 'go' in stacks
        assert 'node' in stacks
        assert len(stacks) == 2

    def test_python_and_go_detected(self, tmp_path):
        from pactkit.skills.visualize import _detect_stacks
        _make_marker(tmp_path, 'pyproject.toml')
        _make_marker(tmp_path, 'go.mod')
        stacks = _detect_stacks(tmp_path)
        assert 'python' in stacks
        assert 'go' in stacks

    def test_all_four_stacks(self, tmp_path):
        from pactkit.skills.visualize import _detect_stacks
        _make_marker(tmp_path, 'pyproject.toml')
        _make_marker(tmp_path, 'package.json')
        _make_marker(tmp_path, 'go.mod')
        _make_marker(tmp_path, 'pom.xml')
        stacks = _detect_stacks(tmp_path)
        assert set(stacks) == {'python', 'node', 'go', 'java'}


# ── AC2: Single-stack backward compatibility ────────────────────────────

class TestAC2SingleStackCompat:
    def test_python_only(self, tmp_path):
        from pactkit.skills.visualize import _detect_stacks
        _make_marker(tmp_path, 'pyproject.toml')
        assert _detect_stacks(tmp_path) == ['python']
        assert _detect_stack(tmp_path) == 'python'

    def test_no_markers_defaults_python(self, tmp_path):
        from pactkit.skills.visualize import _detect_stacks
        assert _detect_stacks(tmp_path) == ['python']
        assert _detect_stack(tmp_path) == 'python'


# ── AC3: Multi-stack file scanning merges all files ─────────────────────

class TestAC3MultiStackScanning:
    def test_go_and_ts_files_merged(self, tmp_path):
        """Simulate a Go+Node project and verify both file types are scanned."""
        from pactkit.skills.visualize import _detect_stacks, _LANG_FILE_EXT
        _make_marker(tmp_path, 'go.mod')
        _make_marker(tmp_path, 'package.json')
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'main.go').write_text('package main\n')
        (src / 'app.ts').write_text('export class App {}\n')

        stacks = _detect_stacks(tmp_path)
        all_files = []
        for stack in stacks:
            exts = [_LANG_FILE_EXT[stack]]
            if stack == 'node':
                exts.append('.js')
            for ext in exts:
                files, _, _ = _scan_files(tmp_path, file_ext=ext)
                all_files.extend(files)

        extensions = {f.suffix for f in all_files}
        assert '.go' in extensions
        assert '.ts' in extensions


# ── AC4: Class mode shows Go structs ────────────────────────────────────

@pytest.mark.skipif(not _has_tree_sitter, reason='tree-sitter not installed')
class TestAC4GoClassMode:
    def test_go_struct_extracted(self, tmp_path):
        from pactkit.skills.visualize import GoAnalyzer
        code = textwrap.dedent('''\
            package main

            type Base struct {}

            func (b *Base) Hello() {}

            type Sub struct {
                Base
            }

            func (s *Sub) Hello() {}
            func (s *Sub) World() {}
        ''')
        p = tmp_path / 'main.go'
        p.write_text(code)
        analyzer = GoAnalyzer()
        classes = analyzer.extract_classes(p, tmp_path)
        names = [c[1] for c in classes]
        assert 'Base' in names
        assert 'Sub' in names
        # Check Sub has Base as parent
        sub_entry = [c for c in classes if c[1] == 'Sub'][0]
        assert 'Base' in sub_entry[2]  # bases list
        # Check methods
        sub_methods = sub_entry[3]
        assert any('Hello' in m for m in sub_methods)
        assert any('World' in m for m in sub_methods)


# ── AC5: Class mode shows TS classes ────────────────────────────────────

@pytest.mark.skipif(not _has_tree_sitter, reason='tree-sitter not installed')
class TestAC5TSClassMode:
    def test_ts_class_extracted(self, tmp_path):
        from pactkit.skills.visualize import TSAnalyzer
        code = textwrap.dedent('''\
            class Animal {
                speak() { return "..."; }
            }

            class Dog extends Animal {
                speak() { return "woof"; }
                fetch() { return "ball"; }
            }
        ''')
        p = tmp_path / 'animals.ts'
        p.write_text(code)
        analyzer = TSAnalyzer()
        classes = analyzer.extract_classes(p, tmp_path)
        names = [c[1] for c in classes]
        assert 'Animal' in names
        assert 'Dog' in names
        dog_entry = [c for c in classes if c[1] == 'Dog'][0]
        assert 'Animal' in dog_entry[2]  # bases
        assert any('fetch' in m for m in dog_entry[3])


# ── AC6: Class mode shows Java classes ──────────────────────────────────

@pytest.mark.skipif(not _has_tree_sitter, reason='tree-sitter not installed')
class TestAC6JavaClassMode:
    def test_java_class_extracted(self, tmp_path):
        from pactkit.skills.visualize import JavaAnalyzer
        code = textwrap.dedent('''\
            class Vehicle {
                void drive() {}
            }

            class Car extends Vehicle {
                void drive() {}
                void park() {}
            }
        ''')
        p = tmp_path / 'Vehicle.java'
        p.write_text(code)
        analyzer = JavaAnalyzer()
        classes = analyzer.extract_classes(p, tmp_path)
        names = [c[1] for c in classes]
        assert 'Vehicle' in names
        assert 'Car' in names
        car_entry = [c for c in classes if c[1] == 'Car'][0]
        assert 'Vehicle' in car_entry[2]
        assert any('park' in m for m in car_entry[3])


# ── AC7: Mixed-stack class graph merges both languages ──────────────────

@pytest.mark.skipif(not _has_tree_sitter, reason='tree-sitter not installed')
class TestAC7MixedStackClassGraph:
    def test_go_and_ts_in_class_graph(self, tmp_path):
        from pactkit.skills.visualize import GoAnalyzer, TSAnalyzer
        # Write Go file
        go_src = tmp_path / 'src'
        go_src.mkdir()
        (go_src / 'model.go').write_text(textwrap.dedent('''\
            package main
            type Server struct {}
            func (s *Server) Start() {}
        '''))
        # Write TS file
        (go_src / 'client.ts').write_text(textwrap.dedent('''\
            class Client {
                connect() {}
            }
        '''))

        # Collect classes from both analyzers
        go_files = list(go_src.glob('*.go'))
        ts_files = list(go_src.glob('*.ts'))

        go_analyzer = GoAnalyzer()
        ts_analyzer = TSAnalyzer()

        all_classes = []
        for f in go_files:
            all_classes.extend(go_analyzer.extract_classes(f, tmp_path))
        for f in ts_files:
            all_classes.extend(ts_analyzer.extract_classes(f, tmp_path))

        names = [c[1] for c in all_classes]
        assert 'Server' in names
        assert 'Client' in names


# ── AC8: _load_code_graph multi-extension scanning ──────────────────────

class TestAC8LoadCodeGraphMultiExt:
    def test_node_project_scans_ts_and_js(self, tmp_path):
        """Verify that for a node project, both .ts and .js files are collected."""
        from pactkit.skills.visualize import _detect_stacks, _LANG_FILE_EXT
        _make_marker(tmp_path, 'package.json')
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'app.ts').write_text('export const x = 1;\n')
        (src / 'util.js').write_text('module.exports = {};\n')

        stacks = _detect_stacks(tmp_path)
        all_files = []
        for stack in stacks:
            exts = [_LANG_FILE_EXT[stack]]
            if stack == 'node':
                exts.append('.js')
            for ext in exts:
                files, _, _ = _scan_files(tmp_path, file_ext=ext)
                all_files.extend(files)

        suffixes = {f.suffix for f in all_files}
        assert '.ts' in suffixes
        assert '.js' in suffixes


# ── AC9: Multi-stack analyzer selection ─────────────────────────────────

@pytest.mark.skipif(not _has_tree_sitter, reason='tree-sitter not installed')
class TestAC9AnalyzerSelection:
    def test_select_analyzers_go_node(self):
        from pactkit.skills.visualize import _select_analyzers, GoAnalyzer, TSAnalyzer
        result = _select_analyzers(['go', 'node'])
        assert len(result) == 2
        stack_map = dict(result)
        assert isinstance(stack_map['go'], GoAnalyzer)
        assert isinstance(stack_map['node'], TSAnalyzer)

    def test_select_analyzers_python_only(self):
        from pactkit.skills.visualize import _select_analyzers
        result = _select_analyzers(['python'])
        assert len(result) == 1
        assert result[0][0] == 'python'
        assert isinstance(result[0][1], PythonAnalyzer)


# ── AC10: pactkit.yaml stack field override ─────────────────────────────

class TestAC10YamlOverride:
    def test_explicit_stack_go(self, tmp_path):
        from pactkit.skills.visualize import _detect_stacks
        _make_pactkit_yaml(tmp_path, 'go')
        # Even if both markers exist, yaml overrides
        _make_marker(tmp_path, 'go.mod')
        _make_marker(tmp_path, 'package.json')
        assert _detect_stacks(tmp_path) == ['go']

    def test_explicit_stack_auto_falls_through(self, tmp_path):
        from pactkit.skills.visualize import _detect_stacks
        _make_pactkit_yaml(tmp_path, 'auto')
        _make_marker(tmp_path, 'go.mod')
        _make_marker(tmp_path, 'package.json')
        stacks = _detect_stacks(tmp_path)
        assert 'go' in stacks
        assert 'node' in stacks

    def test_stack_list_syntax(self, tmp_path):
        """stack: [go, node] in pactkit.yaml returns exactly those stacks."""
        from pactkit.skills.visualize import _detect_stacks
        config_dir = tmp_path / '.claude'
        config_dir.mkdir(parents=True)
        (config_dir / 'pactkit.yaml').write_text('stack:\n  - go\n  - node\n')
        assert _detect_stacks(tmp_path) == ['go', 'node']

    def test_stack_list_filters_invalid(self, tmp_path):
        """Invalid stacks in list are filtered out."""
        from pactkit.skills.visualize import _detect_stacks
        config_dir = tmp_path / '.claude'
        config_dir.mkdir(parents=True)
        (config_dir / 'pactkit.yaml').write_text('stack:\n  - go\n  - rust\n')
        assert _detect_stacks(tmp_path) == ['go']

    def test_stack_list_all_invalid_falls_through(self, tmp_path):
        """If all stacks in list are invalid, fall through to marker detection."""
        from pactkit.skills.visualize import _detect_stacks
        config_dir = tmp_path / '.claude'
        config_dir.mkdir(parents=True)
        (config_dir / 'pactkit.yaml').write_text('stack:\n  - rust\n  - cpp\n')
        _make_marker(tmp_path, 'go.mod')
        assert _detect_stacks(tmp_path) == ['go']


# ── R4: _build_class_graph accepts analyzer ─────────────────────────────

class TestR4BuildClassGraphRefactored:
    def test_python_class_via_analyzer(self, tmp_path):
        """_build_class_graph using PythonAnalyzer produces same output as before."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'example.py').write_text(textwrap.dedent('''\
            class Base:
                def hello(self):
                    pass

            class Child(Base):
                def hello(self):
                    pass
                def world(self):
                    pass
        '''))
        py_files = list(src.glob('*.py'))
        analyzer = PythonAnalyzer()

        dest, content = _build_class_graph(
            tmp_path, py_files, focus=None,
            analyzers=[('python', analyzer, py_files)],
        )
        assert 'Base' in content
        assert 'Child' in content
        assert 'Base <|-- Child' in content
        assert '+hello' in content or '-hello' in content
