"""STORY-slim-20260828d43fae4edbb6: stack-aware commit-gate test commands.

Covers AC1-AC5 of docs/specs/STORY-slim-20260828d43fae4edbb6.md — the
commit-gate must run the project's real suite (npm/go test/mvn/gradle),
never force pytest onto a non-Python repo, and degrade to WARN + allow
when the stack has no runnable test command.
"""

import json

import pytest

from pactkit import commit_gate
from pactkit.commit_gate import GateUnavailable, run_gate, run_pytest
from pactkit.utils import stack_test_command


def _write(root, name, content=""):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ===========================================================================
# AC1: python behavior unchanged
# ===========================================================================


class TestPythonResolution:
    def test_python_markers_keep_pytest(self, tmp_path):
        _write(tmp_path, "pyproject.toml")
        stack, argv = stack_test_command(tmp_path)
        assert stack == "python"
        assert argv[-2:] == ["-m", "pytest"]

    def test_no_markers_default_to_python(self, tmp_path):
        stack, argv = stack_test_command(tmp_path)
        assert stack == "python"
        assert argv[-2:] == ["-m", "pytest"]

    def test_monorepo_with_python_keeps_pytest(self, tmp_path):
        """Python in detect_stacks wins even when node markers coexist."""
        _write(tmp_path, "pyproject.toml")
        _write(tmp_path, "package.json", json.dumps({"scripts": {"test": "vitest"}}))
        stack, _ = stack_test_command(tmp_path)
        assert stack == "python"

    def test_run_pytest_python_invocation_shape(self, tmp_path, monkeypatch):
        """Gate flags + junit count channel + target last (STORY-slim-
        202609025bc9246b6a54 added --junitxml/-o; -rsfE keeps skip reasons
        and adds FAILED/ERROR short-summary lines the tail filter needs)."""
        _write(tmp_path, "pyproject.toml")
        observed = {}

        def fake_run(command, **kwargs):
            observed["cmd"] = command
            return type("Result", (), {"returncode": 0, "stdout": "1 passed", "stderr": ""})()

        monkeypatch.setattr(commit_gate.subprocess, "run", fake_run)
        run_pytest(tmp_path, None)
        cmd = observed["cmd"]
        assert cmd[-1] == "tests/unit/"
        assert "-rsfE" in cmd
        assert "-q" in cmd
        assert "--junitxml" in cmd
        assert cmd[cmd.index("--junitxml") + 1].endswith(".xml")
        assert "junit_family=xunit2" in cmd


# ===========================================================================
# AC2: node resolution
# ===========================================================================


class TestNodeResolution:
    def test_package_json_with_test_script(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"scripts": {"test": "vitest run"}}))
        assert stack_test_command(tmp_path) == ("node", ["npm", "test", "--silent"])

    def test_package_json_without_test_script(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"scripts": {"build": "tsc"}}))
        assert stack_test_command(tmp_path) is None

    def test_corrupt_package_json(self, tmp_path):
        _write(tmp_path, "package.json", "{oops")
        assert stack_test_command(tmp_path) is None


# ===========================================================================
# AC3: go/java resolution
# ===========================================================================


class TestGoJavaResolution:
    def test_go_mod(self, tmp_path):
        _write(tmp_path, "go.mod", "module example.com/x\n")
        assert stack_test_command(tmp_path) == ("go", ["go", "test", "./..."])

    def test_pom_with_wrapper(self, tmp_path):
        _write(tmp_path, "pom.xml")
        _write(tmp_path, "mvnw")
        assert stack_test_command(tmp_path) == ("java", ["./mvnw", "-q", "test"])

    def test_pom_without_wrapper(self, tmp_path):
        _write(tmp_path, "pom.xml")
        assert stack_test_command(tmp_path) == ("java", ["mvn", "-q", "test"])

    def test_gradle_with_wrapper(self, tmp_path):
        _write(tmp_path, "build.gradle")
        _write(tmp_path, "gradlew")
        assert stack_test_command(tmp_path) == ("java", ["./gradlew", "-q", "test"])


# ===========================================================================
# AC4: gate runs the stack's suite; blocks on red; warns when unresolvable
# ===========================================================================


class TestGateRunsStackSuite:
    @pytest.fixture
    def node_repo(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        _write(tmp_path, "package.json", json.dumps({"scripts": {"test": "vitest run"}}))
        monkeypatch.setattr(commit_gate, "collect_changed_files", lambda root: ["src/app.ts"])
        monkeypatch.setattr(commit_gate, "current_branch", lambda root: "feature/x")
        return tmp_path

    def _mock_suite(self, monkeypatch, returncode, output=""):
        observed = {}

        def _run(root, test_files):
            observed["test_files"] = test_files
            return returncode, output, None

        monkeypatch.setattr(commit_gate, "run_pytest", _run)
        return observed

    def test_npm_test_invoked(self, node_repo, monkeypatch):
        observed = {}

        def fake_run(command, **kwargs):
            observed["cmd"] = command
            return type("Result", (), {"returncode": 0, "stdout": "3 passed", "stderr": ""})()

        monkeypatch.setattr(commit_gate.subprocess, "run", fake_run)
        run_pytest(node_repo, ["tests/unit/test_x.py"])  # selection ignored
        assert observed["cmd"] == ["npm", "test", "--silent"]

    def test_red_suite_blocks(self, node_repo, monkeypatch):
        self._mock_suite(monkeypatch, 1, "FAIL src/app.test.ts\n1 failed")
        result = run_gate(node_repo)
        assert result.exit_code == 1
        assert "RED" in result.render()

    def test_unresolvable_stack_warns_and_allows(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        _write(tmp_path, "package.json", json.dumps({"name": "no-tests"}))
        monkeypatch.setattr(commit_gate, "collect_changed_files", lambda root: ["src/app.ts"])
        monkeypatch.setattr(commit_gate, "current_branch", lambda root: "feature/x")
        result = run_gate(tmp_path)
        assert result.exit_code == 0
        assert "unavailable" in result.render()

    def test_run_pytest_raises_gate_unavailable(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"name": "no-tests"}))
        with pytest.raises(GateUnavailable):
            run_pytest(tmp_path, None)


# ===========================================================================
# AC5: doctor probe reports stack-specific status
# ===========================================================================


class TestProbeStackAware:
    def test_node_without_test_script_names_the_real_gap(self, tmp_path):
        from pactkit import enforcement

        (tmp_path / ".git").mkdir()
        _write(tmp_path, "package.json", json.dumps({"name": "no-tests"}))
        probe = enforcement.probe_commit_gate(tmp_path)
        assert probe["status"] == "unavailable"
        assert "test command" in probe["reason"]
        assert "pytest" not in probe["reason"]

    def test_go_repo_probe_full(self, tmp_path, monkeypatch):
        from pactkit import enforcement

        (tmp_path / ".git").mkdir()
        _write(tmp_path, "go.mod", "module x\n")
        monkeypatch.setattr(enforcement.shutil, "which", lambda name: f"/usr/bin/{name}")
        probe = enforcement.probe_commit_gate(tmp_path)
        assert probe["status"] == "full"

    def test_go_repo_without_go_binary(self, tmp_path, monkeypatch):
        from pactkit import enforcement

        (tmp_path / ".git").mkdir()
        _write(tmp_path, "go.mod", "module x\n")
        monkeypatch.setattr(enforcement.shutil, "which", lambda name: None if name == "go" else f"/usr/bin/{name}")
        probe = enforcement.probe_commit_gate(tmp_path)
        assert probe["status"] == "unavailable"
        assert "go" in probe["reason"]
