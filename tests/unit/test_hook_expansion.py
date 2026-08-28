"""STORY-slim-20260828897396a935ab: hook coverage expansion.

Covers AC1-AC6 of docs/specs/STORY-slim-20260828897396a935ab.md:

  AC1  SessionStart regenerates and prints context; failure degrades to WARN
  AC2  PreCompact refreshes state, never blocks compaction
  AC3  spec_guard blocks Act-phase spec edits; receipt absent = allowed
  AC4  auth_gate blocks external-effect commands; TTL token re-opens
  AC5  secrets_gate blocks literal credentials; env indirection exempt
  AC6  registration (SessionStart/PreCompact), config keys, doctor probes
"""

import json

import pytest

from pactkit import commit_gate
from pactkit.commit_gate import hook_entry, install_hook


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A fake git project root with full enforcement settings mocked."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
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


def _payload(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def _tool_payload(tool_name, **tool_input):
    return json.dumps({"tool_name": tool_name, "tool_input": tool_input})


def _record(repo, gate):
    path = repo / ".pactkit" / "enforcement" / f"{gate}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _write_receipt(repo, story_id="STORY-x"):
    """Simulate an active preflight receipt for a story."""
    spec = repo / "docs" / "specs" / f"{story_id}.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("# spec\n", encoding="utf-8")
    receipt_dir = repo / ".pactkit" / "preflight" / story_id
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / "current.json").write_text(
        json.dumps({"story_id": story_id, "spec_sha256": "deadbeef"}), encoding="utf-8"
    )
    return spec


# ===========================================================================
# AC1: SessionStart context injection
# ===========================================================================


class TestSessionStart:
    def test_prints_regenerated_context(self, repo, monkeypatch):
        from pactkit import session_gate

        monkeypatch.setattr(
            session_gate, "generate_context", lambda root, **kw: "# CONTEXT\nSprint Status: 1 story"
        )
        text, code = session_gate.session_start_entry(repo)
        assert code == 0
        assert "Sprint Status" in text
        assert (repo / ".pactkit" / "context.md").exists()

    def test_generation_failure_degrades_to_warn(self, repo, monkeypatch):
        from pactkit import session_gate

        def _boom(root, **kw):
            raise RuntimeError("board unreadable")

        monkeypatch.setattr(session_gate, "generate_context", _boom)
        text, code = session_gate.session_start_entry(repo)
        assert code == 0
        assert "WARN" in text


# ===========================================================================
# AC2: PreCompact refresh never blocks
# ===========================================================================


class TestPreCompact:
    def test_refreshes_context_file(self, repo, monkeypatch):
        from pactkit import session_gate

        monkeypatch.setattr(
            session_gate, "generate_context", lambda root, **kw: "# refreshed"
        )
        text, code = session_gate.pre_compact_entry(repo)
        assert code == 0
        assert (repo / ".pactkit" / "context.md").read_text() == "# refreshed"

    def test_failure_still_exit_zero(self, repo, monkeypatch):
        from pactkit import session_gate

        def _boom(root, **kw):
            raise RuntimeError("nope")

        monkeypatch.setattr(session_gate, "generate_context", _boom)
        _, code = session_gate.pre_compact_entry(repo)
        assert code == 0  # compaction must never be blocked


# ===========================================================================
# AC3: spec_guard — Spec is Law during Act
# ===========================================================================


