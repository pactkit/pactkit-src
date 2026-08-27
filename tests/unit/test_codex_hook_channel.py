"""STORY-slim-20260827024e71df170f R4/R5: codex native hooks thin registration.

AC7 deploy + trust notice + config.toml untouched, AC8 user-entry preservation,
AC9 doctor capability detection.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path



def _project(root: Path) -> None:
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "product").mkdir(parents=True)
    (root / "docs" / "product" / "sprint_board.md").write_text(
        "# Sprint Board\n", encoding="utf-8",
    )


class TestInstallCodexHook:
    def test_ac7_creates_hooks_json_with_pretooluse_entry(self, tmp_path):
        from pactkit.commit_gate import install_codex_hook

        _project(tmp_path)
        message = install_codex_hook(tmp_path)
        hooks_path = tmp_path / ".codex" / "hooks.json"
        assert hooks_path.is_file()
        payload = json.loads(hooks_path.read_text(encoding="utf-8"))
        groups = payload["hooks"]["PreToolUse"]
        assert any(
            g.get("matcher") == "Bash"
            and any("commit-gate" in h.get("command", "") for h in g["hooks"])
            for g in groups
        )
        # AC7: deploy output carries the trust-confirmation notice
        assert "trust" in message.lower()

    def test_ac7_never_touches_existing_config_toml(self, tmp_path):
        from pactkit.commit_gate import install_codex_hook

        _project(tmp_path)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir()
        config = codex_dir / "config.toml"
        config.write_text("[mcp_servers]\nuser = true\n", encoding="utf-8")
        before = hashlib.sha256(config.read_bytes()).hexdigest()
        install_codex_hook(tmp_path)
        assert hashlib.sha256(config.read_bytes()).hexdigest() == before

    def test_ac8_appends_to_user_hooks_json_preserving_entries(self, tmp_path):
        from pactkit.commit_gate import install_codex_hook

        _project(tmp_path)
        hooks_path = tmp_path / ".codex" / "hooks.json"
        hooks_path.parent.mkdir(parents=True)
        user_payload = {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Write", "hooks": [
                        {"type": "command", "command": "user-lint.sh"},
                    ]},
                ],
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "hello.sh"}]},
                ],
            },
        }
        hooks_path.write_text(json.dumps(user_payload), encoding="utf-8")

        install_codex_hook(tmp_path)
        payload = json.loads(hooks_path.read_text(encoding="utf-8"))
        # User entry and user event preserved verbatim
        assert payload["hooks"]["SessionStart"] == user_payload["hooks"]["SessionStart"]
        assert {"matcher": "Write", "hooks": [
            {"type": "command", "command": "user-lint.sh"},
        ]} in payload["hooks"]["PreToolUse"]
        # PactKit entry appended
        assert any(
            g.get("matcher") == "Bash"
            and any("commit-gate" in h.get("command", "") for h in g["hooks"])
            for g in payload["hooks"]["PreToolUse"]
        )

    def test_ac8_idempotent_refresh_of_own_entry(self, tmp_path):
        from pactkit.commit_gate import install_codex_hook

        _project(tmp_path)
        install_codex_hook(tmp_path)
        hooks_path = tmp_path / ".codex" / "hooks.json"
        first = hooks_path.read_text(encoding="utf-8")
        message = install_codex_hook(tmp_path)
        assert hooks_path.read_text(encoding="utf-8") == first
        assert "already" in message or "refreshed" in message or "installed" in message

    def test_invalid_hooks_json_left_untouched(self, tmp_path):
        from pactkit.commit_gate import install_codex_hook

        _project(tmp_path)
        hooks_path = tmp_path / ".codex" / "hooks.json"
        hooks_path.parent.mkdir(parents=True)
        hooks_path.write_text("{broken", encoding="utf-8")
        message = install_codex_hook(tmp_path)
        assert hooks_path.read_text(encoding="utf-8") == "{broken"
        assert "left untouched" in message

    def test_no_git_policy_skips(self, tmp_path):
        from pactkit.commit_gate import install_codex_hook

        _project(tmp_path)
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "pactkit.yaml").write_text(
            "enterprise:\n  no_git: true\n", encoding="utf-8",
        )
        message = install_codex_hook(tmp_path)
        assert "skipped" in message
        assert not (tmp_path / ".codex" / "hooks.json").exists()


class TestHookEntryCodexPayloads:
    def test_codex_string_command_blocks(self, tmp_path, monkeypatch):
        import pactkit.commit_gate as gate

        _project(tmp_path)
        monkeypatch.setattr(gate, "run_gate", lambda root: gate.GateResult(
            lines=["[FAIL] tests are RED"], exit_code=1,
        ))
        payload = json.dumps({
            "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'x'"}, "cwd": str(tmp_path),
        })
        message, exit_code = gate.hook_entry(payload, tmp_path)
        assert exit_code == 2
        assert "tests are RED" in message

    def test_codex_legacy_array_command_blocks(self, tmp_path, monkeypatch):
        import pactkit.commit_gate as gate

        _project(tmp_path)
        monkeypatch.setattr(gate, "run_gate", lambda root: gate.GateResult(
            lines=["[FAIL] tests are RED"], exit_code=1,
        ))
        payload = json.dumps({
            "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": ["git", "commit", "-m", "x"]},
        })
        _message, exit_code = gate.hook_entry(payload, tmp_path)
        assert exit_code == 2

    def test_non_git_command_allows(self, tmp_path):
        from pactkit.commit_gate import hook_entry

        _project(tmp_path)
        payload = json.dumps({
            "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        })
        message, exit_code = hook_entry(payload, tmp_path)
        assert exit_code == 0
        assert message == ""

    def test_payload_cwd_resolves_root(self, tmp_path, monkeypatch):
        import pactkit.commit_gate as gate

        _project(tmp_path)
        seen = {}

        def fake_run_gate(root):
            seen["root"] = root
            return gate.GateResult(lines=[], exit_code=0)

        monkeypatch.setattr(gate, "run_gate", fake_run_gate)
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        payload = json.dumps({
            "tool_input": {"command": "git commit"}, "cwd": str(elsewhere),
        })
        gate.hook_entry(payload, tmp_path)
        assert seen["root"] == elsewhere


class TestEnsureGateChannel:
    def test_codex_format_installs_hooks_json(self, tmp_path):
        from pactkit.commit_gate import ensure_gate_channel

        _project(tmp_path)
        channel = ensure_gate_channel(tmp_path, "codex")
        assert (tmp_path / ".codex" / "hooks.json").is_file()
        assert "codex" in channel.lower()

    def test_gate_channel_reports_codex_hook(self, tmp_path):
        from pactkit.commit_gate import ensure_gate_channel, gate_channel

        _project(tmp_path)
        ensure_gate_channel(tmp_path, "codex")
        assert "codex" in gate_channel(tmp_path).lower()


class TestDoctorCodexHookCapability:
    def test_engine_unavailable_without_binary(self, tmp_path, monkeypatch):
        import pactkit.doctor as doctor_module

        monkeypatch.setattr(doctor_module, "_codex_cli_version", lambda: None)
        capability = doctor_module.check_codex_hook_capability(tmp_path)
        assert capability["engine"] == "unavailable"
        assert capability["hooks_json"] == "absent"

    def test_ac9_reports_engine_and_deployment(self, tmp_path, monkeypatch):
        import pactkit.doctor as doctor_module
        from pactkit.commit_gate import install_codex_hook

        monkeypatch.setattr(doctor_module, "_codex_cli_version", lambda: "0.149.1")
        _project(tmp_path)
        install_codex_hook(tmp_path)
        capability = doctor_module.check_codex_hook_capability(tmp_path)
        assert capability["engine"] == "available"
        assert capability["codex_version"] == "0.149.1"
        assert capability["hooks_json"] == "deployed"
        assert capability["entry_present"] is True

    def test_ac9_old_version_reports_unavailable(self, tmp_path, monkeypatch):
        import pactkit.doctor as doctor_module

        monkeypatch.setattr(doctor_module, "_codex_cli_version", lambda: "0.100.0")
        capability = doctor_module.check_codex_hook_capability(tmp_path)
        assert capability["engine"] == "unavailable"
        assert "0.114" in " ".join(capability["warnings"])

    def test_doctor_json_includes_codex_hooks(self, tmp_path, monkeypatch):
        import pactkit.doctor as doctor_module

        monkeypatch.setattr(doctor_module, "_codex_cli_version", lambda: "0.149.1")
        _project(tmp_path)
        import subprocess

        proc = subprocess.run(
            ["python3", "-m", "pactkit", "-C", str(tmp_path), "doctor", "--json"],
            capture_output=True, text=True, cwd=tmp_path, timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout)
        assert "codex_hooks" in payload
        assert payload["codex_hooks"]["engine"] == "available"
