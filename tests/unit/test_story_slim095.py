"""Tests for STORY-slim-095 — Fix focus call graph + report empty tab."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# --- AC1: Focus call graph non-empty output (R1) ---

class TestAC1FocusCallGraph:
    def test_build_call_graph_with_focus_dir(self, tmp_path):
        """Focus filter should match by file path prefix, not module name."""
        from pactkit.skills.visualize import _build_call_graph

        # Create source files
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'a.py').write_text('def hello():\n    world()\n')
        (src / 'b.py').write_text('def world():\n    pass\n')

        all_files = [src / 'a.py', src / 'b.py']
        # focus = str(src) — a directory path, not a module name
        dest, content = _build_call_graph(tmp_path, all_files, focus=str(src), entry=None)
        # Should have at least 1 node (not just "graph TD")
        lines = [l for l in content.strip().splitlines() if l.strip() and l.strip() != 'graph TD']
        assert len(lines) > 0, f"Focus call graph should not be empty, got: {content}"


# --- AC2: Focus mismatch diagnostic (R1) ---

class TestAC2FocusDiagnostic:
    def test_zero_match_includes_diagnostic(self, tmp_path):
        """When focus filters out everything, output should contain diagnostic."""
        from pactkit.skills.visualize import _build_call_graph

        src = tmp_path / 'src'
        src.mkdir()
        (src / 'a.py').write_text('def hello():\n    pass\n')

        all_files = [src / 'a.py']
        # focus = nonexistent path — nothing matches
        dest, content = _build_call_graph(tmp_path, all_files, focus='/nonexistent/path', entry=None)
        assert '0 functions' in content.lower() or 'no functions' in content.lower(), \
            f"Should have diagnostic for 0 matches, got: {content}"


# --- AC3: Empty Tab shows placeholder (R2) ---

class TestAC3EmptyTabPlaceholder:
    def test_empty_graph_shows_no_data_message(self, tmp_path):
        """loadGraph() should show placeholder when nodes.length === 0."""
        from pactkit.skills.report import generate

        graphs = tmp_path / 'docs' / 'architecture' / 'graphs'
        graphs.mkdir(parents=True)
        # One normal core graph, one empty core graph
        (graphs / 'code_graph.mmd').write_text('graph TD\n    A["hello"]\n    B["world"]\n    A --> B\n')
        (graphs / 'call_graph.mmd').write_text('graph TD\n')

        generate(target=str(tmp_path), all_mode=True)
        html = (graphs / 'report.html').read_text()
        # The JS should have "No data" or "no data" handling
        assert 'no data' in html.lower() or 'No data' in html


# --- AC4: Empty .mmd skipped (R3) ---

class TestAC4EmptyMmdSkipped:
    def test_empty_mmd_not_in_tabs(self, tmp_path):
        """Unified report should skip .mmd files with 0 nodes."""
        from pactkit.skills.report import generate

        graphs = tmp_path / 'docs' / 'architecture' / 'graphs'
        graphs.mkdir(parents=True)
        (graphs / 'code_graph.mmd').write_text('graph TD\n    A["hello"]\n    B["world"]\n    A --> B\n')
        # Empty core graph should be skipped
        (graphs / 'class_graph.mmd').write_text('graph TD\n')
        # Non-core graph should always be excluded (HOTFIX-slim-096)
        (graphs / 'focus_call_graph.mmd').write_text('graph TD\n    Z["z"]\n')

        generate(target=str(tmp_path), all_mode=True)
        html = (graphs / 'report.html').read_text()
        # Empty class_graph should NOT appear as a tab
        assert 'class_graph' not in html.lower().replace(' ', '_')
        # Non-core focus_call_graph should NOT appear
        assert 'focus_call_graph' not in html.lower().replace(' ', '_')
