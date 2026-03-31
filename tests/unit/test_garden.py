"""Tests for garden.py — codebase quality patrol (STORY-slim-070)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def project_tree(tmp_path: Path) -> Path:
    """Create a minimal project tree for garden checks."""
    # Source files
    src = tmp_path / "src" / "myapp"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")

    # docs structure
    specs = tmp_path / "docs" / "specs"
    specs.mkdir(parents=True)
    (tmp_path / "docs" / "product").mkdir(parents=True)
    (tmp_path / "docs" / "test_cases").mkdir(parents=True)

    return tmp_path


# ---------------------------------------------------------------------------
# R1: Dead Code Detection
# ---------------------------------------------------------------------------


class TestCheckDeadImports:
    """AC1 + AC8: dead import detection, pure function contract."""

    def test_detects_unused_import(self, project_tree: Path) -> None:
        """AC1: file with `import os` but os never used."""
        src = project_tree / "src" / "myapp" / "example.py"
        src.write_text("import os\nimport sys\n\nprint(sys.argv)\n")

        from pactkit.garden import check_dead_imports

        result = check_dead_imports(project_tree, scope=None)
        assert "findings" in result
        findings = result["findings"]
        assert any(
            f["type"] == "DEAD-IMPORT" and "os" in f["message"]
            for f in findings
        )

    def test_no_false_positive_on_used_import(self, project_tree: Path) -> None:
        src = project_tree / "src" / "myapp" / "clean.py"
        src.write_text("import os\n\nos.getcwd()\n")

        from pactkit.garden import check_dead_imports

        result = check_dead_imports(project_tree, scope=None)
        assert not any(
            f["file"].endswith("clean.py") for f in result["findings"]
        )

    def test_detects_empty_except_pass(self, project_tree: Path) -> None:
        """R1: empty except: pass blocks."""
        src = project_tree / "src" / "myapp" / "bad.py"
        src.write_text("try:\n    x = 1\nexcept:\n    pass\n")

        from pactkit.garden import check_dead_imports

        result = check_dead_imports(project_tree, scope=None)
        assert any(
            f["type"] == "EMPTY-EXCEPT" for f in result["findings"]
        )

    def test_scope_filters_files(self, project_tree: Path) -> None:
        """AC5: --scope filters to specific directory."""
        skills = project_tree / "src" / "myapp" / "skills"
        skills.mkdir()
        (skills / "tool.py").write_text("import os\n\nprint('hi')\n")
        (project_tree / "src" / "myapp" / "main.py").write_text("import os\n\nprint('hi')\n")

        from pactkit.garden import check_dead_imports

        result = check_dead_imports(project_tree, scope=Path("src/myapp/skills"))
        assert all(
            "skills" in f["file"] for f in result["findings"]
        )

    def test_pure_function_no_side_effects(self, project_tree: Path) -> None:
        """AC8: returns dict, no side effects."""
        from pactkit.garden import check_dead_imports

        result = check_dead_imports(project_tree, scope=None)
        assert isinstance(result, dict)
        assert "findings" in result
        assert isinstance(result["findings"], list)


# ---------------------------------------------------------------------------
# R2: Stale Documentation Detection
# ---------------------------------------------------------------------------


class TestCheckStaleDocs:
    """AC2 + AC3: stale spec references and stale context."""

    def test_detects_stale_spec_reference(self, project_tree: Path) -> None:
        """AC2: Done spec references non-existent file."""
        spec = project_tree / "docs" / "specs" / "STORY-slim-001.md"
        spec.write_text(
            "# STORY-slim-001\n\n"
            "| Field | Value |\n|---|---|\n| Status | Done |\n\n"
            "## Implementation Steps\n\n"
            "| Step | File | Action |\n|---|---|---|\n"
            "| 1 | `src/old_module.py` | Delete |\n"
        )

        from pactkit.garden import check_stale_docs

        result = check_stale_docs(project_tree, scope=None)
        assert any(
            f["type"] == "STALE-DOC" and "old_module.py" in f["message"]
            for f in result["findings"]
        )

    def test_ignores_non_done_specs(self, project_tree: Path) -> None:
        """Only scan specs with Status=Done."""
        spec = project_tree / "docs" / "specs" / "STORY-slim-002.md"
        spec.write_text(
            "# STORY-slim-002\n\n"
            "| Field | Value |\n|---|---|\n| Status | Draft |\n\n"
            "## Implementation Steps\n\n"
            "| Step | File | Action |\n|---|---|---|\n"
            "| 1 | `src/nonexistent.py` | Create |\n"
        )

        from pactkit.garden import check_stale_docs

        result = check_stale_docs(project_tree, scope=None)
        assert not any(
            f["file"].endswith("STORY-slim-002.md") for f in result["findings"]
        )

    def test_detects_stale_context(self, project_tree: Path) -> None:
        """AC3: context.md older than 7 days."""
        ctx = project_tree / "docs" / "product" / "context.md"
        ctx.write_text(
            "# Project Context (Auto-generated)\n"
            "> Last updated: 2026-01-01T00:00:00+00:00 by test\n"
        )

        from pactkit.garden import check_stale_docs

        result = check_stale_docs(project_tree, scope=None)
        assert any(
            f["type"] == "STALE-CTX" for f in result["findings"]
        )

    def test_fresh_context_no_finding(self, project_tree: Path) -> None:
        """Fresh context.md should not trigger."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        ctx = project_tree / "docs" / "product" / "context.md"
        ctx.write_text(
            "# Project Context (Auto-generated)\n"
            f"> Last updated: {now} by test\n"
        )

        from pactkit.garden import check_stale_docs

        result = check_stale_docs(project_tree, scope=None)
        assert not any(
            f["type"] == "STALE-CTX" for f in result["findings"]
        )

    def test_detects_orphaned_test_case(self, project_tree: Path) -> None:
        """R2: test case referencing non-existent spec."""
        tc = project_tree / "docs" / "test_cases" / "STORY-slim-999_case.md"
        tc.write_text("# STORY-slim-999 Test Cases\n")

        from pactkit.garden import check_stale_docs

        result = check_stale_docs(project_tree, scope=None)
        assert any(
            f["type"] == "STALE-DOC" and "STORY-slim-999" in f["message"]
            for f in result["findings"]
        )


