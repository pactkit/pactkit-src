"""Tests for STORY-slim-081: Two-tier module graph with scoped focus for large codebases."""


# --- R1: _detect_modules ---

class TestDetectModules:
    def test_java_monorepo(self, tmp_path):
        """AC1: Multiple pom.xml at different depths detected as modules."""
        from pactkit.skills.visualize import _detect_modules
        (tmp_path / 'dubbo-common/src/main/java').mkdir(parents=True)
        (tmp_path / 'dubbo-common/pom.xml').write_text('<project/>')
        (tmp_path / 'dubbo-config/src/main/java').mkdir(parents=True)
        (tmp_path / 'dubbo-config/pom.xml').write_text('<project/>')
        (tmp_path / 'dubbo-registry/dubbo-registry-api/src').mkdir(parents=True)
        (tmp_path / 'dubbo-registry/dubbo-registry-api/pom.xml').write_text('<project/>')

        modules = _detect_modules(tmp_path)
        names = [m[0] for m in modules]
        assert 'dubbo-common' in names
        assert 'dubbo-config' in names
        assert 'dubbo-registry/dubbo-registry-api' in names

    def test_multi_stack_monorepo(self, tmp_path):
        """AC2: Different stacks detected correctly."""
        from pactkit.skills.visualize import _detect_modules
        (tmp_path / 'backend').mkdir()
        (tmp_path / 'backend/go.mod').write_text('module backend\n')
        (tmp_path / 'frontend').mkdir()
        (tmp_path / 'frontend/package.json').write_text('{}')
        (tmp_path / 'gateway').mkdir()
        (tmp_path / 'gateway/go.mod').write_text('module gateway\n')

        modules = _detect_modules(tmp_path)
        names = {m[0] for m in modules}
        stacks = {m[0]: m[2] for m in modules}
        assert names == {'backend', 'frontend', 'gateway'}
        assert stacks['backend'] == 'go'
        assert stacks['frontend'] == 'node'
        assert stacks['gateway'] == 'go'

    def test_scan_excludes_respected(self, tmp_path):
        """AC9: node_modules marker not detected as module."""
        from pactkit.skills.visualize import _detect_modules
        (tmp_path / 'node_modules/some-pkg').mkdir(parents=True)
        (tmp_path / 'node_modules/some-pkg/package.json').write_text('{}')
        (tmp_path / 'src').mkdir()
        (tmp_path / 'package.json').write_text('{}')

        modules = _detect_modules(tmp_path)
        names = [m[0] for m in modules]
        assert 'node_modules/some-pkg' not in names

    def test_root_level_marker(self, tmp_path):
        """Root-level marker produces module name '.'."""
        from pactkit.skills.visualize import _detect_modules
        (tmp_path / 'pyproject.toml').write_text('[project]\nname="myapp"')

        modules = _detect_modules(tmp_path)
        names = [m[0] for m in modules]
        assert '.' in names

    def test_no_markers(self, tmp_path):
        """No marker files → empty list."""
        from pactkit.skills.visualize import _detect_modules
        (tmp_path / 'src').mkdir()
        (tmp_path / 'src/main.py').write_text('print("hello")')

        modules = _detect_modules(tmp_path)
        assert modules == []


# --- R2: _build_module_graph ---

class TestBuildModuleGraph:
    def test_weighted_edges(self, tmp_path):
        """AC3: Cross-module imports produce weighted edges."""
        from pactkit.skills.visualize import _build_module_graph, _detect_modules
        # Module A imports 3 things from Module B
        (tmp_path / 'mod_a').mkdir()
        (tmp_path / 'mod_a/pyproject.toml').write_text('[project]\nname="a"')
        (tmp_path / 'mod_a/core.py').write_text(
            'from mod_b.utils import foo\nfrom mod_b.utils import bar\nfrom mod_b.helpers import baz\n'
        )
        (tmp_path / 'mod_b').mkdir()
        (tmp_path / 'mod_b/pyproject.toml').write_text('[project]\nname="b"')
        (tmp_path / 'mod_b/utils.py').write_text('def foo(): pass\ndef bar(): pass\n')
        (tmp_path / 'mod_b/helpers.py').write_text('def baz(): pass\n')

        modules = _detect_modules(tmp_path)
        dest, content = _build_module_graph(tmp_path, modules)
        assert 'mod_a' in content
        assert 'mod_b' in content
        assert '-->' in content
        # Edge should have weight label
        assert '|' in content  # weight syntax: -->|N|

    def test_click_links(self, tmp_path):
        """AC10: Nodes have click links to module directory."""
        from pactkit.skills.visualize import _build_module_graph, _detect_modules
        (tmp_path / 'backend').mkdir()
        (tmp_path / 'backend/go.mod').write_text('module backend\n')
        (tmp_path / 'backend/main.go').write_text('package main')

        modules = _detect_modules(tmp_path)
        dest, content = _build_module_graph(tmp_path, modules)
        assert 'click' in content
        assert 'backend/' in content or 'backend"' in content

    def test_no_self_edges(self, tmp_path):
        """Intra-module imports should not produce edges."""
        from pactkit.skills.visualize import _build_module_graph, _detect_modules
        (tmp_path / 'mymod').mkdir()
        (tmp_path / 'mymod/pyproject.toml').write_text('[project]\nname="m"')
        (tmp_path / 'mymod/a.py').write_text('from mymod.b import x\n')
        (tmp_path / 'mymod/b.py').write_text('x = 1\n')

        modules = _detect_modules(tmp_path)
        dest, content = _build_module_graph(tmp_path, modules)
        assert '-->' not in content  # No cross-module edges


