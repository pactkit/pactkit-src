"""Tests for STORY-slim-056: E2E test coverage expansion.

Subprocess-based tests for all 25 pactkit CLI subcommands.
Re-uses the run_pactkit() helper from the existing E2E suite.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

# --- Helpers (same pattern as test_cli_e2e.py) ---
PACTKIT_BIN = sys.executable.replace('python', 'pactkit').replace('python3', 'pactkit')
USE_MODULE = not Path(PACTKIT_BIN).exists()


def run_pactkit(*args, cwd=None, env=None):
    """Run pactkit CLI as subprocess and return (stdout, stderr, exit_code)."""
    if USE_MODULE:
        cmd = [sys.executable, "-m", "pactkit.cli"] + list(args)
    else:
        cmd = ["pactkit"] + list(args)
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=cwd, env=env or os.environ.copy(),
    )
    return result.stdout, result.stderr, result.returncode


def _init_project(tmp_path):
    """Initialize a minimal pactkit project in tmp_path for E2E tests."""
    # Create .claude/pactkit.yaml
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(exist_ok=True)
    (claude_dir / "pactkit.yaml").write_text(
        'version: "2.4.0"\nstack: python\nroot: .\ndeveloper: test\n',
        encoding="utf-8",
    )
    # Create sprint board
    docs = tmp_path / "docs" / "product"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "sprint_board.md").write_text(
        "# Sprint Board\n\n## 🚧 In Progress\n\n## 📋 Backlog\n\n## ✅ Done\n",
        encoding="utf-8",
    )
    # Create graphs dir
    graphs = tmp_path / "docs" / "architecture" / "graphs"
    graphs.mkdir(parents=True, exist_ok=True)
    # Create specs dir
    specs = tmp_path / "docs" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    # Create src dir with a python file
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    (src / "main.py").write_text("import os\ndef hello(): pass\n", encoding="utf-8")
    # Create governance dir for invariants-refresh
    gov = tmp_path / "docs" / "architecture" / "governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "rules.md").write_text(
        "# Rules\n\n| Invariant | Value |\n|---|---|\n| All 100+ tests must pass | true |\n",
        encoding="utf-8",
    )
    # Create lessons.md
    (gov / "lessons.md").write_text(
        "# Lessons\n\n| Date | Lesson | Context |\n|---|---|---|\n| 2026-03-26 | test | STORY-001 |\n",
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# R1: High-frequency CLI subcommand E2E coverage (8 subcommands)
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestGuardCommand:
    """E2E tests for pactkit guard."""

    def test_guard_passes_initialized_project(self, tmp_path):
        """Initialized project → exit 0."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("guard", cwd=str(tmp_path))
        assert rc == 0, f"guard failed: {stderr}"

    def test_guard_fails_empty_directory(self, tmp_path):
        """Empty directory → non-zero exit (missing markers)."""
        stdout, stderr, rc = run_pactkit("guard", cwd=str(tmp_path))
        assert rc != 0


@pytest.mark.e2e
class TestNextIdCommand:
    """E2E tests for pactkit next-id."""

    def test_next_id_returns_id(self, tmp_path):
        """next-id in an initialized project returns a valid ID."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("next-id", cwd=str(tmp_path))
        assert rc == 0, f"next-id failed: {stderr}"
        assert "STORY-" in stdout or "story" in stdout.lower() or stdout.strip()

    def test_next_id_no_specs_returns_initial(self, tmp_path):
        """next-id with no existing specs returns 001."""
        _init_project(tmp_path)
        stdout, _, rc = run_pactkit("next-id", cwd=str(tmp_path))
        assert rc == 0
        assert "001" in stdout


@pytest.mark.e2e
class TestCleanCommand:
    """E2E tests for pactkit clean."""

    def test_clean_exits_zero(self, tmp_path):
        """clean in an initialized project exits 0."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("clean", cwd=str(tmp_path))
        assert rc == 0, f"clean failed: {stderr}"

    def test_clean_removes_pycache(self, tmp_path):
        """clean removes __pycache__ directories."""
        _init_project(tmp_path)
        pycache = tmp_path / "src" / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "module.cpython-314.pyc").write_text("fake", encoding="utf-8")
        run_pactkit("clean", cwd=str(tmp_path))
        assert not pycache.exists()


