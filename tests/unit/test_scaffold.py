"""Tests for scaffold.py — BUG-033: create_spec must pass spec-lint."""
import os

from pactkit.skills.scaffold import create_spec
from pactkit.skills.spec_linter import validate_spec


class TestCreateSpec:
    """BUG-033: create_spec() output must pass spec_linter validation."""

    def test_generated_spec_passes_lint(self, tmp_path):
        """AC1: Generated Spec passes lint with zero errors."""
        # Setup: create docs/specs directory
        specs_dir = tmp_path / "docs" / "specs"
        specs_dir.mkdir(parents=True)

        # Change to temp directory so create_spec writes there
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # When: generate a spec
            result = create_spec("STORY-999", "Test Title")
            assert "✅" in result

            # Then: spec file exists and passes lint
            spec_path = specs_dir / "STORY-999.md"
            assert spec_path.exists()

            lint_result = validate_spec(str(spec_path))
            assert lint_result.passed, f"Spec lint failed: {[e.message for e in lint_result.errors]}"
        finally:
            os.chdir(old_cwd)

    def test_metadata_table_format(self, tmp_path):
        """AC2: Generated Spec contains | Field | Value | metadata table."""
        specs_dir = tmp_path / "docs" / "specs"
        specs_dir.mkdir(parents=True)

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            create_spec("STORY-999", "Test Title")
            content = (specs_dir / "STORY-999.md").read_text()

            # Must have Field | Value header
            assert "| Field | Value |" in content
            # Must have required fields
            assert "| ID |" in content
            assert "| Status |" in content
            assert "| Priority |" in content
            assert "| Release |" in content
        finally:
            os.chdir(old_cwd)

    def test_requirements_have_subsections(self, tmp_path):
        """AC3: Requirements section has ### R1: subsection."""
        specs_dir = tmp_path / "docs" / "specs"
        specs_dir.mkdir(parents=True)

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            create_spec("STORY-999", "Test Title")
            content = (specs_dir / "STORY-999.md").read_text()

            # Must have R1 subsection
            assert "### R1:" in content
            # Must have RFC 2119 keyword
            assert "MUST" in content or "SHOULD" in content or "MAY" in content
        finally:
            os.chdir(old_cwd)

    def test_release_not_tbd(self, tmp_path):
        """R3: Release field must not be literal TBD."""
        specs_dir = tmp_path / "docs" / "specs"
        specs_dir.mkdir(parents=True)

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            create_spec("STORY-999", "Test Title")
            content = (specs_dir / "STORY-999.md").read_text()

            # Release row should not have TBD as value
            # (placeholder like {VERSION} is OK, literal TBD is not)
            lines = content.split('\n')
            for line in lines:
                if '| Release |' in line:
                    # Extract value after Release |
                    parts = line.split('|')
                    if len(parts) >= 3:
                        release_val = parts[2].strip()
                        assert release_val.upper() != "TBD", f"Release should not be TBD, got: {release_val}"
        finally:
            os.chdir(old_cwd)
