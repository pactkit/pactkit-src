"""STORY-slim-202609025bc9246b6a54: commit-gate count parsing robustness.

Live incident (2026-09-02, harness-backend): repo pyproject ``addopts="-q"``
stacked with the gate's own ``-q`` into ``-qq``; pytest 9 at verbosity -2
prints no final summary line, so ``parse_pytest_summary`` returned all zeros
and a genuinely red (flaky) run was misreported as "no tests collected".

These tests run REAL pytest subprocesses in fixture repos — the failure mode
lives in flag/ini composition, which monkeypatching cannot reproduce.

Probe-verified behavior this file pins down:
- ini-level ``-p no:junitxml`` ACCEPTS ``--junitxml`` (no exit 4) but writes
  no XML — the degradation is "missing file → None → terminal fallback";
- CLI-level ``-p no:junitxml`` (probe) rejects the flag with exit 4 —
  unreachable through the gate's own argv, so the retry branch is exercised
  synthetically as defense-in-depth.
"""

from pactkit import commit_gate
from pactkit.commit_gate import parse_junit_counts, run_gate


def _suite(n_pass=0, n_fail=0):
    parts = [f"def test_ok_{i}():\n    assert True\n" for i in range(n_pass)]
    parts += [f"def test_boom_{i}():\n    assert False, 'boom'\n" for i in range(n_fail)]
    return parts


def _make_repo(tmp_path, addopts=None, tests=None):
    """Minimal git repo whose gate run executes real pytest in-process venv."""
    (tmp_path / ".git").mkdir()
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    if tests is None:
        tests = _suite(n_pass=1)
    (unit / "test_smoke.py").write_text("\n\n".join(tests) if tests else "")
    if addopts is not None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\n"
            f'addopts = "{addopts}"\n'
        )
    return tmp_path


def mock_git(monkeypatch, branch="develop"):
    monkeypatch.setattr(commit_gate, "collect_changed_files", lambda root: ["src/pkg/mod.py"])
    monkeypatch.setattr(commit_gate, "current_branch", lambda root: branch)


# ===========================================================================
# AC1: 事故复现 —— addopts 叠加 + 真红
# ===========================================================================