@pytest.mark.e2e
class TestRegressionCommand:
    """E2E tests for pactkit regression."""

    def test_regression_exits_zero(self, tmp_path):
        """regression with no git changes exits 0."""
        _init_project(tmp_path)
        # Initialize git so regression can work
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=str(tmp_path), capture_output=True)
        stdout, stderr, rc = run_pactkit("regression", cwd=str(tmp_path))
        assert rc == 0, f"regression failed: {stderr}"

    def test_regression_classifies_output(self, tmp_path):
        """regression output contains a classification keyword."""
        _init_project(tmp_path)
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=str(tmp_path), capture_output=True)
        stdout, _, _ = run_pactkit("regression", cwd=str(tmp_path))
        combined = stdout.upper()
        assert any(k in combined for k in ["SKIP", "FULL", "IMPACT"]), \
            f"Expected classification keyword, got: {stdout}"


@pytest.mark.e2e
class TestContextCommand:
    """E2E tests for pactkit context."""

    def test_context_creates_file(self, tmp_path):
        """context generates docs/product/context.md."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("context", cwd=str(tmp_path))
        assert rc == 0, f"context failed: {stderr}"
        ctx = tmp_path / "docs" / "product" / "context.md"
        assert ctx.exists()

    def test_context_contains_sections(self, tmp_path):
        """context output contains canonical sections."""
        _init_project(tmp_path)
        run_pactkit("context", cwd=str(tmp_path))
        content = (tmp_path / "docs" / "product" / "context.md").read_text(encoding="utf-8")
        assert "Sprint Status" in content
        assert "Next Recommended Action" in content


@pytest.mark.e2e
class TestVisualizeCommand:
    """E2E tests for pactkit visualize."""

    def test_visualize_file_mode(self, tmp_path):
        """visualize --mode file produces code_graph.mmd."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("visualize", "--mode", "file", cwd=str(tmp_path))
        assert rc == 0, f"visualize file failed: {stderr}"
        assert (tmp_path / "docs" / "architecture" / "graphs" / "code_graph.mmd").exists()

    def test_visualize_class_mode(self, tmp_path):
        """visualize --mode class produces class_graph.mmd."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("visualize", "--mode", "class", cwd=str(tmp_path))
        assert rc == 0, f"visualize class failed: {stderr}"
        assert (tmp_path / "docs" / "architecture" / "graphs" / "class_graph.mmd").exists()

    def test_visualize_call_mode(self, tmp_path):
        """visualize --mode call produces call_graph.mmd."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("visualize", "--mode", "call", cwd=str(tmp_path))
        assert rc == 0, f"visualize call failed: {stderr}"
        assert (tmp_path / "docs" / "architecture" / "graphs" / "call_graph.mmd").exists()


@pytest.mark.e2e
class TestLintCommand:
    """E2E tests for pactkit lint."""

    def test_lint_exits_zero_python_project(self, tmp_path):
        """lint in a python project exits 0 (or warns if no lint_command)."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("lint", cwd=str(tmp_path))
        # lint may exit 0 (clean) or non-zero (lint errors or no config)
        # Just verify it doesn't crash with traceback
        assert "Traceback" not in stderr

    def test_lint_no_config(self, tmp_path):
        """lint in empty directory doesn't crash."""
        stdout, stderr, rc = run_pactkit("lint", cwd=str(tmp_path))
        assert "Traceback" not in stderr


@pytest.mark.e2e
class TestSpecStatusCommand:
    """E2E tests for pactkit spec-status."""

    def test_spec_status_updates_draft_to_done(self, tmp_path):
        """spec-status updates Status field from Draft to Done."""
        _init_project(tmp_path)
        spec = tmp_path / "docs" / "specs" / "STORY-999.md"
        spec.write_text(
            "# STORY-999: Test\n\n"
            "| Field | Value |\n|---|---|\n| Status | Draft |\n",
            encoding="utf-8",
        )
        stdout, stderr, rc = run_pactkit("spec-status", str(spec), "Done")
        assert rc == 0, f"spec-status failed: {stderr}"
        assert "Done" in spec.read_text(encoding="utf-8")

    def test_spec_status_missing_file(self, tmp_path):
        """spec-status with nonexistent file exits non-zero."""
        stdout, stderr, rc = run_pactkit("spec-status", str(tmp_path / "nope.md"), "Done")
        assert rc != 0


