"""Tests for STORY-slim-068: Fix 4 call chain断链 in static analysis pipeline."""
import ast
import textwrap


# ---------------------------------------------------------------------------
# AC1: dict.update merge does not overwrite
# ---------------------------------------------------------------------------
class TestAC1ExtendMerge:
    """When two files define the same function name, call_edges must be merged (extend), not replaced."""

    def test_same_name_callees_merged(self, tmp_path):
        """Two files with same function name 'foo': edges merged, not overwritten."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text(
            "def foo():\n    bar()\n"
        )
        (tmp_path / "src" / "b.py").write_text(
            "def foo():\n    baz()\n\ndef bar(): pass\n\ndef baz(): pass\n"
        )
        from pactkit.skills.visualize import _build_call_graph, PythonAnalyzer

        all_files = [tmp_path / "src" / "a.py", tmp_path / "src" / "b.py"]
        dest, content = _build_call_graph(tmp_path, all_files, focus=None, entry=None, analyzer=PythonAnalyzer())
        # Both 'bar' and 'baz' should appear as callees of 'foo' in the graph
        assert "bar" in content
        assert "baz" in content

    def test_same_name_no_edge_loss(self, tmp_path):
        """Regression: dict.update would lose file A's edges. Extend-merge keeps both."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text(
            "def process():\n    step_a()\n\ndef step_a(): pass\n"
        )
        (tmp_path / "src" / "b.py").write_text(
            "def process():\n    step_b()\n\ndef step_b(): pass\n"
        )
        from pactkit.skills.visualize import _build_call_graph, PythonAnalyzer

        all_files = [tmp_path / "src" / "a.py", tmp_path / "src" / "b.py"]
        dest, content = _build_call_graph(tmp_path, all_files, focus=None, entry="process", analyzer=PythonAnalyzer())
        # Entry-based BFS: both step_a and step_b should be reachable
        assert "step_a" in content
        assert "step_b" in content


# ---------------------------------------------------------------------------
# AC2: pactkit-plugin in default SCAN_EXCLUDES
# ---------------------------------------------------------------------------
class TestAC2ScanExcludes:
    """pactkit-plugin directory must be excluded from default scan."""

    def test_pactkit_plugin_in_excludes(self):
        from pactkit.skills.visualize import SCAN_EXCLUDES
        assert 'pactkit-plugin' in SCAN_EXCLUDES

    def test_plugin_files_not_scanned(self, tmp_path):
        """Files under pactkit-plugin/ should be excluded by _scan_files."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main(): pass\n")
        plugin_dir = tmp_path / "pactkit-plugin" / "scripts"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "dup.py").write_text("def main(): pass\n")

        from pactkit.skills.visualize import _scan_files
        all_files, _, _ = _scan_files(tmp_path)
        file_strs = [str(f) for f in all_files]
        assert any("src" in f for f in file_strs)
        assert not any("pactkit-plugin" in f for f in file_strs)


# ---------------------------------------------------------------------------
# AC3: Dispatch hint parsed
# ---------------------------------------------------------------------------
class TestAC3DispatchHint:
    """# pactkit-trace: dispatches_to comments should inject callee targets."""

    def test_dispatches_to_parsed(self):
        """Function with dispatch hint should include declared targets."""
        code = textwrap.dedent("""\
            def deploy(format):
                # pactkit-trace: dispatches_to ClassicDeployer.deploy, OpenCodeDeployer.deploy
                registry = get_registry()
                deployer = registry[format]()
                deployer.deploy()
        """)
        tree = ast.parse(code)
        func_node = tree.body[0]

        from pactkit.skills.visualize import _extract_calls
        callees = _extract_calls(func_node, current_class=None, source_text=code)
        assert "ClassicDeployer.deploy" in callees
        assert "OpenCodeDeployer.deploy" in callees

    def test_no_hint_no_extra_callees(self):
        """Function without dispatch hint should not inject extra callees."""
        code = textwrap.dedent("""\
            def simple():
                foo()
        """)
        tree = ast.parse(code)
        func_node = tree.body[0]

        from pactkit.skills.visualize import _extract_calls
        callees = _extract_calls(func_node, current_class=None, source_text=code)
        assert callees == ["foo"]

    def test_multiple_hints(self):
        """Multiple dispatch hint lines should all be parsed."""
        code = textwrap.dedent("""\
            def multi():
                # pactkit-trace: dispatches_to A.run
                # pactkit-trace: dispatches_to B.run, C.run
                pass
        """)
        tree = ast.parse(code)
        func_node = tree.body[0]

        from pactkit.skills.visualize import _extract_calls
        callees = _extract_calls(func_node, current_class=None, source_text=code)
        assert "A.run" in callees
        assert "B.run" in callees
        assert "C.run" in callees


