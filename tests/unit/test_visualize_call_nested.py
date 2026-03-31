"""STORY-slim-067: Call graph nested subgraph with fan-in/fan-out.

Tests for depth-based Mermaid subgraph rendering and fan-in/fan-out annotations.
"""

import textwrap

from pactkit.skills.visualize import (
    _build_call_graph,
    _build_reverse_graph,
    _scan_call_edges,
    nl,
)


def _write_py(tmp_path, filename, code):
    """Write a Python file to tmp_path and return the Path."""
    p = tmp_path / filename
    p.write_text(textwrap.dedent(code))
    return p


# ===========================================================================
# AC1: Nested subgraph output (R1, R2)
# ===========================================================================


class TestAC1NestedSubgraph:
    """AC1: --entry produces depth-based subgraphs."""

    def test_linear_chain_has_depth_subgraphs(self, tmp_path):
        """main → process → helper → util produces Depth 0-3 subgraphs."""
        _write_py(tmp_path, "app.py", """\
            def util():
                pass

            def helper():
                util()

            def process():
                helper()

            def main():
                process()
        """)
        all_files = [tmp_path / "app.py"]
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry="main")
        assert 'subgraph "Depth 0"' in content
        assert 'subgraph "Depth 1"' in content
        assert 'subgraph "Depth 2"' in content
        assert 'subgraph "Depth 3"' in content

    def test_entry_at_depth_zero(self, tmp_path):
        """Entry function is in Depth 0 subgraph."""
        _write_py(tmp_path, "app.py", """\
            def child():
                pass

            def parent():
                child()
        """)
        all_files = [tmp_path / "app.py"]
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry="parent")
        # parent should be in Depth 0 block
        lines = content.split(nl())
        depth0_start = None
        depth0_end = None
        for i, line in enumerate(lines):
            if 'subgraph "Depth 0"' in line:
                depth0_start = i
            if depth0_start is not None and depth0_end is None and line.strip() == "end":
                depth0_end = i
                break
        assert depth0_start is not None, "Depth 0 subgraph not found"
        block = lines[depth0_start:depth0_end]
        assert any("parent" in ln for ln in block), "parent not in Depth 0"


# ===========================================================================
# AC2: Fan-in/fan-out labels (R3)
# ===========================================================================


class TestAC2FanInFanOut:
    """AC2: Node labels include ↑N ↓M annotations."""

    def test_fan_in_count(self, tmp_path):
        """helper called by main AND process → fan-in=2."""
        _write_py(tmp_path, "app.py", """\
            def helper():
                pass

            def process():
                helper()

            def main():
                process()
                helper()
        """)
        all_files = [tmp_path / "app.py"]
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry="main")
        # helper has fan-in=2 (called by main and process)
        assert "↑2" in content

    def test_fan_out_count(self, tmp_path):
        """main calls process AND helper → fan-out=2."""
        _write_py(tmp_path, "app.py", """\
            def helper():
                pass

            def process():
                pass

            def main():
                process()
                helper()
        """)
        all_files = [tmp_path / "app.py"]
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry="main")
        # main has fan-out=2 (calls process and helper)
        assert "↓2" in content

    def test_leaf_node_zero_fan_out(self, tmp_path):
        """Leaf function has fan-out=0."""
        _write_py(tmp_path, "app.py", """\
            def leaf():
                pass

            def root():
                leaf()
        """)
        all_files = [tmp_path / "app.py"]
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry="root")
        # leaf should have ↓0
        assert "↓0" in content


# ===========================================================================
# AC3: Full graph unchanged (R5)
# ===========================================================================


class TestAC3FullGraphUnchanged:
    """AC3: No --entry → flat graph TD, no subgraphs."""

    def test_no_entry_no_subgraph(self, tmp_path):
        """Without --entry, output has no subgraph keyword."""
        _write_py(tmp_path, "app.py", """\
            def helper():
                pass

            def main():
                helper()
        """)
        all_files = [tmp_path / "app.py"]
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry=None)
        assert "subgraph" not in content
        assert "graph TD" in content


# ===========================================================================
# AC4: Reverse graph nested (R4)
# ===========================================================================


class TestAC4ReverseNested:
    """AC4: Reverse BFS also uses depth-based subgraphs."""

    def test_reverse_has_depth_subgraphs(self, tmp_path):
        """a → b → c: reverse from c produces Depth 0=c, 1=b, 2=a."""
        _write_py(tmp_path, "app.py", """\
            def c():
                pass

            def b():
                c()

            def a():
                b()
        """)
        all_files = [tmp_path / "app.py"]
        func_registry, call_edges = _scan_call_edges(tmp_path, all_files)
        visited, reverse_edges = _build_reverse_graph(func_registry, call_edges, "c")

        # We need to test the rendering — import the helper that will be created
        from pactkit.skills.visualize import _render_nested_call_graph

        content = _render_nested_call_graph(
            visited, reverse_edges, entry="c", call_edges=call_edges,
            func_registry=func_registry, reverse=True,
        )
        assert 'subgraph "Depth 0"' in content
        assert 'subgraph "Depth 1"' in content
        assert 'subgraph "Depth 2"' in content


# ===========================================================================
# AC5: Cycle annotation (R6)
# ===========================================================================


class TestAC5CycleAnnotation:
    """AC5: Circular calls get ↻ label with dotted arrow."""

    def test_cycle_edge_has_recycle_marker(self, tmp_path):
        """a → b → a cycle: edge b→a uses -.-> and ↻."""
        _write_py(tmp_path, "app.py", """\
            def b():
                a()

            def a():
                b()
        """)
        all_files = [tmp_path / "app.py"]
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry="a")
        assert "↻" in content
        assert "-.->" in content