# ---------------------------------------------------------------------------
# R3: Pattern Duplication Detection
# ---------------------------------------------------------------------------


class TestCheckPatternDuplication:
    """AC7: detect duplicate function signatures."""

    def test_detects_duplicate_function(self, project_tree: Path) -> None:
        """AC7: same function name + param count in different modules."""
        (project_tree / "src" / "myapp" / "billing.py").write_text(
            "def calculate_total(items, tax):\n    return sum(items) * (1 + tax)\n"
        )
        (project_tree / "src" / "myapp" / "invoice.py").write_text(
            "def calculate_total(items, tax):\n    return sum(items) + tax\n"
        )

        from pactkit.garden import check_pattern_duplication

        result = check_pattern_duplication(project_tree, scope=None)
        assert any(
            f["type"] == "DUP-FUNC" and "calculate_total" in f["message"]
            for f in result["findings"]
        )

    def test_no_false_positive_different_params(self, project_tree: Path) -> None:
        """Same name but different param count is not a dup."""
        (project_tree / "src" / "myapp" / "a.py").write_text(
            "def process(data):\n    pass\n"
        )
        (project_tree / "src" / "myapp" / "b.py").write_text(
            "def process(data, config, options):\n    pass\n"
        )

        from pactkit.garden import check_pattern_duplication

        result = check_pattern_duplication(project_tree, scope=None)
        assert not any(
            f["type"] == "DUP-FUNC" and "process" in f["message"]
            for f in result["findings"]
        )

    def test_detects_stale_canonical_copy(self, project_tree: Path) -> None:
        """R3: inline canonical copy that no longer matches source."""
        # Create the "canonical source" file
        (project_tree / "src" / "myapp" / "schemas.py").write_text(
            'BOARD_SECTION_BACKLOG = "## 📋 Backlog"\n'
        )
        # Create a file with a stale inline copy
        (project_tree / "src" / "myapp" / "tool.py").write_text(
            '# Canonical: src/myapp/schemas.py BOARD_SECTION_BACKLOG\n'
            '_BACKLOG = "## Backlog"\n'  # Wrong value — missing emoji
        )

        from pactkit.garden import check_pattern_duplication

        result = check_pattern_duplication(project_tree, scope=None)
        assert any(
            f["type"] == "STALE-CANONICAL" for f in result["findings"]
        )


