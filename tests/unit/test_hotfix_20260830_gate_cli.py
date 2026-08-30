"""HOTFIX-slim-20260830bbb5bc219d35: gate CLI syntax + cross-repo push root.

Two defects from the 2.25.0 release run:
  1. auth-gate's documented `pactkit gate authorize <scope>` failed —
     the parser only accepted the bare positional form.
  2. push-gate judged `cd <other-repo> && git push` by the SESSION cwd's
     enforcement config instead of the target repo's.
"""

import json
from pathlib import Path

import pytest

from pactkit import commit_gate
from pactkit.commit_gate import hook_entry


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.setattr(
        commit_gate,
        "_enforcement_settings",
        lambda root: {
            "protected_branches": ["main", "master"],
            "allow_direct_push": False,
            "tamper_guard": True,
            "spec_guard": True,
            "auth_gate": True,
            "secrets_gate": True,
            "auth_ttl_minutes": 30,
        },
    )
    return tmp_path


def _payload(command, cwd=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd:
        payload["cwd"] = str(cwd)
    return json.dumps(payload)


# ===========================================================================
# Fix 1: gate CLI accepts the documented `authorize <scope>` form
# ===========================================================================


class TestGateCliSyntax:
    def _run_cli(self, argv, tmp_path):
        import sys

        from pactkit.cli import main

        # the CLI requires an init marker before dispatching any command
        marker = tmp_path / ".claude" / "pactkit.yaml"
        marker.parent.mkdir(exist_ok=True)
        marker.write_text("stack: python\n", encoding="utf-8")

        old_argv = sys.argv
        sys.argv = ["pactkit", "-C", str(tmp_path), "gate", *argv]
        try:
            main()
        except SystemExit as exc:
            return exc.code
        finally:
            sys.argv = old_argv
        return 0

    def test_authorize_keyword_form(self, tmp_path, capsys):
        code = self._run_cli(["authorize", "release", "--ttl-minutes", "5"], tmp_path)
        assert code in (0, None)
        token = json.loads(
            (tmp_path / ".pactkit" / "enforcement" / "authorization.json").read_text()
        )
        assert token["scope"] == "release"
        assert "authorized" in capsys.readouterr().out

    def test_bare_scope_form_still_works(self, tmp_path, capsys):
        code = self._run_cli(["release", "--ttl-minutes", "5"], tmp_path)
        assert code in (0, None)
        token = json.loads(
            (tmp_path / ".pactkit" / "enforcement" / "authorization.json").read_text()
        )
        assert token["scope"] == "release"

    def test_authorize_without_scope_errors(self, tmp_path):
        code = self._run_cli(["authorize"], tmp_path)
        assert code not in (0, None)


# ===========================================================================
# Fix 2: push-gate evaluates the command's target repo
# ===========================================================================


class TestCrossRepoPushRoot:
    def test_cd_to_strict_repo_blocks(self, repo, tmp_path_factory, monkeypatch):
        """Target repo has default (protective) config; session repo allows."""
        other = tmp_path_factory.mktemp("other-repo")
        (other / ".git" / "hooks").mkdir(parents=True)
        monkeypatch.setattr(
            commit_gate,
            "_enforcement_settings",
            lambda root: (
                {"protected_branches": ["main"], "allow_direct_push": True,
                 "tamper_guard": False, "spec_guard": True, "auth_gate": True,
                 "secrets_gate": True, "auth_ttl_minutes": 30}
                if Path(root) == Path(repo)
                else {"protected_branches": ["main", "master"],
                      "allow_direct_push": False, "tamper_guard": True,
                      "spec_guard": True, "auth_gate": True,
                      "secrets_gate": True, "auth_ttl_minutes": 30}
            ),
        )
        monkeypatch.setattr(commit_gate, "current_branch",
                            lambda root: "main" if Path(root) == Path(other) else "feature/x")
        monkeypatch.setattr(commit_gate, "run_pytest", lambda root, tf: (0, "1 passed"))

        _, code = hook_entry(
            _payload(f"cd {other} && git push origin main", cwd=repo), repo
        )
        assert code == 2  # judged by the TARGET repo's protective config

    def test_cd_to_permissive_repo_allows(self, repo, tmp_path_factory, monkeypatch):
        """Target repo allows direct push; session repo is protective."""
        other = tmp_path_factory.mktemp("other-repo")
        (other / ".git" / "hooks").mkdir(parents=True)
        monkeypatch.setattr(
            commit_gate,
            "_enforcement_settings",
            lambda root: (
                {"protected_branches": ["main"], "allow_direct_push": True,
                 "tamper_guard": False, "spec_guard": True, "auth_gate": True,
                 "secrets_gate": True, "auth_ttl_minutes": 30}
                if Path(root) == Path(other)
                else {"protected_branches": ["main", "master"],
                      "allow_direct_push": False, "tamper_guard": True,
                      "spec_guard": True, "auth_gate": True,
                      "secrets_gate": True, "auth_ttl_minutes": 30}
            ),
        )
        monkeypatch.setattr(commit_gate, "current_branch",
                            lambda root: "main" if Path(root) == Path(other) else "feature/x")

        _, code = hook_entry(
            _payload(f"cd {other} && git push origin main", cwd=repo), repo
        )
        assert code == 0

    def test_relative_cd_resolved_against_session_root(self, repo, monkeypatch):
        (repo / "sub" / ".git").mkdir(parents=True)
        monkeypatch.setattr(commit_gate, "current_branch",
                            lambda root: "main" if root.name == "sub" else "feature/x")
        monkeypatch.setattr(commit_gate, "run_pytest", lambda root, tf: (0, "1 passed"))
        _, code = hook_entry(_payload("cd sub && git push origin main", cwd=repo), repo)
        assert code == 2

    def test_cd_to_nonexistent_dir_falls_back_to_session_root(self, repo, monkeypatch):
        """A cd that doesn't resolve must not crash or misroute."""
        monkeypatch.setattr(commit_gate, "current_branch", lambda root: "feature/x")
        _, code = hook_entry(_payload("cd /no/such/dir && git push origin feature/x", cwd=repo), repo)
        assert code == 0  # feature branch in session root: allowed
