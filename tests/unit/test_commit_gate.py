"""STORY-slim-138: commit-gate pre-commit test gate."""

import json

import pytest

from pactkit import commit_gate
from pactkit.commit_gate import (
    GateUnavailable,
    decide_test_set,
    hook_entry,
    install_git_hook,
    install_hook,
    parse_pytest_summary,
    run_gate,
    run_pytest,
)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A fake git project root; git/pytest calls are mocked per-test."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    return tmp_path


def mock_git(monkeypatch, branch="feature/x", changed=("src/pkg/mod.py",)):
    monkeypatch.setattr(commit_gate, "collect_changed_files", lambda root: list(changed))
    monkeypatch.setattr(commit_gate, "current_branch", lambda root: branch)


def mock_pytest(monkeypatch, returncode=0, output="10 passed in 1.0s"):
    calls = {}

    def _run(root, test_files):
        calls["test_files"] = test_files
        return returncode, output

    monkeypatch.setattr(commit_gate, "run_pytest", _run)
    return calls


def test_run_pytest_does_not_leak_parent_git_repository_environment(repo, monkeypatch):
    observed = {}

    def fake_run(command, **kwargs):
        observed.update(kwargs["env"])
        return type("Result", (), {"returncode": 0, "stdout": "1 passed", "stderr": ""})()

    monkeypatch.setenv("GIT_INDEX_FILE", "/parent/.git/index.lock")
    monkeypatch.setenv("GIT_DIR", "/parent/.git")
    monkeypatch.setenv("GIT_WORK_TREE", "/parent")
    monkeypatch.setenv("PACTKIT_KEEP_ME", "yes")
    monkeypatch.setattr(commit_gate.subprocess, "run", fake_run)

    assert run_pytest(repo, None) == (0, "1 passed")
    assert "GIT_INDEX_FILE" not in observed
    assert "GIT_DIR" not in observed
    assert "GIT_WORK_TREE" not in observed
    assert observed["PACTKIT_KEEP_ME"] == "yes"


# ---------------------------------------------------------------------------
# AC1: red tests block
# ---------------------------------------------------------------------------


class TestRedBlocks:
    def test_failing_tests_exit_1(self, repo, monkeypatch):
        mock_git(monkeypatch)
        mock_pytest(monkeypatch, returncode=1,
                    output="FAILED tests/unit/test_a.py::test_x - assert 1 == 2\n1 failed, 9 passed in 1.0s")
        result = run_gate(repo)
        assert result.exit_code == 1
        text = result.render()
        assert "9 passed, 1 failed" in text
        assert "FAILED tests/unit/test_a.py" in text


# ---------------------------------------------------------------------------
# AC2: IMPACT runs only mapped tests
# ---------------------------------------------------------------------------


