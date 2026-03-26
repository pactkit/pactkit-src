"""Tests for STORY-slim-055: File I/O safety."""
import inspect


# ---------------------------------------------------------------------------
# R1: visualize.py .mmd output uses atomic write (tmp+rename)
# ---------------------------------------------------------------------------
class TestR1VisualizeAtomicWrite:

    def test_mmd_write_uses_atomic_pattern(self):
        """Source code must use tmp+rename pattern, not bare write_text for .mmd output."""
        import pactkit.skills.visualize as vis
        source = inspect.getsource(vis)
        # The write sites at visualize(), _visualize_unified(), export_focus_graphs()
        # should use os.replace pattern, not bare dest.write_text for .mmd output
        # Check that atomic write helper or inline pattern exists
        assert '_atomic_mmd_write' in source or 'os.replace' in source

    def test_visualize_writes_valid_mmd(self, tmp_path):
        """visualize() output .mmd file must contain valid content after atomic write."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("import os\ndef hello(): pass", encoding="utf-8")

        from pactkit.skills.visualize import _scan_files, _build_file_graph
        all_files, module_index, file_to_node = _scan_files(src)
        dest, content = _build_file_graph(src, all_files, module_index, file_to_node, focus=None)
        assert dest is not None
        assert content.startswith("graph TD")


# ---------------------------------------------------------------------------
# R2: deployer.py read_text encoding='utf-8'
# ---------------------------------------------------------------------------
class TestR2DeployerEncoding:

    def test_no_bare_read_text_in_deployer(self):
        """deployer.py must not have any read_text() without encoding parameter."""
        from pactkit.generators import deployer
        source = inspect.getsource(deployer)
        # Find all lines with .read_text() (no args = platform default encoding)
        lines_with_bare_read = [
            l.strip() for l in source.split('\n')
            if '.read_text()' in l and not l.strip().startswith('#')
        ]
        assert len(lines_with_bare_read) == 0, \
            f"Found read_text() without encoding: {lines_with_bare_read}"


# ---------------------------------------------------------------------------
# R3: visualize.py MAX_FILE_BYTES guard
# ---------------------------------------------------------------------------
class TestR3MaxFileBytesGuard:

    def test_max_file_bytes_constant_exists(self):
        """MAX_FILE_BYTES must be defined alongside MAX_SCAN_FILES."""
        from pactkit.skills.visualize import MAX_FILE_BYTES
        assert MAX_FILE_BYTES == 1_048_576

    def test_large_file_skipped_in_extract_imports(self, tmp_path):
        """Files larger than MAX_FILE_BYTES should be skipped by extract_imports."""
        from pactkit.skills.visualize import PythonAnalyzer, MAX_FILE_BYTES

        big_file = tmp_path / "huge.py"
        # Create a file slightly over the limit
        big_file.write_text("import os\n" * (MAX_FILE_BYTES // 10 + 1), encoding="utf-8")

        analyzer = PythonAnalyzer()
        result = analyzer.extract_imports(big_file)
        assert result == [], "Large file should return empty list (skipped)"

    def test_large_file_skipped_in_extract_functions(self, tmp_path):
        """Files larger than MAX_FILE_BYTES should be skipped by extract_functions_and_calls."""
        from pactkit.skills.visualize import PythonAnalyzer, MAX_FILE_BYTES

        big_file = tmp_path / "huge.py"
        big_file.write_text("def f(): pass\n" * (MAX_FILE_BYTES // 14 + 1), encoding="utf-8")

        analyzer = PythonAnalyzer()
        fr, ce = analyzer.extract_functions_and_calls(big_file)
        assert fr == {} and ce == {}, "Large file should return empty results"

    def test_normal_file_not_skipped(self, tmp_path):
        """Normal-sized files should be processed normally."""
        from pactkit.skills.visualize import PythonAnalyzer

        normal_file = tmp_path / "small.py"
        normal_file.write_text("import os\nimport sys\n", encoding="utf-8")

        analyzer = PythonAnalyzer()
        result = analyzer.extract_imports(normal_file)
        assert 'os' in result
        assert 'sys' in result
