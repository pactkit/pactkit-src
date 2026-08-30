"""STORY-slim-20260830c65491123af1: gate telemetry truthfulness + redaction.

Covers AC1-AC5 of docs/specs/STORY-slim-20260830c65491123af1.md:

  AC1  credentials redacted before persistence (record + event + stderr)
  AC2  authorization_asked/granted events from gates, visible in stats
  AC3  gate_blocked events aggregated per gate
  AC4  Skill-matcher command_invoked telemetry
  AC5  one-time scrub of legacy records via pactkit clean
"""

import json

import pytest

from pactkit import commit_gate
from pactkit.commit_gate import hook_entry
from pactkit.secrets_gate import redact_command


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


def _payload(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def _skill_payload(command):
    return json.dumps({"tool_name": "Skill", "tool_input": {"command": command}})


def _gate_events(repo):
    path = repo / ".pactkit" / "events" / "gates.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def _enforcement(repo, gate):
    path = repo / ".pactkit" / "enforcement" / f"{gate}.json"
    return json.loads(path.read_text()) if path.exists() else None


# ===========================================================================
# AC1: redaction before persistence
# ===========================================================================


class TestRedaction:
    def test_redact_command_replaces_credentials(self):
        redacted = redact_command("PGPASSWORD=s3cret psql -h localhost -U chatbi")
        assert "s3cret" not in redacted
        assert "[REDACTED:password-literal]" in redacted
        assert "-U chatbi" in redacted  # username is not a credential, survives
        assert "psql -h localhost" in redacted  # non-secret text survives

    def test_redact_command_multiple_kinds(self):
        redacted = redact_command("curl -H 'x: AKIAIOSFODNN7EXAMPLE' https://a?password=sec1")
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "sec1" not in redacted
        assert "[REDACTED:aws-access-key]" in redacted

    def test_clean_command_unchanged(self):
        assert redact_command("ls -la && git status") == "ls -la && git status"

    def test_block_record_and_event_are_redacted(self, repo):
        command = "PGPASSWORD=chatbi psql -h localhost -c 'SELECT 1'"
        stderr, code = hook_entry(_payload(command), repo)
        assert code == 2
        record = _enforcement(repo, "secrets_gate")
        assert "chatbi" not in json.dumps(record)
        assert "[REDACTED:password-literal]" in record["reason"]
        events_text = (repo / ".pactkit" / "events" / "gates.jsonl").read_text()
        assert "chatbi" not in events_text
        assert "[REDACTED:password-literal]" in events_text

    def test_stderr_names_kind_without_literal(self, repo):
        stderr, _ = hook_entry(_payload("PGPASSWORD=chatbi psql -h localhost"), repo)
        assert "chatbi" not in stderr
        assert "password-literal" in stderr

    def test_auth_block_reason_redacted(self, repo):
        stderr, code = hook_entry(
            _payload("docker push org/app --password=supersecret1"), repo
        )
        assert code == 2
        record = _enforcement(repo, "auth_gate")
        assert "supersecret1" not in json.dumps(record)
        assert "chatbi" not in json.dumps(record)


# ===========================================================================
# AC2: authorization events from gates
# ===========================================================================


class TestAuthorizationEvents:
    def test_block_emits_asked(self, repo):
        hook_entry(_payload("gh release create v1.0.0"), repo)
        events = _gate_events(repo)
        assert any(e["event"] == "authorization_asked" for e in events)

    def test_authorize_emits_granted(self, repo):
        from pactkit import auth_gate

        auth_gate.authorize(repo, "release")
        events = _gate_events(repo)
        assert any(e["event"] == "authorization_granted" for e in events)

    def test_stats_counts_the_pair(self, repo):
        from pactkit import auth_gate
        from pactkit.run_stats import collect_gate_telemetry

        hook_entry(_payload("gh release create v1.0.0"), repo)
        auth_gate.authorize(repo, "release")
        telemetry = collect_gate_telemetry(repo)
        assert telemetry["authorization_decisions"]["asked"] >= 1
        assert telemetry["authorization_decisions"]["granted"] >= 1

    def test_json_report_includes_gate_telemetry(self, repo):
        from pactkit import auth_gate
        from pactkit.run_stats import collect_gate_telemetry, json_report

        hook_entry(_payload("gh release create v1.0.0"), repo)
        auth_gate.authorize(repo, "release")
        report = json_report([], collect_gate_telemetry(repo))
        gt = report["gate_telemetry"]
        assert gt["authorization_decisions"]["asked"] >= 1
        assert gt["authorization_decisions"]["granted"] >= 1


# ===========================================================================
# AC3: gate_blocked per-gate counting
# ===========================================================================


class TestGateBlockedEvents:
    def test_per_gate_counts(self, repo):
        from pactkit.run_stats import collect_gate_telemetry

        hook_entry(_payload("PGPASSWORD=chatbi1 psql -h localhost"), repo)
        hook_entry(_payload("PGPASSWORD=chatbi2 psql -h localhost"), repo)
        hook_entry(_payload("gh release create v1.0.0"), repo)
        telemetry = collect_gate_telemetry(repo)
        assert telemetry["gate_blocks"]["secrets_gate"] == 2
        assert telemetry["gate_blocks"]["auth_gate"] == 1

    def test_push_block_emits_event(self, repo, monkeypatch):
        from pactkit.run_stats import collect_gate_telemetry

        monkeypatch.setattr(commit_gate, "current_branch", lambda root: "main")
        monkeypatch.setattr(commit_gate, "collect_changed_files", lambda root: [])
        monkeypatch.setattr(commit_gate, "run_pytest", lambda root, tf: (0, "1 passed"))
        _, code = hook_entry(_payload("git push origin main"), repo)
        assert code == 2
        telemetry = collect_gate_telemetry(repo)
        assert telemetry["gate_blocks"]["push_gate"] == 1


# ===========================================================================
# AC4: Skill-invocation telemetry
# ===========================================================================


class TestSkillTelemetry:
    def test_skill_invocation_recorded(self, repo):
        stderr, code = hook_entry(_skill_payload("project-plan"), repo)
        assert code == 0
        events = _gate_events(repo)
        assert any(
            e["event"] == "command_invoked" and e["detail"]["command"] == "project-plan"
            for e in events
        )

    def test_stats_counts_commands(self, repo):
        from pactkit.run_stats import collect_gate_telemetry

        hook_entry(_skill_payload("project-plan"), repo)
        hook_entry(_skill_payload("project-plan"), repo)
        hook_entry(_skill_payload("project-act"), repo)
        telemetry = collect_gate_telemetry(repo)
        assert telemetry["command_invocations"]["project-plan"] == 2
        assert telemetry["command_invocations"]["project-act"] == 1

    def test_install_registers_skill_matcher(self, repo):
        from pactkit.commit_gate import install_hook

        install_hook(repo)
        settings = json.loads((repo / ".claude" / "settings.json").read_text())
        matchers = {e["matcher"] for e in settings["hooks"]["PreToolUse"]}
        assert "Skill" in matchers


# ===========================================================================
# AC5: one-time scrub of legacy records
# ===========================================================================


class TestLegacyScrub:
    def test_clean_scrubs_credential_in_reason(self, repo):
        from pactkit.cleaners import scrub_enforcement_records

        path = repo / ".pactkit" / "enforcement" / "secrets_gate.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            "gate": "secrets_gate", "status": "full",
            "reason": "blocked: password-literal in 'PGPASSWORD=chatbi psql -h localhost'",
            "ts": "2026-08-29T04:35:10+00:00",
        }))
        scrub_enforcement_records(repo)
        record = json.loads(path.read_text())
        assert "chatbi" not in record["reason"]
        assert "[REDACTED:password-literal]" in record["reason"]
        assert record["ts"] == "2026-08-29T04:35:10+00:00"  # rest intact

    def test_clean_leaves_clean_records_untouched(self, repo):
        from pactkit.cleaners import scrub_enforcement_records

        path = repo / ".pactkit" / "enforcement" / "push_gate.json"
        path.parent.mkdir(parents=True)
        original = json.dumps({
            "gate": "push_gate", "status": "full",
            "reason": "target 'develop' not protected", "ts": "2026-08-30T03:00:00+00:00",
        })
        path.write_text(original)
        scrub_enforcement_records(repo)
        assert path.read_text() == original

    def test_corrupt_json_ignored(self, repo):
        from pactkit.cleaners import scrub_enforcement_records

        path = repo / ".pactkit" / "enforcement" / "bad.json"
        path.parent.mkdir(parents=True)
        path.write_text("{oops")
        scrub_enforcement_records(repo)  # must not raise
        assert path.read_text() == "{oops"