# ---------------------------------------------------------------------------
# R4: CLI Interface — run_garden orchestrator
# ---------------------------------------------------------------------------


class TestRunGarden:
    """AC4 + AC6: JSON output, clean exit."""

    def test_json_output_structure(self, project_tree: Path) -> None:
        """AC4: JSON output has correct structure."""
        (project_tree / "src" / "myapp" / "bad.py").write_text("import os\n\nprint('hi')\n")

        from pactkit.garden import run_garden

        output, exit_code = run_garden(project_tree, scope=None, json_output=True)
        data = json.loads(output)
        assert "findings" in data
        assert "total" in data
        assert isinstance(data["findings"], list)
        assert data["total"] > 0
        assert exit_code == 1

    def test_clean_exit_no_findings(self, project_tree: Path) -> None:
        """AC6: no findings → clean message + exit 0."""
        # Only a clean file
        (project_tree / "src" / "myapp" / "clean.py").write_text(
            "import os\n\nos.getcwd()\n"
        )

        from pactkit.garden import run_garden

        output, exit_code = run_garden(project_tree, scope=None, json_output=False)
        assert "all clear" in output.lower()
        assert exit_code == 0

    def test_human_readable_format(self, project_tree: Path) -> None:
        """Human-readable output includes [TYPE] prefix."""
        (project_tree / "src" / "myapp" / "bad.py").write_text("import os\n\nprint('hi')\n")

        from pactkit.garden import run_garden

        output, exit_code = run_garden(project_tree, scope=None, json_output=False)
        assert "[DEAD-IMPORT]" in output
        assert exit_code == 1

    def test_scope_passed_to_checks(self, project_tree: Path) -> None:
        """AC5: scope is passed through to all checks."""
        skills = project_tree / "src" / "myapp" / "skills"
        skills.mkdir()
        (skills / "tool.py").write_text("import os\n\nprint('hi')\n")
        (project_tree / "src" / "myapp" / "main.py").write_text("import os\n\nprint('hi')\n")

        from pactkit.garden import run_garden

        output, exit_code = run_garden(
            project_tree, scope=Path("src/myapp/skills"), json_output=True,
        )
        data = json.loads(output)
        assert all("skills" in f["file"] for f in data["findings"])


# ---------------------------------------------------------------------------
# Security: SEC-1 + SEC-6 — scope path validation
# ---------------------------------------------------------------------------


class TestScopeSecurity:
    """SEC-1 + SEC-6: scope must not escape project root."""

    def test_rejects_parent_traversal(self, project_tree: Path) -> None:
        from pactkit.garden import run_garden

        output, exit_code = run_garden(
            project_tree, scope=Path("../../../etc"), json_output=False,
        )
        assert exit_code == 1
        assert "outside project" in output.lower() or "invalid" in output.lower()

    def test_rejects_absolute_path(self, project_tree: Path) -> None:
        from pactkit.garden import run_garden

        output, exit_code = run_garden(
            project_tree, scope=Path("/etc"), json_output=False,
        )
        assert exit_code == 1
        assert "outside project" in output.lower() or "invalid" in output.lower()
