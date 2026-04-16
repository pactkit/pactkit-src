"""Tests for cyclomatic complexity — STORY-slim-089 R3/R4."""
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


class TestPythonComplexity:
    """AC4: Cyclomatic complexity — Python (R3)."""

    def test_simple_function(self, tmp_path):
        """A function with 3 if statements and 1 for loop should have complexity 5."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'example.py').write_text(
            'def complex_func(x, items):\n'
            '    if x > 0:\n'
            '        pass\n'
            '    if x < 10:\n'
            '        pass\n'
            '    if x == 5:\n'
            '        pass\n'
            '    for item in items:\n'
            '        pass\n',
            encoding='utf-8'
        )

        g = _exec_visualize()
        analyzer = g['PythonAnalyzer']()
        fr, ce, cm = analyzer.extract_functions_and_calls(src / 'example.py', include_complexity=True)

        assert 'complex_func' in cm
        assert cm['complex_func'] == 5, f"Expected 5 (1 base + 3 if + 1 for), got {cm['complex_func']}"

    def test_boolean_operators(self, tmp_path):
        """Boolean operators (and, or) count as decision points."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'boolops.py').write_text(
            'def check(a, b, c):\n'
            '    if a and b or c:\n'
            '        pass\n',
            encoding='utf-8'
        )

        g = _exec_visualize()
        analyzer = g['PythonAnalyzer']()
        fr, ce, cm = analyzer.extract_functions_and_calls(src / 'boolops.py', include_complexity=True)

        # 1 base + 1 if + 1 and + 1 or = 4
        assert cm['check'] == 4, f"Expected 4, got {cm['check']}"

    def test_exception_handling(self, tmp_path):
        """except clauses count as decision points."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'excepts.py').write_text(
            'def risky():\n'
            '    try:\n'
            '        pass\n'
            '    except ValueError:\n'
            '        pass\n'
            '    except KeyError:\n'
            '        pass\n',
            encoding='utf-8'
        )

        g = _exec_visualize()
        analyzer = g['PythonAnalyzer']()
        fr, ce, cm = analyzer.extract_functions_and_calls(src / 'excepts.py', include_complexity=True)

        # 1 base + 2 except = 3
        assert cm['risky'] == 3, f"Expected 3, got {cm['risky']}"

    def test_while_loop(self, tmp_path):
        """While loops count as decision points."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'loops.py').write_text(
            'def looper():\n'
            '    while True:\n'
            '        pass\n',
            encoding='utf-8'
        )

        g = _exec_visualize()
        analyzer = g['PythonAnalyzer']()
        fr, ce, cm = analyzer.extract_functions_and_calls(src / 'loops.py', include_complexity=True)

        # 1 base + 1 while = 2
        assert cm['looper'] == 2, f"Expected 2, got {cm['looper']}"


class TestBackwardCompatibility:
    """AC5: Backward compatibility — 2-tuple unpacking (R3)."""

    def test_default_returns_two_tuple(self, tmp_path):
        """Default call (no include_complexity) must still return 2-tuple."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'simple.py').write_text(
            'def foo():\n'
            '    pass\n',
            encoding='utf-8'
        )

        g = _exec_visualize()
        analyzer = g['PythonAnalyzer']()
        result = analyzer.extract_functions_and_calls(src / 'simple.py')

        # Must unpack as 2-tuple without error
        fr, ce = result
        assert isinstance(fr, dict)
        assert isinstance(ce, dict)

    def test_include_complexity_returns_three_tuple(self, tmp_path):
        """Explicit include_complexity=True must return 3-tuple."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'simple.py').write_text(
            'def foo():\n'
            '    pass\n',
            encoding='utf-8'
        )

        g = _exec_visualize()
        analyzer = g['PythonAnalyzer']()
        result = analyzer.extract_functions_and_calls(src / 'simple.py', include_complexity=True)

        fr, ce, cm = result
        assert isinstance(fr, dict)
        assert isinstance(ce, dict)
        assert isinstance(cm, dict)
        # Simple function: complexity = 1
        assert cm['foo'] == 1


class TestComplexityReport:
    """AC6: Complexity report subcommand (R4)."""

    def test_complexity_report_json(self, tmp_path):
        """complexity() with format=json returns sorted list of functions."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / '__init__.py').write_text('', encoding='utf-8')
        (src / 'funcs.py').write_text(
            'def simple():\n'
            '    pass\n'
            '\n'
            'def complex_one(x, y):\n'
            '    if x > 0:\n'
            '        if y > 0:\n'
            '            for i in range(10):\n'
            '                while True:\n'
            '                    pass\n',
            encoding='utf-8'
        )

        g = _exec_visualize()
        result = g['complexity'](str(tmp_path), fmt='json')
        data = json.loads(result)

        assert isinstance(data, list)
        # Should be sorted descending by complexity
        if len(data) >= 2:
            assert data[0]['complexity'] >= data[1]['complexity']

    def test_complexity_threshold_filter(self, tmp_path):
        """--threshold filters out low-complexity functions."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / '__init__.py').write_text('', encoding='utf-8')
        (src / 'funcs.py').write_text(
            'def simple():\n'
            '    pass\n'
            '\n'
            'def moderate(x):\n'
            '    if x > 0:\n'
            '        if x > 1:\n'
            '            if x > 2:\n'
            '                if x > 3:\n'
            '                    if x > 4:\n'
            '                        pass\n',
            encoding='utf-8'
        )

        g = _exec_visualize()
        result = g['complexity'](str(tmp_path), threshold=3, fmt='json')
        data = json.loads(result)

        # Only functions with complexity >= 3 should appear
        for entry in data:
            assert entry['complexity'] >= 3