class TestSpecGuard:
    def test_edit_blocked_with_active_receipt(self, repo):
        spec = _write_receipt(repo, "STORY-x")
        stderr, code = hook_entry(
            _tool_payload("Edit", file_path=str(spec), old_string="a", new_string="b"),
            repo,
        )
        assert code == 2
        assert "Spec" in stderr
        assert _record(repo, "spec_guard") is not None

    def test_env_bypass_allows(self, repo, monkeypatch):
        spec = _write_receipt(repo, "STORY-x")
        monkeypatch.setenv("PACTKIT_ALLOW_SPEC_EDIT", "1")
        _, code = hook_entry(
            _tool_payload("Edit", file_path=str(spec), old_string="a", new_string="b"),
            repo,
        )
        assert code == 0

    def test_token_allows(self, repo):
        from pactkit import auth_gate

        spec = _write_receipt(repo, "STORY-x")
        auth_gate.authorize(repo, "spec_edit")
        _, code = hook_entry(
            _tool_payload("Edit", file_path=str(spec), old_string="a", new_string="b"),
            repo,
        )
        assert code == 0

    def test_no_receipt_allows_plan_phase_writing(self, repo):
        """Plan phase legitimately writes specs — no receipt exists yet."""
        spec = repo / "docs" / "specs" / "STORY-new.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text("# new spec\n", encoding="utf-8")
        _, code = hook_entry(
            _tool_payload("Edit", file_path=str(spec), old_string="a", new_string="b"),
            repo,
        )
        assert code == 0

    def test_bash_write_to_spec_blocked(self, repo):
        _write_receipt(repo, "STORY-x")
        _, code = hook_entry(_payload("sed -i 's/a/b/' docs/specs/STORY-x.md"), repo)
        assert code == 2


# ===========================================================================
# AC4: auth_gate — external-effect commands
# ===========================================================================


class TestAuthGate:
    @pytest.mark.parametrize(
        "command",
        [
            "gh release create v1.0.0",
            "gh pr create --title x",
            "gh release delete v1.0.0",
            "npm publish",
            "pnpm publish --access public",
            "cargo publish",
            "twine upload dist/*",
            "docker push org/app:1.0",
            "gh repo delete org/old-repo",
        ],
    )
    def test_external_effects_blocked(self, repo, command):
        stderr, code = hook_entry(_payload(command), repo)
        assert code == 2
        assert "authorize" in stderr
        assert _record(repo, "auth_gate") is not None

    @pytest.mark.parametrize(
        "command",
        [
            "gh pr view 12",
            "gh release list",
            "gh repo view org/repo",
            "npm run publish",
            "docker pull org/app:1.0",
        ],
    )
    def test_readonly_variants_pass(self, repo, command):
        _, code = hook_entry(_payload(command), repo)
        assert code == 0
        assert _record(repo, "auth_gate") is None

    def test_valid_token_allows(self, repo):
        from pactkit import auth_gate

        auth_gate.authorize(repo, "release")
        stderr, code = hook_entry(_payload("gh release create v1.0.0"), repo)
        assert code == 0

    def test_expired_token_blocks(self, repo):
        from pactkit import auth_gate

        auth_gate.authorize(repo, "release", ttl_minutes=-1)  # already expired
        stderr, code = hook_entry(_payload("gh release create v1.0.0"), repo)
        assert code == 2

    def test_wrong_scope_token_blocks(self, repo):
        from pactkit import auth_gate

        auth_gate.authorize(repo, "pr")
        _, code = hook_entry(_payload("gh release create v1.0.0"), repo)
        assert code == 2

    def test_env_bypass_allows(self, repo, monkeypatch):
        monkeypatch.setenv("PACTKIT_AUTHORIZED", "1")
        _, code = hook_entry(_payload("gh release create v1.0.0"), repo)
        assert code == 0

    def test_auth_gate_disabled_by_config(self, repo, monkeypatch):
        monkeypatch.setattr(
            commit_gate,
            "_enforcement_settings",
            lambda root: {
                "protected_branches": ["main"],
                "allow_direct_push": False,
                "tamper_guard": True,
                "spec_guard": True,
                "auth_gate": False,
                "secrets_gate": True,
                "auth_ttl_minutes": 30,
            },
        )
        _, code = hook_entry(_payload("gh release create v1.0.0"), repo)
        assert code == 0


# ===========================================================================
# AC5: secrets_gate — literal credentials
# ===========================================================================


