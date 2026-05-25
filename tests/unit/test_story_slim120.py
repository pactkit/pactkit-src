"""Tests for STORY-slim-120: Call graph coverage — test files, scripts, locality resolution.

AC1: Test file calls appear in call graph (R1)
AC2: File and class graphs unchanged — tests/ still excluded (R1)
AC3: Scripts directory scanned in call mode (R2)
AC4: Locality-based callee resolution (R3)
"""
import textwrap
from pathlib import Path

from pactkit.skills.visualize import (
    _build_call_graph,
    _resolve_callee,
    _build_suffix_index,
    SCAN_EXCLUDES,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write(tmp_path: Path, rel: str, src: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(src))
    return p


# ── AC1: Test file calls appear in call graph (R1) ────────────────────────────

class TestTestFilesInCallGraph:
    """R1: _build_call_graph must include test files when tests/ is not excluded."""

    def test_test_function_call_captured(self, tmp_path):
        """Calls made inside a test function appear as edges."""
        _write(tmp_path, "src/mymodule.py", """\
            def foo_func():
                pass
        """)
        _write(tmp_path, "tests/unit/test_foo.py", """\
            def test_something():
                foo_func()
        """)
        all_files = list((tmp_path / "src").rglob("*.py")) + list((tmp_path / "tests").rglob("*.py"))
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry=None)
        assert "test_something" in content
        assert "foo_func" in content

    def test_test_to_source_edge_present(self, tmp_path):
        """test_something --> foo_func edge appears in graph TD output."""
        _write(tmp_path, "src/mymodule.py", """\
            def foo_func():
                pass
        """)
        _write(tmp_path, "tests/unit/test_foo.py", """\
            def test_something():
                foo_func()
        """)
        all_files = list((tmp_path / "src").rglob("*.py")) + list((tmp_path / "tests").rglob("*.py"))
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry=None)
        assert "test_something --> foo_func" in content

    def test_tests_excluded_means_no_test_edges(self, tmp_path):
        """When tests/ is excluded from all_files, no test edges appear."""
        _write(tmp_path, "src/mymodule.py", """\
            def foo_func():
                pass
        """)
        _write(tmp_path, "tests/unit/test_foo.py", """\
            def test_something():
                foo_func()
        """)
        # Only src files — simulates old behavior
        all_files = list((tmp_path / "src").rglob("*.py"))
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry=None)
        assert "test_something" not in content


# ── AC2: File/class graph behavior unchanged — SCAN_EXCLUDES still has tests ──

class TestScanExcludesUnchanged:
    """R1: SCAN_EXCLUDES module constant still contains 'tests' for file/class modes."""

    def test_tests_still_in_scan_excludes(self):
        """'tests' remains in SCAN_EXCLUDES so file and class graphs exclude it."""
        assert 'tests' in SCAN_EXCLUDES

    def test_docs_still_in_scan_excludes(self):
        """'docs' remains in SCAN_EXCLUDES (sanity check — no unintended changes)."""
        assert 'docs' in SCAN_EXCLUDES


# ── AC3: Scripts directory scanned in call mode (R2) ─────────────────────────

class TestScriptsDirectoryInCallGraph:
    """R2: scripts/ functions and their calls appear in call graph when included."""

    def test_script_function_captured(self, tmp_path):
        """Functions in scripts/*.py appear as nodes when included in all_files."""
        _write(tmp_path, "src/utils.py", """\
            def helper():
                pass
        """)
        _write(tmp_path, "scripts/backfill.py", """\
            def run_backfill():
                helper()
        """)
        all_files = (
            list((tmp_path / "src").rglob("*.py")) +
            list((tmp_path / "scripts").rglob("*.py"))
        )
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry=None)
        assert "run_backfill" in content

    def test_script_to_src_edge_present(self, tmp_path):
        """run_backfill --> helper edge appears when scripts/ is included."""
        _write(tmp_path, "src/utils.py", """\
            def helper():
                pass
        """)
        _write(tmp_path, "scripts/backfill.py", """\
            def run_backfill():
                helper()
        """)
        all_files = (
            list((tmp_path / "src").rglob("*.py")) +
            list((tmp_path / "scripts").rglob("*.py"))
        )
        _, content = _build_call_graph(tmp_path, all_files, focus=None, entry=None)
        assert "run_backfill --> helper" in content


# ── AC4: Locality-based callee resolution (R3) ───────────────────────────────

class TestLocalityBasedResolution:
    """R3: _resolve_callee prefers candidates in the same file as the caller."""

    def test_same_file_candidate_preferred(self):
        """When two 'process' functions exist, the one in caller's file wins."""
        all_func_names = {'module_a.process', 'module_b.process'}
        suffix_index = _build_suffix_index(all_func_names)
        result = _resolve_callee('process', all_func_names, suffix_index, caller_file='module_a')
        assert result == 'module_a.process'

    def test_same_file_candidate_preferred_other_direction(self):
        """When caller is in module_b, module_b.process is preferred."""
        all_func_names = {'module_a.process', 'module_b.process'}
        suffix_index = _build_suffix_index(all_func_names)
        result = _resolve_callee('process', all_func_names, suffix_index, caller_file='module_b')
        assert result == 'module_b.process'

    def test_no_locality_match_falls_back(self):
        """When caller file doesn't match any candidate, returns first alphabetically."""
        all_func_names = {'module_a.process', 'module_b.process'}
        suffix_index = _build_suffix_index(all_func_names)
        result = _resolve_callee('process', all_func_names, suffix_index, caller_file='module_c')
        # Falls back — should return something (not None)
        assert result is not None
        assert result in all_func_names

    def test_single_candidate_unaffected(self):
        """Single candidate is returned regardless of caller_file."""
        all_func_names = {'module_a.process'}
        suffix_index = _build_suffix_index(all_func_names)
        result = _resolve_callee('process', all_func_names, suffix_index, caller_file='module_b')
        assert result == 'module_a.process'

    def test_no_caller_file_still_resolves(self):
        """caller_file=None (default) still resolves correctly."""
        all_func_names = {'module_a.process', 'module_b.process'}
        suffix_index = _build_suffix_index(all_func_names)
        result = _resolve_callee('process', all_func_names, suffix_index)
        assert result is not None

    def test_exact_match_bypasses_locality(self):
        """Exact match in all_func_names is returned immediately, no locality needed."""
        all_func_names = {'module_a.process', 'process'}
        suffix_index = _build_suffix_index(all_func_names)
        result = _resolve_callee('process', all_func_names, suffix_index, caller_file='module_b')
        assert result == 'process'

    def test_same_package_preferred_over_different_package(self):
        """pkg.module_a.process preferred over other.module_b.process when caller is in pkg."""
        all_func_names = {'pkg.module_a.process', 'other.module_b.process'}
        suffix_index = _build_suffix_index(all_func_names)
        result = _resolve_callee('process', all_func_names, suffix_index, caller_file='pkg.module_c')
        assert result == 'pkg.module_a.process'
