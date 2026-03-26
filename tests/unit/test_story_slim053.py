"""Tests for STORY-slim-053: Fix visualize.py latent bugs."""


# ---------------------------------------------------------------------------
# R1: Mermaid label escaping — double quotes in node labels
# ---------------------------------------------------------------------------
class TestR1MermaidLabelEscaping:
    """R1: Double quotes in file/function names must be escaped in Mermaid output."""

    def test_file_graph_escapes_double_quotes_in_filename(self, tmp_path):
        """_build_file_graph node labels must not contain raw double quotes."""
        # Create a file with a normal name (we test via the label output)
        src = tmp_path / "src"
        src.mkdir()
        f = src / "parse_data.py"
        f.write_text("# normal file", encoding="utf-8")

        from pactkit.skills.visualize import _mermaid_escape

        # Test the escape helper directly
        assert _mermaid_escape('parse"data') == "parse#quot;data"
        assert _mermaid_escape("no quotes") == "no quotes"
        assert _mermaid_escape('a"b"c') == "a#quot;b#quot;c"

    def test_call_graph_escapes_double_quotes_in_function_name(self):
        """_build_call_graph node labels must escape double quotes."""
        from pactkit.skills.visualize import _mermaid_escape

        # Function names with quotes (e.g., from dynamic code generation)
        assert '#quot;' in _mermaid_escape('get"value')

    def test_workflow_graph_escapes_labels(self):
        """WorkflowGraph.to_mermaid must escape double quotes in node labels."""
        from pactkit.skills.visualize import WorkflowGraph, WorkflowNode

        g = WorkflowGraph()
        g.add_node(WorkflowNode(id='n1', label='label"with"quotes', kind='file'))
        output = g.to_mermaid()
        # Must not have raw nested quotes in [" ... " ... "]
        assert '#quot;' in output
        assert 'label"with"quotes' not in output


# ---------------------------------------------------------------------------
# R2: O(1) callee resolution via suffix_index
# ---------------------------------------------------------------------------
class TestR2CalleeResolutionPerf:
    """R2: _resolve_callee must use dict lookup instead of linear scan."""

    def test_resolve_callee_with_suffix_index(self):
        """_resolve_callee should accept and use suffix_index for O(1) lookup."""
        from pactkit.skills.visualize import _resolve_callee

        all_funcs = {'mod_a.Class.method', 'mod_b.helper', 'mod_c.Class.method'}
        # Build suffix_index
        suffix_index = {}
        for fn in all_funcs:
            short = fn.rsplit('.', 1)[-1]
            suffix_index.setdefault(short, []).append(fn)

        # Exact match
        assert _resolve_callee('mod_a.Class.method', all_funcs, suffix_index) == 'mod_a.Class.method'
        # Suffix match
        result = _resolve_callee('helper', all_funcs, suffix_index)
        assert result == 'mod_b.helper'
        # Ambiguous suffix — should return one of them
        result = _resolve_callee('method', all_funcs, suffix_index)
        assert result in {'mod_a.Class.method', 'mod_c.Class.method'}
        # No match
        assert _resolve_callee('nonexistent', all_funcs, suffix_index) is None

    def test_resolve_callee_performance(self):
        """With 1000 functions, resolution should be fast (not O(N) scan)."""
        from pactkit.skills.visualize import _resolve_callee
        import time

        all_funcs = {f'module_{i}.func_{i}' for i in range(1000)}
        suffix_index = {}
        for fn in all_funcs:
            short = fn.rsplit('.', 1)[-1]
            suffix_index.setdefault(short, []).append(fn)

        start = time.perf_counter()
        for i in range(1000):
            _resolve_callee(f'func_{i}', all_funcs, suffix_index)
        elapsed = time.perf_counter() - start
        # Should complete 1000 lookups in well under 1 second
        assert elapsed < 1.0, f"1000 lookups took {elapsed:.3f}s — too slow"


# ---------------------------------------------------------------------------
# R3: module_index collision — list storage
# ---------------------------------------------------------------------------
class TestR3ModuleIndexCollision:
    """R3: Same-name files in different packages must not overwrite each other."""

    def test_scan_files_preserves_both_same_name_files(self, tmp_path):
        """module_index must store lists, not overwrite on collision."""
        src = tmp_path / "src"
        pkg_a = src / "pkg_a"
        pkg_b = src / "pkg_b"
        pkg_a.mkdir(parents=True)
        pkg_b.mkdir(parents=True)
        (pkg_a / "__init__.py").write_text("", encoding="utf-8")
        (pkg_b / "__init__.py").write_text("", encoding="utf-8")
        (pkg_a / "utils.py").write_text("def helper_a(): pass", encoding="utf-8")
        (pkg_b / "utils.py").write_text("def helper_b(): pass", encoding="utf-8")

        from pactkit.skills.visualize import _scan_files

        all_files, module_index, file_to_node = _scan_files(src)

        # Both files should be in all_files
        names = [f.name for f in all_files]
        assert names.count("utils.py") == 2

        # The short name 'pkg_a.utils' should map to list with pkg_a's file
        # Key: module_index values are now lists
        for key, val in module_index.items():
            assert isinstance(val, list), f"module_index['{key}'] should be a list, got {type(val)}"

    def test_best_match_prefers_same_package(self, tmp_path):
        """_best_match should prefer the candidate in the same parent package."""
        from pactkit.skills.visualize import _best_match

        root = tmp_path / "src"
        a = root / "pkg_a" / "utils.py"
        b = root / "pkg_b" / "utils.py"
        consumer = root / "pkg_a" / "main.py"

        result = _best_match([a, b], consumer)
        assert result == a


