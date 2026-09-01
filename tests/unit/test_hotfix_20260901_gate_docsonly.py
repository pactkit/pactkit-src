"""HOTFIX-slim-20260901469666ef23a8: commit-gate misfires on docs/meta-only commits.

Three defects observed live when harness-backend's zero-code design
baseline (root commit, unborn branch) was blocked three times and forced
test-writing before allowing the commit:
  1. repo/agent meta files (.gitignore, .claude/**, .codex/**) broke
     doc-only classification;
  2. the full-suite target hard-coded tests/unit/ with no tests/ fallback,
     and zero-collected runs (exit 4/5) were reported as "tests are RED";
  3. "No module named pytest" from the venv-less fallback interpreter was
     reported as RED instead of GateUnavailable (R3 self-lock protection).
"""

import pytest

from pactkit import commit_gate
from pactkit.commit_gate import GateUnavailable, run_gate, run_pytest
from pactkit.regression import classify_changes


@pytest.fixture
def repo(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    return tmp_path


def mock_git(monkeypatch, branch="", changed=()):
    monkeypatch.setattr(commit_gate, "collect_changed_files", lambda root: list(changed))
    monkeypatch.setattr(commit_gate, "current_branch", lambda root: branch)


def mock_pytest(monkeypatch, returncode=0, output="10 passed in 1.0s"):
    calls = {}

    def _run(root, test_files):
        calls["test_files"] = test_files
        return returncode, output

    monkeypatch.setattr(commit_gate, "run_pytest", _run)
    return calls


def fake_subprocess(monkeypatch, returncode, stdout="", stderr=""):
    captured = {}

    def _run(command, **kwargs):
        captured["cmd"] = command
        return type(
            "Result", (), {"returncode": returncode, "stdout": stdout, "stderr": stderr}
        )()

    monkeypatch.setattr(commit_gate.subprocess, "run", _run)
    return captured


# ===========================================================================
# Fix 1: repo/agent metadata is doc-only
# ===========================================================================


class TestMetaFilesAreDocOnly:
    def test_design_baseline_commit_skips(self):
        """The exact incident file set: docs + repo/agent meta, zero code → skip."""
        files = [
            ".gitignore",
            ".claude/CLAUDE.md",
            ".claude/settings.json",
            "requirements.txt",
            "docs/product/stories/STORY-x.yaml",
            "docs/specs/STORY-x.md",
            "docs/architecture/system.md",
        ]
        strategy, reason = classify_changes(files)
        assert strategy == "skip"
        assert "doc" in reason.lower()

    def test_codex_meta_files_skip(self):
        assert classify_changes([".codex/hooks.json", "README.md"])[0] == "skip"

    def test_meta_plus_source_still_impact(self):
        """Meta files must not mask real code changes (regression guard)."""
        files = [".gitignore", "src/harness/api/app.py"]
        assert classify_changes(files)[0] == "impact"

    def test_end_to_end_unborn_branch_skip(self, repo, monkeypatch):
        """Root-commit scenario: unresolvable branch + baseline files → SKIP,
        pytest never invoked."""
        mock_git(monkeypatch, branch="", changed=(
            ".gitignore", ".claude/settings.json", "docs/specs/STORY-x.md",
        ))
        calls = mock_pytest(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 0
        assert "test_files" not in calls
        assert "SKIP" in result.render()


# ===========================================================================
# Fix 2: full-suite target fallback + honest zero-collected verdict
# ===========================================================================


class TestFullSuiteTargetFallback:
    def test_flat_tests_dir_is_targeted_when_unit_absent(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        (tmp_path / "tests").mkdir()
        captured = fake_subprocess(monkeypatch, returncode=0, stdout="4 passed")
        run_pytest(tmp_path, None)
        assert captured["cmd"][-1] == "tests/"

    def test_unit_dir_still_preferred(self, repo, monkeypatch):
        captured = fake_subprocess(monkeypatch, returncode=0, stdout="4 passed")
        run_pytest(repo, None)
        assert captured["cmd"][-1] == "tests/unit/"

    def test_no_tests_dir_keeps_convention_target(self, tmp_path, monkeypatch):
        """STORY-slim-20260828d43fae4edbb6 contract: a repo with no tests
        directory at all targets the convention path (exit 4 → RED)."""
        captured = fake_subprocess(monkeypatch, returncode=0, stdout="1 passed")
        run_pytest(tmp_path, None)
        assert captured["cmd"][-1] == "tests/unit/"

    def test_no_tests_collected_reports_honestly(self, repo, monkeypatch):
        """Exit 5 with zero collected blocks, but says 'no tests collected' —
        not 'tests are RED'."""
        mock_git(monkeypatch, changed=("src/pkg/mod.py",))
        mock_pytest(monkeypatch, returncode=5, output="no tests ran in 0.01s")
        result = run_gate(repo)
        assert result.exit_code == 1
        text = result.render()
        assert "no tests collected" in text
        assert "tests are RED" not in text


# ===========================================================================
# Fix 3: missing pytest module is unavailable, not RED
# ===========================================================================


class TestMissingPytestModule:
    def test_no_module_named_pytest_is_unavailable(self, repo, monkeypatch):
        fake_subprocess(
            monkeypatch, returncode=1, stderr="/usr/bin/python3: No module named pytest",
        )
        with pytest.raises(GateUnavailable):
            run_pytest(repo, None)

    def test_module_error_inside_tests_is_still_red(self, repo, monkeypatch):
        """A failing test that legitimately prints a module error for ANOTHER
        module is a real RED, not a toolchain failure."""
        output = (
            "FAILED tests/unit/test_x.py::test_imports - "
            "ModuleNotFoundError: No module named 'requests'\n"
            "1 failed, 0 passed in 0.01s"
        )
        fake_subprocess(monkeypatch, returncode=1, stdout=output)
        returncode, combined = run_pytest(repo, None)
        assert returncode == 1
        assert "No module named 'requests'" in combined