class TestSecretsGate:
    @pytest.mark.parametrize(
        "command",
        [
            "curl -H 'Authorization: AKIAIOSFODNN7EXAMPLE' https://x",
            "psql 'postgres://u:pwd@h/db?password=Test@1234'",
            "openssl rsa -in key.pem  # -----BEGIN RSA PRIVATE KEY-----",
            "export API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456",
            "git clone https://glpat-abcdefghijklmnopqrst@gitlab.com/x",
            "curl -X POST -d 'token=xoxb-1234567890abcdef' https://slack.com",
        ],
    )
    def test_literal_credentials_blocked(self, repo, command):
        stderr, code = hook_entry(_payload(command), repo)
        assert code == 2
        assert _record(repo, "secrets_gate") is not None

    def test_env_bypass_allows(self, repo, monkeypatch):
        monkeypatch.setenv("PACTKIT_ALLOW_SECRET", "1")
        _, code = hook_entry(_payload("psql 'postgres://u:h/db?password=Test@1234'"), repo)
        assert code == 0

    def test_env_indirection_exempt(self, repo):
        _, code = hook_entry(_payload("psql 'postgres://u:h/db?password=$DB_PASS'"), repo)
        assert code == 0

    def test_clean_command_passes(self, repo):
        _, code = hook_entry(_payload("ls -la && git status"), repo)
        assert code == 0

    def test_disabled_by_config(self, repo, monkeypatch):
        monkeypatch.setattr(
            commit_gate,
            "_enforcement_settings",
            lambda root: {
                "protected_branches": ["main"],
                "allow_direct_push": False,
                "tamper_guard": True,
                "spec_guard": True,
                "auth_gate": True,
                "secrets_gate": False,
                "auth_ttl_minutes": 30,
            },
        )
        _, code = hook_entry(_payload("psql 'postgres://u:h/db?password=Test@1234'"), repo)
        assert code == 0


# ===========================================================================
# AC6: registration, config, doctor
# ===========================================================================


class TestRegistrationAndConfig:
    def test_install_registers_session_events(self, repo):
        install_hook(repo)
        settings = json.loads((repo / ".claude" / "settings.json").read_text())
        hooks = settings["hooks"]
        assert any(
            "session-start" in h.get("command", "")
            for e in hooks.get("SessionStart", []) for h in e.get("hooks", [])
        )
        assert any(
            "pre-compact" in h.get("command", "")
            for e in hooks.get("PreCompact", []) for h in e.get("hooks", [])
        )

    def test_install_idempotent(self, repo):
        install_hook(repo)
        install_hook(repo)
        settings = json.loads((repo / ".claude" / "settings.json").read_text())
        assert len(settings["hooks"]["SessionStart"]) == 1

    def test_codex_channel_has_no_session_events(self, repo):
        from pactkit.commit_gate import ensure_gate_channel

        (repo / ".git" / "hooks").mkdir(exist_ok=True)
        ensure_gate_channel(repo, "codex")
        payload = json.loads((repo / ".codex" / "hooks.json").read_text())
        assert "SessionStart" not in json.dumps(payload)
        assert "PreCompact" not in json.dumps(payload)

    def test_gates_registry_extended(self):
        from pactkit import enforcement

        for gate in ("spec_guard", "auth_gate", "secrets_gate"):
            assert gate in enforcement.GATES
            assert gate in enforcement._PROBES

    def test_enforcement_settings_defaults(self, tmp_path):
        from pactkit.commit_gate import _enforcement_settings

        settings = _enforcement_settings(tmp_path)  # no pactkit.yaml at all
        assert settings["spec_guard"] is True
        assert settings["auth_gate"] is True
        assert settings["secrets_gate"] is True
        assert settings["auth_ttl_minutes"] == 30

    def test_validator_rejects_bad_ttl(self):
        from pactkit.config import _validate_enforcement

        msgs = _validate_enforcement(
            "enforcement", {"auth_ttl_minutes": "30 minutes"}
        )
        assert any("auth_ttl_minutes" in m for m in msgs)

    def test_validator_accepts_new_keys(self):
        from pactkit.config import _validate_enforcement

        assert _validate_enforcement(
            "enforcement",
            {"spec_guard": False, "auth_gate": True, "secrets_gate": True,
             "auth_ttl_minutes": 10},
        ) == []

    def test_probe_reports_disabled(self, tmp_path, monkeypatch):
        from pactkit import enforcement

        (tmp_path / ".git").mkdir()
        monkeypatch.setattr(
            "pactkit.commit_gate._enforcement_settings",
            lambda root: {"secrets_gate": False},
        )
        probe = enforcement.probe_secrets_gate(tmp_path)
        assert probe["status"] == "unavailable"
        assert "secrets_gate" in probe["reason"]