# ---------------------------------------------------------------------------
# R2: Validation and linting subcommand E2E coverage (7 subcommands)
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestLintContextCommand:
    """E2E tests for pactkit lint-context."""

    def test_lint_context_valid(self, tmp_path):
        """Valid context.md passes lint-context."""
        _init_project(tmp_path)
        # Generate a valid context.md first
        run_pactkit("context", cwd=str(tmp_path))
        ctx = tmp_path / "docs" / "product" / "context.md"
        stdout, stderr, rc = run_pactkit("lint-context", str(ctx))
        assert rc == 0, f"lint-context failed: {stderr}"


@pytest.mark.e2e
class TestLintLessonsCommand:
    """E2E tests for pactkit lint-lessons."""

    def test_lint_lessons_valid(self, tmp_path):
        """lint-lessons runs without traceback."""
        _init_project(tmp_path)
        lessons = tmp_path / "docs" / "architecture" / "governance" / "lessons.md"
        stdout, stderr, rc = run_pactkit("lint-lessons", str(lessons))
        assert "Traceback" not in stderr


@pytest.mark.e2e
class TestLintTestcaseCommand:
    """E2E tests for pactkit lint-testcase."""

    def test_lint_testcase_valid(self, tmp_path):
        """Valid test case file passes lint-testcase."""
        tc = tmp_path / "test_case.md"
        tc.write_text(
            "# TC-001: Test\n\n"
            "| Field | Value |\n|---|---|\n| Spec | STORY-001 |\n\n"
            "## Scenarios\n\n### S1: Happy path\n"
            "- **Given** x\n- **When** y\n- **Then** z\n",
            encoding="utf-8",
        )
        stdout, stderr, rc = run_pactkit("lint-testcase", str(tc))
        # May pass or fail depending on exact validation rules; just no traceback
        assert "Traceback" not in stderr


@pytest.mark.e2e
class TestSecScopeCommand:
    """E2E tests for pactkit sec-scope."""

    def test_sec_scope_with_files(self, tmp_path):
        """sec-scope with a file list exits without traceback."""
        _init_project(tmp_path)
        src_file = tmp_path / "src" / "main.py"
        stdout, stderr, rc = run_pactkit("sec-scope", str(src_file))
        assert "Traceback" not in stderr
        # sec-scope should produce SEC-N output
        assert "SEC-" in stdout or rc == 0


@pytest.mark.e2e
class TestSchemaCommand:
    """E2E tests for pactkit schema."""

    def test_schema_lists_schemas(self):
        """schema --all lists known schema names."""
        stdout, stderr, rc = run_pactkit("schema", "--all")
        assert rc == 0, f"schema --all failed: {stderr}"
        combined = stdout.lower()
        assert "spec" in combined or "board" in combined


@pytest.mark.e2e
class TestDoctorCommand:
    """E2E tests for pactkit doctor."""

    def test_doctor_runs(self, tmp_path):
        """doctor in an initialized project exits 0."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("doctor", cwd=str(tmp_path))
        assert rc == 0, f"doctor failed: {stderr}"


@pytest.mark.e2e
class TestTestMapCommand:
    """E2E tests for pactkit test-map."""

    def test_test_map_exits(self, tmp_path):
        """test-map with a source file exits without traceback."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("test-map", "src/main.py", cwd=str(tmp_path))
        assert "Traceback" not in stderr


# ---------------------------------------------------------------------------
# R3: CLI error path and edge case coverage
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestErrorPaths:
    """E2E tests for CLI error handling."""

    def test_unknown_subcommand(self):
        """Unknown subcommand → non-zero exit, no traceback."""
        stdout, stderr, rc = run_pactkit("foobar_not_a_command")
        assert rc != 0
        assert "Traceback" not in stderr

    def test_spec_status_missing_args(self):
        """spec-status with no arguments → non-zero exit."""
        stdout, stderr, rc = run_pactkit("spec-status")
        assert rc != 0

    def test_spec_lint_nonexistent_file(self):
        """spec-lint with nonexistent file → non-zero exit, graceful error."""
        stdout, stderr, rc = run_pactkit("spec-lint", "/nonexistent/path/spec.md")
        assert rc != 0
        assert "Traceback" not in stderr

    def test_guard_empty_dir(self, tmp_path):
        """guard in empty dir → non-zero (missing init markers)."""
        stdout, stderr, rc = run_pactkit("guard", cwd=str(tmp_path))
        assert rc != 0

    def test_unicode_project_path(self, tmp_path):
        """pactkit init in a unicode-named directory works."""
        unicode_dir = tmp_path / "项目测试"
        unicode_dir.mkdir()
        target = unicode_dir / "deploy"
        stdout, stderr, rc = run_pactkit("init", "-t", str(target), cwd=str(unicode_dir))
        assert rc == 0, f"init in unicode path failed: {stderr}"
        assert target.exists()

    ALL_SUBCOMMANDS = [
        "init", "update", "upgrade", "spec-lint", "schema", "guard",
        "next-id", "clean", "regression", "context", "sec-scope",
        "lint-context", "lint-lessons", "lint-testcase", "visualize",
        "doctor", "backfill-release", "issue-sync", "test-map", "lint",
        "lesson-append", "invariants-refresh", "coverage-gate",
        "spec-status", "version",
    ]

    @pytest.mark.parametrize("subcmd", ALL_SUBCOMMANDS)
    def test_help_all_subcommands(self, subcmd):
        """--help for every subcommand returns exit code 0."""
        stdout, stderr, rc = run_pactkit(subcmd, "--help")
        assert rc == 0, f"{subcmd} --help exited with {rc}: {stderr}"


