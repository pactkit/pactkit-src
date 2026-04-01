"""Tests for STORY-slim-077: Monorepo stack detection + redetect-stack CLI."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# AC1: Monorepo subdirectory detection (R1)
# ---------------------------------------------------------------------------
class TestMonorepoSubdirDetection:
    """detect_stacks() should find markers in depth-1 subdirectories."""

    def test_ac1_subdir_markers_only(self, tmp_path):
        """backend/go.mod + frontend/package.json → ['go', 'node']."""
        from pactkit.cleaners import detect_stacks

        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "go.mod").write_text("module x")
        (tmp_path / "frontend").mkdir()
        (tmp_path / "frontend" / "package.json").write_text("{}")

        result = detect_stacks(tmp_path)
        assert "go" in result
        assert "node" in result
        assert len(result) == 2

    def test_ac1_subdir_java_marker(self, tmp_path):
        """services/pom.xml → ['java']."""
        from pactkit.cleaners import detect_stacks

        (tmp_path / "services").mkdir()
        (tmp_path / "services" / "pom.xml").write_text("<project/>")

        result = detect_stacks(tmp_path)
        assert result == ["java"]


# ---------------------------------------------------------------------------
# AC2: Mixed root + subdirectory markers (R1, R4)
# ---------------------------------------------------------------------------
class TestMixedRootAndSubdir:

    def test_ac2_root_python_plus_subdir_go(self, tmp_path):
        """pyproject.toml at root + backend/go.mod → ['python', 'go']."""
        from pactkit.cleaners import detect_stacks

        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "go.mod").write_text("module x")

        result = detect_stacks(tmp_path)
        assert result == ["python", "go"]

    def test_ac2_no_duplicate_from_subdir(self, tmp_path):
        """Root package.json + frontend/package.json → ['node'] (no dup)."""
        from pactkit.cleaners import detect_stacks

        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "frontend").mkdir()
        (tmp_path / "frontend" / "package.json").write_text("{}")

        result = detect_stacks(tmp_path)
        assert result == ["node"]


# ---------------------------------------------------------------------------
# AC3: Root-only project unchanged (R4)
# ---------------------------------------------------------------------------
class TestRootOnlyBackwardCompat:

    def test_ac3_root_only_python(self, tmp_path):
        """pyproject.toml at root only → ['python']."""
        from pactkit.cleaners import detect_stacks

        (tmp_path / "pyproject.toml").write_text("[project]")
        result = detect_stacks(tmp_path)
        assert result == ["python"]

    def test_ac3_no_markers_defaults_python(self, tmp_path):
        """No markers anywhere → ['python']."""
        from pactkit.cleaners import detect_stacks

        result = detect_stacks(tmp_path)
        assert result == ["python"]


# ---------------------------------------------------------------------------
# AC8: Depth-1 only — no deep recursion (R1)
# ---------------------------------------------------------------------------
class TestDepthLimit:

    def test_ac8_deep_nested_not_detected(self, tmp_path):
        """deep/nested/sub/go.mod → NOT detected."""
        from pactkit.cleaners import detect_stacks

        deep = tmp_path / "deep" / "nested" / "sub"
        deep.mkdir(parents=True)
        (deep / "go.mod").write_text("module x")

        result = detect_stacks(tmp_path)
        assert result == ["python"]  # default fallback

    def test_ac8_files_not_dirs_ignored(self, tmp_path):
        """A file named 'backend' (not a dir) should not be scanned."""
        from pactkit.cleaners import detect_stacks

        (tmp_path / "backend").write_text("not a directory")
        result = detect_stacks(tmp_path)
        assert result == ["python"]


# ---------------------------------------------------------------------------
# AC6: visualize _detect_stacks subdirectory fallback (R1)
# ---------------------------------------------------------------------------
class TestVisualizeDetectStacks:

    def test_ac6_visualize_subdir_with_auto_yaml(self, tmp_path):
        """yaml stack:auto + subdir markers → detects from subdirs."""
        from pactkit.skills.visualize import _detect_stacks

        # Write yaml with stack: auto
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "pactkit.yaml").write_text("stack: auto\n")

        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "go.mod").write_text("module x")
        (tmp_path / "frontend").mkdir()
        (tmp_path / "frontend" / "package.json").write_text("{}")

        result = _detect_stacks(tmp_path)
        assert "go" in result
        assert "node" in result


# ---------------------------------------------------------------------------
# AC4: redetect-stack updates yaml (R2)
# ---------------------------------------------------------------------------
class TestUpdateYamlStack:

    def test_ac4_update_yaml_stack(self, tmp_path):
        """update_yaml_stack rewrites stack field in existing yaml."""
        from pactkit.config import update_yaml_stack

        yaml_path = tmp_path / "pactkit.yaml"
        yaml_path.write_text(
            "# PactKit\nversion: \"2.9.11\"\nstack: node\nroot: .\n"
        )

        update_yaml_stack(yaml_path, ["go", "node"])

        content = yaml_path.read_text()
        assert "stack:" in content
        assert "  - go" in content
        assert "  - node" in content
        # version and root preserved
        assert 'version: "2.9.11"' in content
        assert "root: ." in content

    def test_ac4_single_stack_unwrap(self, tmp_path):
        """Single-element list unwraps to plain string."""
        from pactkit.config import update_yaml_stack

        yaml_path = tmp_path / "pactkit.yaml"
        yaml_path.write_text(
            "# PactKit\nversion: \"2.9.11\"\nstack: auto\nroot: .\n"
        )

        update_yaml_stack(yaml_path, ["python"])

        content = yaml_path.read_text()
        assert "stack: python" in content
        assert "  - python" not in content


# ---------------------------------------------------------------------------
# AC5: redetect-stack no yaml (R2)
# ---------------------------------------------------------------------------
class TestRedetectStackCLI:

    def test_ac5_no_yaml_exits_with_error(self, tmp_path):
        """redetect-stack with no yaml prints error."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "pactkit", "redetect-stack"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode != 0
        combined = (result.stdout + result.stderr).lower()
        assert "pactkit init" in combined


