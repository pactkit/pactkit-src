"""STORY-slim-202608289e83eeb30df4: protected-branch push gate + L1 override protocol.

Covers AC1-AC8 of docs/specs/STORY-slim-202608289e83eeb30df4.md:

  AC1  agent push to protected branch is blocked (exit 2, actionable message)
  AC2  push to a feature branch passes fast (pytest never invoked)
  AC3  PACTKIT_ALLOW_DIRECT_PUSH=1 human bypass allows + is audited
  AC4  direct commit on protected branch blocked by default; config/env re-opens
  AC5  --no-verify no longer free-passes the PreToolUse channel
  AC6  L1 override protocol present in the deployed rules text
  AC7  tamper guard blocks enforcement-artifact modification
  AC8  channel parity (pre-push hook, dual matcher, GATES/probes)
"""

import inspect
import json

import pytest

from pactkit import commit_gate
from pactkit.commit_gate import (
    PUSH_BYPASS_ENV,
    hook_entry,
    install_hook,
    install_pre_push_hook,
    resolve_push_target,
    run_gate,
)
from pactkit.tamper_guard import CONFIG_EDIT_BYPASS_ENV


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A fake git project root; git/pytest calls are mocked per-test."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    # Default enforcement settings: main/master protected, everything strict.
    monkeypatch.setattr(
        commit_gate,
        "_enforcement_settings",
        lambda root: {
            "protected_branches": ["main", "master"],
            "allow_direct_push": False,
            "tamper_guard": True,
        },
    )
    return tmp_path


def mock_git(monkeypatch, branch="feature/x", changed=("src/pkg/mod.py",)):
    monkeypatch.setattr(commit_gate, "collect_changed_files", lambda root: list(changed))
    monkeypatch.setattr(commit_gate, "current_branch", lambda root: branch)


def mock_pytest(monkeypatch, returncode=0, output="10 passed in 1.0s"):
    calls = {}

    def _run(root, test_files):
        calls["test_files"] = test_files
        return returncode, output, None

    monkeypatch.setattr(commit_gate, "run_pytest", _run)
    return calls