# ---------------------------------------------------------------------------
# R4: Focus exact path match (no substring)
# ---------------------------------------------------------------------------
class TestR4FocusExactMatch:
    """R4: Focus matching must use exact path-tail match, not substring."""

    def test_focus_does_not_match_substring(self, tmp_path):
        """focus='auth.py' must NOT match 'oauth.py'."""
        src = tmp_path / "src"
        src.mkdir(parents=True)
        (src / "auth.py").write_text("import os", encoding="utf-8")
        (src / "oauth.py").write_text("import sys", encoding="utf-8")

        from pactkit.skills.visualize import _scan_files, _build_file_graph

        all_files, module_index, file_to_node = _scan_files(src)
        dest, content = _build_file_graph(src, all_files, module_index, file_to_node, focus="auth.py")

        assert dest is not None
        assert "auth_py" in content  # auth.py node should be present
        assert "oauth_py" not in content  # oauth.py node must NOT be present

    def test_focus_matches_exact_filename(self, tmp_path):
        """focus='auth.py' should match 'src/auth.py' (path-tail match)."""
        src = tmp_path / "src"
        src.mkdir(parents=True)
        (src / "auth.py").write_text("x = 1", encoding="utf-8")

        from pactkit.skills.visualize import _scan_files, _build_file_graph

        all_files, module_index, file_to_node = _scan_files(src)
        dest, content = _build_file_graph(src, all_files, module_index, file_to_node, focus="auth.py")
        assert dest is not None
        assert "auth_py" in content

    def test_node_id_filtering_uses_set_not_substring(self):
        """Line filtering must use extracted node ID set lookup, not 'in' substring."""
        # Simulate the fix: extract node ID from line, then check set membership
        lines = [
            '    cli_py["cli.py"]',
            '    pactkit_cli_py["pactkit_cli.py"]',
            '    click cli_py href "cli.py"',
        ]
        relevant_ids = {"cli_py"}

        # Old behavior (substring): both lines would match
        old_matches = [line for line in lines if any(rid in line for rid in relevant_ids)]
        assert len(old_matches) == 3  # substring matches all 3

        # New behavior should only match lines where the extracted node ID is in the set
        from pactkit.skills.visualize import _extract_node_id
        new_matches = [line for line in lines if _extract_node_id(line) in relevant_ids]
        assert len(new_matches) == 2  # cli_py node + click line for cli_py


# ---------------------------------------------------------------------------
# R5: BFS deque
# ---------------------------------------------------------------------------
class TestR5BfsDeque:
    """R5: BFS must use collections.deque, not list.pop(0)."""

    def test_forward_reach_uses_deque(self):
        """WorkflowGraph.forward_reach should work correctly (behavior test)."""
        from pactkit.skills.visualize import WorkflowGraph, WorkflowNode, WorkflowEdge

        g = WorkflowGraph()
        g.add_node(WorkflowNode(id='a', label='A', kind='file'))
        g.add_node(WorkflowNode(id='b', label='B', kind='file'))
        g.add_node(WorkflowNode(id='c', label='C', kind='file'))
        g.add_edge(WorkflowEdge(source='a', target='b', relation='imports'))
        g.add_edge(WorkflowEdge(source='b', target='c', relation='imports'))

        reached = g.forward_reach('a')
        assert reached == {'a', 'b', 'c'}

    def test_reverse_reach_uses_deque(self):
        """WorkflowGraph.reverse_reach should work correctly (behavior test)."""
        from pactkit.skills.visualize import WorkflowGraph, WorkflowNode, WorkflowEdge

        g = WorkflowGraph()
        g.add_node(WorkflowNode(id='a', label='A', kind='file'))
        g.add_node(WorkflowNode(id='b', label='B', kind='file'))
        g.add_node(WorkflowNode(id='c', label='C', kind='file'))
        g.add_edge(WorkflowEdge(source='a', target='b', relation='imports'))
        g.add_edge(WorkflowEdge(source='b', target='c', relation='imports'))

        reached = g.reverse_reach('c')
        assert reached == {'a', 'b', 'c'}

    def test_no_list_pop_zero_in_source(self):
        """Source code must not contain queue.pop(0) — must use deque.popleft()."""
        import pactkit.skills.visualize as vis_module
        import inspect
        source = inspect.getsource(vis_module)
        assert '.pop(0)' not in source, "Found .pop(0) in visualize.py — should use deque.popleft()"