# --- R3: Auto-degradation ---

class TestAutoDegradation:
    def test_file_mode_degrades_when_over_limit(self, tmp_path):
        """AC4: When files exceed MAX_SCAN_FILES, module graph is generated instead."""
        from pactkit.skills.visualize import visualize, MAX_SCAN_FILES
        # Create 2 modules with enough files to exceed limit
        for mod_name in ['mod_a', 'mod_b']:
            mod_dir = tmp_path / mod_name
            mod_dir.mkdir()
            (mod_dir / 'pyproject.toml').write_text(f'[project]\nname="{mod_name}"')
            for i in range(MAX_SCAN_FILES // 2 + 10):
                (mod_dir / f'file_{i}.py').write_text(f'x_{i} = {i}\n')

        graphs_dir = tmp_path / 'docs/architecture/graphs'
        graphs_dir.mkdir(parents=True)
        result = visualize(target=str(tmp_path), mode='file')
        # Should have generated module_graph.mmd, not code_graph.mmd
        assert (graphs_dir / 'module_graph.mmd').exists()
        assert 'module graph' in result.lower() or 'module_graph' in result.lower()

    def test_small_project_no_degradation(self, tmp_path):
        """AC7: Small project still gets file-level graph."""
        from pactkit.skills.visualize import visualize
        (tmp_path / 'pyproject.toml').write_text('[project]\nname="small"')
        (tmp_path / 'app.py').write_text('import os\n')
        (tmp_path / 'util.py').write_text('x = 1\n')

        graphs_dir = tmp_path / 'docs/architecture/graphs'
        graphs_dir.mkdir(parents=True)
        result = visualize(target=str(tmp_path), mode='file')
        assert (graphs_dir / 'code_graph.mmd').exists()


# --- R4: Scoped focus ---

class TestScopedFocus:
    def test_focus_scans_only_target_module(self, tmp_path):
        """AC5: Focus on one module scans only that directory."""
        from pactkit.skills.visualize import visualize
        # Two modules
        (tmp_path / 'backend').mkdir()
        (tmp_path / 'backend/go.mod').write_text('module backend\n')
        (tmp_path / 'backend/main.go').write_text('package main')
        (tmp_path / 'backend/handler.go').write_text('package main')
        (tmp_path / 'frontend').mkdir()
        (tmp_path / 'frontend/package.json').write_text('{}')
        (tmp_path / 'frontend/app.ts').write_text('const x = 1;')

        graphs_dir = tmp_path / 'docs/architecture/graphs'
        graphs_dir.mkdir(parents=True)
        result = visualize(target=str(tmp_path), mode='file', focus='backend')
        graph_content = (graphs_dir / 'code_graph.mmd').read_text()
        # Should contain backend files but NOT frontend files
        assert 'main' in graph_content or 'handler' in graph_content
        assert 'app_ts' not in graph_content

    def test_focus_invalid_module_lists_available(self, tmp_path):
        """AC6: Invalid focus name produces helpful error."""
        from pactkit.skills.visualize import visualize
        (tmp_path / 'backend').mkdir()
        (tmp_path / 'backend/go.mod').write_text('module backend\n')
        (tmp_path / 'frontend').mkdir()
        (tmp_path / 'frontend/package.json').write_text('{}')

        graphs_dir = tmp_path / 'docs/architecture/graphs'
        graphs_dir.mkdir(parents=True)
        result = visualize(target=str(tmp_path), mode='file', focus='nonexistent')
        assert 'backend' in result
        assert 'frontend' in result


# --- R5: .tsx/.jsx extension ---

class TestTsxExtension:
    def test_tsx_files_scanned(self, tmp_path):
        """AC8: .tsx files appear as nodes."""
        from pactkit.skills.visualize import visualize
        (tmp_path / 'package.json').write_text('{}')
        (tmp_path / 'tsconfig.json').write_text('{"compilerOptions":{}}')
        (tmp_path / 'src').mkdir()
        (tmp_path / 'src/app.tsx').write_text('export default function App() { return <div/>; }')
        (tmp_path / 'src/utils.ts').write_text('export const x = 1;')

        graphs_dir = tmp_path / 'docs/architecture/graphs'
        graphs_dir.mkdir(parents=True)
        result = visualize(target=str(tmp_path), mode='file')
        graph_content = (graphs_dir / 'code_graph.mmd').read_text()
        assert 'app' in graph_content.lower()


# --- R2: Module mode explicit ---

class TestModuleMode:
    def test_explicit_module_mode(self, tmp_path):
        """Module mode always generates module_graph.mmd."""
        from pactkit.skills.visualize import visualize
        (tmp_path / 'mod_a').mkdir()
        (tmp_path / 'mod_a/pyproject.toml').write_text('[project]\nname="a"')
        (tmp_path / 'mod_a/core.py').write_text('x = 1\n')
        (tmp_path / 'mod_b').mkdir()
        (tmp_path / 'mod_b/pyproject.toml').write_text('[project]\nname="b"')
        (tmp_path / 'mod_b/util.py').write_text('y = 2\n')

        graphs_dir = tmp_path / 'docs/architecture/graphs'
        graphs_dir.mkdir(parents=True)
        result = visualize(target=str(tmp_path), mode='module')
        assert (graphs_dir / 'module_graph.mmd').exists()
        content = (graphs_dir / 'module_graph.mmd').read_text()
        assert 'mod_a' in content
        assert 'mod_b' in content