class TestIncidentRepro:
    def test_ac1_addopts_q_red_reports_real_counts(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path, addopts="-q", tests=_suite(n_pass=2, n_fail=1))
        mock_git(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 1
        text = result.render()
        assert "2 passed, 1 failed" in text
        assert "tests are RED" in text
        assert "no tests" not in text

    def test_ac1_failed_tail_survives_qq(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path, addopts="-q", tests=_suite(n_fail=1))
        mock_git(monkeypatch)
        result = run_gate(repo)
        assert "FAILED" in result.render()


# ===========================================================================
# AC2: 绿灯 + addopts 叠加 —— 放行且计数真实
# ===========================================================================


class TestGreenWithAddopts:
    def test_ac2_allows_with_real_counts(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path, addopts="-q", tests=_suite(n_pass=2))
        mock_git(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 0
        assert "2 passed, 0 failed" in result.render()


# ===========================================================================
# AC3: junitxml 被禁用的 repo —— 不自锁
# ===========================================================================


class TestJunitxmlDisabled:
    def test_ac3_no_selflock_when_plugin_disabled(self, tmp_path, monkeypatch):
        """ini 级 -p no:junitxml:旗标被接受但 XML 不写——降级为终端解析,放行。"""
        repo = _make_repo(tmp_path, addopts="-p no:junitxml", tests=_suite(n_pass=1))
        mock_git(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 0
        assert "1 passed" in result.render()

    def test_ac3_accepted_flag_means_single_run(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path, addopts="-p no:junitxml", tests=_suite(n_pass=1))
        mock_git(monkeypatch)
        cmds = []
        real_run = commit_gate.subprocess.run

        def spy_run(cmd, **kwargs):
            cmds.append(list(cmd))
            return real_run(cmd, **kwargs)

        monkeypatch.setattr(commit_gate.subprocess, "run", spy_run)
        assert run_gate(repo).exit_code == 0
        assert len(cmds) == 1  # 旗标被接受,无需重试
        assert "--junitxml" in cmds[0]

    def test_exit4_unrecognized_junitxml_retries_without_flags(self, tmp_path, monkeypatch):
        """防御分支:若某配置形态真的拒收 --junitxml(exit 4 + unrecognized),
        必须去旗标重试;重试命令也不得残留 -o junit_family(插件禁用下是
        未知 ini 键,会引入第二个 exit 4)。"""
        repo = _make_repo(tmp_path, addopts="-q", tests=_suite(n_pass=1))
        mock_git(monkeypatch)
        cmds = []
        real_run = commit_gate.subprocess.run

        def fake_then_real(cmd, **kwargs):
            cmds.append(list(cmd))
            if len(cmds) == 1:
                return type("Result", (), {
                    "returncode": 4,
                    "stdout": "",
                    "stderr": "error: unrecognized arguments: --junitxml=/tmp/x.xml",
                })()
            return real_run(cmd, **kwargs)

        monkeypatch.setattr(commit_gate.subprocess, "run", fake_then_real)
        result = run_gate(repo)
        assert result.exit_code == 0
        assert len(cmds) == 2
        assert "--junitxml" in cmds[0]
        assert "--junitxml" not in cmds[1]
        assert "junit_family=xunit2" not in cmds[1]


# ===========================================================================
# AC4: exit 5 —— 文案明示 no tests ran
# ===========================================================================


class TestExitFive:
    def test_ac4_says_no_tests_ran(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path, addopts="-q", tests=_suite())
        mock_git(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 1
        text = result.render()
        assert "no tests ran" in text
        assert "no tests collected" not in text
        assert "tests are RED" not in text


# ===========================================================================
# AC5: 双重病态 —— 计数不可解析时的诚实文案
# ===========================================================================


class TestCountsUnparseable:
    def test_ac5_honest_message_not_no_tests_collected(self, tmp_path, monkeypatch):
        """-q 叠加(无 summary)+ 插件禁用(无 junit)→ 计数来源全灭,
        但文案必须报告真相而非断言 "no tests collected"。"""
        repo = _make_repo(tmp_path, addopts="-q -p no:junitxml", tests=_suite(n_fail=1))
        mock_git(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 1
        text = result.render()
        assert "counts unparseable" in text
        assert "no tests collected" not in text
        assert "addopts" in text  # 干扰提示


# ===========================================================================
# junitxml 契约单测:解析防御 + 临时文件生命周期
# ===========================================================================


class TestParseJunitCounts:
    def test_missing_file_is_none(self, tmp_path):
        assert parse_junit_counts(str(tmp_path / "nope.xml")) is None

    def test_garbage_xml_is_none(self, tmp_path):
        p = tmp_path / "bad.xml"
        p.write_text("<not-xml")
        assert parse_junit_counts(str(p)) is None

    def test_real_counts(self, tmp_path):
        p = tmp_path / "j.xml"
        p.write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<testsuites><testsuite name="pytest" errors="1" failures="2" '
            'skipped="3" tests="10" time="0.1"></testsuite></testsuites>'
        )
        assert parse_junit_counts(str(p)) == {
            "passed": 4, "failed": 2, "skipped": 3, "errors": 1,
        }

    def test_junit_file_removed_after_run(self, tmp_path, monkeypatch):
        repo = _make_repo(tmp_path, addopts="-q", tests=_suite(n_pass=1))
        created = []
        real_mkstemp = commit_gate.tempfile.mkstemp

        def spy_mkstemp(*a, **kw):
            fd, path = real_mkstemp(*a, **kw)
            created.append(path)
            return fd, path

        monkeypatch.setattr(commit_gate.tempfile, "mkstemp", spy_mkstemp)
        mock_git(monkeypatch)
        run_gate(repo)
        assert created, "junit temp file was never created"
        import os

        assert not any(os.path.exists(p) for p in created)