# ---------------------------------------------------------------------------
# AC7: init updates stale stack (R3)
# ---------------------------------------------------------------------------
class TestInitUpdatesStack:

    def test_ac7_deploy_updates_stale_stack(self, tmp_path):
        """_update_stack_if_stale detects new stacks and rewrites yaml."""
        from pactkit.generators.deployer import _update_stack_if_stale

        yaml_path = tmp_path / ".claude" / "pactkit.yaml"
        yaml_path.parent.mkdir(parents=True)
        yaml_path.write_text(
            '# PactKit\nversion: "2.9.11"\nstack: node\nroot: .\ndeveloper: ""\n'
        )

        # Create monorepo markers
        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "go.mod").write_text("module x")
        (tmp_path / "frontend").mkdir()
        (tmp_path / "frontend" / "package.json").write_text("{}")

        updated = _update_stack_if_stale(yaml_path, tmp_path)
        assert updated is True

        import yaml
        data = yaml.safe_load(yaml_path.read_text())
        stack = data.get("stack")
        if isinstance(stack, list):
            assert "go" in stack
            assert "node" in stack
        else:
            pytest.fail(f"Expected list, got {type(stack)}: {stack}")

    def test_ac7_no_change_if_already_correct(self, tmp_path):
        """_update_stack_if_stale returns False when stack is already correct."""
        from pactkit.generators.deployer import _update_stack_if_stale

        yaml_path = tmp_path / ".claude" / "pactkit.yaml"
        yaml_path.parent.mkdir(parents=True)
        yaml_path.write_text(
            '# PactKit\nversion: "2.9.11"\nstack: python\nroot: .\ndeveloper: ""\n'
        )
        (tmp_path / "pyproject.toml").write_text("[project]")

        updated = _update_stack_if_stale(yaml_path, tmp_path)
        assert updated is False