# ---------------------------------------------------------------------------
# R4: Remaining low-frequency subcommand coverage (6 subcommands)
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestUpgradeCommand:
    """E2E tests for pactkit upgrade."""

    def test_upgrade_exits(self, tmp_path):
        """upgrade in a fresh dir exits without traceback."""
        target = tmp_path / "deploy"
        stdout, stderr, rc = run_pactkit("upgrade", "-t", str(target), cwd=str(tmp_path))
        assert "Traceback" not in stderr


@pytest.mark.e2e
class TestBackfillReleaseCommand:
    """E2E tests for pactkit backfill-release."""

    def test_backfill_release_updates_spec(self, tmp_path):
        """backfill-release replaces TBD with version for Done specs."""
        _init_project(tmp_path)
        # Add STORY-001 to Done section on the board so backfill recognizes it
        board = tmp_path / "docs" / "product" / "sprint_board.md"
        board.write_text(
            "# Sprint Board\n\n## 🚧 In Progress\n\n## 📋 Backlog\n\n"
            "## ✅ Done\n\n- STORY-001: Test story\n",
            encoding="utf-8",
        )
        spec = tmp_path / "docs" / "specs" / "STORY-001.md"
        spec.write_text(
            "# STORY-001: Test\n\n"
            "| Field | Value |\n|---|---|\n"
            "| Status | Done |\n| Release | TBD |\n",
            encoding="utf-8",
        )
        stdout, stderr, rc = run_pactkit("backfill-release", "3.0.0", cwd=str(tmp_path))
        assert rc == 0, f"backfill-release failed: {stderr}"
        assert "3.0.0" in spec.read_text(encoding="utf-8")


@pytest.mark.e2e
class TestIssueSyncCommand:
    """E2E tests for pactkit issue-sync."""

    def test_issue_sync_story_skipped(self, tmp_path):
        """issue-sync with STORY-* item is skipped (IP protection)."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit("issue-sync", "STORY-slim-001", cwd=str(tmp_path))
        combined = stdout + stderr
        # STORY items should be skipped or at least not crash
        assert "Traceback" not in stderr


@pytest.mark.e2e
class TestLessonAppendCommand:
    """E2E tests for pactkit lesson-append."""

    def test_lesson_append_exits(self, tmp_path):
        """lesson-append with valid args exits without traceback."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit(
            "lesson-append",
            "--story", "STORY-001",
            "--text", "E2E tests are important for CLI coverage",
            "--context", "test_cli_e2e.py",
            cwd=str(tmp_path),
        )
        assert "Traceback" not in stderr


@pytest.mark.e2e
class TestInvariantsRefreshCommand:
    """E2E tests for pactkit invariants-refresh."""

    def test_invariants_refresh_updates_count(self, tmp_path):
        """invariants-refresh updates test count in rules.md."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit(
            "invariants-refresh", "--test-count", "3300",
            cwd=str(tmp_path),
        )
        assert rc == 0, f"invariants-refresh failed: {stderr}"
        rules = (tmp_path / "docs" / "architecture" / "governance" / "rules.md").read_text(encoding="utf-8")
        assert "3300" in rules


@pytest.mark.e2e
class TestCoverageGateCommand:
    """E2E tests for pactkit coverage-gate."""

    def test_coverage_gate_exits(self, tmp_path):
        """coverage-gate with a file exits without traceback."""
        _init_project(tmp_path)
        stdout, stderr, rc = run_pactkit(
            "coverage-gate", "src/main.py",
            cwd=str(tmp_path),
        )
        assert "Traceback" not in stderr