# ---------------------------------------------------------------------------
# AC4: Inheritance override edges
# ---------------------------------------------------------------------------
class TestAC4InheritanceEdges:
    """Subclass method overrides should generate virtual edges from base to sub."""

    def test_override_edge_created(self, tmp_path):
        """Base.deploy -> Sub.deploy virtual edge when Sub overrides Base."""
        code = textwrap.dedent("""\
            class Base:
                def deploy(self): pass

            class Sub(Base):
                def deploy(self): pass
        """)
        src_file = tmp_path / "demo.py"
        src_file.write_text(code)

        from pactkit.skills.visualize import PythonAnalyzer
        analyzer = PythonAnalyzer()
        func_reg, call_edges = analyzer.extract_functions_and_calls(src_file)

        # Virtual edge: Base.deploy -> Sub.deploy
        assert "Sub.deploy" in call_edges.get("Base.deploy", [])

    def test_no_false_inheritance_edge(self, tmp_path):
        """Methods that don't match base class should not get virtual edges."""
        code = textwrap.dedent("""\
            class Base:
                def deploy(self): pass

            class Sub(Base):
                def other_method(self): pass
        """)
        src_file = tmp_path / "demo.py"
        src_file.write_text(code)

        from pactkit.skills.visualize import PythonAnalyzer
        analyzer = PythonAnalyzer()
        func_reg, call_edges = analyzer.extract_functions_and_calls(src_file)

        # No false edge for non-matching methods
        assert "Sub.other_method" not in call_edges.get("Base.deploy", [])

    def test_multi_level_inheritance(self, tmp_path):
        """Multi-level inheritance: GrandChild overrides Base method."""
        code = textwrap.dedent("""\
            class Base:
                def run(self): pass

            class Mid(Base):
                def run(self): pass

            class Child(Mid):
                def run(self): pass
        """)
        src_file = tmp_path / "demo.py"
        src_file.write_text(code)

        from pactkit.skills.visualize import PythonAnalyzer
        analyzer = PythonAnalyzer()
        func_reg, call_edges = analyzer.extract_functions_and_calls(src_file)

        # Direct parent edges
        assert "Mid.run" in call_edges.get("Base.run", [])
        assert "Child.run" in call_edges.get("Mid.run", [])


# ---------------------------------------------------------------------------
# AC5: Stub edges injected from config
# ---------------------------------------------------------------------------
class TestAC5StubEdges:
    """stub_edges from pactkit.yaml should be injected into call graph."""

    def test_stub_edges_injected(self, tmp_path):
        """Configured stub_edges appear in call graph output."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            "def deploy(): pass\n"
        )
        # Create pactkit.yaml with stub_edges
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "pactkit.yaml").write_text(
            "visualize:\n  stub_edges:\n    - 'deploy -> pactkit_opencode.deployer.deploy'\n"
        )

        from pactkit.skills.visualize import _build_call_graph, PythonAnalyzer
        all_files = [tmp_path / "src" / "main.py"]
        dest, content = _build_call_graph(tmp_path, all_files, focus=None, entry=None, analyzer=PythonAnalyzer())
        assert "pactkit_opencode" in content

    def test_no_stub_edges_no_crash(self, tmp_path):
        """Without stub_edges config, call graph builds normally."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            "def deploy():\n    helper()\n\ndef helper(): pass\n"
        )

        from pactkit.skills.visualize import _build_call_graph, PythonAnalyzer
        all_files = [tmp_path / "src" / "main.py"]
        dest, content = _build_call_graph(tmp_path, all_files, focus=None, entry=None, analyzer=PythonAnalyzer())
        assert "deploy" in content
        assert "helper" in content