class TestImpactSelection:
    def test_mapped_subset_only(self, repo, monkeypatch):
        mock_git(monkeypatch, changed=("src/pactkit/done_verify.py",))
        (repo / "tests" / "unit" / "test_done_verify.py").write_text("")
        calls = mock_pytest(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 0
        assert calls["test_files"] == ["tests/unit/test_done_verify.py"]
        assert "IMPACT" in result.render()

    def test_empty_mapping_falls_back_to_full(self, repo, monkeypatch):
        mock_git(monkeypatch, changed=("src/pactkit/no_such_module.py",))
        calls = mock_pytest(monkeypatch)
        run_gate(repo)
        assert calls["test_files"] is None  # full suite

    def test_doc_only_skips(self, repo, monkeypatch):
        mock_git(monkeypatch, changed=("docs/specs/STORY-x.md",))
        calls = mock_pytest(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 0
        assert "test_files" not in calls  # pytest never invoked
        assert "SKIP" in result.render()


# ---------------------------------------------------------------------------
# AC3: skip transparency
# ---------------------------------------------------------------------------


class TestSkipTransparency:
    OUTPUT = (
        "SKIPPED [1] tests/unit/test_pg.py:10: PG unreachable\n"
        "SKIPPED [1] tests/unit/test_pg.py:20: PG unreachable\n"
        "SKIPPED [1] tests/unit/test_pg.py:30: PG unreachable\n"
        "10 passed, 3 skipped in 2.0s"
    )

    def test_skips_are_listed_not_absorbed(self, repo, monkeypatch):
        mock_git(monkeypatch)
        mock_pytest(monkeypatch, output=self.OUTPUT)
        result = run_gate(repo)
        assert result.exit_code == 0  # skips alone do not block
        text = result.render()
        assert "10 passed, 0 failed, 3 skipped" in text
        assert "SKIPPED" in text and "PG unreachable" in text
        assert "skip != pass" in text

    def test_parse_counts(self):
        summary = parse_pytest_summary(self.OUTPUT)
        assert summary["passed"] == 10
        assert summary["skipped"] == 3
        assert summary["failed"] == 0
        assert len(summary["skip_reasons"]) == 3


# ---------------------------------------------------------------------------
# AC4/AC5: hook mode
# ---------------------------------------------------------------------------


class TestHookMode:
    def _payload(self, command):
        return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})

    def test_non_commit_exits_0_silently(self, repo, monkeypatch):
        mock_git(monkeypatch)
        calls = mock_pytest(monkeypatch)
        _, code = hook_entry(self._payload("git status"), repo)
        assert code == 0
        assert "test_files" not in calls

    def test_commit_red_blocks_with_exit_2(self, repo, monkeypatch):
        mock_git(monkeypatch)
        mock_pytest(monkeypatch, returncode=1, output="1 failed in 1.0s")
        stderr, code = hook_entry(self._payload('git commit -m "x"'), repo)
        assert code == 2
        assert "blocked" in stderr

    def test_commit_green_allows(self, repo, monkeypatch):
        mock_git(monkeypatch)
        mock_pytest(monkeypatch)
        _, code = hook_entry(self._payload('git commit -m "x"'), repo)
        assert code == 0

    def test_commit_with_flags_detected(self, repo, monkeypatch):
        mock_git(monkeypatch)
        mock_pytest(monkeypatch, returncode=1, output="1 failed in 1.0s")
        _, code = hook_entry(self._payload('git -C /repo commit --amend'), repo)
        assert code == 2

    def test_no_verify_still_gates(self, repo, monkeypatch):
        """STORY-slim-202608289e83eeb30df4 R3: --no-verify is no longer a free
        bypass — the agent can type it, so the PreToolUse gate still runs."""
        mock_git(monkeypatch)
        mock_pytest(monkeypatch, returncode=1, output="1 failed in 1.0s")
        stderr, code = hook_entry(self._payload('git commit --no-verify -m "x"'), repo)
        assert code == 2
        assert "blocked" in stderr

    def test_gate_failure_allows_with_warn(self, repo, monkeypatch):
        """AC5 self-lock protection: pytest missing must not block commits."""
        mock_git(monkeypatch)

        def _boom(root, test_files):
            raise GateUnavailable("pytest not found")

        monkeypatch.setattr(commit_gate, "run_pytest", _boom)
        stderr, code = hook_entry(self._payload('git commit -m "fix gate"'), repo)
        assert code == 0
        assert "commit-gate unavailable" in stderr

    def test_malformed_stdin_allows(self, repo):
        _, code = hook_entry("not json", repo)
        assert code == 0


# ---------------------------------------------------------------------------
# AC7: main-branch commits always run the full suite
# ---------------------------------------------------------------------------


class TestMainBranchStance:
    """STORY-slim-202608289e83eeb30df4 R2: main/master block by default;
    develop (not in the default protected set) keeps the full-suite rule."""

    @pytest.mark.parametrize("branch", ["main", "master"])
    def test_protected_branch_blocks(self, repo, monkeypatch, branch):
        mock_git(monkeypatch, branch=branch, changed=("src/pactkit/done_verify.py",))
        strategy, test_files, reason = decide_test_set(repo, ["src/pactkit/done_verify.py"])
        assert strategy == "blocked"
        assert branch in reason

    @pytest.mark.parametrize("branch", ["develop"])
    def test_develop_still_forces_full(self, repo, monkeypatch, branch):
        mock_git(monkeypatch, branch=branch, changed=("src/pactkit/done_verify.py",))
        (repo / "tests" / "unit" / "test_done_verify.py").write_text("")
        strategy, test_files, reason = decide_test_set(repo, ["src/pactkit/done_verify.py"])
        assert strategy == "full"
        assert test_files is None
        assert branch in reason


# ---------------------------------------------------------------------------
# AC6: hook deployment
# ---------------------------------------------------------------------------


class TestHookDeployment:
    def test_install_into_empty_settings(self, repo):
        msg = install_hook(repo)
        settings = json.loads((repo / ".claude" / "settings.json").read_text())
        entries = settings["hooks"]["PreToolUse"]
        # Bash feeds the commit/push pipeline, Edit|Write the tamper guard,
        # Skill the command_invoked telemetry (STORY-slim-20260830c65491123af1 R4).
        assert {e["matcher"] for e in entries} == {"Bash", "Edit|Write", "Skill"}
        assert all(e["hooks"][0]["command"] == "pactkit commit-gate --hook" for e in entries)
        assert "installed" in msg

    def test_preserves_user_config_and_idempotent(self, repo):
        (repo / ".claude").mkdir(exist_ok=True)
        existing = {"model": "opus", "hooks": {"PreToolUse": [{"matcher": "Write", "hooks": [
            {"type": "command", "command": "my-formatter"}]}]}}
        (repo / ".claude" / "settings.json").write_text(json.dumps(existing))
        install_hook(repo)
        install_hook(repo)  # twice
        settings = json.loads((repo / ".claude" / "settings.json").read_text())
        assert settings["model"] == "opus"
        pre = settings["hooks"]["PreToolUse"]
        assert len(pre) == 4  # user's + our three matchers, no duplication
        assert sum("commit-gate" in h.get("command", "") for e in pre for h in e["hooks"]) == 3

    def test_invalid_json_left_untouched(self, repo):
        (repo / ".claude").mkdir(exist_ok=True)
        (repo / ".claude" / "settings.json").write_text("{oops")
        msg = install_hook(repo)
        assert "left untouched" in msg
        assert (repo / ".claude" / "settings.json").read_text() == "{oops"

    def test_no_git_skips_install(self, repo):
        (repo / ".claude").mkdir(exist_ok=True)
        (repo / ".claude" / "pactkit.yaml").write_text("enterprise:\n  no_git: true\n")
        msg = install_hook(repo)
        assert "no_git" in msg
        assert not (repo / ".claude" / "settings.json").exists()