def _payload(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def _tool_payload(tool_name, **tool_input):
    return json.dumps({"tool_name": tool_name, "tool_input": tool_input})


def _record(repo, gate):
    path = repo / ".pactkit" / "enforcement" / f"{gate}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


# ===========================================================================
# AC1: agent push to a protected branch is blocked
# ===========================================================================


class TestPushBlocked:
    def test_bare_push_on_main_blocks(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        mock_pytest(monkeypatch)
        stderr, code = hook_entry(_payload("git push"), repo)
        assert code == 2
        assert "protected branch" in stderr
        assert "pull request" in stderr.lower() or "PR" in stderr
        assert PUSH_BYPASS_ENV in stderr

    @pytest.mark.parametrize(
        "command",
        [
            "git push origin main",
            "git push origin master",
            "git push origin HEAD",
            "git push origin HEAD:main",
            "git push origin refs/heads/main",
            "git -C /repo push origin main",
            "git push --force origin main",
        ],
    )
    def test_push_refspec_forms_block(self, repo, monkeypatch, command):
        mock_git(monkeypatch, branch="main")
        mock_pytest(monkeypatch)
        _, code = hook_entry(_payload(command), repo)
        assert code == 2

    def test_block_is_audited(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        mock_pytest(monkeypatch)
        hook_entry(_payload("git push origin main"), repo)
        record = _record(repo, "push_gate")
        assert record is not None
        assert "main" in (record.get("reason") or record.get("last_run", {}).get("reason") or "")

    def test_push_delete_refspec_blocks(self, repo, monkeypatch):
        """`git push origin :main` deletes remote main — must block too."""
        mock_git(monkeypatch, branch="feature/x")
        mock_pytest(monkeypatch)
        _, code = hook_entry(_payload("git push origin :main"), repo)
        assert code == 2


# ===========================================================================
# AC2: push to a feature branch passes fast (pytest never invoked)
# ===========================================================================


class TestPushAllowed:
    def test_feature_branch_push_allows_without_pytest(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="feature/STORY-x-desc")
        calls = mock_pytest(monkeypatch)
        stderr, code = hook_entry(_payload("git push -u origin feature/STORY-x-desc"), repo)
        assert code == 0
        assert "test_files" not in calls  # sub-second: no pytest ever runs

    def test_non_git_command_untouched(self, repo, monkeypatch):
        mock_git(monkeypatch)
        calls = mock_pytest(monkeypatch)
        _, code = hook_entry(_payload("ls -la"), repo)
        assert code == 0
        assert "test_files" not in calls

    def test_unresolvable_target_allows_with_warn(self, repo, monkeypatch):
        """R1: branch unresolvable → allow + WARN + DEGRADED (fail-open by design)."""
        mock_git(monkeypatch, branch="")  # detached HEAD / probe failure
        mock_pytest(monkeypatch)
        stderr, code = hook_entry(_payload("git push"), repo)
        assert code == 0
        assert "WARN" in stderr
        record = _record(repo, "push_gate")
        assert record["status"] == "degraded"


# ===========================================================================
# AC3: human bypass env var allows the push and is audited
# ===========================================================================


class TestPushBypass:
    def test_env_bypass_allows_push(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        mock_pytest(monkeypatch)
        monkeypatch.setenv(PUSH_BYPASS_ENV, "1")
        stderr, code = hook_entry(_payload("git push origin main"), repo)
        assert code == 0
        assert "bypass" in stderr.lower()

    def test_env_bypass_audited(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        mock_pytest(monkeypatch)
        monkeypatch.setenv(PUSH_BYPASS_ENV, "1")
        hook_entry(_payload("git push origin main"), repo)
        record = _record(repo, "push_gate")
        assert record is not None
        assert record["status"] == "full"


# ===========================================================================
# AC4: direct commit on protected branch blocked by default (R2)
# ===========================================================================


class TestCommitOnMainBlocked:
    def test_commit_on_main_blocks_by_default(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        calls = mock_pytest(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 1
        assert "test_files" not in calls  # blocked before any pytest run
        assert "protected branch" in result.render()

    def test_commit_on_main_with_allow_config_runs_full_suite(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        calls = mock_pytest(monkeypatch)
        monkeypatch.setattr(
            commit_gate,
            "_enforcement_settings",
            lambda root: {
                "protected_branches": ["main", "master"],
                "allow_direct_push": True,
                "tamper_guard": True,
            },
        )
        result = run_gate(repo)
        assert result.exit_code == 0
        assert calls["test_files"] is None  # full suite — pre-existing behavior

    def test_commit_on_main_with_env_bypass_runs_full_suite(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        calls = mock_pytest(monkeypatch)
        monkeypatch.setenv(PUSH_BYPASS_ENV, "1")
        result = run_gate(repo)
        assert result.exit_code == 0
        assert calls["test_files"] is None

    def test_develop_still_full_suite(self, repo, monkeypatch):
        """Develop is not in the default protected set — old behavior preserved."""
        mock_git(monkeypatch, branch="develop", changed=("src/pactkit/done_verify.py",))
        calls = mock_pytest(monkeypatch)
        result = run_gate(repo)
        assert result.exit_code == 0
        assert calls["test_files"] is None
        assert "develop" in result.render()

    def test_custom_protected_branches_respected(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="release")
        mock_pytest(monkeypatch)
        monkeypatch.setattr(
            commit_gate,
            "_enforcement_settings",
            lambda root: {
                "protected_branches": ["release"],
                "allow_direct_push": False,
                "tamper_guard": True,
            },
        )
        result = run_gate(repo)
        assert result.exit_code == 1


# ===========================================================================
# AC5: --no-verify no longer free-passes the PreToolUse channel (R3)
# ===========================================================================


class TestNoVerifyClosed:
    def test_no_verify_still_gates_red_tests(self, repo, monkeypatch):
        mock_git(monkeypatch)
        mock_pytest(monkeypatch, returncode=1, output="1 failed in 1.0s")
        stderr, code = hook_entry(_payload('git commit --no-verify -m "x"'), repo)
        assert code == 2
        assert "blocked" in stderr

    def test_no_verify_green_allows(self, repo, monkeypatch):
        mock_git(monkeypatch)
        mock_pytest(monkeypatch)
        _, code = hook_entry(_payload('git commit --no-verify -m "x"'), repo)
        assert code == 0


# ===========================================================================
# AC7: tamper guard blocks enforcement-artifact modification (R5)
# ===========================================================================


class TestTamperGuard:
    def test_edit_git_hook_blocked(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        stderr, code = hook_entry(
            _tool_payload("Edit", file_path=str(repo / ".git" / "hooks" / "pre-commit"),
                          old_string="exec pactkit commit-gate",
                          new_string="true"),
            repo,
        )
        assert code == 2
        assert "tamper" in stderr.lower()

    def test_write_codex_hooks_blocked(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        _, code = hook_entry(
            _tool_payload("Write", file_path=str(repo / ".codex" / "hooks.json"),
                          content="{}"),
            repo,
        )
        assert code == 2

    def test_edit_settings_removing_gate_entry_blocked(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        settings = repo / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps(
            {"hooks": {"PreToolUse": [{"matcher": "Bash",
             "hooks": [{"type": "command", "command": "pactkit commit-gate --hook"}]}]}}))
        stderr, code = hook_entry(
            _tool_payload("Edit", file_path=str(settings),
                          old_string='"command": "pactkit commit-gate --hook"',
                          new_string='"command": "true"'),
            repo,
        )
        assert code == 2

    def test_edit_settings_other_content_allowed(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        settings = repo / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"permissions": {"allow": ["ls"]}}))
        _, code = hook_entry(
            _tool_payload("Edit", file_path=str(settings),
                          old_string='"ls"', new_string='"pwd"'),
            repo,
        )
        assert code == 0

    def test_bash_write_to_git_hooks_blocked(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        _, code = hook_entry(_payload("rm .git/hooks/pre-commit"), repo)
        assert code == 2

    def test_bash_redirect_to_codex_hooks_blocked(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        _, code = hook_entry(_payload("echo '{}' > .codex/hooks.json"), repo)
        assert code == 2

    def test_bash_write_to_enforcement_records_blocked(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        _, code = hook_entry(_payload("rm -rf .pactkit/enforcement"), repo)
        assert code == 2

    def test_bash_read_of_protected_path_allowed(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        _, code = hook_entry(_payload("cat .git/hooks/pre-commit"), repo)
        assert code == 0

    def test_bypass_env_allows_tamper_edit(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        monkeypatch.setenv(CONFIG_EDIT_BYPASS_ENV, "1")
        _, code = hook_entry(
            _tool_payload("Edit", file_path=str(repo / ".git" / "hooks" / "pre-commit"),
                          old_string="exec pactkit commit-gate", new_string="true"),
            repo,
        )
        assert code == 0

    def test_tamper_guard_disabled_by_config(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        monkeypatch.setattr(
            commit_gate,
            "_enforcement_settings",
            lambda root: {
                "protected_branches": ["main", "master"],
                "allow_direct_push": False,
                "tamper_guard": False,
            },
        )
        _, code = hook_entry(
            _tool_payload("Edit", file_path=str(repo / ".git" / "hooks" / "pre-commit"),
                          old_string="exec pactkit commit-gate", new_string="true"),
            repo,
        )
        assert code == 0

    def test_blocked_tamper_is_audited(self, repo, monkeypatch):
        mock_pytest(monkeypatch)
        hook_entry(_payload("rm .git/hooks/pre-commit"), repo)
        assert _record(repo, "tamper_guard") is not None


# ===========================================================================
# AC6: L1 override protocol present in the deployed rules text (R4)
# ===========================================================================


class TestRulesText:
    def test_override_protocol_present(self):
        from pactkit.prompts import rules

        source = inspect.getsource(rules)
        assert "Override Protocol" in source
        assert PUSH_BYPASS_ENV in source
        # Hard rules MUST NOT be waivable in-conversation
        assert "MUST NOT" in source

    def test_protected_branch_is_l1(self):
        from pactkit.prompts import rules

        source = inspect.getsource(rules)
        assert "protected-branch direct push" in source
        # Rule/hook tampering is Spec tampering — explicitly L1
        assert "enforcement-artifact tampering" in source


# ===========================================================================
# AC8: channel parity — pre-push hook, dual matcher, GATES/probes (R6)
# ===========================================================================


class TestChannelParity:
    def test_install_hook_registers_edit_write_matcher(self, repo):
        install_hook(repo)
        settings = json.loads((repo / ".claude" / "settings.json").read_text())
        matchers = {e["matcher"] for e in settings["hooks"]["PreToolUse"]}
        assert "Bash" in matchers
        assert "Edit|Write" in matchers

    def test_install_pre_push_hook(self, repo):
        msg = install_pre_push_hook(repo)
        script = (repo / ".git" / "hooks" / "pre-push").read_text()
        assert "commit-gate" in script
        assert "command -v pactkit" in script  # HOTFIX-slim-20260828ee6cde3108fb probe
        assert "installed" in msg

    def test_install_pre_push_hook_idempotent(self, repo):
        install_pre_push_hook(repo)
        msg = install_pre_push_hook(repo)
        assert "already installed" in msg

    def test_gates_registry_extended(self):
        from pactkit import enforcement

        assert "push_gate" in enforcement.GATES
        assert "tamper_guard" in enforcement.GATES
        assert "push_gate" in enforcement._PROBES
        assert "tamper_guard" in enforcement._PROBES

    def test_probe_push_gate_unavailable_outside_repo(self, tmp_path):
        from pactkit import enforcement

        probe = enforcement.probe_push_gate(tmp_path)
        assert probe["status"] == "unavailable"


# ===========================================================================
# refspec parsing unit tests (R1)
# ===========================================================================


class TestResolvePushTarget:
    def test_bare_push_uses_current_branch(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="feature/x")
        assert resolve_push_target("git push", repo) == "feature/x"

    def test_remote_only_uses_current_branch(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="feature/x")
        assert resolve_push_target("git push origin", repo) == "feature/x"

    def test_head_refspec_uses_current_branch(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        assert resolve_push_target("git push origin HEAD", repo) == "main"

    def test_explicit_refspec(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="feature/x")
        assert resolve_push_target("git push origin main", repo) == "main"

    def test_colon_refspec_uses_dst(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="feature/x")
        assert resolve_push_target("git push origin HEAD:main", repo) == "main"

    def test_delete_refspec_uses_dst(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="feature/x")
        assert resolve_push_target("git push origin :main", repo) == "main"

    def test_refs_heads_prefix_stripped(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="feature/x")
        assert resolve_push_target("git push origin refs/heads/main", repo) == "main"

    def test_flags_skipped(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="feature/x")
        assert resolve_push_target("git push --force-with-lease origin main", repo) == "main"

    def test_unresolvable_returns_empty(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="")
        assert resolve_push_target("git push", repo) == ""


# ===========================================================================
# Block messages advertise the config channel for single maintainers
# ===========================================================================


class TestBlockMessageConfigHint:
    """Blocked messages must tell single maintainers their sanctioned channel.

    The terse 'config: enforcement.allow_direct_push' mention was easy to
    miss: in a 2026-09-03 blocked session the user relayed only the
    feature-branch and env-bypass channels, dropping the config one. The
    message must state WHO the config channel is for.
    """

    def test_push_block_message_names_single_maintainer_channel(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        mock_pytest(monkeypatch)
        stderr, code = hook_entry(_payload("git push origin main"), repo)
        assert code == 2
        assert "allow_direct_push" in stderr
        assert "single-maintainer" in stderr

    def test_commit_block_message_names_single_maintainer_channel(self, repo, monkeypatch):
        mock_git(monkeypatch, branch="main")
        result = run_gate(repo)
        assert result.exit_code == 1
        rendered = result.render()
        assert "protected branch" in rendered
        assert "allow_direct_push" in rendered
        assert "single-maintainer" in rendered


# ===========================================================================
# Codegraph auto-detect default (user rule: installed on machine = enabled)
# ===========================================================================


class TestCodegraphAutoDetect:
    """graph_provider unset + codegraph installed + index present -> codegraph.

    User rule (2026-09-03): a machine-installed codegraph MUST be the default
    provider; per-project yaml config must not be a prerequisite.
    """

    def test_autodetect_picks_codegraph_when_installed_and_indexed(self, tmp_path, monkeypatch):
        from pactkit.graph_query import detect_graph_provider

        (tmp_path / ".codegraph").mkdir()
        (tmp_path / ".codegraph" / "codegraph.db").write_bytes(b"x")
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/codegraph" if name == "codegraph" else None)
        assert detect_graph_provider(tmp_path) == "codegraph"

    def test_autodetect_falls_back_when_no_index(self, tmp_path, monkeypatch):
        from pactkit.graph_query import detect_graph_provider

        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/codegraph" if name == "codegraph" else None)
        assert detect_graph_provider(tmp_path) is None

    def test_autodetect_falls_back_when_not_installed(self, tmp_path, monkeypatch):
        from pactkit.graph_query import detect_graph_provider

        (tmp_path / ".codegraph" / "codegraph.db").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / ".codegraph" / "codegraph.db").write_bytes(b"x")
        monkeypatch.setattr("shutil.which", lambda name: None)
        assert detect_graph_provider(tmp_path) is None
