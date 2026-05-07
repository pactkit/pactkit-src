"""Tests for pactkit interface-summary CLI command (STORY-slim-113)."""
import textwrap

import pytest


@pytest.fixture
def sample_python_file(tmp_path):
    """Create a sample Python file with classes, functions, constants."""
    content = textwrap.dedent('''\
        """Module docstring for sample."""
        import os
        from pathlib import Path

        MAX_RETRIES = 3
        DEFAULT_TIMEOUT: int = 30
        _INTERNAL_CACHE = {}

        class BaseProcessor:
            """Base class for all processors."""

            def process(self, data: list[str]) -> dict:
                """Process incoming data and return results."""
                result = {}
                for item in data:
                    result[item] = len(item)
                return result

            def _internal_helper(self) -> None:
                """Private helper method."""
                pass

        class AdvancedProcessor(BaseProcessor):
            """Advanced processor with extra features."""

            def process(self, data: list[str]) -> dict:
                """Override with advanced logic."""
                base = super().process(data)
                base["extra"] = True
                return base

            def transform(self, input_data: str, mode: str = "default") -> str:
                """Transform input based on mode."""
                if mode == "upper":
                    return input_data.upper()
                return input_data

        def standalone_function(path: Path, recursive: bool = False) -> list[str]:
            """Find all files in path."""
            results = []
            if recursive:
                for root, dirs, files in os.walk(path):
                    results.extend(files)
            else:
                results = list(path.iterdir())
            return results

        def _private_function():
            """This is private."""
            pass
    ''')
    p = tmp_path / "sample.py"
    p.write_text(content)
    return p


@pytest.fixture
def empty_python_file(tmp_path):
    """Create an empty Python file."""
    p = tmp_path / "empty.py"
    p.write_text("")
    return p


@pytest.fixture
def syntax_error_file(tmp_path):
    """Create a file with syntax errors."""
    p = tmp_path / "broken.py"
    p.write_text("def foo(\n")
    return p


class TestGenerateSummary:
    """Test the core generate_summary function."""

    def test_extracts_classes_with_methods(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        assert "class BaseProcessor:" in output
        assert "class AdvancedProcessor(BaseProcessor):" in output

    def test_extracts_method_signatures(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        assert "def process(self, data: list[str]) -> dict:" in output
        assert "def transform(self, input_data: str, mode: str = \"default\") -> str:" in output

    def test_extracts_docstrings(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        assert "Base class for all processors." in output
        assert "Find all files in path." in output

    def test_extracts_top_level_functions(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        assert "def standalone_function(path: Path, recursive: bool = False) -> list[str]:" in output

    def test_extracts_constants(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        assert "MAX_RETRIES" in output
        assert "DEFAULT_TIMEOUT" in output

    def test_excludes_internal_constants(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        assert "_INTERNAL_CACHE" not in output

    def test_excludes_function_bodies(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        assert "for item in data:" not in output
        assert "result[item] = len(item)" not in output
        assert 'base["extra"] = True' not in output

    def test_output_significantly_shorter_than_source(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        source_lines = sample_python_file.read_text().count("\n")
        output_lines = output.count("\n")
        assert output_lines <= source_lines * 0.5

    def test_multiple_files(self, sample_python_file, empty_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file, empty_python_file])
        assert "sample.py" in output
        assert "empty.py" in output

    def test_empty_file_graceful(self, empty_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([empty_python_file])
        assert "empty.py" in output

    def test_syntax_error_graceful(self, syntax_error_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([syntax_error_file])
        assert "broken.py" in output
        assert "parse error" in output.lower() or "syntax" in output.lower()

    def test_nonexistent_file_graceful(self, tmp_path):
        from pactkit.skills.interface_summary import generate_summary

        fake = tmp_path / "nonexistent.py"
        output = generate_summary([fake])
        assert "not found" in output.lower() or "nonexistent.py" in output

    def test_includes_private_methods(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        # Private methods should be listed (with - prefix in class view)
        assert "_internal_helper" in output

    def test_file_header_format(self, sample_python_file):
        from pactkit.skills.interface_summary import generate_summary

        output = generate_summary([sample_python_file])
        assert "# sample.py — Interface Summary" in output


class TestCLIIntegration:
    """Test the CLI entry point."""

    def test_cli_runs_without_error(self, sample_python_file):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "pactkit", "interface-summary",
             str(sample_python_file)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Interface Summary" in result.stdout

    def test_cli_unsupported_extension(self, tmp_path):
        import subprocess
        import sys
        f = tmp_path / "test.rb"
        f.write_text("def hello; end")
        result = subprocess.run(
            [sys.executable, "-m", "pactkit", "interface-summary", str(f)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "unsupported" in result.stdout.lower() or "unavailable" in result.stdout.lower()