class TestGitHook:
    def test_fresh_install(self, repo):
        (repo / ".git" / "hooks").mkdir()
        msg = install_git_hook(repo)
        hook = repo / ".git" / "hooks" / "pre-commit"
        assert "pactkit commit-gate" in hook.read_text()
        assert "installed" in msg

    def test_missing_binary_warns_and_allows(self, repo):
        """HOTFIX-slim-20260828ee6cde3108fb: without the PATH probe, a missing
        pactkit binary exits 127 and git blocks every commit."""
        (repo / ".git" / "hooks").mkdir()
        install_git_hook(repo)
        script = (repo / ".git" / "hooks" / "pre-commit").read_text()
        assert "command -v pactkit" in script
        assert "exit 0" in script  # WARN + allow, never lock out

    def test_chains_existing_hook(self, repo):
        hooks = repo / ".git" / "hooks"
        hooks.mkdir()
        (hooks / "pre-commit").write_text("#!/bin/sh\necho existing\n")
        msg = install_git_hook(repo)
        content = (hooks / "pre-commit").read_text()
        assert "echo existing" in content
        assert "pactkit commit-gate" in content
        assert "command -v pactkit" in content  # probe present when chaining too
        assert (hooks / "pre-commit.pre-pactkit").exists()
        assert "chained" in msg


# ---------------------------------------------------------------------------
# STORY-slim-140: format-aware gate channel dispatch
# ---------------------------------------------------------------------------


class TestGateChannelDispatch:
    def test_classic_gets_pretooluse(self, repo):
        from pactkit.commit_gate import ensure_gate_channel

        channel = ensure_gate_channel(repo, "classic")
        assert channel == "PreToolUse hook"
        settings = json.loads((repo / ".claude" / "settings.json").read_text())
        assert "commit-gate" in settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        assert not (repo / ".git" / "hooks" / "pre-commit").exists()

    def test_non_claude_gets_git_hook(self, repo):
        """AC1 (amended, STORY-slim-20260827024e71df170f R4): codex deploy
        installs the native hooks.json channel plus the git pre-commit
        fallback (active until the user completes Codex's trust prompt).
        STORY-slim-202608289e83eeb30df4 R6 adds the pre-push fallback."""
        from pactkit.commit_gate import ensure_gate_channel

        (repo / ".git" / "hooks").mkdir()
        channel = ensure_gate_channel(repo, "codex")
        assert channel == "codex PreToolUse hook + git pre-commit + git pre-push"
        assert (repo / ".codex" / "hooks.json").is_file()
        assert "pactkit commit-gate" in (repo / ".git" / "hooks" / "pre-commit").read_text()
        assert "push-gate" in (repo / ".git" / "hooks" / "pre-push").read_text()
        assert not (repo / ".claude" / "settings.json").exists()

    def test_non_claude_without_git_repo(self, repo):
        from pactkit.commit_gate import ensure_gate_channel

        (repo / ".git").rmdir()  # remove the fixture's .git
        channel = ensure_gate_channel(repo, "opencode")
        assert channel.startswith("none")

    def test_no_git_disables_everything(self, repo):
        """AC3: enterprise.no_git -> no hook of any kind, explicit channel."""
        from pactkit.commit_gate import ensure_gate_channel

        (repo / ".claude").mkdir(exist_ok=True)
        (repo / ".claude" / "pactkit.yaml").write_text("enterprise:\n  no_git: true\n")
        (repo / ".git" / "hooks").mkdir()
        channel = ensure_gate_channel(repo, "codex")
        assert "no_git" in channel
        assert not (repo / ".git" / "hooks" / "pre-commit").exists()

    def test_idempotent_and_chained(self, repo):
        """AC4: repeat dispatch keeps third-party hook content, single entry."""
        from pactkit.commit_gate import ensure_gate_channel

        hooks = repo / ".git" / "hooks"
        hooks.mkdir()
        (hooks / "pre-commit").write_text("#!/bin/sh\necho third-party\n")
        ensure_gate_channel(repo, "codex")
        ensure_gate_channel(repo, "codex")
        content = (hooks / "pre-commit").read_text()
        assert "echo third-party" in content
        assert content.count("pactkit commit-gate") == 1
