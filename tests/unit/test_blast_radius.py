"""Tests for blast_radius() — STORY-slim-089 R1/R2."""
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _exec_visualize():
    from pactkit.prompts import VISUALIZE_SOURCE
    g = {}
    exec(VISUALIZE_SOURCE, g)
    return g


def _create_chain_project(tmp_path):
    """Create A→B→C→D dependency chain (A imports B, B imports C, C imports D)."""
    src = tmp_path / 'src'
    src.mkdir()
    (src / '__init__.py').write_text('', encoding='utf-8')

    (src / 'a.py').write_text(
        'from src.b import func_b\n'
        '\n'
        'def func_a():\n'
        '    return func_b()\n',
        encoding='utf-8'
    )
    (src / 'b.py').write_text(
        'from src.c import func_c\n'
        '\n'
        'def func_b():\n'
        '    return func_c()\n',
        encoding='utf-8'
    )
    (src / 'c.py').write_text(
        'from src.d import func_d\n'
        '\n'
        'def func_c():\n'
        '    return func_d()\n',
        encoding='utf-8'
    )
    (src / 'd.py').write_text(
        'def func_d():\n'
        '    return 42\n',
        encoding='utf-8'
    )
    return tmp_path


class TestBlastRadiusFileLevel:
    """AC1: Blast radius — single file (R1)."""

    def test_middle_file_both_directions(self, tmp_path):
        """Given A→B→C→D, blast_radius(target=B) should find A (importer) and C (importee)."""
        root = _create_chain_project(tmp_path)
        g = _exec_visualize()
        result = g['blast_radius'](str(root), target_file='src/b.py')
        data = json.loads(result)

        assert data['target'] == 'src/b.py'
        affected = set(data['affected_files'])
        assert 'src/a.py' in affected, "A imports B, should be in blast radius"
        assert 'src/c.py' in affected, "B imports C, should be in blast radius"
        assert data['total_count'] >= 2

    def test_leaf_file_only_importers(self, tmp_path):
        """Given A→B→C→D, blast_radius(target=D) should find C (only importer)."""
        root = _create_chain_project(tmp_path)
        g = _exec_visualize()
        result = g['blast_radius'](str(root), target_file='src/d.py')
        data = json.loads(result)

        affected = set(data['affected_files'])
        assert 'src/c.py' in affected
        assert 'src/d.py' not in affected, "Target itself should not be in affected list"


class TestBlastRadiusDepthLimit:
    """AC2: Blast radius — depth limit (R1)."""

    def test_depth_1_limits_hops(self, tmp_path):
        """Given A→B→C→D, blast_radius(target=B, depth=1) should find A and C but NOT D."""
        root = _create_chain_project(tmp_path)
        g = _exec_visualize()
        result = g['blast_radius'](str(root), target_file='src/b.py', depth=1)
        data = json.loads(result)

        affected = set(data['affected_files'])
        assert 'src/a.py' in affected
        assert 'src/c.py' in affected
        assert 'src/d.py' not in affected, "D is 2 hops from B, should be excluded at depth=1"

    def test_depth_0_unlimited(self, tmp_path):
        """depth=0 means unlimited — should find all transitively connected files."""
        root = _create_chain_project(tmp_path)
        g = _exec_visualize()
        result = g['blast_radius'](str(root), target_file='src/b.py', depth=0)
        data = json.loads(result)

        affected = set(data['affected_files'])
        # With unlimited depth, A, C, and D should all be reachable
        assert 'src/a.py' in affected
        assert 'src/c.py' in affected
        assert 'src/d.py' in affected


class TestBlastRadiusFunctionLevel:
    """AC3: Blast radius — function-level (R2)."""

    def test_function_blast_radius(self, tmp_path):
        """Given func_a→func_b→func_c, blast_radius(entry=func_b) finds func_a and func_c."""
        root = _create_chain_project(tmp_path)
        g = _exec_visualize()
        result = g['blast_radius'](str(root), entry='func_b')
        data = json.loads(result)

        assert data['entry'] == 'func_b'
        affected_funcs = set(data['affected_functions'])
        assert 'func_a' in affected_funcs or any('func_a' in f for f in affected_funcs)
        assert 'func_c' in affected_funcs or any('func_c' in f for f in affected_funcs)
        # affected_files should list unique files
        assert len(data['affected_files']) >= 1
